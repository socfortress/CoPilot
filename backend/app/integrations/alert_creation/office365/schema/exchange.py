from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class ValidOffice365Workloads(Enum):
    THREAT_INTEL_VALUE = "ThreatIntelligence"
    EXCHANGE_VALUE = "Exchange"
    ACTIVE_DIRECTORY_VALUE = "AzureActiveDirectory"


############### ! REQUEST BODY RECEIVED ! ################


class Office365ExchangeAlertBase(BaseModel):
    id: str = Field(..., description="Unique identifier for the alert", alias="_id")
    index: str = Field(
        ...,
        description="Index of the alert in the database",
        alias="_index",
    )
    data_office365_OrganizationId: str = Field(
        ...,
        description="Organization ID of the alert",
    )
    data_office365_Operation: str = Field(..., description="Operation of the alert")
    data_office365_Workload: str = Field(..., description="Workload of the alert")
    data_office365_UserId: str = Field(..., description="User ID of the alert")
    data_office365_Id: str = Field(..., description="ID of the alert")
    rule_description: str = Field(..., description="Description of the alert")
    rule_id: str = Field(..., description="ID of the alert")
    rule_level: int = Field(..., description="Level of the alert")
    timestamp: str = Field(..., description="The timestamp of the alert.")
    timestamp_utc: Optional[str] = Field(
        ...,
        description="The UTC timestamp of the alert.",
    )
    time_field: Optional[str] = Field(
        "timestamp",
        description="The timefield of the alert to be used when creating the IRIS alert.",
    )

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ExchangeAlertRequest(Office365ExchangeAlertBase):
    rule_mitre_tactic: Optional[str] = Field(
        None,
        description="MITRE tactic of the alert",
    )
    rule_mitre_id: Optional[str] = Field(None, description="MITRE ID of the alert")
    rule_mitre_technique: Optional[str] = Field(
        None,
        description="MITRE technique of the alert",
    )

    class Config:
        allow_population_by_field_name = True
        extra = Extra.allow

    def to_dict(self):
        return self.dict(exclude_none=True)


class Office365ExchangeAlertResponse(BaseModel):
    success: bool
    message: str
    alert_id: int = Field(..., description="The alert id as created in IRIS.")
    customer: str = Field(..., description="The customer name.")
    alert_source_link: str = Field(
        ...,
        description="The link to the alert within Grafana.",
    )


########### ! Create Alerts Schemas ! ###########
class IrisAsset(BaseModel):
    asset_name: Optional[str] = Field(
        "Could not find data_office365_UserId in alert",
        description="Name of the asset",
        example="Server01",
    )
    asset_ip: Optional[str] = Field(
        "n/a",
        description="IP address of the asset",
        example="192.168.1.1",
    )
    asset_description: Optional[str] = Field(
        "Office365 User ID",
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
        example="Office365 Exchange Alert",
    )
    alert_level: int = Field(..., description="Severity level of the alert", example=3)
    rule_id: int = Field(
        ...,
        description="ID of the Suricata rule that triggered the alert",
        example="2001",
    )
    asset_name: Optional[str] = Field(
        "Could not find data_office365_UserId in alert",
        description="Name of the asset",
        example="Server01",
    )
    asset_ip: Optional[str] = Field(
        "n/a",
        description="IP address of the asset",
        example="1.1.1.1",
    )
    asset_type: Optional[int] = Field(
        1,
        description="Type ID of the asset",
        example=1,
    )
    office365_operation: str = Field(
        ...,
        description="Operation of the alert",
        example="MailItemsAccessed",
    )
    data_office365_Id: str = Field(
        ...,
        description="ID of the alert",
        example="123",
    )
    rule_mitre_id: Optional[str] = Field(None, description="MITRE ID of the alert")
    rule_mitre_tactic: Optional[str] = Field(
        None,
        description="MITRE tactic of the alert",
    )
    rule_mitre_technique: Optional[str] = Field(
        None,
        description="MITRE technique of the alert",
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
