from typing import Any, AsyncGenerator, Dict, Iterable, List

from cohere import ChatSearchQuery, ChatSearchResult, ChatSearchResultConnector, ChatbotMessage, SearchResultsStreamedChatResponse, StreamStartStreamedChatResponse
from openai import OpenAI

import asyncio
import logging

from backend.model_deployments.base import BaseDeployment
from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.context import Context
from backend.config.settings import Settings
from backend.model_deployments.utils import get_model_config_var
from backend.chat.collate import to_dict
from backend.services.openai_cohere_conveter import CohereToOpenAI
from backend.schemas.chat import ChatRole, ChatMessage
# Set up logging
logger = logging.getLogger(__name__)
import uuid

from openai.types.chat.completion_create_params import CompletionCreateParamsBase
from openai.types.completion_create_params import CompletionCreateParams


OPENAI_URL_ENV_VAR = "OPENAI_ENDPOINT_URL"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_DEFAULT_MODEL_ENV_VAR = "OPENAI_DEFAULT_MODEL"

OPENAI_ENV_VARS = [OPENAI_API_KEY_ENV_VAR, OPENAI_URL_ENV_VAR, OPENAI_DEFAULT_MODEL_ENV_VAR]

class OpenAIDeployment(BaseDeployment):
    """
    OpenAI Deployment class using the OpenAI SDK.
    Handles chat and model invocations using an OpenAI-compatible API.
    """

    # DEFAULT_MODELS = ["openai/yejingfu_Meta-Llama-3.1-8B-Instruct-FP8-128K"]  # Update with compatible models if needed
    
    openai_config = Settings().deployments.openai 
    default_api_key = openai_config.api_key 
    default_endpoint = openai_config.endpoint_url 
    default_model = openai_config.default_model
    openai = OpenAI(
        api_key=default_api_key,
        base_url=default_endpoint,
    )
    def __init__(self, **kwargs: Any):
        # Override environment variables or use defaults from config
        self.api_key = get_model_config_var(
            OPENAI_API_KEY_ENV_VAR, OpenAIDeployment.default_api_key, **kwargs 
        )
        self.endpoint_url = get_model_config_var(
            OPENAI_URL_ENV_VAR, OpenAIDeployment.default_endpoint, **kwargs 
        )
        
        # Configure the OpenAI SDK with the API key and base URL if available
        self.openai = OpenAI(
            api_key=self.api_key,
            base_url=self.endpoint_url,
        )

    @property
    def rerank_enabled(self) -> bool:
        # OpenAI-compatible models typically do not support reranking directly
        return False

    @classmethod
    def list_models(cls) -> List[str]: 
        """List available models."""
        if not cls.is_available():
            return []
        try:
            models_list = [model.id for model in cls.openai.models.list().data]
        except Exception as e:
            models_list = []
            
        if (len(models_list) == 0):
            if cls.default_model:
                return [cls.default_model]
            else:
                return []        
        
        return models_list

    @classmethod
    def is_available(cls) -> bool: 
        """Check if the deployment is available based on the API key."""
        return cls.default_api_key is not None

    async def invoke_chat(self, chat_request: Any) -> Any: 
        """Invoke chat completion using the OpenAI-compatible API."""
        try:
            response = await asyncio.to_thread(
                self.openai.chat.completions.create,
                model=chat_request.model,
                messages=chat_request.model_dump(exclude={"stream", "file_ids", "agent_id"})["messages"],
                # extra_body={"options": {"num_ctx": 128000}},
                stream=False
            )
            return to_dict(response)
        except Exception as e:
            logger.error(f"Error invoking chat: {e}")
            raise

    
  
    async def invoke_chat_stream(
        self, chat_request: CohereChatRequest, ctx: Context, **kwargs: Any
    ) -> AsyncGenerator[Any, Any]:
        
        build_template = True
        
        """Invoke chat stream using the OpenAI-compatible API."""
        generation_id = uuid.uuid4().hex
        
        appended_user_message = False
        first_request_is_sent = False
        function_triggered = 'none'
        full_previous_response = ''
        result_sent = False

        if not appended_user_message and chat_request.message:
            user_message = ChatMessage(role=ChatRole.USER, message=chat_request.message)
            if chat_request.chat_history and len(chat_request.chat_history) > 0:
                chat_request.chat_history.append(user_message)
            else:
                chat_request.chat_history = [user_message]
            appended_user_message = True

        if build_template:
            openAi_chat_request = CohereToOpenAI.cohere_to_openai_completion_request_body(chat_request)
            try:
                stream = await asyncio.wait_for(asyncio.to_thread(
                    self.openai.completions.create,
                    **openAi_chat_request,
                    stream=True
                ), timeout=30)  # Set a timeout of 30 seconds
                logger.info("Successfully initiated OpenAI completion stream")
            except asyncio.TimeoutError:
                logger.error("Timeout while waiting for OpenAI completions")
                raise
            except Exception as e:
                logger.error(f"Failed to initiate OpenAI completions: {e}")
                raise
                
        else:
            openAi_chat_request = CohereToOpenAI.cohere_to_openai_chat_request_body(chat_request)
            try:
                stream = await asyncio.wait_for(asyncio.to_thread(
                    self.openai.chat.completions.create,
                    **openAi_chat_request,
                    stream=True
                ), timeout=30)  # Set a timeout of 30 seconds
                logger.info("Successfully initiated OpenAI chat stream")
            except asyncio.TimeoutError:
                logger.error("Timeout while waiting for OpenAI chat stream")
                raise
            except Exception as e:
                logger.error(f"Failed to initiate OpenAI chat stream: {e}")
                raise
                
        logger.debug("==============================================")
        logger.debug(f"Cohere Original chat request: {chat_request}")
        logger.debug("==============================================")
        logger.debug(f"OpenAI chat request: {openAi_chat_request}")
        logger.debug("==============================================")

        try:
            if stream:
                logger.info("OpenAI chat stream started")
                for event in stream:
                    logger.debug(f"Received event: {event}")  # Log each event received

                    # Extract the message from the event
                    event_dict = event.model_dump(serialize_as_any=True)
                    print("Event Dict: ", event_dict)
                    stream_message = ""
                    finish_reason = None
                    delta = None
                    if build_template:
                        if event.choices:
                            stream_message = event.choices[0].text
                            finish_reason = event.choices[0].finish_reason
                            delta = getattr(event.choices[0], 'delta', None)
                        elif event.content:
                            stream_message = event.content
                            print('======== event_dict.get("stop")', event_dict['stop'])
                            if event_dict['stop']:
                                finish_reason = "stop" 
                    else:
                        stream_message = event.choices[0].delta.content
                        finish_reason = event.choices[0].finish_reason
                        delta = getattr(event.choices[0], 'delta', None)
                    
                    if stream_message:
                        full_previous_response += stream_message

                    if function_triggered != 'calling':
                        print("==================================")
                        print("OpenAi_Event: ", event)
                        cohere_events = CohereToOpenAI.openai_to_cohere_event_chunk(event=event, previous_response=full_previous_response, function_triggered=function_triggered, chat_request=chat_request, build_template=build_template, stream_message=stream_message, finish_reason=finish_reason, delta=delta, generation_id=generation_id)
                        print("cohere_events: ", cohere_events)
                        print("==================================")
                    else:
                        cohere_events = []

                    if cohere_events and len(cohere_events) > 0:
                        for cohere_event in cohere_events:
                            if (cohere_event.event_type == "tool-calls-generation" or cohere_event.event_type == "tool-calls-chunk"):
                                function_triggered = "calling"
                                if cohere_event.event_type == "tool-calls-generation" and cohere_event.tool_calls and len(cohere_event.tool_calls) > 0:
                                    for tool_call in cohere_event.tool_calls:
                                        tool_call_dict = {f"{str(tool_call.name)}": tool_call.parameters}
                                        tool_call_message = ChatMessage(role=ChatRole.CHATBOT, message="I'm calling a system tool to retrieve information", tool_calls=[tool_call_dict])
                                        if chat_request.chat_history and len(chat_request.chat_history) > 0:
                                            chat_request.chat_history.append(tool_call_message)
                                        else:
                                            chat_request.chat_history = [tool_call_message]

                            if not first_request_is_sent:
                                stream_start = StreamStartStreamedChatResponse(event_type="stream-start", generation_id=generation_id)
                                yield to_dict(stream_start)

                            yield to_dict(cohere_event)

                    if chat_request.tool_results and not result_sent:
                        for tool_result in chat_request.tool_results:
                            if chat_request.tool_results and len(chat_request.tool_results):
                                output_str = CohereToOpenAI.clean_string(str(tool_result))
                                chat_search_query = ChatSearchQuery(text=output_str, generation_id=generation_id)
                                connector = ChatSearchResultConnector(id="")
                                search_result = ChatSearchResult(document_ids=chat_request.file_ids or [], search_query=chat_search_query, connector=connector)
                                search_event = SearchResultsStreamedChatResponse(event_type="search-results", documents=[], search_results=[search_result])
                                result_sent = True
                                yield to_dict(search_event)
            else:
                logger.error("Stream is undefined")
        except Exception as e:
            logger.error(f"Error invoking chat stream: {e}")
            logger.error(f"Chat request: {chat_request}")
            logger.error(f"OpenAI chat request: {openAi_chat_request}")
            raise

    async def invoke_rerank(
        self, query: str, documents: List[Dict[str, Any]], ctx: Context, **kwargs: Any
    ) -> Any:
        """Rerank is not supported for OpenAI in this context."""
        return None



