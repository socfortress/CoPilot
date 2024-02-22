from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class Configuration(BaseModel):
    api_url: Optional[str] = Field(None, alias="@value")
    http_connect_timeout: Optional[int] = Field(None, alias="@value")
    http_read_timeout: Optional[int] = Field(None, alias="@value")
    http_user_agent: Optional[str] = Field(None, alias="@value")
    http_write_timeout: Optional[int] = Field(None, alias="@value")
    indicator: Optional[str] = Field(None, alias="@value")
    type: Optional[str] = Field(None, alias="@value")
    # Add other fields as needed

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class Data(BaseModel):
    # configuration: Optional[Configuration]
    description: Optional[str] = Field(None, alias="@value")
    name: Optional[str] = Field(None, alias="@value")
    title: Optional[str] = Field(None, alias="@value")
    # Define other fields as per your JSON structure

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class Type(BaseModel):
    name: str
    version: str

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class Constraint(BaseModel):
    type: str
    version: str
    # Additional fields based on constraints data

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class Entity(BaseModel):
    id: str
    type: Type
    v: str
    data: Data
    constraints: List[Constraint]

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class ContentPack(BaseModel):
    id: str
    rev: int
    v: str
    name: str
    summary: str
    description: str
    vendor: str
    url: str
    created_at: str
    server_version: str
    parameters: List
    entities: List[Entity]

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.


class ContentPackList(BaseModel):
    total: int
    content_packs: List[ContentPack]
    content_packs_metadata: Optional[Dict[str, Any]]

    class Config:
        extra = Extra.allow  # This line allows for additional fields that are not defined in the model.
