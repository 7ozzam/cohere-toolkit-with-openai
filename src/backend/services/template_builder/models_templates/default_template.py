from .base import BaseTemplateBuilder
from typing import Any, List
from openai.types.chat import ChatCompletionSystemMessageParam

class DefaultTemplateBuilder(BaseTemplateBuilder):
    def __init__(self, chat_messages: List[ChatCompletionSystemMessageParam], tools: List[dict] = [], tool_response: Any = None):
        super().__init__(chat_messages, tools, tool_response)

    def create_default_system_message(self, current_date: str) -> dict:
        return {
            "content": f"Default system message as of {current_date}",
            "role": "system",
            "name": "System"
        }

    def build_system_initial_message(self) -> str:
        return "Default system initial message."

    def build_chat_messages(self) -> str:
        return "Default chat messages."

    def build_tool_response_section(self) -> str:
        return "Default tool response."

    def build_tools_section(self, full_body: bool = True) -> str:
        return "Default tools section."

    def build_full_template(self) -> str:
        return "Default full template."
