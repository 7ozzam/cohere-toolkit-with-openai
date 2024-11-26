from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Dict, List, Union, TypeVar
from uuid import uuid4

# from cohere import ChatStreamEndEventFinishReason, NonStreamedChatResponse, StreamEndStreamedChatResponse
from pydantic import BaseModel, Field

from backend.chat.enums import StreamEvent
from backend.schemas.citation import Citation
from backend.schemas.document import Document
from backend.schemas.search_query import SearchQuery
from backend.schemas.tool import Tool, ToolCall, ToolCallDelta


import typing_extensions


@dataclass
class EventState:
    distances_plans: list
    distances_actions: list
    previous_plan: str
    previous_action: str

class ChatRole(StrEnum):
    """One of CHATBOT|USER|SYSTEM to identify who the message is coming from."""

    CHATBOT = "CHATBOT"
    USER = "USER"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"


class ChatCitationQuality(StrEnum):
    """Dictates the approach taken to generating citations by allowing the user to specify whether they want "accurate" results or "fast" results. Defaults to "accurate"."""

    FAST = "FAST"
    ACCURATE = "ACCURATE"


class ToolInputType(StrEnum):
    """Type of input passed to the tool"""

    QUERY = "QUERY"
    CODE = "CODE"


class ChatMessage(BaseModel):
    """A list of previous messages between the user and the model, meant to give the model conversational context for responding to the user's message."""

    role: ChatRole = Field(
        title="One of CHATBOT|USER|SYSTEM to identify who the message is coming from.",
    )
    message: str | None = Field(
        title="Contents of the chat message.",
        default=None,
    )
    tool_plan: str | None = Field(
        title="Contents of the tool plan.",
        default=None,
    )
    tool_results: List[Dict[str, Any]] | None = Field(
        title="Results from the tool call.",
        default=None,
    )
    tool_calls: List[Dict[str, Any]] | None = Field(
        title="List of tool calls generated for custom tools",
        default=None,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "message": self.message,
            "tool_results": self.tool_results,
            "tool_calls": self.tool_calls,
        }


# TODO: fix titles of these types
class ChatResponse(BaseModel):
    event_type: StreamEvent = Field()


class StreamStart(ChatResponse):
    """Stream start event."""
    event_type: StreamEvent = StreamEvent.STREAM_START
    generation_id: str | None = Field(default=None)
    conversation_id: str | None = Field(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.STREAM_START

class StreamTextGeneration(ChatResponse):
    """Stream text generation event."""
    event_type: StreamEvent = StreamEvent.TEXT_GENERATION
    text: str = Field(title="Contents of the chat message.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.TEXT_GENERATION

class StreamCitationGeneration(ChatResponse):
    """Stream citation generation event."""
    event_type: StreamEvent = StreamEvent.CITATION_GENERATION
    citations: List[Citation] = Field(title="Citations for the chat message.", default=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.CITATION_GENERATION

class StreamQueryGeneration(ChatResponse):
    """Stream query generation event."""
    event_type: StreamEvent = StreamEvent.SEARCH_QUERIES_GENERATION
    query: str = Field(title="Search query used to generate grounded response with citations.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.SEARCH_QUERIES_GENERATION

class StreamSearchResults(ChatResponse):
    """Stream search results event."""
    event_type: StreamEvent = StreamEvent.SEARCH_RESULTS
    search_results: List[Dict[str, Any]] = Field(title="Search results.", default=[])
    documents: List[Document] = Field(title="Documents used to generate grounded response with citations.", default=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.SEARCH_RESULTS

class StreamToolInput(ChatResponse):
    """Stream tool input event."""
    event_type: StreamEvent = StreamEvent.TOOL_INPUT
    input_type: ToolInputType
    tool_name: str
    input: str
    text: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.TOOL_INPUT

class StreamToolResult(ChatResponse):
    """Stream tool result event."""
    event_type: StreamEvent = StreamEvent.TOOL_RESULT
    result: Any
    tool_name: str
    documents: List[Document] = Field(title="Documents used to generate grounded response with citations.", default=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.TOOL_RESULT

class StreamSearchQueriesGeneration(ChatResponse):
    """Stream queries generation event."""
    event_type: StreamEvent = StreamEvent.SEARCH_QUERIES_GENERATION
    search_queries: List[SearchQuery] = Field(title="Search queries for grounded response.", default=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.SEARCH_QUERIES_GENERATION

class StreamToolCallsGeneration(ChatResponse):
    """Stream tool calls generation event."""
    event_type: StreamEvent = StreamEvent.TOOL_CALLS_GENERATION
    stream_search_results: StreamSearchResults | None = Field(default=None)
    tool_calls: List[ToolCall] | None = Field(default=[])
    text: str | None = Field(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.TOOL_CALLS_GENERATION

class StreamInlineFix(ChatResponse):
    """Stream tool calls generation event."""
    event_type: StreamEvent = StreamEvent.INLINE_FIX
    text: str | None = Field(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.INLINE_FIX


class NonStreamedChatResponse(ChatResponse):
    event_type: StreamEvent = StreamEvent.NON_STREAMED_CHAT_RESPONSE
    
    response_id: str | None = Field(
        title="Unique identifier for the response.", default=None
    )
    generation_id: str | None = Field(
        title="Unique identifier for the generation.", default=None
    )
    chat_history: List[ChatMessage] | None = Field(
        title="A list of previous messages between the user and the model, meant to give the model conversational context for responding to the user's message.",
    )
    finish_reason: str = Field(
        title="Reason the chat stream ended.",
    )
    text: str | None = Field(
        title="Contents of the chat message.",
    )
    citations: List[Citation] | None = Field(
        title="Citations for the chat message.",
        default=[],
    )
    documents: List[Document] | None = Field(
        title="Documents used to generate grounded response with citations.",
        default=[],
    )
    search_results: List[Dict[str, Any]] | None = Field(
        title="Search results used to generate grounded response with citations.",
        default=[],
    )
    search_queries: List[SearchQuery] | None = Field(
        title="List of generated search queries.",
        default=[],
    )
    conversation_id: str | None = Field(
        title="To store a conversation then create a conversation id and use it for every related request.", default=None
    )
    tool_calls: List[ToolCall] | None = Field(
        title="List of tool calls generated for custom tools",
        default=[],
    )
    error: str | None = Field(
        title="Error message if the response is an error.",
        default=None,
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.NON_STREAMED_CHAT_RESPONSE

class StreamEnd(ChatResponse):
    message_id: str | None = Field(default=None)
    response_id: str | None = Field(default=None)
    event_type: StreamEvent = StreamEvent.STREAM_END
    generation_id: str | None = Field(default=None)
    conversation_id: str | None = Field(default=None)
    text: str = Field(
        title="Contents of the chat message.",
        default="",
    )
    response: NonStreamedChatResponse = Field(
        title="The Whole Response.", default=None
    )
    citations: List[Citation] = Field(
        title="Citations for the chat message.", default=[]
    )
    documents: List[Document] = Field(
        title="Documents used to generate grounded response with citations.",
        default=[],
    )
    search_results: List[Dict[str, Any]] = Field(
        title="Search results used to generate grounded response with citations.",
        default=[],
    )
    search_queries: List[SearchQuery] = Field(
        title="List of generated search queries.",
        default=[],
    )
    tool_calls: List[ToolCall] = Field(
        title="List of tool calls generated for custom tools",
        default=[],
    )
    finish_reason: str | None = (Field(default=None),)
    chat_history: List[ChatMessage] | None = Field(
        default=None,
        title="A list of entries used to construct the conversation. If provided, these messages will be used to build the prompt and the conversation_id will be ignored so no data will be stored to maintain state.",
    )
    error: str | None = Field(
        title="Error message if the response is an error.",
        default=None,
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.STREAM_END
        
class StreamToolCallsChunk(ChatResponse):
    event_type: StreamEvent = StreamEvent.TOOL_CALLS_CHUNK
    part_to_remove: str = Field(
        title="Partial to be removed from generation stream", default=None
    )
    tool_call_delta: ToolCallDelta | None = Field(
        title="Partial tool call",
        default=ToolCallDelta(
            name=None,
            index=None,
            parameters=None,
        ),
    )

    text: str | None = Field(
        title="Contents of the chat message.",
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.event_type = StreamEvent.TOOL_CALLS_CHUNK

class UnionMetadata:
    discriminant: str

    def __init__(self, *, discriminant: str) -> None:
        self.discriminant = discriminant


# Model = TypeVar("Model", bound=pydantic.BaseModel)


StreamedChatEvent = typing_extensions.Annotated[
    Union[
        StreamStart,
        StreamTextGeneration,
        StreamCitationGeneration,
        StreamQueryGeneration,
        StreamSearchResults,
        StreamEnd,
        StreamToolInput,
        StreamToolResult,
        StreamSearchQueriesGeneration,
        StreamToolCallsGeneration,
        StreamToolCallsChunk,
        NonStreamedChatResponse,
        StreamInlineFix
    ],
    Field(discriminator='event_type')
]

StreamEventType = Union[
    StreamStart,
    StreamTextGeneration,
    StreamCitationGeneration,
    StreamQueryGeneration,
    StreamSearchResults,
    StreamEnd,
    StreamToolInput,
    StreamToolResult,
    StreamSearchQueriesGeneration,
    StreamToolCallsGeneration,
    StreamToolCallsChunk,
    NonStreamedChatResponse,
    StreamInlineFix
    
]


class ChatResponseEvent(BaseModel):
    event: StreamEvent = Field(
        title="type of stream event",
    )

    data: StreamEventType = Field(
        title="Data returned from chat response of a given event type",
    )


class BaseChatRequest(BaseModel):
    message: str = Field(
        title="The message to send to the chatbot.",
    )
    chat_history: List[ChatMessage] | None = Field(
        default=None,
        title="A list of entries used to construct the conversation. If provided, these messages will be used to build the prompt and the conversation_id will be ignored so no data will be stored to maintain state.",
    )
    conversation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        title="To store a conversation then create a conversation id and use it for every related request",
    )
    tools: List[Tool] | None = Field(
        default_factory=list,
        title="""
            List of custom or managed tools to use for the response.
            If passing in managed tools, you only need to provide the name of the tool.
            If passing in custom tools, you need to provide the name, description, and optionally parameter defintions of the tool.
            Passing a mix of custom and managed tools is not supported.

            Managed Tools Examples:
            tools=[
                {
                    "name": "Wiki Retriever - LangChain",
                },
                {
                    "name": "Calculator",
                }
            ]

            Custom Tools Examples:
            tools=[
                {
                    "name": "movie_title_generator",
                    "description": "tool to generate a cool movie title",
                    "parameter_definitions": {
                        "synopsis": {
                            "description": "short synopsis of the movie",
                            "type": "str",
                            "required": true
                        }
                    }
                },
                {
                    "name": "random_number_generator",
                    "description": "tool to generate a random number between min and max",
                    "parameter_definitions": {
                        "min": {
                            "description": "minimum number",
                            "type": "int",
                            "required": true
                        },
                        "max": {
                            "description": "maximum number",
                            "type": "int",
                            "required": true
                        }
                    }
                },
                {
                    "name": "joke_generator",
                    "description": "tool to generate a random joke",
                }
            ]
        """,
    )
