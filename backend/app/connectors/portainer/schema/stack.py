from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel


class ResourceControl(BaseModel):
    Id: int
    ResourceId: str
    SubResourceIds: List[str]
    Type: int
    UserAccesses: List[str]
    TeamAccesses: List[str]
    Public: bool
    AdministratorsOnly: bool
    System: bool


class StackData(BaseModel):
    Id: int
    Name: str
    Type: int
    EndpointId: int
    SwarmId: str
    EntryPoint: str
    Env: List[Any]
    ResourceControl: ResourceControl
    Status: int
    ProjectPath: str
    CreationDate: int
    CreatedBy: str
    UpdateDate: int
    UpdatedBy: str
    AdditionalFiles: Optional[Any] = None
    AutoUpdate: Optional[Any] = None
    Option: Optional[Any] = None
    GitConfig: Optional[Any] = None
    FromAppTemplate: bool
    Namespace: str
    IsComposeFormat: bool


class StackResponse(BaseModel):
    data: StackData
    success: bool
    message: str

class StacksResponse(BaseModel):
    data: List[StackData]
    success: bool
    message: str
