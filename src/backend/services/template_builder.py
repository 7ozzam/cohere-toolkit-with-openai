from typing import Any, List, Union, TypedDict, Literal, Iterable
from typing_extensions import Required
from openai.types.chat import ChatCompletionSystemMessageParam
import json
# Function to build the template with messages and tools
class TemplateBuilder:
    def __init__(self, chat_messages: List[ChatCompletionSystemMessageParam],tools: List[dict] = [], system_message: ChatCompletionSystemMessageParam | None = None, tool_response: Any = None):
        default_system_message = {
            "content": "You are a helpful assistant with tool calling capabilities. When you receive a tool call response, use the output to format an answer to the orginal use question.",
            "role": "system",
            "name": "System"
        }
        self.system_message = system_message or default_system_message
        self.chat_messages = chat_messages
        self.tools = tools
        self.tool_response = tool_response

    def build_system_initial_message(self) -> str:
        """
        Build the initial system message for the template.
        """
        template = "<|start_header_id|>system<|end_header_id|>\n"
        if isinstance(self.system_message["content"], str):
            template += f"{self.system_message['content']}\n"
        elif isinstance(self.system_message["content"], Iterable):
            content_parts = ''.join([part["text"] for part in self.system_message["content"]])
            template += f"{content_parts}\n"
        
        template += "<|eot_id|>\n"
        return template

    def build_chat_messages(self) -> str:
        """
        Build the user and assistant chat messages in the template.
        """
        template = ""
        for message in self.chat_messages:
            if message["role"] == "user":
                template += f"<|start_header_id|>user<|end_header_id|>\n"
            elif message["role"] == "assistant":
                template += f"<|start_header_id|>assistant<|end_header_id|>\n"

            if isinstance(message["content"], str):
                template += f"{message['content']}\n"
            elif isinstance(message["content"], Iterable):
                content_parts = ''.join([part["text"] for part in message["content"]])
                template += f"{content_parts}\n"
            
            template += "<|eot_id|>\n"
        return template

    def build_tool_response_section(self) -> str:
        """
        Build the tools section for the template by converting the tools list to JSON.
        """
        if not self.tool_response:
            return ""
        
        template = "<|start_header_id|>ipython<|end_header_id|>\n"
        template += f"{self.tool_response}\n"
        template += "<|eot_id|>\n"
        
        return template
    def build_tools_section(self) -> str:
        """
        Build the tools section for the template by converting the tools list to JSON.
        """
        if not len(self.tools):
            return ""
        initial_part = """Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.
        Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}. Do not use variables."""
        template = "<|start_header_id|>user<|end_header_id|>\n" + initial_part
        tools_json = json.dumps(self.tools, indent=4)  # Format tools as a pretty-printed JSON string
        template += f"{tools_json}\n"
        template += "<|eot_id|>\n"
        return template

    def build_full_template(self) -> str:
        """
        Combine the system initial message, chat messages, and tools section into the full template.
        """
        initial_part = "<|begin_of_text|>"
        full_template = self.build_system_initial_message()
        full_template += self.build_chat_messages()
        full_template += self.build_tools_section()
        return initial_part + full_template
    
    



