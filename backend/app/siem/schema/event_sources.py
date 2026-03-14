from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class EventType(str, Enum):
    EDR = "EDR"
    EPP = "EPP"
    CLOUD_INTEGRATION = "Cloud Integration"
    NETWORK_SECURITY = "Network Security"


class EventSourceCreate(BaseModel):
    customer_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    index_pattern: str = Field(..., max_length=1024)
    event_type: EventType
    time_field: str = Field("timestamp", max_length=255)
    enabled: bool = True


class EventSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    index_pattern: Optional[str] = Field(None, max_length=1024)
    event_type: Optional[EventType] = None
    time_field: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None


class EventSourceResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    index_pattern: str
    event_type: str
    time_field: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class EventSourcesListResponse(BaseModel):
    event_sources: List[EventSourceResponse]
    success: bool
    message: str


class EventSourceOperationResponse(BaseModel):
    event_source: Optional[EventSourceResponse] = None
    success: bool
    message: str


class EventSourceDeleteResponse(BaseModel):
    success: bool
    message: str
