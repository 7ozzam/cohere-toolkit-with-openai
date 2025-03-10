from sqlalchemy.orm import Session

from backend.database_models.file import File
from backend.services.transaction import validate_transaction


@validate_transaction
def create_file(db: Session, file: File) -> File:
    """
    Create a new file.

    Args:
        db (Session): Database session.
        file (File): File data to be created.

    Returns:
        File: Created file.
    """
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


@validate_transaction
def batch_create_files(db: Session, files: list[File]) -> list[File]:
    """
    Batch create files.
    """
    db.add_all(files)
    db.commit()
    for file in files:
        db.refresh(file)
    return files


@validate_transaction
def get_file(db: Session, file_id: str, user_id: str) -> File:
    """
    Get a file by ID.

    Args:
        db (Session): Database session.
        file_id (str): File ID.
        user_id (str): User ID.

    Returns:
        File: File with the given ID.
    """
    return db.query(File).filter(File.id == file_id, File.user_id == user_id).first()


@validate_transaction
def get_file_by_name(db: Session, file_name: str, user_id: str) -> File:
    """
    Get a file by ID.

    Args:
        db (Session): Database session.
        file_id (str): File ID.
        user_id (str): User ID.

    Returns:
        File: File with the given ID.
    """
    return db.query(File).filter(File.file_name == file_name, File.user_id == user_id).first()

@validate_transaction
def get_file_by_name_or_id(db: Session, identifier: str, user_id: str) -> File:
    """
    Get a file by either name or ID.

    Args:
        db (Session): Database session.
        identifier (str): File name or ID.
        user_id (str): User ID.

    Returns:
        File: File with the given name or ID.
    """
    # Try to find by ID first
    file = get_file(db, identifier, user_id)
    if file:
        return file
    
    # If not found by ID, try by name
    return get_file_by_name(db, identifier, user_id)

@validate_transaction
def get_files(db: Session, user_id: str, offset: int = 0, limit: int = 100):
    """
    List all files.

    Args:
        db (Session): Database session.
        user_id (str): User ID.
        offset (int): Offset to start the list.
        limit (int): Limit of files to be listed.

    Returns:
        list[File]: List of files.
    """
    return (
        db.query(File).filter(File.user_id == user_id).offset(offset).limit(limit).all()
    )


def get_files_by_ids(db: Session, file_ids: list[str], user_id: str) -> list[File]:
    """
    Get files by IDs.

    Args:
        db (Session): Database session.
        file_ids (list[str]): File IDs.
        user_id (str): User ID.

    Returns:
        list[File]: List of files with the given IDs.
    """
    return db.query(File).filter(File.id.in_(file_ids), File.user_id == user_id).all()


def get_files_by_names(db: Session, file_names: list[str], user_id: str) -> list[File]:
    """
    Get files by IDs.

    Args:
        db (Session): Database session.
        file_ids (list[str]): File IDs.
        user_id (str): User ID.

    Returns:
        list[File]: List of files with the given IDs.
    """
    return db.query(File).filter(File.file_name.in_(file_names), File.user_id == user_id).all()

@validate_transaction
def get_files_by_file_names(
    db: Session, file_names: list[str], user_id: str
) -> list[File]:
    """
    Get files by file names.

    Args:
        db (Session): Database session.
        file_names (list[str]): File names.
        user_id (str): User ID.

    Returns:
        list[File]: List of files with the given file names.
    """
    return (
        db.query(File)
        .filter(File.file_name.in_(file_names), File.user_id == user_id)
        .all()
    )


@validate_transaction
def get_files_by_user_id(db: Session, user_id: str) -> list[File]:
    """
    List all files by user ID.

    Args:
        db (Session): Database session.
        user_id (str): User ID.

    Returns:
        list[File]: List of files by user ID.
    """
    return db.query(File).filter(File.user_id == user_id).all()


@validate_transaction
def delete_file(db: Session, file_id: str, user_id: str) -> None:
    """
    Delete a file by ID.

    Args:
        db (Session): Database session.
        file_id (str): File ID.
        user_id (str): User ID.
    """
    file = db.query(File).filter(File.id == file_id, File.user_id == user_id)
    file.delete()
    db.commit()


def bulk_delete_files(db: Session, file_ids: list[str], user_id: str) -> None:
    """
    Bulk delete files by IDs.

    Args:
        db (Session): Database session.
        file_ids (list[str]): List of file IDs.
        user_id (str): User ID.
    """
    files = db.query(File).filter(File.id.in_(file_ids), File.user_id == user_id)
    files.delete()
    db.commit()

@validate_transaction
def get_files_by_identifiers(db: Session, identifiers: list[str], user_id: str) -> list[File]:
    """
    Get files by either their IDs or names.

    Args:
        db (Session): Database session.
        identifiers (list[str]): List of file IDs or names.
        user_id (str): User ID.

    Returns:
        list[File]: List of files matching the given IDs or names.
    """
    return (
        db.query(File)
        .filter(
            File.user_id == user_id,
            (File.id.in_(identifiers) | File.file_name.in_(identifiers))
        )
        .all()
    )
