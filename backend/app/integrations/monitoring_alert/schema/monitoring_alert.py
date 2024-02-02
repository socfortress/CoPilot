from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pydantic import Extra

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

    @property
    def alert_index(self) -> str:
        return self.origin_context.split(":")[4]

class GraylogPostRequest(BaseModel):
    event_definition_id: str = Field(..., description="Identifier for the event definition", example="65bd28505e9a2d550cf521e7")
    event_definition_type: str = Field(..., description="Type of the event definition", example="aggregation-v1")
    event_definition_title: str = Field(..., description="Title of the event definition", example="COPILOT TESTING WAZUH")
    event_definition_description: Optional[str] = Field(None, description="Description of the event definition", example="")
    job_definition_id: str = Field(..., description="Identifier for the job definition", example="65bd284b5e9a2d550cf521dc")
    job_trigger_id: str = Field(..., description="Identifier for the job trigger", example="65bd2b625e9a2d550cf528e4")
    event: GraylogEvent = Field(..., description="Event details")
    backlog: List[str] = Field(..., description="List of backlog items associated with the event", example=[])

class GraylogPostResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the request was successful", example=True)
    message: str = Field(..., description="Message associated with the response", example="Event processed successfully")

class WazuhAnalysisResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the request was successful", example=True)
    message: str = Field(..., description="Message associated with the response", example="Analysis completed successfully")


# ! Wazuh Indexer Schema ! #
class WazuhSourceModel(BaseModel):
    agent_name: str = Field(..., description="The name of the agent.")
    agent_id: str = Field(..., description="The id of the agent.")
    agent_labels_customer: str = Field(..., description="The customer of the agent.")
    rule_id: str = Field(..., description="The id of the rule.")
    rule_level: int = Field(..., description="The level of the rule.")
    rule_description: str = Field(..., description="The description of the rule.")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        None,
        description="The UTC timestamp of the alert.",
    )

    class Config:
        extra = Extra.allow

class WazuhAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: WazuhSourceModel
    asset_type_id: Optional[int] = Field(
        None,
        description="The asset type id of the alert which is needed for when we add the asset to IRIS.",
    )
    ioc_value: Optional[str] = Field(
        None,
        description="The IoC value of the alert which is needed for when we add the IoC to IRIS.",
    )
    ioc_type: Optional[str] = Field(
        None,
        description="The IoC type of the alert which is needed for when we add the IoC to IRIS.",
    )

    class Config:
        extra = Extra.allow
