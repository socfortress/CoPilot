from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator

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
    original_alert_id: Optional[str] = Field(None, alias='original_alert_id')
    original_alert_index_name: Optional[str] = Field(None, alias='original_alert_index_name')

    @validator('original_alert_id', 'original_alert_index_name', allow_reuse=True, pre=True)
    def extract_origin_context(cls, v, values, **kwargs):
        origin_context = values.get('origin_context', '')
        try:
            # Assuming the format is always as given in the example
            parts = origin_context.split(':')
            if len(parts) == 6:
                _, _, _, _, index_name, alert_id = parts
                if 'original_alert_id' in kwargs['field'].name:
                    return alert_id
                elif 'original_alert_index_name' in kwargs['field'].name:
                    return index_name
        except Exception as e:
            return None
        return v

class AlertPayloadItem(BaseModel):
    index: str = Field(..., alias='_index')
    id: str = Field(..., alias='_id')
    score: float = Field(..., alias='_score')
    source: Source = Field(..., alias='_source')

class AlertsPayload(BaseModel):
    alerts: List[AlertPayloadItem]
    success: Optional[bool] = True
    message: Optional[str] = "Success"

