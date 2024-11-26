from typing import Union, Optional

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    pass


class Document(BaseModel):
    document_id: Optional[Union[str, None]] = Field(default=None)
    id: Optional[Union[str, None]]= Field(default=None)
    text: str = Field(default="")
    

    title: Union[str, None] = Field(default="")
    url: Union[str, None] = Field(default=None)
    fields: Union[dict, None] = Field(default=None)
    tool_name: Union[str, None] = Field(default=None)

    class Config:
        from_attributes = True
