from typing import Any, List
from openai.types.chat import ChatCompletionSystemMessageParam
from abc import ABC, abstractmethod

class BaseTemplateBuilder(ABC):
    def __init__(self, chat_messages: List[ChatCompletionSystemMessageParam], tools: List[dict] = [], tool_response: Any = None):
        self.chat_messages = chat_messages
        self.tools = tools
        self.tool_response = tool_response

    @abstractmethod
    def create_default_system_message(self) -> dict:
        """
        Create the default system message.
        This must be implemented by any class that inherits from BaseTemplateBuilder.
        """
        pass

    @abstractmethod
    def build_system_initial_message(self) -> str:
        """
        Build the initial system message for the template.
        Must be implemented by the subclass.
        """
        pass

    @abstractmethod
    def build_chat_messages(self) -> str:
        """
        Build the user and assistant chat messages in the template.
        Must be implemented by the subclass.
        """
        pass

    @abstractmethod
    def build_tool_response_section(self) -> str:
        """
        Build the tool response section for the template.
        Must be implemented by the subclass.
        """
        pass

    @abstractmethod
    def build_tools_section(self, full_body: bool = True) -> str:
        """
        Build the tools section for the template.
        Must be implemented by the subclass.
        """
        pass

    @abstractmethod
    def build_full_template(self) -> str:
        """
        Combine the system initial message, chat messages, and tools section into the full template.
        Must be implemented by the subclass.
        """
        pass
