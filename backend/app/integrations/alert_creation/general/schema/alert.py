from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class ValidIocFields(Enum):
    MISP_VALUE = "misp_value"
    OPENCTI_VALUE = "opencti_value"
    THREAT_INTEL_VALUE = "threat_intel_value"


class RawGenericSourceModel(BaseModel):
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    rule_description: Optional[str] = Field(
        "No autogenerated rule_description found",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    syslog_level: Optional[str] = Field(
        "No autogenerated syslog_level found",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )

    class Config:
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class CreateAlertRequest(BaseModel):
    index: str = Field(
        ...,
        alias="_index",
    )  # Needing to alias these fields because they are reserved words in Python
    id: str = Field(
        ...,
        alias="_id",
    )  # Needing to alias these fields because they are reserved words in Python
    agent_name: str = Field(..., description="The name of the agent.")
    agent_ip: str = Field(
        ...,
        description="IP address of the agent that triggered the alert",
        example="1.1.1.1",
    )
    agent_id: str = Field(..., description="The id of the agent.")
    agent_labels_customer: str = Field(..., description="The customer of the agent.")
    rule_id: str = Field(..., description="The id of the rule.")
    rule_level: int = Field(..., description="The level of the rule.")
    rule_description: str = Field(..., description="The description of the rule.")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )
    asset_type_id: Optional[int] = Field(
        9,
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
    _source: RawGenericSourceModel

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class CreateAlertResponse(BaseModel):
    success: bool
    message: str
    alert_id: int = Field(..., description="The alert id as created in IRIS.")
    customer: str = Field(..., description="The customer name.")
    alert_source_link: str = Field(
        ...,
        description="The link to the alert within Grafana.",
    )


class GenericSourceModel(BaseModel):
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


class GenericAlertModel(BaseModel):
    _index: str
    _id: str
    _version: int
    _source: GenericSourceModel
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


# Sample data from `get_single_alert_details`
sample_data = {
    "_index": "some_index",
    "_id": "some_id",
    "_version": 1,
    "_source": {
        "agent_name": "some_agent_name",
        "agent_id": "some_agent_id",
        # ... other fields
    },
    # ... other fields
}


########### ! Create Alerts Schemas ! ###########
class IrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Asset Not Found. Verify Wazuh Manager API is Running",
        description="Name of the asset",
        example="Server01",
    )
    asset_ip: Optional[str] = Field(
        "Asset IP Not Found. Verify Wazuh Manager API is Running",
        description="IP address of the asset",
        example="192.168.1.1",
    )
    asset_description: Optional[str] = Field(
        "Asset Not Found. Verify Wazuh Manager API is Running",
        description="Description of the asset",
        example="Windows Server",
    )
    asset_type_id: Optional[int] = Field(
        9,
        description="Type ID of the asset",
        example=1,
    )
    asset_tags: Optional[str] = Field(
        "Agent ID not found. Ensure the agent has been registered with Wazuh Manager and synced to the Agents table.",
        description="Tags of the asset",
        example="001",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class IrisIoc(BaseModel):
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

    def to_dict(self):
        return self.dict(exclude_none=True)


class IrisTags(BaseModel):
    rule_id: str = Field(..., description="Rule ID from the alert", example="001")

    def to_dict(self):
        return self.dict(exclude_none=True)


class IrisAlertContext(BaseModel):
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
    alert_id: str = Field(..., description="ID of the alert", example="123")
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
    asset_name: str = Field(
        ...,
        description="Name of the affected asset",
        example="Server01",
    )
    asset_ip: str = Field(
        ...,
        description="IP address of the affected asset",
        example="192.168.1.1",
    )
    asset_type: int = Field(..., description="Type ID of the affected asset", example=1)
    process_id: Optional[str] = Field(
        "No process ID found",
        description="Process ID involved in the alert",
        example="4567",
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


class IrisAlertPayload(BaseModel):
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
    alert_source_link: str = Field(
        ...,
        description="Link to the alert within Grafana",
        example="https://grafana.com",
    )
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
    alert_context: IrisAlertContext = Field(
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


########### ! Send to Shuffle Schema ! ###########
class ShuffleAlertPayload(BaseModel):
    alert_title: str = Field(
        ...,
        description="Title of the alert",
        example="Intrusion Detected",
    )
    alert_source: str = Field(..., description="Source of the alert", example="Wazuh")
    asset_name: Optional[str] = Field(None, description="Name of the affected asset")
    alert_id: int = Field(..., description="Alert ID as created in IRIS")
    customer: str = Field(..., description="Customer name")
    alert_link: str = Field(..., description="Link to the alert in IRIS")

    def to_dict(self):
        return self.dict(exclude_none=True)
