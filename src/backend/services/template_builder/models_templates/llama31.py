from backend.services.template_builder.models_templates.base import BaseTemplateBuilder
from typing import Any, List
from openai.types.chat import ChatCompletionSystemMessageParam
from datetime import datetime as Datetime
import json

class Llama31TemplateBuilder(BaseTemplateBuilder):
    def __init__(self, chat_messages: List[ChatCompletionSystemMessageParam], tools: List[dict] = [], system_message: ChatCompletionSystemMessageParam | None = None, tool_response: Any = None):
        super().__init__(chat_messages, tools, tool_response)
        
        
        self.system_message = system_message or self.create_default_system_message()

    def create_default_system_message(self) -> dict:
        """
        Create the default system message for LLaMA.
        """
        current_date = Datetime.now().strftime("%d %B %Y")
        # Main Instructions
        # - Your role is an expert writing assistant who gives highly concise and accurate information to the user who work with critical and important novels and documents that requires accuracy and clarity.
        return {
            "content": f"""
            Environment: ipython
            Tools: brave_search, wolfram_alpha
            Cutting Knowledge Date: December 2023
            Today Date: {current_date}
            
            # Main Instructions
            - Your role is an expert AI writing assistant, focused on accuracy and clarity and conciseness.
            - You must provide concise, accurate, and contextually relevant information. You must not hallucinate or generate misleading content.
            - When the user uploads a file, you can use functions to read it if needed.
            - Maintain focus at all times, avoiding context switching, especially between similar parts of documents.
            - If a task involves a document, stick strictly to the original content, avoiding any misinterpretation or alterations.
            - When the user asks to read or access specific sections or chapters or parts of a document, ensure you retrieve the exact requested part exactly as it written, avoid confusion with similar parts.
            
            # Functions Instructions
            - When the user asks you a question, you can use relevant functions if needed.
            - Don't try to call any function that the system didn't told you about.
            - When looking for information, use relevant functions if available.
            - When you receive a result from the function, do not call it again.
            - Respect the function results without changes, unless the user asked for that.
            
            
            # Function Call Guidelines
            - If calling any functions, use the format:
              {{'name': 'function_name', 'parameters': As Defined in the function}}
            You SHOULD NOT include any other text in the response.
            - All function calls must strictly follow the format outlined above.
            - Include all necessary parameters as defined by the function.
            - Only one function call is allowed per response.
            - Always include sources or references when using search tools to answer a query.
            
            You have access to the following functions:
            {self.build_tools_section(full_body=False)}

            Reminder:
                - Function calls MUST follow the specified format.
                - Required parameters MUST be specified.
                - Only call one function at a time.
                - Place the entire function call reply on one line.
                - Always add sources when using search results to answer a query.
            """,
            "role": "system",
            "name": "System"
        }

    def build_system_initial_message(self) -> str:
        """
        Build the initial system message for the template.
        """
        template = f"<|start_header_id|>{self.system_message['role']}<|end_header_id|>\n"
        if isinstance(self.system_message["content"], str):
            template += f"{self.system_message['content']}\n"
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
            elif message["role"] == "system":
                template += f"<|start_header_id|>system<|end_header_id|>\n"
                
            if isinstance(message["content"], str):
                template += f"{message['content']}\n"
            template += "<|eot_id|>\n"
        return template

    def build_tool_response_section(self) -> str:
        """
        Build the tool response section for the template.
        """
        if not self.tool_response:
            return ""
        
        template = "<|start_header_id|>ipython<|end_header_id|>\n"
        template += f"{self.tool_response}\n"
        template += "<|eot_id|>\n"
        return template

    def build_tools_section(self, full_body: bool = True) -> str:
        """
        Build the tools section for the template by converting the tools list to JSON.
        """
        if not self.tools:
            return ""
        
        initial_part = "<|start_header_id|>user<|end_header_id|>"
        message_body = """
        Given the following functions, respond with a JSON-formatted function call with proper arguments.
        Format: {"name": "function_name", "parameters": {Required Parameters}} 
        
        Reminder:
            - Function calls MUST follow the specified format.
            - Required parameters MUST be included.
            - Only call one function at a time.
            - Always add your sources when using search results.
        """
        template = initial_part + message_body
        tools_json = json.dumps(self.tools, indent=4)  # Format tools as a pretty-printed JSON string
        template += f"{tools_json}\n<|eot_id|>\n"
        return template if full_body else tools_json

    def build_full_template(self) -> str:
        """
        Combine the system initial message, chat messages, and tools section into the full template.
        """
        initial_part = "<|begin_of_text|>"
        full_template = self.build_system_initial_message()
        full_template += self.build_chat_messages()
        full_template += self.build_tool_response_section()
        end_part = "<|start_header_id|>assistant<|end_header_id|>"
        return initial_part + full_template + end_part
