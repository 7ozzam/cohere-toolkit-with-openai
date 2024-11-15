from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database_models.base import Base

# Avoid importing File at the top to prevent circular import

class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    created_at: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[int] = mapped_column(default=0)

    # Define relationships
    def __init__(self, *args, **kwargs):
        from backend.database_models.file import File
        from backend.database_models.conversation import ConversationFolderAssociation
        
        self.files = relationship("File", back_populates="folder")
        self.conversation_folder_associations = relationship(
            "ConversationFolderAssociation", back_populates="folder"
        )
        super().__init__(*args, **kwargs)

    __table_args__ = ()
