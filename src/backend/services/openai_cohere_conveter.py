from typing import Iterable, List, Dict, Any, Optional, Union


from openai.types.chat.completion_create_params import CompletionCreateParamsBase as ChatCompletionCreateParamsBase
from openai.types.completion_create_params import CompletionCreateParamsBase as RegularCompletionCreateParamsBase
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam,ChatCompletionAssistantMessageParam, ChatCompletionMessageParam, ChatCompletionChunk, ChatCompletionToolParam, ChatCompletionMessageToolCallParam, ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types import FunctionParameters
from openai.types.chat.chat_completion_message_tool_call_param import Function as OpenAIFunction

from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.chat import ChatRole, ChatMessage
from cohere.types import ToolParameterDefinitionsValue, ToolCall, ChatbotMessage, UserMessage, ToolMessage, SystemMessage, ToolResult, StreamedChatResponse
from backend.schemas.chat_native import StreamedChatEvent, StreamTextGeneration, StreamCitationGeneration, StreamToolCallsGeneration, StreamEnd, StreamToolCallsChunk, ToolCallDelta, ToolCall, NonStreamedChatResponse, StreamToolResult, StreamInlineFix
# from backend.schemas.message import Message
from backend.schemas.context import Context

from backend.chat.enums import StreamEvent

from backend.services.template_builder.template_builder import TemplateBuilderFactory as TemplateBuilder
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
    def convert_backend_message_to_openai_message(chatMessages: List[ChatMessage]) -> List[Dict[str, Any]]:
        new_chat_history = []
        for x in chatMessages:
            try:
                if x and hasattr(x, "role") and hasattr(x, "message"):
                    if x.role == ChatRole.CHATBOT:
                        message_body = x.message or ""
                        if hasattr(x, "tool_calls") and x.tool_calls:
                            message_body += str(x.tool_calls)
                        
                        updated_dict = x.to_dict()
                        updated_dict.update({'role': ChatRole.CHATBOT, "message": message_body})
                    elif x.role == ChatRole.USER:
                        updated_dict = x.to_dict()
                        updated_dict.update({'role': ChatRole.USER, "message": x.message})
                    elif x.role == ChatRole.TOOL:
                        updated_dict = x.to_dict()
                        updated_dict.update({'role': ChatRole.TOOL})
                    elif x.role == ChatRole.SYSTEM:
                        message_body = f"Tool Response: {x.tool_results}" if x.tool_results else x.message
                        updated_dict = x.to_dict()
                        updated_dict.update({'role': ChatRole.SYSTEM, "message": message_body})
                    
                    new_chat_history.append(dict(ChatMessage(**updated_dict)))
            except Exception as e:
                print(f"Error processing message: {x}. Exception: {e}")
                raise
        return new_chat_history

                    
                    
    @staticmethod
    def extract_json_from_string(string_with_json: str, keep_original: bool = False) -> str:
        # Find the position of the first '{'
        start = string_with_json.find('{')
        # Find the position of the last '}'
        end = string_with_json.rfind('}')
        
        # If both braces are found, slice the string
        if start != -1 and end != -1 and start < end:
            # Replace tuples with arrays
            json_string = string_with_json[start:end + 1]
            if not keep_original:           
                json_string = json_string.replace('(', '[').replace(')', ']').replace("'", '"')
            
            return json_string
        else:
            return ""  # Return None if no valid JSON structure is found
    ChatCompletionChunk
    @staticmethod
    def openai_to_cohere_event_chunk(
        event: Any,
        previous_response: Optional[str] = None, 
        function_triggered: str = 'none', 
        chat_request: CohereChatRequest | None = None, 
        generation_id: Optional[str] = "", 
        build_template: bool = False,
        stream_message: Optional[str] = "",
        finish_reason: Optional[str] = None,
        delta: Optional[ChoiceDeltaToolCall] = None,
        ctx: Context = None
    ) -> list[StreamedChatEvent] | None:
        
        # # # # Extract the message from the event
        # # # stream_message = ""
        # # # finish_reason = None
        # # # delta = None
        # # # if build_template:
        # # #     if event.choices:
        # # #         stream_message = event.choices[0].text
        # # #         finish_reason = event.choices[0].finish_reason
        # # #         delta = getattr(event.choices[0], 'delta', None)
        # # #     elif event.content:
        # # #         stream_message = event.content
        # # #         if event.stop:
        # # #             finish_reason = "stop" 
        # # # else:
        # # #     stream_message = event.choices[0].delta.content
        # # #     finish_reason = event.choices[0].finish_reason
        # # #     delta = getattr(event.choices[0], 'delta', None)
        
        # # # If message exists, append to the previous response
        # # # if stream_message:
        # # #     previous_response = (previous_response or "") + stream_message
        
        conversation_id = chat_request.conversation_id
        response_id = ctx.get_trace_id()
        print("stream_message:", stream_message)
        print("finish_reason:", finish_reason)
        print("delta:", delta)
        new_chat_history = CohereToOpenAI.convert_backend_message_to_openai_message(chat_request.chat_history)
        
        
        # Extract JSON from the response
        original_json_string = CohereToOpenAI.extract_json_from_string(previous_response, keep_original=True)
        extracted_json_string = CohereToOpenAI.extract_json_from_string(previous_response)
        print("extracted_json_string:", extracted_json_string)

        # Check if JSON is complete (matching curly braces)
        is_json_full = extracted_json_string.strip().count("{") == extracted_json_string.strip().count("}") if extracted_json_string else False

        # Parse the extracted JSON
        try:
            parsed_response = jp.parse(extracted_json_string)
            is_json_present = len(parsed_response) > 0
        except Exception as e:
            parsed_response = None
            is_json_present = False
            

        # If JSON is valid and complete, handle the tool call
        if is_json_present and is_json_full:
            func_name = CohereToOpenAI.get_value(parsed_response, "name")
            func_params: Dict[str, Any] = CohereToOpenAI.get_value(parsed_response, "parameters")

            tool_call_class = ToolCall(name=str(func_name), parameters=dict(func_params))
            tool_call_delta = ToolCallDelta(name=func_name, index=0, parameters=str(func_params))

            
            message_rest = ""
            if type(previous_response) == str and  any(quote in previous_response for quote in ("```", "'", '"')) and not previous_response.endswith(("```", "'", '"')):
                if "```" in previous_response:
                    message_rest = "\n```\n"
                    
            stream_message = stream_message + message_rest if stream_message else message_rest
            
            # Handle response based on function_triggered status
            if function_triggered == 'none':
                tool_call_message = ChatMessage(role=ChatRole.CHATBOT, message="", tool_calls=[dict(tool_call_class)])
                new_chat_history.append(dict(tool_call_message))

                response = NonStreamedChatResponse(
                    text="", 
                    chat_history=new_chat_history, 
                    generation_id=generation_id, 
                    conversation_id=conversation_id,
                    finish_reason="COMPLETE", 
                    tool_calls=[tool_call_class],
                    response_id=response_id
                )
                
                end_response = StreamEnd(
                    event_type=StreamEvent.STREAM_END, 
                    chat_history=new_chat_history,
                    finish_reason="COMPLETE", 
                    response=response,
                    tool_calls=[tool_call_class]
                )

                # class RemoveResponse:
                #     def __init__(self, extracted_json_string):
                #         self.event_type = "remove-part"
                #         self.part = extracted_json_string

                
                # removeResponse = ToolCallsChunkStreamedChatResponse(event_type="tool-calls-chunk", text="OAI_REMOVE", part=extracted_json_string)

                return [
                    StreamTextGeneration(event_type=StreamEvent.TEXT_GENERATION, text=stream_message),
                    StreamToolCallsChunk(text="Calling A Tool",event_type=StreamEvent.TOOL_CALLS_CHUNK, tool_call_delta=tool_call_delta, part_to_remove=original_json_string),
                    StreamToolCallsGeneration(
                        event_type=StreamEvent.TOOL_CALLS_GENERATION, 
                        tool_calls=[tool_call_class], 
                        text=f"{original_json_string}"
                        # text=f"{str(parsed_response)})"
                    ),
                    # StreamInlineFix(
                    #     event_type=StreamEvent.INLINE_FIX, 
                    #     text=f"oai-remove-part:{original_json_string}"
                    #     # text=f"{str(parsed_response)})"
                    # ),
                    end_response
                ]

        
              # Handle tool call completion or stop signals
        
        
        if finish_reason in ["tool_calls", "function_call"] or (delta and delta.function_call):
            tool_calls = getattr(delta, 'tool_calls', None)
            if tool_calls:
                tool_call_deltas = [CohereToOpenAI.convert_tool_call_delta(tc) for tc in tool_calls]
                return [StreamToolCallsChunk(event_type=StreamEvent.TOOL_CALLS_CHUNK, tool_call_delta=tool_call_deltas[0])]
            return [StreamTextGeneration(event_type=StreamEvent.TEXT_GENERATION, text=stream_message or '')]
        
        if finish_reason == "stop":
            print(f"Chat history content: {new_chat_history}")
            response = NonStreamedChatResponse(
                text= stream_message or "", 
                chat_history=new_chat_history,
                generation_id=generation_id,
                conversation_id=conversation_id,
                response_id=response_id,
                finish_reason="COMPLETE", 
            )
            # response = NonStreamedChatResponse(text=stream_message or '')
            return [StreamEnd(event_type=StreamEvent.STREAM_END, finish_reason="COMPLETE", response=response)]
        return [StreamTextGeneration(event_type=StreamEvent.TEXT_GENERATION, text=stream_message or '')]

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
    def cohere_to_open_ai_request_tool_call(tool_calls: List[Any | None]) -> List[ChatCompletionMessageToolCallParam]:
        oai_calls = []
        if tool_calls and len(tool_calls) > 0:
            for tool_call in tool_calls:
                if tool_call:
                    tool_call_dict = dict(tool_call)
                    if tool_call_dict and tool_call_dict["parameters"] and tool_call_dict["name"]:
                        arguments = str(tool_call_dict.get("parameters"))
                        # print("parameters: ", tool_call.parameters)
                        # print("arguments: ", arguments)
                        name = str(tool_call_dict.get("name"))
                        function = OpenAIFunction(arguments=arguments, name=name)
                        
                        
                        call = ChatCompletionMessageToolCallParam(id="",type="function", function=function)
                        oai_calls.append(call)
        return oai_calls
        
    @staticmethod
    def cohere_to_openai_chat_request_body(cohere_request: CohereChatRequest) -> ChatCompletionCreateParamsBase:
        messages: List[ChatCompletionMessageParam] = []
        cohere_messages = cohere_request.chat_history.copy() if cohere_request.chat_history else []

        # Process chat history
        if cohere_messages:
            messages.extend(CohereToOpenAI.process_chat_history(cohere_messages))

        # Process tool results
        if cohere_request.tool_results and len(cohere_request.tool_results):
            messages.extend(CohereToOpenAI.process_tool_results_as_message(cohere_request.tool_results))

        # Prepare OpenAI request parameters
        tools = CohereToOpenAI.convert_tools(cohere_request.tools)
        
        builder = TemplateBuilder.get_template_builder(template_name="qwen",chat_messages=messages, tools=tools)
        system_message = builder.create_default_system_message()
        messages.insert(0, system_message)
        
        openai_request = CohereToOpenAI._create_request_without_template(cohere_request, messages)

        return openai_request
    
    @staticmethod
    def cohere_to_openai_completion_request_body(cohere_request: CohereChatRequest) -> RegularCompletionCreateParamsBase:
        messages: List[ChatCompletionMessageParam] = []
        cohere_messages = cohere_request.chat_history.copy() if cohere_request.chat_history else []
        # Process chat history
        if cohere_messages:
            messages.extend(CohereToOpenAI.process_chat_history(cohere_messages))

        # Process tool results
        tools_response = None
        if cohere_request.tool_results and len(cohere_request.tool_results):
            tools_response = str(CohereToOpenAI.process_tool_results_as_text(cohere_request.tool_results))
        
        tools = CohereToOpenAI.convert_tools(cohere_request.tools)
        openai_request = CohereToOpenAI._create_request_with_template(cohere_request, messages, tools, tool_response=tools_response)

        return openai_request

    @staticmethod
    def process_chat_history(cohere_messages: List[ChatMessage]) -> List[ChatCompletionMessageParam]:
        messages = []
        for chat_entry in cohere_messages:
            print("==============================")
            chat_entry_dict = CohereToOpenAI.to_dict(chat_entry)
            if chat_entry_dict is None:
                print("Skipping entry: chat_entry is not a dict or an object.")
                continue

            role = chat_entry_dict.get("role")
            message = chat_entry_dict.get("message", "")
            tool_calls = CohereToOpenAI.get_tool_calls(chat_entry_dict)
            tool_results = chat_entry_dict.get("tool_results", "")
            
            
            print("Embedding message: ", chat_entry)
            if role and (message or tool_results or tool_calls):
                print("Found Something to embed")
                print("==============================")
                if role == 'SYSTEM':
                    messages.append(CohereToOpenAI.append_system_message(message, tool_calls))
                elif role == 'USER':
                    messages.append(CohereToOpenAI.append_user_message(message))
                elif role in ['ASSISTANT', 'CHATBOT']:
                    if tool_calls and not len(message):
                        message = f"{str(tool_calls)}"
                    messages.append(CohereToOpenAI.append_assistant_message(message, tool_calls))
                else:
                    print(f"Skipping entry with unknown role: {role}")
        return messages

    @staticmethod
    def process_tool_result_entry_as_text(tool_result: ToolResult) -> str:
        text_outputs: str = ""
        
        tool_result_dict = dict(tool_result)
        # print("tool_result_dict: ", tool_result_dict)
        outputs: List[Any]  = tool_result_dict.get("outputs", [])
        call: Any  = tool_result_dict.get("call", [])
        if len(outputs) > 0:
            for output in outputs:
                # print("OTYPE:", isinstance(output, dict))
                # print("OUTTEXT:", output["text"])
                if output and isinstance(output, dict) and output["text"]:
                    text = output["text"]
                else:
                    text = str(output)
                    
                text_outputs += f"""Here's the tool response: 
                
                Tool Call:
                {call}
                
                Result: 
                {text}
                """ or ""
                # text_outputs += f'{{"output": "{text}"}}' or ""
            
        return text_outputs or ""
    @staticmethod
    def process_tool_results_as_text(tool_results: List[ToolResult]) -> str | None:
        text_outputs: str = ""
        
        if len(tool_results):
            for tool_result in tool_results:            
                text_outputs += CohereToOpenAI.process_tool_result_entry_as_text(tool_result)
                # text_outputs += f'{{"output": "{text}"}}' or ""
            
        return text_outputs
    @staticmethod
    def process_tool_results_as_message(tool_results: List[ToolResult]) -> List[ChatCompletionMessageParam]:
        messages = []
        tool_response = CohereToOpenAI.process_tool_results_as_text(tool_results)
        if tool_response and len(tool_response):
            message = CohereToOpenAI.generate_tool_reponse_message(f"{tool_response}")
            messages.append(message)
        return messages

    # @staticmethod
    # def append_tool_responses(outputs: List[Any]) -> List[ChatCompletionMessageParam]:
    #     messages = []
    #     for output_dict in outputs:
    #         output_str = CohereToOpenAI.clean_string(str(output_dict.get('text', str(output_dict))))
    #         messages.append(CohereToOpenAI.generate_tool_reponse_message(f"the tool response is: {output_str}"))
    #     return messages

    @staticmethod
    def _create_request_without_template(
        cohere_request: CohereChatRequest,
        messages: List[ChatCompletionMessageParam],
    ) -> ChatCompletionCreateParamsBase:
        """Create OpenAI request parameters without building a template."""
        
        return ChatCompletionCreateParamsBase(
            messages=messages,
            model=cohere_request.model,  # type: ignore
            max_tokens=cohere_request.max_tokens or -1,
            temperature=None, #cohere_request.temperature,
            frequency_penalty=cohere_request.frequency_penalty,
            presence_penalty=cohere_request.presence_penalty,
            stop=cohere_request.stop_sequences,
            # tools=tools
        )

    @staticmethod
    def _create_request_with_template(
        cohere_request: CohereChatRequest,
        messages: List[ChatCompletionMessageParam],
        tools: Any,
        tool_response: Any
    ) -> RegularCompletionCreateParamsBase:
        """Create OpenAI request parameters by building a template."""
        # template_builder = TemplateBuilder(template_name="",chat_messages=messages, tools=tools, tool_response=tool_response)
        full_template = TemplateBuilder.build_full_template(template_name="llama3.1",chat_messages=messages, tools=tools, tool_response=tool_response)
        print(full_template)  # Output the final template
        return RegularCompletionCreateParamsBase(
            prompt=full_template,
            model=cohere_request.model,  # type: ignore
            max_tokens=cohere_request.max_tokens or 4096,
            temperature=None, #cohere_request.temperature,
            frequency_penalty=cohere_request.frequency_penalty,
            presence_penalty=cohere_request.presence_penalty,
            stop=cohere_request.stop_sequences,
        )


    @staticmethod
    def to_dict(obj: Any) -> dict | None:
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return None

    @staticmethod
    def get_tool_calls(chat_entry_dict: dict) -> Any:
        print("Getting Tools")
        print('chat_entry_dict["tool_calls"]', chat_entry_dict["tool_calls"])
        print('chat_entry_dict.get("tool_calls")', chat_entry_dict.get("tool_calls"))
        oai_tools = CohereToOpenAI.cohere_to_open_ai_request_tool_call(chat_entry_dict["tool_calls"])
        print("oai_tools: ", oai_tools)
        return oai_tools

    @staticmethod
    def append_system_message(message: str, tool_calls: Any) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(role="system", content=message, tool_calls=tool_calls)

    @staticmethod
    def append_user_message(message: str) -> ChatCompletionUserMessageParam:
        return ChatCompletionUserMessageParam(role="user", content=message)

    @staticmethod
    def append_assistant_message(message: str, tool_calls: Any) -> ChatCompletionAssistantMessageParam:
        if tool_calls:
            message = f"{tool_calls}"
        
        return ChatCompletionAssistantMessageParam(role="assistant", content=message, tool_calls=tool_calls)

    @staticmethod
    def generate_tool_reponse_message(content: str) -> ChatCompletionToolMessageParam:
        return ChatCompletionToolMessageParam(role="tool", content=content)

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
                parameters = {"type": "dict",**params, "required": required_parameters}
                
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

  
  
        