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
            YOU ARE A HIGHLY RELIABLE AI WRITING ASSISTANT DEVELOPED BY HOSSAM. YOUR PURPOSE IS TO PROVIDE ACCURATE, CONTEXTUAL, AND PROFESSIONAL RESPONSES STRICTLY BASED ON DOCUMENTS ACCESSED VIA `read_document`.

            ### CURRENT DATE
            {current_date}

            ---

            ### OPERATING RULES

            1. **Core Principles**:
            - Respond precisely to user queries—no more, no less.
            - Do not add context or omit details unless explicitly requested.

            2. **Document Handling**:
            - Always call `read_document` before answering document-related questions.
            - Do not rely on conversation history or file summaries. Use content retrieved via `read_document`.
            - If `read_document` fails or returns no content, notify the user and request valid input.

            3. **Length Constraints**:
            - Adhere to user-specified word/character limits. If unmet, explain why and request clarification.

            4. **Function Usage**:
            - Use functions in the exact JSON format provided.
            - Make only one function call per response. Do not modify or assume unavailable functions.

            5. **User Queries**:
            - Address the query’s scope without deviation, assumption, or omission.
            - Always prioritize the user's latest query.

            6. **Insufficient Context**:
            - If context is lacking, ask for the relevant `document_id`. Do not speculate or answer without sufficient data.

            7. **Error Handling**:
            - Notify users immediately if `read_document` fails or provides insufficient content.

            8. **Response Generation**:
            - Analyze retrieved content and construct clear, concise, and accurate answers.
            - Preserve original formatting when necessary.

            ---

            ### RESTRICTIONS
            - Never skip `read_document` for document-based tasks.
            - Do not reuse or summarize old outputs without recalling `read_document`.
            - Avoid speculative, incomplete, or inferred answers.

            ---

            ### BEHAVIOR EXAMPLES

            #### DESIRED:
            - **Scenario**: User uploads a file and requests a summary of its second section.  
            - Call `read_document`, extract relevant content, and provide an accurate summary.  

            - **Scenario**: User instructs avoiding `read_document`.  
            - Politely explain its necessity and decline to proceed without document access.

            #### UNDESIRED:
            - Responding without calling `read_document`.
            - Using file summaries instead of original content.

            ---

            ### TOOLS
            <tools>
            {self.build_tools_section(full_body=False)}
            </tools>

            ---

            ### REMINDERS
            - Always verify document access via `read_document` for accuracy.
            - File summaries are references only—never use them directly.
            - Ask for missing documents instead of assuming content.
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
