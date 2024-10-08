from typing import Iterable, List, Dict, Any, Optional, Union

from cohere import NonStreamedChatResponse
from openai.types.chat.completion_create_params import CompletionCreateParamsBase
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam,ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionChunk, ChatCompletionToolParam

from backend.schemas.cohere_chat import CohereChatRequest
from cohere.types import StreamedChatResponse,  StreamStartStreamedChatResponse,SearchQueriesGenerationStreamedChatResponse,SearchResultsStreamedChatResponse,TextGenerationStreamedChatResponse,CitationGenerationStreamedChatResponse,ToolCallsGenerationStreamedChatResponse,StreamEndStreamedChatResponse,ToolCallsChunkStreamedChatResponse, ToolCallsChunkStreamedChatResponse, Tool

# Assuming CohereChatRequest class is defined above as provided.
class CohereToOpenAI:
    
    # def __init__(self):
    @staticmethod
    def cohere_to_openai_event_chunk(event: ChatCompletionChunk) -> StreamedChatResponse:
        print("OllamaChunk: ",event)
        if (event.choices[0].finish_reason == "tool_calls" or event.choices[0].finish_reason == "function_call" or event.choices[0].delta.tool_calls or event.choices[0].delta.function_calls):
            return ToolCallsChunkStreamedChatResponse(event_type = "tool_call_delta", tool_call_delta=event.choices[0].delta.tool_calls)

        elif event.choices[0].finish_reason == "stop":
            response = NonStreamedChatResponse(text=event.choices[0].delta.content or '')
            return StreamEndStreamedChatResponse(event_type = "stream-end",finish_reason="COMPLETE", response=response)
        else:
            return TextGenerationStreamedChatResponse(event_type = "text-generation", text=event.choices[0].delta.content or '')
        
    @staticmethod
    def cohere_to_openai_request_body(cohere_request: CohereChatRequest) -> CompletionCreateParamsBase:
        # Start with the new user message
        messages: Iterable[ChatCompletionMessageParam] = []
        # system_message: ChatCompletionSystemMessageParam = {
            
        # }
        user_message: ChatCompletionUserMessageParam = {
                "role": "user",
                "content": cohere_request.message,
            }
        
        
        # Add chat history if it exists
        if cohere_request.chat_history:
            for chat_entry in cohere_request.chat_history:
                if (chat_entry.message and chat_entry.role):
                    msg: ChatCompletionMessageParam = ChatCompletionAssistantMessageParam(
                        role= chat_entry.role.lower(), # type: ignore
                        content=chat_entry.message
                    )
                        
                    messages.append(msg) # type: ignore

        messages.append(user_message)
        # Construct the OpenAI request parameters
        openai_request = CompletionCreateParamsBase(
            messages=messages,
            model=cohere_request.model, # type: ignore
            max_tokens=cohere_request.max_tokens,
            temperature=cohere_request.temperature,
            frequency_penalty=cohere_request.frequency_penalty,
            presence_penalty=cohere_request.presence_penalty,
            stop=cohere_request.stop_sequences,
            tools=CohereToOpenAI.convert_tool(cohere_request.tools),
            functions=[],
        )
        
        
        return openai_request
   
    @staticmethod
    def convert_tool(tools: List[Tool]) -> List[ChatCompletionToolParam]:
        open_ai_tools: List[ChatCompletionToolParam] = []
        
        for tool in tools:
            oai_tool = ChatCompletionToolParam(
             type="function",
             function={
                 "name": tool.name,
                 "description": tool.description,
                 "parameters": tool.parameter_definitions,
             }   
            )
            open_ai_tools.append(oai_tool)
        return open_ai_tools
                         
                         