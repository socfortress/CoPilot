from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class MonitoringAlertsRequestModel(BaseModel):
    id: Optional[int] = None
    alert_id: str
    alert_index: str
    customer_code: str
    alert_source: str

    class Config:
        orm_mode = True

class GraylogEventFields(BaseModel):
    ALERT_ID: str = Field(..., description="Unique identifier for the alert", example="65f6a260-c1f3-11ee-93bc-86000046278a")
    ALERT_SOURCE: str = Field(..., description="Source of the alert", example="WAZUH")
    CUSTOMER_CODE: str = Field(..., description="Customer code associated with the alert", example="00002")
    ALERT_INDEX: str = Field(..., description="Index where the alert is stored", example="wazuh_00002")

class GraylogEvent(BaseModel):
    id: str = Field(..., description="Unique identifier for the event", example="01HNNF2YCM5SSV3KDQJSRK0EV0")
    event_definition_type: str = Field(..., description="Type of event definition", example="aggregation-v1")
    event_definition_id: str = Field(..., description="Identifier for the event definition", example="65bd28505e9a2d550cf521e7")
    origin_context: str = Field(..., description="Context from which the event originated", example="urn:graylog:message:es:wazuh_00002_290:65f6a260-c1f3-11ee-93bc-86000046278a")
    timestamp: str = Field(..., description="Timestamp when the event occurred", example="2024-02-02T17:49:22.694Z")
    timestamp_processing: str = Field(..., description="Timestamp when the event was processed", example="2024-02-02T17:50:26.708Z")
    timerange_start: Optional[str] = Field(None, description="Start of the timerange for the event", example=None)
    timerange_end: Optional[str] = Field(None, description="End of the timerange for the event", example=None)
    streams: List[str] = Field(..., description="List of streams associated with the event", example=[])
    source_streams: List[str] = Field(..., description="List of source streams for the event", example=["645a3a6123e5cc30bbc0e5dc"])
    message: str = Field(..., description="Message associated with the event", example="COPILOT TESTING WAZUH")
    source: str = Field(..., description="Source of the event", example="ASHGRL02")
    key_tuple: List[str] = Field(..., description="Tuple keys associated with the event", example=[])
    key: str = Field(..., description="Key associated with the event", example="")
    priority: int = Field(..., description="Priority of the event", example=2)
    alert: bool = Field(..., description="Indicates if the event is an alert", example=True)
    fields: GraylogEventFields = Field(..., description="Custom fields for the event")
    group_by_fields: Dict[str, Any] = Field(..., description="Fields used to group events", example={})

class GraylogPostRequest(BaseModel):
    event_definition_id: str = Field(..., description="Identifier for the event definition", example="65bd28505e9a2d550cf521e7")
    event_definition_type: str = Field(..., description="Type of the event definition", example="aggregation-v1")
    event_definition_title: str = Field(..., description="Title of the event definition", example="COPILOT TESTING WAZUH")
    event_definition_description: Optional[str] = Field(None, description="Description of the event definition", example="")
    job_definition_id: str = Field(..., description="Identifier for the job definition", example="65bd284b5e9a2d550cf521dc")
    job_trigger_id: str = Field(..., description="Identifier for the job trigger", example="65bd2b625e9a2d550cf528e4")
    event: GraylogEvent = Field(..., description="Event details")
    backlog: List[str] = Field(..., description="List of backlog items associated with the event", example=[])
