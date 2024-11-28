from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database_models.base import Base

# Import Folder model if not already imported
from backend.database_models.folder import Folder

class File(Base):
    __tablename__ = "files"

    user_id: Mapped[str] = mapped_column(String, nullable=True)
    file_name: Mapped[str] = mapped_column(default="", nullable=True)
    file_generated_name: Mapped[str] = mapped_column(default="", nullable=True)
    file_size: Mapped[int] = mapped_column(default=0)
    file_content: Mapped[str] = mapped_column(default="")
    file_summary: Mapped[str] = mapped_column(default="", nullable=True)
    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id"), nullable=True)
    path: Mapped[str] = mapped_column(default=None, nullable=True)

    # Define the relationship to Folder (inverse of the above relationship)
    folder: Mapped["Folder"] = relationship("Folder", back_populates="files")

    __table_args__ = ()
