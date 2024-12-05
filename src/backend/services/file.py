import io
import re
import os

from typing import Optional
import pandas as pd
from docx import Document
from fastapi import Depends, HTTPException
from fastapi import UploadFile as FastAPIUploadFile
from python_calamine.pandas import pandas_monkeypatch




import backend.crud.conversation as conversation_crud
import backend.crud.file as file_crud
from backend.crud import message as message_crud
from backend.database_models.conversation import ConversationFileAssociation
from backend.database_models.database import DBSessionDep, get_session
from backend.database_models.file import File as FileModel
from backend.database_models.folder import Folder
from backend.schemas.cohere_chat import CohereChatRequest
from backend.schemas.context import Context
from backend.schemas.file import ConversationFilePublic, File
from backend.services import utils
from backend.services.agent import validate_agent_exists
from backend.services.context import get_context
from backend.services.logger.utils import LoggerFactory
from backend.services.chat import generate_chat_response
# from backend.services.conversation import (
#     validate_conversation,
# )
from backend.schemas.agent import Agent
from backend.crud import agent as agent_crud


MAX_FILE_SIZE = 20_000_000  # 20MB
MAX_TOTAL_FILE_SIZE = 1_000_000_000  # 1GB

PDF_EXTENSION = "pdf"
TEXT_EXTENSION = "txt"
MARKDOWN_EXTENSION = "md"
CSV_EXTENSION = "csv"
TSV_EXTENSION = "tsv"
EXCEL_EXTENSION = "xlsx"
EXCEL_OLD_EXTENSION = "xls"
JSON_EXTENSION = "json"
DOCX_EXTENSION = "docx"
PARQUET_EXTENSION = "parquet"


DEFAULT_TITLE = ""
FOLDER_INFO_PROMPT_PART="""
This file is a part of a folder called {folder_name}.
in the path: {file_path}
"""
GENERATE_FILE_NAME_PROMPT = """# TASK
Given the following file information, write a short file name that summarizes the topic of file. Be concise and respond with just a generated file name that suites the file.

## START FILE Information
{folder_prompt_part}
The Original File name is: {file_name}
## END FILE Information

## START File Content
{file_content}
## END File Content

# TITLE
"""
GENERATE_FILE_SUMMARY_PROMPT = """# TASK
Given the following file information, write a concise summary of the file content in a very tiny 2-5 titles. Focus on the main Titles.

## START FILE Information
{folder_prompt_part}
The File name is: {file_name}
## END FILE Information

## START File Content
{file_content}
## END File Content

# SUMMARY
"""

# Monkey patch Pandas to use Calamine for Excel reading because Calamine is faster than Pandas
pandas_monkeypatch()

file_service = None

logger = LoggerFactory().get_logger()


def get_file_service():
    """
    Initialize a singular instance of FileService if not initialized yet

    Returns:
        FileService: The singleton FileService instance
    """
    global file_service
    if file_service is None:
        file_service = FileService()
    return file_service


class FileService:
    """
    FileService class

    This class manages interfacing with different file storage solutions,
    currently supports storing files in PostgreSQL.
    """

    async def create_conversation_files(
        self,
        session: DBSessionDep,
        files: list[FastAPIUploadFile],
        user_id: str,
        conversation_id: str,
        ctx: Context,
    ) -> list[File]:
        """
        Create files and associations with a conversation

        Args:
            session (DBSessionDep): The database session
            files (list[FastAPIUploadFile]): The files to upload
            user_id (str): The user ID
            conversation_id (str): The conversation ID
            ctx (Context): Context object

        Returns:
            list[File]: The files that were created
        """
        uploaded_files = await insert_files_in_db(session, files, user_id, conversation_id= conversation_id, ctx=ctx)

        for file in uploaded_files:
            conversation_crud.create_conversation_file_association(
                session,
                ConversationFileAssociation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    file_id=file.id,
                ),
            )

        return uploaded_files

    async def create_agent_files(
        self,
        session: DBSessionDep,
        files: list[FastAPIUploadFile],
        user_id: str,
        ctx: Context,
    ) -> list[File]:
        """
        Create files and associations with an agent

        Args:
            session (DBSessionDep): The database session
            files (list[FastAPIUploadFile]): The files to upload
            user_id (str): The user ID
        Returns:
            list[File]: The files that were created
        """
        uploaded_files = await insert_files_in_db(session, files, user_id)

        return uploaded_files


    def get_files_by_user_id(
            self, session: DBSessionDep, user_id: str, ctx: Context
        ) -> list[File]:
            """
            Get all files associated with a user that are not in any folder

            Args:
                session (DBSessionDep): The database session
                user_id (str): The user ID

            Returns:
                list[File]: The files created by the user that are not in any folder
            """
            # Get all files for the user
            files = file_crud.get_files_by_user_id(session, user_id)
            # Filter out files that have a folder_id
            files_without_folder = [file for file in files if not file.folder_id]

            return files_without_folder
    def get_files_by_agent_id(
        self, session: DBSessionDep, user_id: str, agent_id: str, ctx: Context
    ) -> list[File]:
        """
        Get files by agent ID

        Args:
            session (DBSessionDep): The database session
            user_id (str): The user ID
            agent_id (str): The agent ID

        Returns:
            list[File]: The files that were created
        """
        from backend.config.tools import ToolName
        from backend.tools.files import FileToolsArtifactTypes

        agent = validate_agent_exists(session, agent_id, user_id)

        files = []
        agent_tool_metadata = agent.tools_metadata
        if agent_tool_metadata is not None and len(agent_tool_metadata) > 0:
            artifacts = next(
                (
                    tool_metadata.artifacts
                    for tool_metadata in agent_tool_metadata
                    if tool_metadata.tool_name == ToolName.Read_File
                    or tool_metadata.tool_name == ToolName.Search_File
                ),
                [],  # Default value if the generator is empty
            )

            file_ids = list(
                {
                    artifact.get("id")
                    for artifact in artifacts
                    if artifact.get("type") == FileToolsArtifactTypes.local_file
                }
            )

            files = file_crud.get_files_by_ids(session, file_ids, user_id)

        return files
    
    
    def get_files_by_ids(self, files_ids: list[str], session: DBSessionDep = Depends(get_session), ctx: Context = Depends(get_context)):
        user_id = ctx.get_user_id()
        files = file_crud.get_files_by_ids(session, files_ids, user_id)

        return files

    def get_file_by_id(self, file_id: str, session: DBSessionDep = Depends(get_session), ctx: Context = Depends(get_context)):
        user_id = ctx.get_user_id()
        file = file_crud.get_file(session, file_id, user_id)

        return file
    
    
    
    def get_files_by_conversation_id(
        self, session: DBSessionDep, user_id: str, conversation_id: str, ctx: Context
    ) -> list[FileModel]:
        """
        Get files by conversation ID

        Args:
            session (DBSessionDep): The database session
            user_id (str): The user ID
            conversation_id (str): The conversation ID

        Returns:
            list[File]: The files that were created
        """
        conversation = conversation_crud.get_conversation(
            session, conversation_id, user_id
        )
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation with ID: {conversation_id} not found.",
            )
        file_ids = conversation.file_ids

        files = []
        if file_ids is not None:
            files = file_crud.get_files_by_ids(session, file_ids, user_id)

        return files
    
    def get_files_without_folders_by_conversation_id(
        self, session: DBSessionDep, user_id: str, conversation_id: str, ctx: Context
        ) -> list[FileModel]:
        """
        Get files by conversation ID that are not associated with any folder.

        Args:
            session (DBSessionDep): The database session
            user_id (str): The user ID
            conversation_id (str): The conversation ID

        Returns:
            list[FileModel]: The files that are not associated with any folder.
        """
        conversation = conversation_crud.get_conversation(
            session, conversation_id, user_id
        )
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation with ID: {conversation_id} not found.",
            )
        file_ids = conversation.file_ids

        files = []
        if file_ids is not None:
            # Retrieve files by their IDs
            all_files = file_crud.get_files_by_ids(session, file_ids, user_id)
            # Filter files that do not have a folder_id
            files = [file for file in all_files if not file.folder_id]

        return files


    def delete_conversation_file_by_id(
        self,
        session: DBSessionDep,
        conversation_id: str,
        file_id: str,
        user_id: str,
        ctx: Context,
    ) -> None:
        """
        Delete a file asociated with a conversation

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            file_id (str): The file ID
            user_id (str): The user ID
        """
        conversation_crud.delete_conversation_file_association(
            session, conversation_id, file_id, user_id
        )

        file_crud.delete_file(session, file_id, user_id)

        return

    def delete_agent_file_by_id(
        self,
        session: DBSessionDep,
        agent_id: str,
        file_id: str,
        user_id: str,
        ctx: Context,
    ) -> None:
        """
        Delete a file asociated with an agent

        Args:
            session (DBSessionDep): The database session
            agent_id (str): The agent ID
            file_id (str): The file ID
            user_id (str): The user ID
        """
        file_crud.delete_file(session, file_id, user_id)

        return

    def delete_all_conversation_files(
        self,
        session: DBSessionDep,
        conversation_id: str,
        file_ids: list[str],
        user_id: str,
        ctx: Context = Depends(get_context),
    ) -> None:
        """
        Delete all files associated with a conversation

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            file_ids (list[str]): The file IDs
            user_id (str): The user ID
            ctx (Context): Context object
        """
        logger = ctx.get_logger()

        logger.info(
                event=f"Deleting conversation {conversation_id} files from DB."
            )
        file_crud.bulk_delete_files(session, file_ids, user_id)

    def get_files_by_message_id(
        self, session: DBSessionDep, message_id: str, user_id: str, ctx: Context
    ) -> list[File]:
        """
        Get message files

        Args:
            session (DBSessionDep): The database session
            message_id (str): The message ID
            user_id (str): The user ID

        Returns:
            list[File]: The files that were created
        """
        message = message_crud.get_message(session, message_id, user_id)
        files = []
        if message.file_ids is not None:
            files = file_crud.get_files_by_ids(session, message.file_ids, user_id)

        return files
    
    # Files Folder Handling
    async def associate_files_to_folder(
        self,
        session: DBSessionDep,
        folder: Folder,
        user_id: str,
        files: list[FastAPIUploadFile],
        paths: list[str],
        names: list[str],
        conversation_id: str,
        ctx: Context = Depends(get_context),
    ) -> list:
        """
        Associates uploaded files to a specific folder.

        Args:
            session (DBSessionDep): The database session
            folder_id (str): The folder ID to associate files with
            user_id (str): The user ID
            files (list[FastAPIUploadFile]): A list of files to associate with the folder

        Returns:
            list: List of file metadata
        """
        associated_files: list[File] = []
        
        for index, file in enumerate(files):
            # Check file extension
            # _, extension = os.path.splitext(file.filename)
            # extension = extension[1:].lower()  # Get the file extension and convert to lower case
            
            # if extension not in SUPPORTED_EXTENSIONS:
            #     raise HTTPException(
            #         status_code=400,
            #         detail=f"File type {extension} is not supported."
            #     )

            # Save the file (You will need to implement this)
            # await self.save_file(file, file_location)
            saved_file = await insert_files_in_db(session, [file], user_id, folder=folder, path=paths[index], name=names[index], ctx=ctx, conversation_id=conversation_id)
            for file in saved_file:
                associated_files.append(file)

        return associated_files

    async def associate_file_with_conversation(
        self,
        session: DBSessionDep,
        conversation_id: str,
        file_id: str,
        user_id: str,
        ctx: Context,
    ) -> None:
        """
        Associate a file with a conversation.

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            file_id (str): The file ID
            user_id (str): The user ID
            ctx (Context): Context object
        """
        # Create the conversation file association
        conversation_crud.create_conversation_file_association(
            session,
            ConversationFileAssociation(
                conversation_id=conversation_id,
                user_id=user_id,
                file_id=file_id,
            ),
        )
        return

    async def deassociate_file_from_conversation(
        self,
        session: DBSessionDep,
        conversation_id: str,
        file_id: str,
        user_id: str,
        ctx: Context,
    ) -> None:
        """
        Deassociate a file from a conversation.

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            file_id (str): The file ID
            user_id (str): The user ID
            ctx (Context): Context object
        """
        # Delete the conversation file association
        conversation_crud.delete_conversation_file_association(
            session,
            conversation_id,
            file_id,
            user_id
        )
        return

# Misc
def validate_file(
    session: DBSessionDep, file_id: str, user_id: str
) -> File:
    """
    Validates if a file exists and belongs to the user

    Args:
        session (DBSessionDep): Database session
        file_id (str): File ID
        user_id (str): User ID

    Returns:
        File: File object

    Raises:
        HTTPException: If the file is not found
    """
    file = file_crud.get_file(session, file_id, user_id)

    if not file:
        raise HTTPException(
            status_code=404,
            detail=f"File with ID: {file_id} not found.",
        )
        
        
def sanitize_filename(filename: str) -> str:
    # Remove or replace any characters that are not alphanumeric, dash, underscore, or dot
    sanitized = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
    
    # Optionally truncate if filename is too long for some file systems
    return sanitized[:255] if len(sanitized) > 255 else sanitized


async def insert_files_in_db(
    session: DBSessionDep,
    files: list[FastAPIUploadFile],
    user_id: str,
    path: str = None,
    name: str = None,
    conversation_id: str = None,
    folder: Folder = None,
    ctx: Context = Depends(get_context),
) -> list[File]:
    """
    Insert files into the database

    Args:
        session (DBSessionDep): The database session
        files (list[FastAPIUploadFile]): The files to upload
        user_id (str): The user ID

    Returns:
        list[File]: The files that were created
    """
    files_to_upload = []
    for file in files:
        content = await get_file_content(file)
        cleaned_content = content.replace("\x00", "")
        if name:
            filename = name
        else:
            filename = file.filename
        
        filename = filename.encode("ascii", "ignore").decode("utf-8")
        _, extension = os.path.splitext(filename)
        
        # I found that file name sometimes affect the accuracy of the model.
        
        # filename = sanitize_filename(filename)
        
        conversation = conversation_crud.get_conversation(session, conversation_id, user_id)
        print("Conversation O User: ", conversation)
        try:
            agent_id = conversation.agent_id if conversation and conversation.agent_id else None

            if agent_id:
                agent = agent_crud.get_agent_by_id(session, agent_id, user_id)
                agent_schema = Agent.model_validate(agent)
                ctx.with_agent(agent_schema)
                deployment = agent.deployments[0]
                ctx.with_deployment_name(deployment.name)
                
            print("Agent ID GEN FILE: ", agent_id)
            print("Agent GEN FILE: ", agent)
            print("MODEL GEN FILE: ", agent.model)
        
            generated_file_name, error = await generate_file_name(session, file_name=filename, folder_name=folder.name if folder else None, file_content=content, path=path, agent_id=agent_id, ctx=ctx, model=agent.model)
            generated_summary, summary_error = await generate_file_summary(session, file_name=filename, folder_name=folder.name if folder else None, file_content=content, path=path, agent_id=agent_id, ctx=ctx, model=agent.model)
        except Exception as e:
            print("Error generating file name or summary: ", e)
            generated_file_name = filename
            generated_summary = ""
            
        file_generated_name = f"{generated_file_name}{extension}"
        # file_generated_name = content[0:64].replace(" ", "").encode("ascii", "ignore").decode("utf-8") + f"{extension}"
        file_generated_name = sanitize_filename(file_generated_name)
        
        files_to_upload.append(
            FileModel(
                file_name=filename,
                file_generated_name=file_generated_name,
                file_size=file.size,
                file_content=cleaned_content,
                file_summary=generated_summary,
                user_id=user_id,
                folder_id=folder.id if folder else None,
                path=path
            )
        )

    uploaded_files = file_crud.batch_create_files(session, files_to_upload)
    return uploaded_files


def attach_conversation_id_to_files(
    conversation_id: str, files: list[FileModel]
) -> list[ConversationFilePublic]:
    results = []
    for file in files:
        results.append(
            ConversationFilePublic(
                id=file.id,
                conversation_id=conversation_id,
                file_name=file.file_name,
                file_size=file.file_size,
                user_id=file.user_id,
                created_at=file.created_at,
                updated_at=file.updated_at,
            )
        )
    return results



def read_excel(file_contents: bytes) -> str:
    """Reads the text from an Excel file using Pandas

    Args:
        file_contents (bytes): The file contents

    Returns:
        str: The text extracted from the Excel
    """
    excel = pd.read_excel(io.BytesIO(file_contents), engine="calamine")
    return excel.to_string()


def read_docx(file_contents: bytes) -> str:
    """Reads the text from a DOCX file

    Args:
        file_contents (bytes): The file contents

    Returns:
        str: The text extracted from the DOCX file, with each paragraph separated by a newline
    """
    document = Document(io.BytesIO(file_contents))
    text = ""

    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"

    return text


def read_parquet(file_contents: bytes) -> str:
    """Reads the text from a Parquet file using Pandas

    Args:
        file_contents (bytes): The file contents

    Returns:
        str: The text extracted from the Parquet
    """
    parquet = pd.read_parquet(io.BytesIO(file_contents), engine="pyarrow")
    return parquet.to_string()



def get_file_extension(file_name: str) -> str:
    """Returns the file extension

    Args:
        file_name (str): The file name

    Returns:
        str: The file extension
    """
    return file_name.split(".")[-1].lower()


async def get_file_content(file: FastAPIUploadFile) -> str:
    """Reads the file contents based on the file extension

    Args:
        file (UploadFile): The file to read

    Returns:
        str: The file contents

    Raises:
        ValueError: If the file extension is not supported
    """
    file_contents = await file.read()
    file_extension = get_file_extension(file.filename)

    if file_extension == PDF_EXTENSION:
        return utils.read_pdf(file_contents)
    elif file_extension == DOCX_EXTENSION:
        return read_docx(file_contents)
    elif file_extension == PARQUET_EXTENSION:
        return read_parquet(file_contents)
    elif file_extension in [
        TEXT_EXTENSION,
        MARKDOWN_EXTENSION,
        CSV_EXTENSION,
        TSV_EXTENSION,
        JSON_EXTENSION,
    ]:
        return file_contents.decode("utf-8")
    elif file_extension in [EXCEL_EXTENSION, EXCEL_OLD_EXTENSION]:
        return read_excel(file_contents)

    raise ValueError(f"File extension {file_extension} is not supported")


async def generate_file_name(
    session: DBSessionDep,
    file_name: str,
    file_content: str,
    agent_id: str,
    path: str | None,
    folder_name: str | None = None,
    ctx: Context = Depends(get_context),
    model: Optional[str] = "command-r",
) -> tuple[str, str | None]:
    """Generate a title for a conversation

    Args:
        request: Request object
        session: Database session
        conversation: Conversation object
        model_config: Model configuration
        agent_id: Agent ID
        ctx: Context object
        model: Model name

    Returns:
        str: Generated title
        str: Error message
    """
    
    from backend.chat.custom.custom import CustomChat
    
    user_id = ctx.get_user_id()
    logger = ctx.get_logger()
    generated_file_name = ""
    error = None

    # try:
    folder_prompt_part = ""
    if path and folder_name:
        folder_prompt_part = FOLDER_INFO_PROMPT_PART.format(folder_name=folder_name, file_path=path)
    prompt = GENERATE_FILE_NAME_PROMPT.format(file_content=file_content, file_path=path, file_name=file_name, folder_prompt_part=folder_prompt_part)
    # prompt = GENERATE_FILE_NAME_PROMPT % file_content
    chat_request = CohereChatRequest(
        message=prompt,
        model=model,
    )

    response = await generate_chat_response(
        session,
        CustomChat().chat(
            chat_request,
            stream=False,
            agent_id=agent_id,
            ctx=ctx,
        ),
        response_message=None,
        conversation_id=None,
        user_id=user_id,
        should_store=False,
        ctx=ctx,
    )
    
    generated_file_name = response.text
    error = response.error
    # except Exception as e:
    #     generated_file_name = DEFAULT_TITLE
    #     error = str(e)
    #     logger.error(
    #         event=f"[Conversation] Error generating file name: File, {e}",
    #     )

    return generated_file_name, error

async def generate_file_summary(
    session: DBSessionDep,
    file_name: str,
    file_content: str,
    agent_id: str,
    path: str | None,
    folder_name: str | None = None,
    ctx: Context = Depends(get_context),
    model: Optional[str] = "command-r",
) -> tuple[str, str | None]:
    """Generate a summary for a file

    Args:
        session: Database session
        file_name: Name of the file
        file_content: Content of the file
        agent_id: Agent ID
        path: File path
        folder_name: Name of the folder containing the file
        ctx: Context object
        model: Model name

    Returns:
        str: Generated summary
        str: Error message
    """
    from backend.chat.custom.custom import CustomChat
    
    user_id = ctx.get_user_id()
    logger = ctx.get_logger()
    generated_summary = ""
    error = None

    folder_prompt_part = ""
    if path and folder_name:
        folder_prompt_part = FOLDER_INFO_PROMPT_PART.format(folder_name=folder_name, file_path=path)
    
    prompt = GENERATE_FILE_SUMMARY_PROMPT.format(
        file_content=file_content,
        file_path=path,
        file_name=file_name,
        folder_prompt_part=folder_prompt_part
    )

    chat_request = CohereChatRequest(
        message=prompt,
        model=model,
    )

    response = await generate_chat_response(
        session,
        CustomChat().chat(
            chat_request,
            stream=False,
            agent_id=agent_id,
            ctx=ctx,
        ),
        response_message=None,
        conversation_id=None,
        user_id=user_id,
        should_store=False,
        ctx=ctx,
    )
    
    generated_summary = response.text
    error = response.error

    return generated_summary, error
