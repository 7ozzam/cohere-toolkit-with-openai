from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from backend.database_models.folder import Folder
from backend.database_models.conversation import ConversationFolderAssociation
from backend.services.transaction import validate_transaction


@validate_transaction
def create_folder(db: Session, folder:Folder, conversation_id: str, user_id: str) -> Folder:
    """
    Create a new folder.

    Args:
        db (Session): Database session.
        folder_name (str): The name of the folder to create.
        user_id (str): The user ID.
        description (str, optional): Folder description. Defaults to "".

    Returns:
        Folder: The created folder.
    """
    folder = Folder(name=folder.name, user_id=folder.user_id, description=folder.description)
    
    db.add(folder)
    db.commit()
    db.refresh(folder)
    
   
    
    return folder

@validate_transaction
def associate_folder_with_conversation(db: Session, folder_id:str, conversation_id: str, user_id: str) -> ConversationFolderAssociation:
    """
    Create a new folder.

    Args:
        db (Session): Database session.
        folder_name (str): The name of the folder to create.
        user_id (str): The user ID.
        description (str, optional): Folder description. Defaults to "".

    Returns:
        Folder: The created folder.
    """
    conversation_folder_association = ConversationFolderAssociation(
        folder_id=folder_id,
        conversation_id=conversation_id,
        user_id=user_id
    )

    # Add the association to the session
    db.add(conversation_folder_association)
    db.commit()
    db.refresh(conversation_folder_association)
    
   
    
    return conversation_folder_association

@validate_transaction
def update_folder(
    db: Session, folder_id: str, user_id: str, name: Optional[str] = None, description: Optional[str] = None
) -> Folder:
    """
    Update folder details.

    Args:
        db (Session): Database session.
        folder_id (int): Folder ID.
        user_id (str): User ID.
        name (Optional[str]): New name for the folder.
        description (Optional[str]): New description for the folder.

    Returns:
        Folder: Updated folder.

    Raises:
        FileNotFoundError: If the folder does not exist.
    """
    folder = get_folder_by_id(db, folder_id, user_id)
    if name:
        folder.name = name
    if description:
        folder.description = description
    db.commit()
    db.refresh(folder)
    return folder


@validate_transaction
def delete_folder(db: Session, folder_id: str, user_id: str) -> None:
    """
    Delete a folder by its ID.

    Args:
        db (Session): Database session.
        folder_id (int): Folder ID.
        user_id (str): User ID.

    Raises:
        FileNotFoundError: If the folder does not exist.
    """
    folder = get_folder_by_id(db, folder_id, user_id)
    db.delete(folder)
    db.commit()


@validate_transaction
def bulk_delete_folders(db: Session, folder_ids: List[str], user_id: str) -> int:
    """
    Bulk delete folders by their IDs.

    Args:
        db (Session): Database session.
        folder_ids (List[int]): List of folder IDs.
        user_id (str): User ID.

    Returns:
        int: Number of deleted folders.
    """
    folders = db.query(Folder).filter(Folder.id.in_(folder_ids), Folder.user_id == user_id)
    deleted_count = folders.delete(synchronize_session=False)
    db.commit()
    return deleted_count


@validate_transaction
def create_conversation_folder_association(
    db: Session, conversation_id: str, folder_id: str, user_id: str
) -> ConversationFolderAssociation:
    """
    Associate a folder with a conversation.

    Args:
        db (Session): Database session.
        conversation_id (int): Conversation ID.
        folder_id (int): Folder ID.
        user_id (str): User ID.

    Returns:
        ConversationFolderAssociation: The created association.
    """
    association = ConversationFolderAssociation(
        conversation_id=conversation_id, folder_id=folder_id, user_id=user_id
    )
    db.add(association)
    db.commit()
    db.refresh(association)
    return association


@validate_transaction
def get_conversation_folder_associations(
    db: Session, conversation_id: str, user_id: str
) -> List[ConversationFolderAssociation]:
    """
    Get all folder associations for a specific conversation.

    Args:
        db (Session): Database session.
        conversation_id (int): Conversation ID.
        user_id (str): User ID.

    Returns:
        List[ConversationFolderAssociation]: List of folder associations.
    """
    return (
        db.query(ConversationFolderAssociation)
        .filter(
            ConversationFolderAssociation.conversation_id == conversation_id,
            ConversationFolderAssociation.user_id == user_id,
        )
        .all()
    )


@validate_transaction
def get_folders_by_ids(db: Session, folder_ids: List[int], user_id: str) -> List[Folder]:
    """
    Get folders by a list of IDs.

    Args:
        db (Session): Database session.
        folder_ids (List[int]): List of folder IDs.
        user_id (str): User ID.

    Returns:
        List[Folder]: List of folders matching the IDs.
    """
    return (
        db.query(Folder)
        .filter(Folder.id.in_(folder_ids), Folder.user_id == user_id)
        .all()
    )



@validate_transaction
def get_folders_by_user_id(
    db: Session, user_id: str, offset: int = 0, limit: int = 100
) -> List[Folder]:
    """
    Get folders by user ID.

    Args:
        db (Session): Database session.
        user_id (str): User ID.
        offset (int): Offset for pagination.
        limit (int): Limit for pagination.

    Returns:
        List[Folder]: List of folders created by the user.
    """
    return (
        db.query(Folder)
        .filter(Folder.user_id == user_id)
        .offset(offset)
        .limit(limit)
        .all()
    )

@validate_transaction
def get_folder_by_id(db: Session, folder_id: str, user_id: str) -> Folder:
    """
    Get a folder by its ID and user ID.

    Args:
        db (Session): Database session.
        folder_id (str): The ID of the folder to retrieve.
        user_id (str): The user ID who owns the folder.

    Returns:
        Folder: The requested folder.

    Raises:
        FileNotFoundError: If the folder does not exist or doesn't belong to the user.
    """
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == user_id
    ).first()
    

    return folder

@validate_transaction
def delete_conversation_folder_association(db: Session, folder_id: str, conversation_id: str, user_id: str) -> None:
    """
    Delete the association between a folder and a conversation.

    Args:
        db (Session): Database session.
        folder_id (str): The ID of the folder.
        conversation_id (str): The ID of the conversation.
        user_id (str): The user ID.

    Raises:
        FileNotFoundError: If the association does not exist.
    """
    association = db.query(ConversationFolderAssociation).filter(
        ConversationFolderAssociation.folder_id == folder_id,
        ConversationFolderAssociation.conversation_id == conversation_id,
        ConversationFolderAssociation.user_id == user_id
    ).first()
    
    if not association:
        raise FileNotFoundError(f"Association between folder {folder_id} and conversation {conversation_id} not found")
    
    db.delete(association)
    db.commit()
    
    # No return value as the function is void
