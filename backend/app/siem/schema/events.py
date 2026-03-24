from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class EventsQueryParams(BaseModel):
    timerange: str = Field("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')")
    page_size: int = Field(50, ge=1, le=1000, description="Number of results per page")
    scroll_id: Optional[str] = Field(None, description="Scroll ID for fetching the next page")
    query: Optional[str] = Field(None, description="Lucene query string (e.g. 'agent_name:piHole AND agent_id:088')")
    time_from: Optional[str] = Field(
        None,
        description="Absolute start time in ISO format (e.g. '2025-01-01T00:00:00Z'). Overrides timerange.",
    )
    time_to: Optional[str] = Field(None, description="Absolute end time in ISO format (e.g. '2025-01-31T23:59:59Z'). Overrides timerange.")


class EventsQueryResponse(BaseModel):
    events: List[Dict[str, Any]]
    total: int
    scroll_id: Optional[str] = None
    page_size: int
    success: bool
    message: str


class FieldMapping(BaseModel):
    field: str = Field(..., description="Field name (e.g. 'agent_name', 'agent_id')")
    type: str = Field(..., description="OpenSearch field type (e.g. 'keyword', 'text', 'long', 'date')")


class FieldMappingsResponse(BaseModel):
    fields: List[FieldMapping]
    total: int
    index_pattern: str
    success: bool
    message: str
