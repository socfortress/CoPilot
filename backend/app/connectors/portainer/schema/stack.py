from typing import Any
from typing import List
from typing import Optional
from enum import IntEnum

from pydantic import BaseModel, validator
from loguru import logger

class StackStatus(IntEnum):
    """Enum for Portainer stack status values"""
    ACTIVE = 1
    DOWN = 2
    INACTIVE = 3

    @classmethod
    def _missing_(cls, value: int) -> "StackStatus":
        """Handle unknown status values"""
        return cls.INACTIVE

    def __str__(self) -> str:
        """Return human-readable status"""
        return self.name.title()

class ResourceControlResponse(BaseModel):
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
    ResourceControl: Optional[ResourceControlResponse] = None
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

class DeleteStackResponse(BaseModel):
    data: Optional[Any] = None
    success: bool
    message: str

class StackIDResponse(BaseModel):
    stack_id: int
    success: bool
    message: str

