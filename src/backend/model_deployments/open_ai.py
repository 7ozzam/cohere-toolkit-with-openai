from typing import Any, AsyncGenerator, Dict, Iterable, List

from cohere import ChatSearchQuery, ChatSearchResult, ChatSearchResultConnector, ChatbotMessage, SearchResultsStreamedChatResponse, StreamStartStreamedChatResponse, ChatDocument

from backend.schemas.chat import SearchQuery
from backend.schemas.chat_native import StreamSearchResults, StreamStart
from cohere import ChatSearchResult, ChatSearchResultConnector
from fastapi import Depends
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
from backend.chat.enums import StreamEvent
from backend.schemas.document import Document
from backend.services.file import get_file_service
from backend.database_models.database import DBSessionDep, get_session
from backend.services.context import Context, get_context

# Set up logging
logger = logging.getLogger(__name__)
import uuid

from openai.types.chat.completion_create_params import CompletionCreateParamsBase
from openai.types.completion_create_params import CompletionCreateParams


OPENAI_URL_ENV_VAR = "OPENAI_ENDPOINT_URL"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_DEFAULT_MODEL_ENV_VAR = "OPENAI_DEFAULT_MODEL"
OPENAI_DEFAULT_USE_LEGACY_API_ENV_VAR = "OPENAI_DEFAULT_USE_LEGACY_API"

OPENAI_ENV_VARS = [OPENAI_API_KEY_ENV_VAR, OPENAI_URL_ENV_VAR, OPENAI_DEFAULT_MODEL_ENV_VAR, OPENAI_DEFAULT_USE_LEGACY_API_ENV_VAR]

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
    default_use_legacy_api = openai_config.default_use_legacy_api
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
    def list_models(cls) -> List[Any]: 
        """List available models."""
        if not cls.is_available():
            return []
        try:
            models = cls.openai.models.list().data
            models_list = [model.to_dict().get("id") for model in models]
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
            # Append user message if needed
            appended_user_message = False
            if not appended_user_message and chat_request.message:
                user_message = ChatMessage(role=ChatRole.USER, message=chat_request.message)
                if chat_request.chat_history and len(chat_request.chat_history) > 0:
                    chat_request.chat_history.append(user_message)
                else:
                    chat_request.chat_history = [user_message]
                appended_user_message = True

            # Prepare request body
            openAi_chat_request = CohereToOpenAI.cohere_to_openai_chat_request_body(chat_request)

            # Invoke OpenAI API for non-streamed response
            response = await asyncio.to_thread(
                self.openai.chat.completions.create,
                **openAi_chat_request,
                stream=False
            )

            # Extract and process the response
            response_dict = to_dict(response)
            full_message = ""

            # Process response content
            choices = response_dict.get("choices", [])
            if choices and len(choices) > 0:
                full_message = choices[0].get("message", {}).get("content", "")

            # Construct final output
            if full_message:
                print("Full Response Message: ", full_message)
                return {"message": full_message, "raw_response": response_dict}

            # Log and raise an error if no message is present
            logger.error("No message content found in the response")
            raise ValueError("Invalid response: Missing content")

        except Exception as e:
            logger.error(f"Error invoking chat: {e}")
            raise


    
  
    async def invoke_chat_stream(
        self, chat_request: CohereChatRequest, ctx: Context, **kwargs: Any
    ) -> AsyncGenerator[Any, Any]:
        
        session = kwargs.get("session")
        print("Default use legacy API: ", self.default_use_legacy_api)
        build_template = self.default_use_legacy_api
        
        """Invoke chat stream using the OpenAI-compatible API."""
        generation_id = uuid.uuid4().hex
        # conversation_id = chat_request.conversation_id
        
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
            print("==============================================")
            print(f"Cohere Original chat request: {chat_request}")
            print("==============================================")
            print(f"OpenAI chat request: {openAi_chat_request}")
            print("==============================================")
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
                
        print("==============================================")
        print(f"Cohere Original chat request: {chat_request}")
        print("==============================================")
        print(f"OpenAI chat request: {openAi_chat_request}")
        print("==============================================")

        try:
            if stream:
                logger.info("OpenAI chat stream started")
                for event in stream:
                    print(f"Received event: {event}")  # Log each event received

                    # Attempt to convert event to a dictionary
                    try:
                        event_dict: Any = event.model_dump(serialize_as_any=False)
                    except Exception as e:
                        logger.error(f"Failed to convert event to dict: {e}")
                        event_dict = {}

                    print("Event Dict: ", event_dict)
                    stream_message = ""
                    finish_reason = None
                    delta = None

                    if build_template:
                        choices = event_dict.get("choices", [])
                        if choices and len(choices) > 0:
                            print("I'm in Choices Condition")
                            stream_message = choices[0].get("text", "")
                            finish_reason = choices[0].get("finish_reason", "")
                            delta = choices[0].get('delta', None)

                        content = event_dict.get("content")
                        if content is not None:
                            print("I'm in Content Condition")
                            stream_message = content
                            stop_signal = event_dict.get('stop')
                            if stop_signal:
                                finish_reason = "stop"
                    else:
                        choices = getattr(event, 'choices', [])
                        if choices and len(choices) > 0:
                            stream_message = getattr(choices[0].delta, 'content', "")
                            finish_reason = getattr(choices[0], 'finish_reason', "")
                            delta = getattr(choices[0], 'delta', None)

                    
                    if stream_message:
                        full_previous_response += stream_message

                    if function_triggered != 'calling':
                        print("==================================")
                        print("OpenAi_Event: ", event)
                        cohere_events = CohereToOpenAI.openai_to_cohere_event_chunk(event=event, previous_response=full_previous_response, function_triggered=function_triggered, chat_request=chat_request, build_template=build_template, stream_message=stream_message, finish_reason=finish_reason, delta=delta, generation_id=generation_id, ctx=ctx)
                        
                        print("cohere_events: ", cohere_events)
                        print("==================================")
                    else:
                        cohere_events = []

                    if cohere_events and len(cohere_events) > 0:
                                    
                        for cohere_event in cohere_events:
                            if cohere_event.event_type == StreamEvent.INLINE_FIX and cohere_event.text and "REMOVE" in cohere_event.text:
                                to_remove = cohere_event.text.replace("REMOVE", "")  # Strip any leading/trailing spaces
                                print("BEFORE REMOVED TOOL CALL", full_previous_response)
                                print("REMOVING", f"""{to_remove}""")
                                
                                # Check if the text to remove exists in the previous response before attempting to replace
                                if to_remove in full_previous_response:
                                    full_previous_response = full_previous_response.replace(f"""{to_remove}""", "")
                                    print("REMOVED TOOL CALL", full_previous_response)
                                else:
                                    print(f"Text '{to_remove}' not found in the previous response.")

                                
                            if (cohere_event.event_type == StreamEvent.TOOL_CALLS_GENERATION or cohere_event.event_type == StreamEvent.TOOL_CALLS_CHUNK):
                                function_triggered = "calling"
                                    
                                    
                                if cohere_event.event_type == StreamEvent.TOOL_CALLS_GENERATION and cohere_event.tool_calls and len(cohere_event.tool_calls) > 0:
                                    for tool_call in cohere_event.tool_calls:
                                        
                                        tool_call_dict = {f"{str(tool_call.name)}": tool_call.parameters}
                                        
                                        
                                        
                                        
                                        tool_call_message = ChatMessage(role=ChatRole.CHATBOT, message="I'm calling a system tool to retrieve information", tool_calls=[tool_call_dict])
                                        if chat_request.chat_history and len(chat_request.chat_history) > 0:
                                            chat_request.chat_history.append(tool_call_message)
                                        else:
                                            chat_request.chat_history = [tool_call_message]

                            if not first_request_is_sent:
                                stream_start = StreamStart(event_type=StreamEvent.STREAM_START, generation_id=generation_id)
                                yield to_dict(stream_start)

                            yield to_dict(cohere_event)

                    if chat_request.tool_results and not result_sent:
                        if chat_request.tool_results and len(chat_request.tool_results):
                            print("Original tool results: ", chat_request.tool_results)
                            
                            for result in chat_request.tool_results:
                                tool_call = dict(result['call'])
                                tool_call_parameters = dict(tool_call['parameters'])
                                file_ids = tool_call_parameters.get('file_ids')
                                output_str = CohereToOpenAI.process_tool_result_entry_as_text(chat_request.tool_results)
                                search_result,search_event = self.process_tool_result_event(output_str=output_str, generation_id=generation_id, file_ids=file_ids, ctx=ctx)
                                
                                # chat_request.search_results.append(dict(search_result))
                                result_sent = True
                                yield to_dict(search_event)
                                  
                            # output_str = CohereToOpenAI.process_tool_results_as_text(tool_results=chat_request.tool_results)
                            # if output_str and len(output_str) > 0:
                            #     search_event = self.process_tool_result_event(output_str=output_str, generation_id=generation_id, file_ids=chat_request.file_ids, ctx=ctx)
                            #     result_sent = True
                            #     yield to_dict(search_event)
            else:
                logger.error("Stream is undefined")
        except Exception as e:
            logger.error(f"Error invoking chat stream: {e}")
            logger.error(f"Chat request: {chat_request}")
            logger.error(f"OpenAI chat request: {openAi_chat_request}")
            raise

    @staticmethod
    def process_tool_result_event(generation_id: str,file_ids=None, output_str="", tool_calls: Dict[str, Any] = None, ctx: Context = Depends(get_context)):
        
        chat_search_query = ChatSearchQuery(text=output_str, generation_id=generation_id)
        connector = ChatSearchResultConnector(id="")
        search_result = ChatSearchResult(document_ids=file_ids or [], search_query=chat_search_query, connector=connector)
        
        with next(get_session()) as db:
            file_service = get_file_service()
            files = file_service.get_files_by_ids( files_ids=file_ids or [], ctx=ctx, session=db)
            
            documents = [Document(id=file.id, text=file.file_content, title=file.file_name) for file in files]

        # document: ChatDocument = {"text": output_str, "title": } 
        search_event = StreamSearchResults(event_type=StreamEvent.SEARCH_RESULTS, documents=documents, search_results=[dict(search_result)])
        
        return search_result, search_event
    
    async def invoke_rerank(
        self, query: str, documents: List[Dict[str, Any]], ctx: Context, **kwargs: Any
    ) -> Any:
        """Rerank is not supported for OpenAI in this context."""
        return None



