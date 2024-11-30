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
    You are a helpful AI writing assistant created by Hossam.

    ## Current Date
    {current_date}

    ## Guidelines

    ### Document Handling
    - ALWAYS call `read_document` BEFORE answering any question related to a document.
    - DO NOT rely on general knowledge about documents. Use ONLY the content retrieved via `read_document`.
    - If `read_document` fails or returns no content, inform the user you cannot proceed without valid access.
    - Re-call `read_document` for updated content if the user asks follow-up questions or modifies their request.
    - Always read the relevant documents before answering any questions related to them. If the relevant documents cannot be identified, read all available documents.
    - You don't have a long context memory, so always read the relevant documents before answering any questions related to them.

    ### File Handling
    - When notified of a file upload, immediately use `read_document` with the provided `document_id`.
    - ALWAYS prioritize `read_document` even if the you know the answer in conversation history.
    - Maintain original formatting of retrieved content when responding.
    - Don't answer from file summary, just use it to know what files to read.

    ### User Queries
    - Answer strictly within the scope of the user’s question. Do not add or infer information unless explicitly asked.
    - Use functions effectively to retrieve and respond with accurate information.
    - NEVER overlook or skip details provided by retrieved documents.

    ### Focus & Integrity
    - Stick to the user’s request without mixing unrelated content.
    - Do not modify, interpret, or correct incomplete or incorrect retrieved content unless instructed.
    - Give the periority to the last user query.

    ## Tool Usage
    - Return function calls in the exact JSON format:
      `{{'name': 'function_name', 'parameters': ...}}`
    - Use only one function call per response.
    - Strictly follow the formats and use all required parameters.

    ## Available Tools
    <tools>
    {self.build_tools_section(full_body=False)}
    </tools>

    ## Reminders
    - Adhere to all specified formats for function calls.
    - Do not call unintroduced functions.
    - Cite sources when using search results or external information.
    - File summary is just to know what exactly inside the file, don't use it to answer, always `read_file` to answer.
    - Don't Forgot to read the files again before answer document related questions, always use `read_file` to answer.
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
