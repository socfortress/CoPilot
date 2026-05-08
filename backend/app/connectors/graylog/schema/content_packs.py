from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import ConfigDict, BaseModel
from pydantic import Field


class Configuration(BaseModel):
    api_url: Optional[str] = Field(None, alias="@value")
    http_connect_timeout: Optional[int] = Field(None, alias="@value")
    http_read_timeout: Optional[int] = Field(None, alias="@value")
    http_user_agent: Optional[str] = Field(None, alias="@value")
    http_write_timeout: Optional[int] = Field(None, alias="@value")
    indicator: Optional[str] = Field(None, alias="@value")
    type: Optional[str] = Field(None, alias="@value")
    model_config = ConfigDict(extra="allow")


class Data(BaseModel):
    # configuration: Optional[Configuration]
    description: Optional[str] = Field(None, alias="@value")
    name: Optional[str] = Field(None, alias="@value")
    title: Optional[str] = Field(None, alias="@value")
    model_config = ConfigDict(extra="allow")


class Type(BaseModel):
    name: str
    version: str
    model_config = ConfigDict(extra="allow")


class Constraint(BaseModel):
    type: str
    version: str
    model_config = ConfigDict(extra="allow")


class Entity(BaseModel):
    id: str
    type: Type
    v: str
    data: Data
    constraints: List[Constraint]
    model_config = ConfigDict(extra="allow")


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
    model_config = ConfigDict(extra="allow")


class ContentPackList(BaseModel):
    total: int
    content_packs: List[ContentPack]
    content_packs_metadata: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(extra="allow")
