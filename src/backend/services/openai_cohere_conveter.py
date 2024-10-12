from typing import Iterable, List, Dict, Any, Optional, Union

from cohere import NonStreamedChatResponse, ToolResult
from openai.types.chat.completion_create_params import CompletionCreateParamsBase
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam,ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionChunk, ChatCompletionToolParam, ChatCompletionMessageToolCallParam, ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types import FunctionParameters
from openai.types.chat.chat_completion_message_tool_call_param import Function as OpenAIFunction

from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.chat import ChatRole, ChatMessage
from cohere.types import StreamedChatResponse,  StreamStartStreamedChatResponse,SearchQueriesGenerationStreamedChatResponse,SearchResultsStreamedChatResponse,TextGenerationStreamedChatResponse,CitationGenerationStreamedChatResponse,ToolCallsGenerationStreamedChatResponse,StreamEndStreamedChatResponse,ToolCallsChunkStreamedChatResponse, ToolCallsChunkStreamedChatResponse, ToolCallDelta, ToolParameterDefinitionsValue, ToolCall, Message, ChatbotMessage, UserMessage, ToolMessage, SystemMessage

from cohere.types import Tool as CohereTool
from backend.schemas.tool import Tool as BackendTool
import partial_json_parser as pjp
from partialjson import JSONParser as jsonparser
from partial_json_parser import JSON
import json
import re

jp = jsonparser()

# Assuming CohereChatRequest class is defined above as provided.
class CohereToOpenAI:
    @staticmethod
    def get_value(json_obj: JSON, key: str) -> Any:
        if isinstance(json_obj, dict):
            return json_obj.get(key, None)
        return None
    # def __init__(self):
    
    @staticmethod
    def convert_backend_message_to_openai_message(chatMessages: List[ChatMessage]) -> List[Message]:
        new_chat_history = []
        for x in chatMessages:
            if hasattr(x, "role") and hasattr(x, "message"):
                if (x.role == ChatRole.CHATBOT):
                    updated_dict = {**x.to_dict(), 'role': 'CHATBOT',"message": x.message}

                    new_chat_history.append(ChatbotMessage(**updated_dict))
                elif(x.role == ChatRole.USER):
                    updated_dict = {**x.to_dict(), 'role': 'USER', "message": x.message}

                    new_chat_history.append(UserMessage(**updated_dict))
                elif(x.role == ChatRole.TOOL):
                    updated_dict = {**x.to_dict(), 'role': 'TOOL'}

                    new_chat_history.append(ToolMessage(**updated_dict))
                elif(x.role == ChatRole.SYSTEM):
                    if x.tool_results:
                        updated_dict = {**x.to_dict(), 'role': 'SYSTEM', "message": f"Tool Response: x.tool_results"}
                    else:
                        updated_dict = {**x.to_dict(), 'role': 'SYSTEM'}

                    new_chat_history.append(SystemMessage(**updated_dict))
                
        return new_chat_history
                    
                    
    @staticmethod
    def extract_json_from_string(string_with_json: str):
        # Find the position of the first '{'
        start = string_with_json.find('{')
        # Find the position of the last '}'
        end = string_with_json.rfind('}')
        
        # If both braces are found, slice the string
        if start != -1 and end != -1 and start < end:
            return string_with_json[start:end + 1]
        else:
            return ""  # Return None if no valid JSON structure is found
    
    @staticmethod
    def openai_to_cohere_event_chunk(event: ChatCompletionChunk, previous_response: Optional[str] = None, function_triggered: str = 'none', chat_request: CohereChatRequest = None, generation_id: Optional[str] = "") -> list[StreamedChatResponse] | None:
        
        # tool_call_is_complete = CohereToOpenAI.check_if_tool_call_in_text_chunk_is_complete(previous_response or "")
        
        extracted_json_string = CohereToOpenAI.extract_json_from_string(previous_response)
        print("extracted_json_string: ",extracted_json_string)
        
        if (len(extracted_json_string) > 0):
            is_json_full = extracted_json_string.strip().count("{") == extracted_json_string.strip().count("}")
        else:
            is_json_full = False
            
        parsed_previous_response = jp.parse(extracted_json_string)
        is_there_json = len(parsed_previous_response) > 0
        # print("tool_call_is_complete: ",tool_call_is_complete)
        if (is_there_json and is_json_full):
            # parsed_previous_response = pjp.parse_json(previous_response)
            
            if (parsed_previous_response):
                print("parsed_previous_response: ",parsed_previous_response)
                
                
                func_name = CohereToOpenAI.get_value(parsed_previous_response, "name")
                func_params: Dict[str, Any] = CohereToOpenAI.get_value(parsed_previous_response, "parameters")
                
                tool_call_dict = {"name":func_name, "parameters":func_params}
                tool_call_class = ToolCall(**tool_call_dict)
                tool_call_delta = ToolCallDelta(name=func_name, index=0, parameters=str(func_params))
                # Copy the chat history and append the tool_call_message
                

                new_chat_history = CohereToOpenAI.convert_backend_message_to_openai_message(chat_request.chat_history)
                if function_triggered == 'none':
                    # if chat_request:
                    tool_call_message = ChatbotMessage(role='CHATBOT', message="", tool_calls=[tool_call_class])
                    # {"message":"", "role":"CHATBOT","tool_calls":[tool_call_class]}
                    # tool_call_chat_message = ChatMessage(message=event.choices[0].delta.content or "", role="CHATBOT",tool_calls=[tool_call_dict])
                    new_chat_history.append(tool_call_message)
                    # new_chat_history.extend([tool_call_message])
                        
                    response = NonStreamedChatResponse(text="",chat_history=new_chat_history, generation_id=generation_id, finish_reason="COMPLETE", tool_calls=[tool_call_class])
                    end_response = StreamEndStreamedChatResponse(event_type = "stream-end",finish_reason="COMPLETE", response=response)
                    
                    return [
                        TextGenerationStreamedChatResponse(event_type = "text-generation", text=event.choices[0].delta.content or ''),
                        ToolCallsChunkStreamedChatResponse(event_type = "tool-calls-chunk", tool_call_delta=tool_call_delta),
                            ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-generation", tool_calls=[tool_call_class], text="I will read the document to find the names of all the chapters."),
                            end_response
                            ]
                    
                # if function_triggered == 'calling':
                #     return [ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-generation", tool_calls=[tool_call], text="I will read the document to find the names of all the chapters.")]
        
        
        print("OllamaChunk: ",event)
        if (event.choices[0].finish_reason == "tool_calls" or event.choices[0].finish_reason == "function_call" or event.choices[0].delta.function_call):
            if (event.choices[0].delta.tool_calls):
                for tool_call_dict in event.choices[0].delta.tool_calls:
                    return [ToolCallsGenerationStreamedChatResponse(event_type = "tool-calls-chunk", tool_call_delta=CohereToOpenAI.convert_tool_call_delta(tool_call_dict))]
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
        if tool_calls and len(tool_calls) > 1:
            for tool_call in tool_calls:
                if tool_call and tool_call["parameters"] and tool_call["name"]:
                    arguments = str(tool_call.get("parameters"))
                    # print("parameters: ", tool_call.parameters)
                    # print("arguments: ", arguments)
                    name = str(tool_call.get("name"))
                    function = OpenAIFunction(arguments=arguments, name=name)
                    
                    
                    call = ChatCompletionMessageToolCallParam(id="",type="function", function=function)
                    oai_calls.append(call)
        return oai_calls
        
    @staticmethod
    def cohere_to_openai_request_body(cohere_request: CohereChatRequest) -> CompletionCreateParamsBase:
        # Start with the new user message
        messages: List[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content="You are a helpful assistant. Engage with the user in the conversation. Dont use the tools unless it's absolutely necessary to assist the user with information you don't already, Now you can start chatting")
        ]
        
        # Make a copy of chat history if it exists
        cohere_messages = cohere_request.chat_history.copy() if cohere_request.chat_history else []
        
        def append_message_safe(role, content=None, tool_calls=None, to_end=True):
            """Appends a message if the content exists, otherwise skips."""
            if not content:  # Skip appending if content is None or empty
                print(f"Skipping {role} message: content is empty or missing.")
                return
            
            message_data = {"role": role, "content": content}
            
            # Add tool_calls only if it's relevant
            if tool_calls:
                message_data["tool_calls"] = tool_calls
            
            # Instantiate the correct message type based on role
            if role == "system":
                message_instance = ChatCompletionSystemMessageParam(**message_data)
            elif role == "user":
                message_instance = ChatCompletionUserMessageParam(**message_data)
            elif role == "assistant":
                message_instance = ChatCompletionAssistantMessageParam(**message_data)
            elif role == "tool":
                message_instance = ChatCompletionToolMessageParam(**message_data)
            else:
                print(f"Skipping unknown role: {role}")
                return
            
            # print(f"Appending {role} message:", message_instance)
            if to_end:
                messages.append(message_instance)
            else:
                messages.insert(0, message_instance)
            # print("Current messages:", messages)
        
        # Helper function to convert object to dictionary
        def to_dict(obj):
            if isinstance(obj, dict):
                return obj
            elif hasattr(obj, '__dict__'):
                return obj.__dict__  # Convert object to dict
            return None  # Return None for unsupported types

        # Process chat history
        if cohere_messages:
            
            
                    
                    
            print("HERE IS THE HISTORY", cohere_messages)
            
            
            for chat_entry in cohere_messages:
                print(f"Type of chat_entry: {type(chat_entry)}")  # Debug the type
                
                # Convert chat_entry to dictionary if it's an object
                chat_entry_dict = to_dict(chat_entry)
                if chat_entry_dict is None:
                    print(f"Skipping entry: chat_entry is not a dict or an object.")
                    continue

                print(f"chat_entry: {chat_entry_dict}")

                # Access role and message using dictionary syntax
                role = chat_entry_dict.get("role")  # Use dictionary's .get() method
                message = chat_entry_dict.get("message", "")
                tool_results = chat_entry_dict.get("tool_results", "")
                tool_calls = (
                    CohereToOpenAI.cohere_to_open_ai_request_tool_call(chat_entry_dict.get("tool_calls", []))
                    if "tool_calls" in chat_entry_dict
                    else None
                )
                print("Chat Entry Parsed Details: ", f"role: {role}, message: {message}, tool_results: {tool_results}, tool_calls: {tool_calls}")

                if not role:
                    print("Skipping entry: No role found.")
                    continue

                # Append messages based on role
                if role and (message or tool_results or tool_calls):
                    if role == 'SYSTEM':
                        if "The user uploaded the following attachments" in str(message):
                            append_message_safe("system", f"{message}", tool_calls, to_end=False)
                        else:
                            append_message_safe("system", f"{message}", tool_calls)
                    elif role == 'USER':
                        append_message_safe("user", f"{message}")
                    elif role == 'ASSISTANT' or role == 'CHATBOT':  # Added CHATBOT to align with your example
                        append_message_safe("assistant", f"{message}", tool_calls)
                    else:
                        print(f"Skipping entry with unknown role: {role}")
       
            if cohere_request.tool_results and len(cohere_request.tool_results):
                # results: List[ToolResult] = cohere_request.tool_results # type: ignore
                for tool_result in cohere_request.tool_results:
                    # Add the tool results
                    filter = ''.join([chr(i) for i in range(1, 32)])
                    # print("tool_result: ", tool_result)
                    outputs: List[Any] = tool_result.get("outputs")
                    if len(outputs) == 1:
                        output_dict: dict = outputs[0]
                        print("output_dict: ", output_dict)
                        if  output_dict and "text" in output_dict.keys():
                            output_str= CohereToOpenAI.clean_string(str(output_dict['text']))
                        else:
                            output_str= CohereToOpenAI.clean_string(str(outputs))
                            
                        append_message_safe("tool", content=f"the tool response is: {output_str}")
                    elif len(outputs) > 1:
                        for output_dict in outputs:
                            if output_dict['text']:
                                output_str= CohereToOpenAI.clean_string(str(output_dict['text']))
                            else:
                                output_str= CohereToOpenAI.clean_string(str(output_dict))
                            append_message_safe("tool", content=f"the tool response is: {output_str}")
                        
                    
                
        # if cohere_request.message:
        #     # Add the new user message
        #     # user_message = {
        #     #     "role": "user",
        #     #     "content": cohere_request.message,
        #     # }
        #     append_message_safe("user", cohere_request.message)
            
        #     print("messages: ", messages)
        
        
       
                
                # print("messages: ", messages)
        
        # Construct the OpenAI request parameters
        openai_request = CompletionCreateParamsBase(
            messages=messages,
            model=cohere_request.model,  # type: ignore
            max_tokens=cohere_request.max_tokens,
            temperature=cohere_request.temperature,
            frequency_penalty=cohere_request.frequency_penalty,
            presence_penalty=cohere_request.presence_penalty,
            stop=cohere_request.stop_sequences,
            tools=CohereToOpenAI.convert_tools(cohere_request.tools),
        )
        
        return openai_request

    @staticmethod
    def clean_string(input_string):
        # Remove unnecessary escape sequences (like \n and \\)
        cleaned_string = input_string.replace("\\n", "\n").replace("\\\\", "\\")

        # Remove object/array brackets and slashes
        cleaned_string = re.sub(r'[{}\[\]\\]', '', cleaned_string)

        # Normalize whitespace: replace multiple spaces with a single space
        cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()

        return cleaned_string
    @staticmethod
    def remove_markdown_formatting(text):
        # Remove headers
        text = re.sub(r'#{1,6}\s*', '', text)  # Remove Markdown headers
        # Remove bold and italic formatting
        text = re.sub(r'\*\*([^*]+)\*\*|\*([^*]+)\*|__([^_]+)__|_([^_]+)_', r'\1\2\3\4', text)  # Remove bold and italic
        # Remove links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Remove links
        # Remove images
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)  # Remove images
        # Remove blockquotes
        text = re.sub(r'>\s*', '', text)  # Remove blockquotes
        # Remove lists
        text = re.sub(r'^\s*[\*\-\+]\s*', '', text, flags=re.MULTILINE)  # Remove unordered list markers
        text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)  # Remove ordered list markers
        # Remove escape characters
        text = re.sub(r'\\(.)', r'\1', text)  # Remove escaping backslashes
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
        text = text.strip()  # Remove leading and trailing whitespace
        return text

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
    def convert_tools(tools: List[BackendTool] | None) -> List[ChatCompletionToolParam]:
        def convert_tool_parameter_defination(tool_parameter_definitions: Dict[str, ToolParameterDefinitionsValue] | None) -> Dict[str, object]:
            if not tool_parameter_definitions:
                return {}
            
            params: Dict[str, object] = {}
            for key, value in tool_parameter_definitions.items():
                if key != 'required':
                    params[key] = value
            return params
        open_ai_tools: List[ChatCompletionToolParam] = []
        if not tools:
            return open_ai_tools
        
        required_parameters = []
        parameters: dict[str, Any] = {}
        for tool in tools:
            if tool.parameter_definitions:
                required_parameters: List[str] = [key for key,value in tool.parameter_definitions.items()  if value and value['required']]
                
            params = convert_tool_parameter_defination(tool.parameter_definitions)
            
            if len(params) > 0:
                parameters = {"type": "object",**params, "required": required_parameters}
                
            oai_tool = ChatCompletionToolParam(
            type="function",
            function={
                "name": tool.name or '',
                "description": tool.description or '',
                "parameters": parameters,
                # "strict": False
            }
            )
            open_ai_tools.append(oai_tool)
        
        
            
        return open_ai_tools

  
  
        