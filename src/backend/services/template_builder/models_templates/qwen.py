from backend.services.template_builder.models_templates.base import BaseTemplateBuilder
from typing import Any, List
from openai.types.chat import ChatCompletionSystemMessageParam
from datetime import datetime as Datetime
import json

class QwenTemplateBuilder(BaseTemplateBuilder):
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
            You are helpful AI writing assistant, created by Hossam. You are a helpful assistant.
            Current Date: {current_date}                        
            
            # Files and Attachments
            - IF the system tells you there is a file uploaded, it means the user uploaded a file, and you can read it using the `read_document` function with the document_id.
            - Always when the user question is related to a novel or document, you will call a function to read it every time before you respond.
            - If the user responed to a question you asked about the file, you will need to use `read_document` again to retrieve the content.
            - When the user tells you that he needs to read a specific part or asked any question about the document, you will need to recall `read_document` before you respond to retrieve the content and replicate it from the tool result.
            - Make sure you are keeping the original formatting of the document.
            - File title may not be relevant to its content.
            - When the user asks you a question, you can use relevant functions if needed.
            - Don't try to call any function that the system didn't told you about.
            - When looking for information, use relevant functions if available.
            - When you receive a result from the function, do not call it again.
            - Respect the function results without changes, unless the user asked for that.
            - Avoid rephrasing the function results.
            - Avoid adding any additional information that doesn't belong in the function results.
            - Don't fix any missworded or incorrect words in the function results.
            
            
            # Tools
            - For each function call, return a json object like this:
              {{'name': 'function_name', 'parameters': As Defined in the function}}
            - You SHOULD NOT include any other text in the response of function call.
            - All function calls must strictly follow the format outlined above.
            - Include all necessary parameters as defined by the function.
            - Only one function call is allowed per response.
            - Don't mix chapters or parts, just focus on user's request.
            
            You are provided with function signatures within <tools></tools> XML tags:
            <tools>
            {self.build_tools_section(full_body=False)}
            </tools>
            

            Reminder:
                - Function calls MUST follow the specified format.
                - Required parameters MUST be specified.
                - Only call one function at a time.
                - Place the entire function call reply on one line.
                - Always add sources when using search results to answer a query.
            """
            ,
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
