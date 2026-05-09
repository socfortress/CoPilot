from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class EventType(str, Enum):
    EDR = "EDR"
    EPP = "EPP"
    CLOUD_INTEGRATION = "Cloud Integration"
    NETWORK_SECURITY = "Network Security"


class DisplayColumn(BaseModel):
    """One column the SOC has chosen to surface in the event-search table."""

    key: str = Field(
        ...,
        description="Field path in the event source's _source object (dotted, e.g. 'agent.name' or 'data.win.eventdata.targetUserName').",
    )
    label: str = Field(..., description="Human-readable column header.")
    width: Optional[int] = Field(None, description="Optional pixel width hint for the table column.")


class EventSourceCreate(BaseModel):
    customer_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    index_pattern: str = Field(..., max_length=1024)
    event_type: EventType
    time_field: str = Field("timestamp", max_length=255)
    enabled: bool = True
    displayed_columns: Optional[List[DisplayColumn]] = Field(
        None,
        description="Per-source column layout for the event-search table. None or empty falls back to the frontend's hardcoded defaults.",
    )


class EventSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    index_pattern: Optional[str] = Field(None, max_length=1024)
    event_type: Optional[EventType] = None
    time_field: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    displayed_columns: Optional[List[DisplayColumn]] = None


class EventSourceResponse(BaseModel):
    id: int
    customer_code: str
    name: str
    index_pattern: str
    event_type: str
    time_field: str
    enabled: bool
    displayed_columns: Optional[List[DisplayColumn]] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


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
