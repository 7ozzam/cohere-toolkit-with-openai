import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class File(BaseModel):
    id: str
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]

    user_id: str
    conversation_id: Optional[str] = ""
    file_content: Optional[str] = ""
    file_name: str
    file_path: Optional[str] = Field(default="")
    file_size: int = Field(default=0, ge=0)
    # folder_id: Optional[str]
    

    class Config:
        from_attributes = True


class ConversationFilePublic(BaseModel):
    id: str
    user_id: str = Field(default="")
    created_at: datetime.datetime
    updated_at: datetime.datetime

    conversation_id: str = Field(default="")
    file_name: str = Field(default="")
    file_size: int = Field(default=0, ge=0)



class AgentFilePublic(BaseModel):
    id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    file_name: str
    file_size: int = Field(default=0, ge=0)

class ListConversationFile(ConversationFilePublic):
    file_path: Optional[str] = Field(default="")
    item_type: Literal["file", "folder"] = Field(default="file")
    folder_id: Optional[str] = None
    files: Optional[list[File]] = None

class UserConversationFileAndFolderList(ListConversationFile):
    is_associated: bool
    
class UploadConversationFileResponse(ConversationFilePublic):
    pass


class UploadAgentFileResponse(AgentFilePublic):
    pass


class DeleteConversationFileResponse(BaseModel):
    pass


class DeleteAgentFileResponse(BaseModel):
    pass
