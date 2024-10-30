from backend.services.template_builder.models_templates.llama31 import Llama31TemplateBuilder
from backend.services.template_builder.models_templates.llama32 import Llama32TemplateBuilder
from backend.services.template_builder.models_templates.qwen import QwenTemplateBuilder
from backend.services.template_builder.models_templates.default_template import DefaultTemplateBuilder
from backend.services.template_builder.models_templates.base import BaseTemplateBuilder

from typing import Any, List, Type
from openai.types.chat import ChatCompletionSystemMessageParam

class TemplateBuilderFactory:
    # Map of template names to their respective classes
    templates = {
        "llama3.1": Llama31TemplateBuilder,
        "llama3.2": Llama32TemplateBuilder,
        "qwen": QwenTemplateBuilder,
        # Add more templates here as needed
    }

    @classmethod
    def get_template_builder(cls, template_name: str, chat_messages: List[ChatCompletionSystemMessageParam], tools: List[dict] = [], tool_response: Any = None) -> BaseTemplateBuilder:
        """
        Retrieve the template class by name, or fallback to DefaultTemplateBuilder.
        
        :param template_name: The name of the template to use (e.g., "llama").
        :param chat_messages: A list of chat messages.
        :param tools: A list of tools to include in the template.
        :param tool_response: The response from the tools (if any).
        :return: An instance of the selected template class or DefaultTemplateBuilder.
        """
        if not template_name:
            template_name = "llama3.1"
            
        template_class: Type[BaseTemplateBuilder] = cls.templates.get(template_name, DefaultTemplateBuilder)
        return template_class(chat_messages=chat_messages, tools=tools, tool_response=tool_response)

    @classmethod
    def build_full_template(cls, template_name: str, chat_messages: List[ChatCompletionSystemMessageParam], tools: List[dict] = [], tool_response: Any = None) -> str:
        """
        Retrieve the template class by name, or fallback to DefaultTemplateBuilder.
        
        :param template_name: The name of the template to use (e.g., "llama").
        :param chat_messages: A list of chat messages.
        :param tools: A list of tools to include in the template.
        :param tool_response: The response from the tools (if any).
        :return: An instance of the selected template class or DefaultTemplateBuilder.
        """
        template_class: Type[BaseTemplateBuilder] = cls.templates.get(template_name, DefaultTemplateBuilder)
        return template_class(chat_messages=chat_messages, tools=tools, tool_response=tool_response).build_full_template()
    # @classmethod
    # def register_template(cls, template_name: str, template_class: Type[BaseTemplateBuilder]) -> None:
    #     """
    #     Register a new template class under a specific name.
        
    #     :param template_name: The name of the template to register.
    #     :param template_class: The template class to register.
    #     """
    #     cls.templates[template_name] = template_class
