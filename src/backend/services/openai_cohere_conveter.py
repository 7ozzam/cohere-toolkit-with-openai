from typing import Iterable, List, Dict, Any, Optional, Union

from cohere import NonStreamedChatResponse
from openai.types.chat.completion_create_params import CompletionCreateParamsBase
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam,ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionChunk, ChatCompletionToolParam, ChatCompletionMessageToolCallParam
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types import FunctionParameters
from openai.types.chat.chat_completion_message_tool_call_param import Function as OpenAIFunction

from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.chat import ChatRole
from cohere.types import StreamedChatResponse,  StreamStartStreamedChatResponse,SearchQueriesGenerationStreamedChatResponse,SearchResultsStreamedChatResponse,TextGenerationStreamedChatResponse,CitationGenerationStreamedChatResponse,ToolCallsGenerationStreamedChatResponse,StreamEndStreamedChatResponse,ToolCallsChunkStreamedChatResponse, ToolCallsChunkStreamedChatResponse, ToolCallDelta, ToolParameterDefinitionsValue, ToolCall, Message, ChatbotMessage, UserMessage, ToolMessage, SystemMessage, ChatMessage

from cohere.types import Tool as CohereTool
from backend.schemas.tool import Tool as BackendTool
import partial_json_parser as pjp
from partial_json_parser import JSON
import json
# Assuming CohereChatRequest class is defined above as provided.
class CohereToOpenAI:
    
    @staticmethod
    def get_value(json_obj: JSON, key: str) -> Any:
        if isinstance(json_obj, dict):
            return json_obj.get(key, None)
        return None
    # def __init__(self):
    
    @staticmethod
    def convert_chatmessage_to_message(chatMessages: List[ChatMessage]) -> List[Message]:
        new_chat_history = []
        for x in chatMessages:
            if (x.role == ChatRole.CHATBOT):
                new_chat_history.append(ChatbotMessage(message=x.message, role="CHATBOT", tool_calls=x.tool_calls))
            elif(x.role == ChatRole.USER):
                new_chat_history.append(UserMessage(message=x.message, role="USER", tool_calls=x.tool_calls))
            elif(x.role == ChatRole.TOOL):
                new_chat_history.append(ToolMessage(message=x.message, role="TOOL", tool_results=x.tool_results, tool_calls=x.tool_calls))
            elif(x.role == ChatRole.SYSTEM):
                new_chat_history.append(SystemMessage(message=x.message, role="SYSTEM", tool_calls=x.tool_calls))
                
        return new_chat_history
                    
    @staticmethod
    def cohere_to_openai_event_chunk(event: ChatCompletionChunk, previous_response: Optional[str] = None, function_triggered: str = 'none', chat_request: CohereChatRequest = None, generation_id: Optional[str] = "") -> List[StreamedChatResponse]:
        
        # tool_call_is_complete = CohereToOpenAI.check_if_tool_call_in_text_chunk_is_complete(previous_response or "")
        is_there_json = len(pjp.parse_json(previous_response).keys()) > 0
        is_json_full = full_text.strip().endswith("}") and full_text.strip().count("{") == full_text.strip().count("}")
        print("tool_call_is_complete: ",tool_call_is_complete)
        if (is_there_json and is_json_full):
            parsed_previous_response = pjp.parse_json(previous_response)
            
            if (parsed_previous_response):
                print("parsed_previous_response: ",parsed_previous_response)
                
                func_name = CohereToOpenAI.get_value(parsed_previous_response, "name")
                func_params: Dict[str, Any] = CohereToOpenAI.get_value(parsed_previous_response, "parameters")

                tool_call = ToolCall(name=func_name, parameters=func_params)
                tool_call_delta = ToolCallDelta(name=func_name, index=0, parameters=str(func_params))
                # Copy the chat history and append the tool_call_message
                

                new_chat_history = CohereToOpenAI.convert_chatmessage_to_message(chat_request.chat_history)
                if function_triggered == 'none':
                    # if chat_request:
                    tool_call_message = ChatbotMessage(message=event.choices[0].delta.content or '', role='CHATBOT',tool_calls=[tool_call])
                    new_chat_history.append(tool_call_message)
                    chat_request.chat_history.extend(new_chat_history)
                    response = NonStreamedChatResponse(text=event.choices[0].delta.content or '',chat_history=new_chat_history, generation_id=generation_id, finish_reason="COMPLETE")
                    return [ToolCallsChunkStreamedChatResponse(event_type = "tool-calls-chunk", tool_call_delta=tool_call_delta),
                            ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-generation", tool_calls=[tool_call], text="I will read the document to find the names of all the chapters."),
                            ]
                    
                # if function_triggered == 'calling':
                #     return [ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-generation", tool_calls=[tool_call], text="I will read the document to find the names of all the chapters.")]
        
        
        print("OllamaChunk: ",event)
        if (event.choices[0].finish_reason == "tool_calls" or event.choices[0].finish_reason == "function_call" or event.choices[0].delta.function_call):
            if (event.choices[0].delta.tool_calls):
                for tool_call in event.choices[0].delta.tool_calls:
                    return [ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-chunk", tool_call_delta=CohereToOpenAI.convert_tool_call_delta(tool_call))]
            else:
                return [TextGenerationStreamedChatResponse(event_type = "text-generation", text=event.choices[0].delta.content or '')]
        elif event.choices[0].finish_reason == "stop":
            response = NonStreamedChatResponse(text=event.choices[0].delta.content or '')
            return [StreamEndStreamedChatResponse(event_type = "stream-end",finish_reason="COMPLETE", response=response)]
        else:
            return [TextGenerationStreamedChatResponse(event_type = "text-generation", text=event.choices[0].delta.content or '')]
    
    @staticmethod
    def check_if_tool_call_in_text_chunk_is_complete(full_text: str) -> bool:
        if full_text.strip().endswith("}") and full_text.strip().count("{") == full_text.strip().count("}"):
            try:
                # Try to parse the buffer as JSON
                parsed_json = json.loads(full_text)
                print("Complete JSON received:", parsed_json)
                
                return True
            except json.JSONDecodeError:
                # If it's not valid JSON, continue accumulating chunks
                print("Incomplete or invalid JSON, waiting for more chunks...")
                return False
        return False
        
    @staticmethod
    def cohere_to_open_ai_request_tool_call(tool_calls: List[Dict[str, Any] | None]) -> List[ChatCompletionMessageToolCallParam]:
        oai_calls = []
        if not tool_calls:
            return oai_calls
        for tool_call in tool_calls:
            arguments = str(tool_call.parameters)
            name = str(tool_call.name)
            function = OpenAIFunction(arguments=arguments, name=name)
            
            
            call = ChatCompletionMessageToolCallParam(id="",type="function", function=function)
            oai_calls.append(call)
        return oai_calls
        
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
                    chat_entry.tool_calls
                    msg: ChatCompletionMessageParam = ChatCompletionAssistantMessageParam(
                        role= chat_entry.role.lower(), # type: ignore
                        content=chat_entry.message,
                        tool_calls=CohereToOpenAI.cohere_to_open_ai_request_tool_call(chat_entry.tool_calls),
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
    def convert_tool_call_delta(delta: ChoiceDeltaToolCall) -> ToolCallDelta:
        if (delta.function):
            return ToolCallDelta(
                name=delta.function.name,
                parameters=delta.function.arguments
            )
        else:
            return ToolCallDelta(
                name=None,
                parameters=None
            )
        
        
   
#    Tools as Input Defination

    @staticmethod
    def convert_tool(tools: List[BackendTool] | None) -> List[ChatCompletionToolParam]:
        open_ai_tools: List[ChatCompletionToolParam] = []
        if not tools:
            return open_ai_tools
        for tool in tools:
            parameters = CohereToOpenAI.convert_tool_parameter_defination(tool.parameter_definitions)
            oai_tool = ChatCompletionToolParam(
            type="function",
            function={
                "name": tool.name or '',
                "description": tool.description or '',
                "parameters": parameters,
                "strict": tool.name == 'read_document'
            }
            )
            open_ai_tools.append(oai_tool)
        
            
        return open_ai_tools

    @staticmethod
    def convert_tool_parameter_defination(tool_parameter_definitions: Dict[str, ToolParameterDefinitionsValue] | None) -> Dict[str, object]:
        if not tool_parameter_definitions:
            return {}
        
        params: Dict[str, object] = {}
        for key, value in tool_parameter_definitions.items():
            params[key] = value
        return params
        