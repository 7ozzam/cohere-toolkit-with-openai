from typing import Optional

from pydantic import BaseModel


class Model(BaseModel):
    id: str
    name: str
    deployment_id: str
    cohere_name: Optional[str]
    description: Optional[str]
    use_compelation: Optional[str]
    prompt_template: Optional[str]
    
    class Config:
        from_attributes = True


class ModelCreate(BaseModel):
    name: str
    cohere_name: Optional[str]
    description: Optional[str]
    deployment_id: str
    use_compelation: Optional[str]
    prompt_template: Optional[str]


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    cohere_name: Optional[str] = None
    description: Optional[str] = None
    deployment_id: Optional[str] = None
    use_compelation: Optional[str] = None
    prompt_template: Optional[str] = None


class DeleteModel(BaseModel):
    pass


class ModelSimple(BaseModel):
    id: str
    name: str
    cohere_name: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True
        use_enum_values = True
