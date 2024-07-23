from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Fields(BaseModel):
    ALERT_ID: Optional[str] = None
    ALERT_SOURCE: Optional[str] = None
    CUSTOMER_CODE: Optional[str] = None
    test: Optional[str] = None

class Source(BaseModel):
    id: str
    event_definition_type: str
    event_definition_id: str
    origin_context: str
    timestamp: str
    timestamp_processing: str
    timerange_start: Optional[str] = None
    timerange_end: Optional[str] = None
    streams: List[str]
    source_streams: List[str]
    message: str
    source: str
    key_tuple: List[str]
    key: str
    priority: int
    alert: bool
    fields: Fields
    group_by_fields: Dict = Field(default_factory=dict)

class AlertPayloadItem(BaseModel):
    index: str = Field(..., alias='_index')
    id: str = Field(..., alias='_id')
    score: float = Field(..., alias='_score')
    source: Source = Field(..., alias='_source')

class AlertsPayload(BaseModel):
    alerts: List[AlertPayloadItem]
