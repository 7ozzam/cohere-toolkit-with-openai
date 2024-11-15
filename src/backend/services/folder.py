import os
from fastapi import HTTPException
import backend.crud.folder as folder_crud
import backend.crud.file as file_crud
from backend.database_models.folder import Folder
from backend.services.file import sanitize_filename
from backend.database_models.conversation import ConversationFolderAssociation
# from backend.database_models.agent import AgentFolderAssociation

from backend.services.logger.utils import LoggerFactory
from backend.database_models.database import DBSessionDep
from backend.schemas.context import Context

logger = LoggerFactory().get_logger()

class FolderService:
    """
    FolderService class to manage folder operations
    """

    def __init__(self):
        pass

    async def create_folder(
        self, session: DBSessionDep, folder_name: str, user_id: str, ctx: Context
    ) -> Folder:
        """
        Create a new folder

        Args:
            session (DBSessionDep): The database session
            folder_name (str): The name of the folder to create
            user_id (str): The user ID
            ctx (Context): Context object

        Returns:
            Folder: The created folder
        """
        sanitized_folder_name = sanitize_filename(folder_name)
        folder = Folder(folder_name=sanitized_folder_name, user_id=user_id)

        folder = folder_crud.create_folder(session, folder)

        return folder

    def get_folders_by_user_id(
        self, session: DBSessionDep, user_id: str, ctx: Context
    ) -> list[Folder]:
        """
        Get all folders associated with a user

        Args:
            session (DBSessionDep): The database session
            user_id (str): The user ID

        Returns:
            list[Folder]: The folders created by the user
        """
        folders = folder_crud.get_folders_by_user_id(session, user_id)

        return folders

    def get_folders_by_conversation_id(
        self, session: DBSessionDep, user_id: str, conversation_id: str, ctx: Context
    ) -> list[Folder]:
        """
        Get all folders associated with a conversation

        Args:
            session (DBSessionDep): The database session
            user_id (str): The user ID
            conversation_id (str): The conversation ID

        Returns:
            list[Folder]: The folders associated with the conversation
        """
        conversation_folders = folder_crud.get_conversation_folder_associations(session, conversation_id, user_id)
        folder_ids = [association.folder_id for association in conversation_folders]

        folders = folder_crud.get_folders_by_ids(session, folder_ids, user_id)

        return folders

    async def associate_folder_with_conversation(
        self,
        session: DBSessionDep,
        conversation_id: str,
        folder_id: str,
        user_id: str,
        ctx: Context
    ) -> None:
        """
        Associate a folder with a conversation

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            folder_id (str): The folder ID to associate
            user_id (str): The user ID
        """
        folder_crud.create_conversation_folder_association(
            session, conversation_id=conversation_id, folder_id=folder_id, user_id=user_id
        )

    # async def associate_folder_with_agent(
    #     self,
    #     session: DBSessionDep,
    #     agent_id: str,
    #     folder_id: str,
    #     user_id: str,
    #     ctx: Context
    # ) -> None:
    #     """
    #     Associate a folder with an agent

    #     Args:
    #         session (DBSessionDep): The database session
    #         agent_id (str): The agent ID
    #         folder_id (str): The folder ID to associate
    #         user_id (str): The user ID
    #     """
    #     folder_crud.create_agent_folder_association(
    #         session, AgentFolderAssociation(agent_id=agent_id, folder_id=folder_id, user_id=user_id)
    #     )

    def delete_folder_by_id(
        self,
        session: DBSessionDep,
        folder_id: str,
        user_id: str,
        ctx: Context
    ) -> None:
        """
        Delete a folder by its ID

        Args:
            session (DBSessionDep): The database session
            folder_id (str): The folder ID to delete
            user_id (str): The user ID
        """
        folder_crud.delete_folder(session, folder_id, user_id)

    def delete_all_folders_by_conversation_id(
        self,
        session: DBSessionDep,
        conversation_id: str,
        folder_ids: list[str],
        user_id: str,
        ctx: Context
    ) -> None:
        """
        Delete all folders associated with a conversation

        Args:
            session (DBSessionDep): The database session
            conversation_id (str): The conversation ID
            folder_ids (list[str]): The list of folder IDs to delete
            user_id (str): The user ID
        """
        folder_crud.bulk_delete_folders(session, folder_ids, user_id)

    # def attach_conversation_id_to_folders(
    #     self, conversation_id: str, folders: list[Folder]
    # ) -> list[ConversationFolderPublic]:
    #     """
    #     Attach conversation ID to folders for response

    #     Args:
    #         conversation_id (str): The conversation ID
    #         folders (list[FolderModel]): List of folders to associate

    #     Returns:
    #         list[ConversationFolderPublic]: The response format
    #     """
    #     results = []
    #     for folder in folders:
    #         results.append(
    #             ConversationFolderPublic(
    #                 id=folder.id,
    #                 conversation_id=conversation_id,
    #                 folder_name=folder.folder_name,
    #                 user_id=folder.user_id,
    #                 created_at=folder.created_at,
    #                 updated_at=folder.updated_at,
    #             )
    #         )
    #     return results
