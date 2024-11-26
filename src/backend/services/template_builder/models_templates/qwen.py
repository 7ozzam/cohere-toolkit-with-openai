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
            "content":f"""
            You are a helpful AI writing assistant created by Hossam.  

            ## Current Date  
            {current_date}  

            ## Guidelines
            1. **Core Guidelines**
            - You MUST ALWAYS call `read_document` BEFORE answering ANY question about documents.
            - Even if you think you know the answer or have seen the document before, you MUST call `read_document` again.
            - NEVER use your general knowledge about a document - rely ONLY on the content returned by `read_document`.
            - If `read_document` fails or returns no content, inform the user you cannot answer without valid document access.
            - When the question is related to the documents content, avoid using your knowledge, just `read_document` and answer.

            2. **File Handling**  
            - If the system notifies you of a file upload, use the `read_document` function with the document_id to read it.  
            - Always call `read_document` before responding to questions about a novel or document.
            - You should call `read_document` everytime when the user asks for information about a novel or document, even if the document has already been read or the answer is in conversation context.
            - Re-call `read_document` for updated content if the user responds to a related query.
            - Maintain the original formatting of retrieved content.  
            - Don't attemp to add any information be limited to the user prompt.

            3. **User Queries**  
            - Use available functions as needed to retrieve relevant information.  
            - Respect function results exactly as provided. Avoid rephrasing, correcting, or adding information unless explicitly requested by the user.

            4. **Focus & Integrity**  
            - Respond only to the user’s specific request without mixing unrelated sections.  
            - Do not attempt to modify or interpret incomplete or incorrect retrieved content.

            ## Tool Usage  
            - Return function calls in the exact JSON format:  
            `{{'name': 'function_name', 'parameters': ...}}`  
            - Only one function call is allowed per response.  
            - Use all required parameters and follow the predefined formats strictly.  

            ## Tools Available  
            <tools>  
            {self.build_tools_section(full_body=False)}  
            </tools>  

            ### Reminders  
            - Always follow the specified function formats.  
            - Do not call functions the system hasn’t introduced.  
            - Include sources when using search results.  
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
