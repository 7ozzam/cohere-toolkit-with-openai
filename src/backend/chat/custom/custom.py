from typing import Any, AsyncGenerator, Dict, List

from fastapi import HTTPException

from backend.chat.base import BaseChat
from backend.chat.custom.tool_calls import async_call_tools
from backend.chat.custom.utils import get_deployment
from backend.chat.enums import StreamEvent
from backend.config.tools import AVAILABLE_TOOLS
from backend.database_models.file import File
from backend.model_deployments.base import BaseDeployment
from backend.schemas.chat import ChatMessage, ChatRole, EventState
from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.context import Context
from backend.schemas.tool import Category, Tool
from backend.services.chat import check_death_loop
from backend.services.file import get_file_service
from backend.services.folder import get_folder_service
from backend.tools.utils.tools_checkers import tool_has_category
from backend.crud import model as model_crud
from backend.database_models import Model

from backend.crud import deployment as deployment_crud
from backend.database_models import Deployment
# from backend.database_models.deployment import 
from backend.database_models.database import DBSessionDep



MAX_STEPS = 15


class CustomChat(BaseChat):
    """Custom chat flow not using integrations for models."""

    event_state = EventState(
        distances_plans=[],
        distances_actions=[],
        previous_plan="",
        previous_action="",
    )

    async def chat(
        self,
        chat_request: CohereChatRequest,
        ctx: Context,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, Any]:
        """
        Chat flow for custom models.

        Args:
            chat_request (CohereChatRequest): Chat request.
            ctx (Context): Context.
            **kwargs (Any): Keyword arguments.

        Returns:
            Generator[StreamResponse, None, None]: Chat response.
        """
        
        logger = ctx.get_logger()
        # TODO Eugene: Discuss with Scott how to get agent here and use the Agent deployment
        # Choose the deployment model - validation already performed by request validator
        agent_id = ctx.get_agent_id()
        deployment = []
        deployment_name = ctx.get_deployment_name() or ''
        
        if agent_id:
            try:
                if (kwargs.get('session')):
                    session: Any = kwargs.get('session')
                    deployment = deployment_crud.get_deployments_by_agent_id(db=session, agent_id=agent_id or '')
            except Exception as e:
                raise HTTPException(status_code=400, detail="Agent Get Deployments Error: " + str(e))
        
        if len(deployment):
            deployment_name = deployment[0].name
        
        
        # model = model_crud.get_model(session, model_id)
        
        print("===================================================")
        print(ctx)
        print(deployment)
        print(agent_id)
        print("===================================================")
        
        deployment_model = get_deployment(deployment_name, ctx)

        # Bind the logger with the conversation ID
        logger.debug(
            event=f"[Custom Chat] Using deployment: {deployment_model.__class__.__name__}",
        )

        if len(chat_request.tools) > 0 and len(chat_request.documents) > 0:
            raise HTTPException(
                status_code=400, detail="Both tools and documents cannot be provided."
            )

        self.chat_request = chat_request
        self.is_first_start = True

        try:
            stream = self.call_chat(self.chat_request, deployment_model, ctx, **kwargs)

            async for event in stream:
                result = self.handle_event(event, chat_request, ctx)

                if result:
                    yield result

                if (event["event_type"] == StreamEvent.STREAM_END
                and self.is_final_event(event, chat_request)):
                    logger.debug(event=f"Final event: {event}")
                    break
        except Exception as e:
            logger.exception(
                event="[Custom Chat] Error occurred during chat stream",
                error=str(e),
            )
            yield {
                "event_type": StreamEvent.STREAM_END,
                "finish_reason": "ERROR",
                "error": str(e),
                "status_code": 500,
            }

    def is_final_event(
        self, event: Dict[str, Any], chat_request: CohereChatRequest
    ) -> bool:
        # The event is final if:
        # 1. It is a stream end event with no tool calls - direct answer
        # 2. It is a stream end event with tool calls, but no managed tools - tool calls generation only
        if "response" in event:
            response = event["response"]
        else:
            return True

        return not ("tool_calls" in response and response["tool_calls"]) or (
            "tool_calls" in response
            and response["tool_calls"]
            and chat_request.tools
            and not self.get_managed_tools(self.chat_request)
        )

    def handle_event(
        self, event: Dict[str, Any], chat_request: CohereChatRequest, ctx: Context
    ) -> Dict[str, Any]:
        # All events other than stream start and stream end are returned
        if (
            event["event_type"] != StreamEvent.STREAM_START
            and event["event_type"] != StreamEvent.STREAM_END
            and event["event_type"] != StreamEvent.TOOL_CALLS_GENERATION
        ):
            return event

        # If the event is a tool call generation, we need to check if the tool call is similar to previous tool calls
        if event["event_type"] == StreamEvent.TOOL_CALLS_GENERATION:
            self.event_state = check_death_loop(event, self.event_state, ctx)
            return event

        # Only the first occurrence of stream start is returned
        if event["event_type"] == StreamEvent.STREAM_START:
            if self.is_first_start:
                self.is_first_start = False
                return event

        # Only the final occurrence of stream end is returned
        # The final event is the one that does not contain tool calls
        if event["event_type"] == StreamEvent.STREAM_END:
            if self.is_final_event(event, chat_request):
                return event

        return None

    def is_not_direct_answer(self, event: Dict[str, Any]) -> bool:
        # If the event contains tool calls, it is not a direct answer
        return (
            event["event_type"] == StreamEvent.TOOL_CALLS_GENERATION
            and "tool_calls" in event
        )

    async def call_chat(
        self,
        chat_request: CohereChatRequest,
        deployment_model: BaseDeployment,
        ctx: Context,
        **kwargs: Any,
    ):
        logger = ctx.get_logger()
        managed_tools = self.get_managed_tools(chat_request)
        managed_tools_full_schema = self.get_managed_tools(chat_request, full_schema=True)
        session = kwargs.get("session")
        user_id = ctx.get_user_id()
        agent_id = ctx.get_agent_id()

        file_reader_tools_names = []
        if managed_tools:
            chat_request.tools = managed_tools
            file_reader_tools_names = [tool.name for tool in managed_tools_full_schema if tool_has_category(tool, Category.FileLoader)]

        # Get files if available
        all_files = []
        if chat_request.file_ids or chat_request.agent_id:
            if file_reader_tools_names:
                files = get_file_service().get_files_by_conversation_id(
                    session, user_id, ctx.get_conversation_id(), ctx
                )
                
                folders = get_folder_service().get_folders_by_conversation_id(
                    session, user_id, ctx.get_conversation_id(), ctx)
                folders_files = sorted([file for folder in folders for file in folder.files], key=lambda x: x.path or '')

                agent_files = []
                if agent_id:
                    agent_files = get_file_service().get_files_by_agent_id(
                        session, user_id, agent_id, ctx
                    )

                all_files = files + agent_files + folders_files
        print("all_files: ", all_files)
        # Add files to chat history if there are any
        # Otherwise, remove the Read_File and Search_File tools and all other FileReader tools
        if all_files:
            chat_request.chat_history = self.add_files_to_chat_history(
                chat_request.chat_history,
                session,
                files + agent_files + folders_files,
            )
        else:
            chat_request.tools = [
                tool
                for tool in chat_request.tools
                if tool.name not in file_reader_tools_names
            ]

        # Loop until there are no new tool calls
        for step in range(MAX_STEPS):
            logger.debug(
                event=f"[Custom Chat] Chat request: {chat_request.model_dump()}",
                step=step + 1,
            )

            # Invoke chat stream
            has_tool_calls = False
            async for event in deployment_model.invoke_chat_stream(
                chat_request,
                ctx,
            ):
                if event["event_type"] == StreamEvent.STREAM_END:
                    print("HistoryUpdated", event)
                    chat_request.chat_history = event["response"].get(
                        "chat_history", []
                    )
                elif event["event_type"] == StreamEvent.TOOL_CALLS_GENERATION:
                    has_tool_calls = True

                yield event

            logger.info(
                event=f"[Custom Chat] Chat stream completed: Has tool calls {has_tool_calls}",
            )

            # Check for new tool calls in the chat history
            if has_tool_calls:
                # Handle tool calls
                tool_results = await async_call_tools(
                    chat_request.chat_history, deployment_model, ctx, **kwargs
                )

                # Remove the message if tool results are present
                if tool_results:
                    chat_request.tool_results = list(tool_results)
                    # toolMessage =  ChatMessage(role=ChatRole.SYSTEM, message="", tool_results=tool_results)
                    # searchResultChunk = StreamSearchResults(search_results=tool_results, documents=[])
                    
                    if chat_request.chat_history and len(chat_request.chat_history) > 0:
                        # chat_request.chat_history.append(toolMessage)
                        chat_request.message = ""
                    
            else:
                break  # Exit loop if there are no new tool calls

        # Restore the original chat request message if needed
        self.chat_request = chat_request

    def update_chat_history_with_tool_results(
        self, chat_request: Any, tool_results: List[Dict[str, Any]]
    ):
        if not hasattr(chat_request, "chat_history"):
            chat_request.chat_history = []

        chat_request.chat_history.extend(tool_results)

    def get_managed_tools(self, chat_request: CohereChatRequest, full_schema=False):
        if full_schema:
            return [
                AVAILABLE_TOOLS.get(tool.name)
                for tool in chat_request.tools
                if AVAILABLE_TOOLS.get(tool.name)
            ]

        return [
            Tool(**AVAILABLE_TOOLS.get(tool.name).model_dump())
            for tool in chat_request.tools
            if AVAILABLE_TOOLS.get(tool.name)
        ]

    def add_files_to_chat_history(
        self,
        chat_history: List[Dict[str, str]],
        session: Any,
        files: list[File],
    ) -> List[Dict[str, str]]:
        if session is None or len(files) == 0:
            return chat_history

        files_message = "The user uploaded the following files:\n"

        for file in files:
            word_count = len(file.file_content.split())

            # Use the first 25 words as the document preview in the preamble
            num_words = min(25, word_count)
            preview = " ".join(file.file_content.split()[:num_words])
            file_smmary = ""
            folder_info = ""
            if file.folder and file.folder.name and file.path:
            # Construct folder info
                file_smmary = f'"file_summary": """Read the file to see it\'s content, the summary is just an indicator don\'t use it for answer :\n\n {file.file_summary}""", '
                folder_info = f'"folder_name": "{file.folder.name}", '
                if file.path:
                    folder_info += f'"file_path": "{file.path}", '
            else:
                # Empty folder info if the condition is not met
                folder_info = ""

            # Construct the file message
            files_message += (
                f'"filename": "{file.file_name}", '
                f'"file_id": "{file.id}", '
                f'{folder_info}'  # Append folder info dynamically
                f'"word_count": {word_count}, '
                f'{file_smmary}'
                # f'"preview": "{preview}"}}\n'
            )

            # files_message += f'Filename: "{file.file_name}"\nFile ID: "{file.id}"\nWord Count: {word_count} Preview: {preview}\n\n'

        chat_history.append(ChatMessage(message=files_message, role=ChatRole.SYSTEM))
        return chat_history
