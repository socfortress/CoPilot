from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic import validator

from app.integrations.alert_creation.general.schema.alert import IrisAsset
from app.integrations.alert_creation.general.schema.alert import IrisIoc


class WazuhSourceFieldsToRemove(Enum):
    GL2 = "gl2"
    RULE_MITRE_TACTIC = "rule_mitre_tactic"
    RULE_MITRE_ID = "rule_mitre_id"
    RULE_MITRE_TECHNIQUE = "rule_mitre_technique"
    RULE_ID = "rule_id"
    MESSAGE = "message"
    # Add more fields as needed


class MonitoringAlertsRequestModel(BaseModel):
    id: Optional[int] = None
    alert_id: str
    alert_index: str
    customer_code: str
    alert_source: str

    class Config:
        orm_mode = True


class MonitoringAlertsResponseModel(BaseModel):
    success: bool
    message: str
    monitoring_alerts: List[MonitoringAlertsRequestModel]


class MonitoringWazuhAlertsRequestModel(BaseModel):
    customer_code: str


class GraylogEventFields(BaseModel):
    ALERT_ID: str = Field(
        ...,
        description="Unique identifier for the alert",
        example="65f6a260-c1f3-11ee-93bc-86000046278a",
    )
    ALERT_SOURCE: str = Field(..., description="Source of the alert", example="WAZUH")
    CUSTOMER_CODE: str = Field(
        ...,
        description="Customer code associated with the alert",
        example="00002",
    )


class GraylogEvent(BaseModel):
    id: str = Field(
        ...,
        description="Unique identifier for the event",
        example="01HNNF2YCM5SSV3KDQJSRK0EV0",
    )
    event_definition_type: str = Field(
        ...,
        description="Type of event definition",
        example="aggregation-v1",
    )
    event_definition_id: str = Field(
        ...,
        description="Identifier for the event definition",
        example="65bd28505e9a2d550cf521e7",
    )
    origin_context: str = Field(
        ...,
        description="Context from which the event originated",
        example="urn:graylog:message:es:wazuh_00002_290:65f6a260-c1f3-11ee-93bc-86000046278a",
    )
    timestamp: str = Field(
        ...,
        description="Timestamp when the event occurred",
        example="2024-02-02T17:49:22.694Z",
    )
    timestamp_processing: str = Field(
        ...,
        description="Timestamp when the event was processed",
        example="2024-02-02T17:50:26.708Z",
    )
    timerange_start: Optional[str] = Field(
        None,
        description="Start of the timerange for the event",
        example=None,
    )
    timerange_end: Optional[str] = Field(
        None,
        description="End of the timerange for the event",
        example=None,
    )
    streams: List[str] = Field(
        ...,
        description="List of streams associated with the event",
        example=[],
    )
    source_streams: List[str] = Field(
        ...,
        description="List of source streams for the event",
        example=["645a3a6123e5cc30bbc0e5dc"],
    )
    message: str = Field(
        ...,
        description="Message associated with the event",
        example="COPILOT TESTING WAZUH",
    )
    source: str = Field(..., description="Source of the event", example="ASHGRL02")
    key_tuple: List[str] = Field(
        ...,
        description="Tuple keys associated with the event",
        example=[],
    )
    key: str = Field(..., description="Key associated with the event", example="")
    priority: int = Field(..., description="Priority of the event", example=2)
    alert: bool = Field(
        ...,
        description="Indicates if the event is an alert",
        example=True,
    )
    # fields: GraylogEventFields = Field(..., description="Custom fields for the event")
    fields: Dict[str, Any] = Field(..., description="Custom fields for the event")
    group_by_fields: Dict[str, Any] = Field(
        ...,
        description="Fields used to group events",
        example={},
    )

    @property
    def alert_index(self) -> str:
        return self.origin_context.split(":")[4]

    @property
    def alert_id(self) -> str:
        return self.origin_context.split(":")[5]

    @validator("fields")
    def check_customer_code(cls, fields):
        if "CUSTOMER_CODE" not in fields:
            raise HTTPException(
                status_code=400,
                detail="CUSTOMER_CODE is required in the fields",
            )
        return fields


class GraylogPostRequest(BaseModel):
    event_definition_id: str = Field(
        ...,
        description="Identifier for the event definition",
        example="65bd28505e9a2d550cf521e7",
    )
    event_definition_type: str = Field(
        ...,
        description="Type of the event definition",
        example="aggregation-v1",
    )
    event_definition_title: str = Field(
        ...,
        description="Title of the event definition",
        example="COPILOT TESTING WAZUH",
    )
    event_definition_description: Optional[str] = Field(
        None,
        description="Description of the event definition",
        example="",
    )
    job_definition_id: str = Field(
        ...,
        description="Identifier for the job definition",
        example="65bd284b5e9a2d550cf521dc",
    )
    job_trigger_id: str = Field(
        ...,
        description="Identifier for the job trigger",
        example="65bd2b625e9a2d550cf528e4",
    )
    event: GraylogEvent = Field(..., description="Event details")
    backlog: List[str] = Field(
        ...,
        description="List of backlog items associated with the event",
        example=[],
    )


class GraylogPostResponse(BaseModel):
    success: bool = Field(
        ...,
        description="Indicates if the request was successful",
        example=True,
    )
    message: str = Field(
        ...,
        description="Message associated with the response",
        example="Event processed successfully",
    )


class AlertAnalysisResponse(BaseModel):
    success: bool = Field(
        ...,
        description="Indicates if the request was successful",
        example=True,
    )
    message: str = Field(
        ...,
        description="Message associated with the response",
        example="Analysis completed successfully",
    )


# ! Wazuh Indexer Schema ! #
class WazuhSourceModel(BaseModel):
    agent_name: str = Field(..., description="The name of the agent.")
    agent_id: str = Field(..., description="The id of the agent.")
    agent_labels_customer: str = Field(..., description="The customer of the agent.")
    rule_id: str = Field(..., description="The id of the rule.")
    rule_level: int = Field(..., description="The level of the rule.")
    rule_description: str = Field(..., description="The description of the rule.")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    process_id: Optional[str] = Field(
        "n/a",
        description="The process id of the alert.",
    )
    timestamp_utc: Optional[str] = Field(
        None,
        description="The UTC timestamp of the alert.",
    )
    process_image: Optional[str] = Field(
        "n/a",
        description="The process image of the alert.",
    )
    data_win_eventdata_image: Optional[str] = Field(
        "n/a",
        description="The image of the event data.",
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

    def to_dict(self):
        return self.dict(exclude_none=True)


class SortOrder(Enum):
    desc = "desc"
    asc = "asc"


class FilterAlertsRequest(BaseModel):
    per_page: int = Field(1000, description="The number of alerts to return per page.")
    page: int = Field(1, description="The page number to return.")
    sort: SortOrder = Field(
        SortOrder.desc,
        description="The sort order for the alerts.",
    )
    alert_tags: str = Field(..., description="The tags of the alert.")
    alert_status_id: int = Field(
        3,
        description="The status of the alert. Default to assigned.",
        example=3,
    )
    alert_customer_id: int = Field(
        ...,
        description="The customer id of the alert.",
        example=1,
    )


class WazuhIrisAlertContext(BaseModel):
    customer_iris_id: int = Field(
        ...,
        description="IRIS ID of the customer",
        example=1,
    )
    customer_name: str = Field(
        ...,
        description="Name of the customer",
        example="SOCFortress",
    )
    customer_cases_index: str = Field(
        ...,
        description="IRIS case index name in the Wazuh-Indexer",
        example="dfir_iris_00001",
    )
    alert_name: str = Field(
        ...,
        description="Name of the alert",
        example="Intrusion Detected",
    )
    alert_level: int = Field(..., description="Severity level of the alert", example=3)
    rule_id: str = Field(
        ...,
        description="ID of the rule that triggered the alert",
        example="2001",
    )
    rule_mitre_id: Optional[str] = Field(
        "n/a",
        description="MITRE ATT&CK ID of the rule",
        example="T1234",
    )
    rule_mitre_tactic: Optional[str] = Field(
        "n/a",
        description="MITRE ATT&CK Tactic",
        example="Execution",
    )
    rule_mitre_technique: Optional[str] = Field(
        "n/a",
        description="MITRE ATT&CK Technique",
        example="Scripting",
    )
    process_name: Optional[List[str]] = Field(
        example=["No process name found"],
        description="Name of the process",
    )

    class Config:
        extra = Extra.allow


class WazuhIrisAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_description: str = Field(
        ...,
        description="Description of the alert",
        example="Intrusion Detected by Firewall",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Wazuh")
    assets: List[IrisAsset] = Field(..., description="List of affected assets")
    alert_status_id: int = Field(..., description="Status ID of the alert", example=3)
    alert_severity_id: int = Field(
        ...,
        description="Severity ID of the alert",
        example=5,
    )
    alert_customer_id: int = Field(
        ...,
        description="Customer ID related to the alert",
        example=1,
    )
    alert_source_content: Dict[str, Any] = Field(
        ...,
        description="Original content from the alert source",
    )
    alert_context: WazuhIrisAlertContext = Field(
        ...,
        description="Contextual information about the alert",
    )
    alert_iocs: Optional[List[IrisIoc]] = Field(
        None,
        description="List of IoCs related to the alert",
    )
    alert_source_event_time: str = Field(
        ...,
        description="Timestamp of the alert",
        example="2021-01-01T00:00:00.000Z",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


########### ! CUSTOM ALERTS SCHEMA ! ###########
class CustomSourceModel(BaseModel):
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    date: Optional[float] = Field(
        None,
        description="Date of the alert in Unix timestamp",
    )
    alert_metadata_tag: Optional[str] = Field(
        None,
        description="Metadata tag for the alert",
    )
    alert_gid: Optional[int] = Field(None, description="Alert group ID")

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class CustomAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: CustomSourceModel
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

    def to_dict(self):
        return self.dict(exclude_none=True)


########### ! Create Custom Alerts In IRIS Schemas ! ###########
class CustomIrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Asset Does Not Apply to Custom Alerts",
        description="Name of the asset",
        example="Server01",
    )
    asset_ip: Optional[str] = Field(
        "Asset Does Not Apply to Custom Alerts",
        description="IP address of the asset",
        example="192.168.1.1",
    )
    asset_description: Optional[str] = Field(
        "Asset Does Not Apply to Custom Alerts",
        description="Description of the asset",
        example="Windows Server",
    )
    asset_type_id: Optional[int] = Field(
        9,
        description="Type ID of the asset",
        example=1,
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class CustomIrisIoc(BaseModel):
    ioc_value: str = Field(
        ...,
        description="Value of the IoC",
        example="www.google.com",
    )
    ioc_description: str = Field(
        ...,
        description="Description of the IoC",
        example="Google",
    )
    ioc_tlp_id: int = Field(1, description="TLP ID of the IoC", example=1)
    ioc_type_id: int = Field(20, description="Type ID of the IoC", example=20)


class CustomIrisAlertContext(Dict[str, Any]):
    _source: CustomSourceModel
    alert_id: str = Field(..., description="ID of the alert", example="123")
    alert_name: str = Field(
        ...,
        description="Name of the alert",
        example="Intrusion Detected",
    )
    customer_iris_id: Optional[int] = Field(
        None,
        description="IRIS ID of the customer",
    )
    customer_name: Optional[str] = Field(
        None,
        description="Name of the customer",
    )
    customer_cases_index: Optional[str] = Field(
        None,
        description="IRIS case index name in the Wazuh-Indexer",
    )
    time_field: Optional[str] = Field(
        "timestamp_utc",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class CustomIrisAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_description: str = Field(
        ...,
        description="Description of the alert",
        example="Intrusion Detected by Firewall",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Suricata")
    assets: List[CustomIrisAsset] = Field(..., description="List of affected assets")
    alert_status_id: int = Field(..., description="Status ID of the alert", example=3)
    alert_severity_id: int = Field(
        ...,
        description="Severity ID of the alert",
        example=5,
    )
    alert_customer_id: int = Field(
        ...,
        description="Customer ID related to the alert",
        example=1,
    )
    alert_source_content: Dict[str, Any] = Field(
        ...,
        description="Original content from the alert source",
    )
    alert_context: CustomIrisAlertContext = Field(
        ...,
        description="Contextual information about the alert",
    )
    alert_iocs: Optional[List[IrisIoc]] = Field(
        None,
        description="List of IoCs related to the alert",
    )
    alert_source_event_time: str = Field(
        ...,
        description="Timestamp of the alert",
        example="2021-01-01T00:00:00.000Z",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


########### ! SURICATA ALERTS SCHEMA ! ###########
class SuricataSourceModel(BaseModel):
    alert_signature: str = Field(..., description="Signature of the alert")
    alert_severity: int = Field(..., description="Severity level of the alert")
    alert_signature_id: int = Field(..., description="Signature ID of the alert")
    src_ip: str = Field(..., description="Source IP address")
    dest_ip: str = Field(..., description="Destination IP address")
    app_proto: str = Field(..., description="Application protocol")
    agent_labels_customer: str = Field(..., description="Customer of the agent")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    date: Optional[float] = Field(
        None,
        description="Date of the alert in Unix timestamp",
    )
    alert_metadata_tag: Optional[str] = Field(
        None,
        description="Metadata tag for the alert",
    )
    alert_gid: Optional[int] = Field(None, description="Alert group ID")

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class SuricataAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: SuricataSourceModel
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


########### ! Create Suricata Alerts In IRIS Schemas ! ###########
class SuricataIrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Asset Does Not Apply to Suricata Alerts",
        description="Name of the asset",
        example="Server01",
    )
    asset_ip: Optional[str] = Field(
        "Asset Does Not Apply to Suricata Alerts",
        description="IP address of the asset",
        example="192.168.1.1",
    )
    asset_description: Optional[str] = Field(
        "Asset Does Not Apply to Suricata Alerts",
        description="Description of the asset",
        example="Windows Server",
    )
    asset_type_id: Optional[int] = Field(
        9,
        description="Type ID of the asset",
        example=1,
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class SuricataIrisIoc(BaseModel):
    ioc_value: str = Field(
        ...,
        description="Value of the IoC",
        example="www.google.com",
    )
    ioc_description: str = Field(
        ...,
        description="Description of the IoC",
        example="Google",
    )
    ioc_tlp_id: int = Field(1, description="TLP ID of the IoC", example=1)
    ioc_type_id: int = Field(20, description="Type ID of the IoC", example=20)


class SuricataIrisAlertContext(BaseModel):
    _source: SuricataSourceModel
    alert_id: str = Field(..., description="ID of the alert", example="123")
    alert_name: str = Field(
        ...,
        description="Name of the alert",
        example="Intrusion Detected",
    )
    alert_level: int = Field(..., description="Severity level of the alert", example=3)
    rule_id: int = Field(
        ...,
        description="ID of the Suricata rule that triggered the alert",
        example="2001",
    )
    src_ip: str = Field(
        ...,
        description="Source IP address of the alert",
        example="1.1.1.1",
    )
    dest_ip: str = Field(
        ...,
        description="Destination IP address of the alert",
        example="8.8.8.8",
    )
    app_proto: str = Field(
        ...,
        description="Application protocol of the alert",
        example="TCP",
    )
    agent_labels_customer: str = Field(
        ...,
        description="Customer of the endpoint",
        example="SOCFortress",
    )
    customer_iris_id: Optional[int] = Field(
        None,
        description="IRIS ID of the customer",
    )
    customer_name: Optional[str] = Field(
        None,
        description="Name of the customer",
    )
    customer_cases_index: Optional[str] = Field(
        None,
        description="IRIS case index name in the Wazuh-Indexer",
    )
    time_field: Optional[str] = Field(
        "timestamp_utc",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class SuricataIrisAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_description: str = Field(
        ...,
        description="Description of the alert",
        example="Intrusion Detected by Firewall",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Suricata")
    assets: List[SuricataIrisAsset] = Field(..., description="List of affected assets")
    alert_status_id: int = Field(..., description="Status ID of the alert", example=3)
    alert_severity_id: int = Field(
        ...,
        description="Severity ID of the alert",
        example=5,
    )
    alert_customer_id: int = Field(
        ...,
        description="Customer ID related to the alert",
        example=1,
    )
    alert_source_content: Dict[str, Any] = Field(
        ...,
        description="Original content from the alert source",
    )
    alert_context: SuricataIrisAlertContext = Field(
        ...,
        description="Contextual information about the alert",
    )
    alert_iocs: Optional[List[IrisIoc]] = Field(
        None,
        description="List of IoCs related to the alert",
    )
    alert_source_event_time: str = Field(
        ...,
        description="Timestamp of the alert",
        example="2021-01-01T00:00:00.000Z",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


########### ! Office365 Exchange ALERTS SCHEMA ! ###########
class Office365ExchangeSourceModel(BaseModel):
    client_ip: Optional[str] = Field("Not found", description="Client IP address")
    operation: Optional[str] = Field("Not found", description="Operation")
    creation_time: Optional[str] = Field("Not found", description="Creation time")
    office365_id: str = Field(..., description="Office365 ID")
    organization_name: str = Field(..., description="Organization name")
    user_id: str = Field(..., description="User ID")
    workload: str = Field(..., description="Workload")
    organization_id: str = Field(..., description="Organization ID")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    date: Optional[float] = Field(
        None,
        description="Date of the alert in Unix timestamp",
    )
    rule_description: str = Field(
        ...,
        description="Description of the rule",
    )

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ExchangeAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: Office365ExchangeSourceModel
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


########### ! Create Office365 Exchange Alerts In IRIS Schemas ! ###########
class Office365ExchangeIrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Asset Does Not Apply to Office365 Exchange Alerts",
        description="Name of the asset",
        example="test@socfortress.co",
    )
    asset_description: Optional[str] = Field(
        "Asset Does Not Apply to Office365 Exchange Alerts",
        description="Description of the asset",
        example="Windows Server",
    )
    asset_type_id: Optional[int] = Field(
        1,
        description="Type ID of the asset",
        example=1,
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ExchangeIrisAlertContext(BaseModel):
    _source: Office365ExchangeSourceModel = Field(..., description="Source of the alert")
    client_ip: Optional[str] = Field("Not found", description="Client IP address")
    operation: Optional[str] = Field("Not found", description="Operation")
    creation_time: Optional[str] = Field("Not found", description="Creation time")
    office365_id: str = Field(..., description="Office365 ID")
    organization_name: str = Field(..., description="Organization name")
    user_id: str = Field(..., description="User ID")
    workload: str = Field(..., description="Workload")
    organization_id: str = Field(..., description="Organization ID")
    customer_iris_id: Optional[int] = Field(
        None,
        description="IRIS ID of the customer",
    )
    customer_name: Optional[str] = Field(
        None,
        description="Name of the customer",
    )
    customer_cases_index: Optional[str] = Field(
        None,
        description="IRIS case index name in the Wazuh-Indexer",
    )
    time_field: Optional[str] = Field(
        "timestamp_utc",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    rule_description: str = Field(
        ...,
        description="Description of the rule",
    )
    rule_id: str = Field(
        ...,
        description="ID of the rule that triggered the alert",
        example="2001",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ExchangeIrisAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_description: str = Field(
        ...,
        description="Description of the alert",
        example="Intrusion Detected by Firewall",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Suricata")
    assets: List[Office365ExchangeIrisAsset] = Field(..., description="List of affected assets")
    alert_status_id: int = Field(..., description="Status ID of the alert", example=3)
    alert_severity_id: int = Field(
        ...,
        description="Severity ID of the alert",
        example=5,
    )
    alert_customer_id: int = Field(
        ...,
        description="Customer ID related to the alert",
        example=1,
    )
    alert_source_content: Dict[str, Any] = Field(
        ...,
        description="Original content from the alert source",
    )
    alert_context: Office365ExchangeIrisAlertContext = Field(
        ...,
        description="Contextual information about the alert",
    )
    alert_iocs: Optional[List[IrisIoc]] = Field(
        None,
        description="List of IoCs related to the alert",
    )
    alert_source_event_time: str = Field(
        ...,
        description="Timestamp of the alert",
        example="2021-01-01T00:00:00.000Z",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


########### ! Office365 Threat Intel ALERTS SCHEMA ! ###########
class Office365ThreatIntelSourceModel(BaseModel):
    sender_ip: Optional[str] = Field("Not found", description="Sender IP address")
    operation: Optional[str] = Field("Not found", description="Operation")
    creation_time: Optional[str] = Field("Not found", description="Creation time")
    office365_id: str = Field(..., description="Office365 ID")
    recipients: str = Field(..., description="Recipients")
    workload: str = Field(..., description="Workload")
    organization_id: str = Field(..., description="Organization ID")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    date: Optional[float] = Field(
        None,
        description="Date of the alert in Unix timestamp",
    )
    rule_description: str = Field(
        ...,
        description="Description of the rule",
    )

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ThreatIntelAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: Office365ThreatIntelSourceModel
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


########### ! Create Office365 Threat Intel Alerts In IRIS Schemas ! ###########
class Office365ThreatIntelIrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Asset Does Not Apply to Office365 Exchange Alerts",
        description="Name of the asset",
        example="test@socfortress.co",
    )
    asset_description: Optional[str] = Field(
        "Asset Does Not Apply to Office365 Exchange Alerts",
        description="Description of the asset",
        example="Windows Server",
    )
    asset_type_id: Optional[int] = Field(
        1,
        description="Type ID of the asset",
        example=1,
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ThreatIntelIrisAlertContext(BaseModel):
    _source: Office365ThreatIntelSourceModel = Field(..., description="Source of the alert")
    sender_ip: Optional[str] = Field("Not found", description="Sender IP address")
    operation: Optional[str] = Field("Not found", description="Operation")
    creation_time: Optional[str] = Field("Not found", description="Creation time")
    office365_id: str = Field(..., description="Office365 ID")
    recipients: str = Field(..., description="Recipients")
    workload: str = Field(..., description="Workload")
    organization_id: str = Field(..., description="Organization ID")
    customer_iris_id: Optional[int] = Field(
        None,
        description="IRIS ID of the customer",
    )
    customer_name: Optional[str] = Field(
        None,
        description="Name of the customer",
    )
    customer_cases_index: Optional[str] = Field(
        None,
        description="IRIS case index name in the Wazuh-Indexer",
    )
    time_field: Optional[str] = Field(
        "timestamp_utc",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    rule_description: str = Field(
        ...,
        description="Description of the rule",
    )
    rule_id: str = Field(
        ...,
        description="ID of the rule that triggered the alert",
        example="2001",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ThreatIntelIrisAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_description: str = Field(
        ...,
        description="Description of the alert",
        example="Intrusion Detected by Firewall",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Suricata")
    assets: List[Office365ThreatIntelIrisAsset] = Field(..., description="List of affected assets")
    alert_status_id: int = Field(..., description="Status ID of the alert", example=3)
    alert_severity_id: int = Field(
        ...,
        description="Severity ID of the alert",
        example=5,
    )
    alert_customer_id: int = Field(
        ...,
        description="Customer ID related to the alert",
        example=1,
    )
    alert_source_content: Dict[str, Any] = Field(
        ...,
        description="Original content from the alert source",
    )
    alert_context: Office365ThreatIntelIrisAlertContext = Field(
        ...,
        description="Contextual information about the alert",
    )
    alert_iocs: Optional[List[IrisIoc]] = Field(
        None,
        description="List of IoCs related to the alert",
    )
    alert_source_event_time: str = Field(
        ...,
        description="Timestamp of the alert",
        example="2021-01-01T00:00:00.000Z",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)
