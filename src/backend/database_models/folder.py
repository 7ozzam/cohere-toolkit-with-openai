from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List  # Ensure List is imported
from backend.database_models.base import Base
from backend.database_models.conversation import ConversationFolderAssociation


class Folder(Base):
    __tablename__ = "folders"

    # id: Mapped[str] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    created_at: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[int] = mapped_column(default=0)

    # Define the relationships with unique backref names to avoid conflict
    conversation_folder_associations: Mapped[List[ConversationFolderAssociation]] = relationship(
        "ConversationFolderAssociation", backref="folder_association", lazy="subquery"
    )
    
    files: Mapped[List["File"]] = relationship("File", back_populates="folder", lazy="subquery")
    
    __table_args__ = ()
