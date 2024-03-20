from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator
from pydantic import validator


class AvailableMonitoringAlerts(str, Enum):
    """
    The available monitoring alerts.
    """

    WAZUH_SYSLOG_LEVEL_ALERT = (
        "This alert monitors the SYSLOG_LEVEL field in the Wazuh logs. When the level is ALERT, "
        "it triggers an alert that is created within DFIR-IRIS. Ensure that you have a pipeline "
        "rule that sets the SYSLOG_LEVEL field to ALERT when the Wazuh rule level is greater than 11."
    )
    SURICATA_ALERT_SEVERITY_1 = (
        "This alert monitors the Suricata logs. When an the alert_severity field is 1, it triggers "
        "an alert that is created within DFIR-IRIS. Ensure that you have a pipeline rule that sets "
    )
    OFFICE365_EXCHANGE_ONLINE = (
        "This alert monitors the Office365 Exchange events. When an alert is detected, it triggers an "
        "alert that is created within DFIR-IRIS. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Office365 alert is detected."
    )
    OFFICE365_THREAT_INTEL = (
        "This alert monitors the Office365 Threat Intelligence events. When an alert is detected, it triggers an "
        "alert that is created within DFIR-IRIS. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Office365 alert is detected."
    )


class AvailableMonitoringAlertsResponse(BaseModel):
    """
    The available monitoring alerts response.
    """

    success: bool
    message: str
    available_monitoring_alerts: List[Dict[str, str]]


class ProvisionMonitoringAlertRequest(BaseModel):
    search_within_last: int = Field(
        ...,
        description="The time in seconds to search within for the alert.",
    )
    execute_every: int = Field(
        ...,
        description="The time in seconds to execute the alert search.",
    )
    alert_name: str = Field(
        "WAZUH_SYSLOG_LEVEL_ALERT",
        description="The name of the alert to provision.",
    )

    @validator("alert_name")
    def validate_alert_name(cls, v):
        v = v.replace(" ", "_").upper()
        if v not in AvailableMonitoringAlerts.__members__:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid alert name: {v}. Must be one of: {', '.join(AvailableMonitoringAlerts.__members__)}",
            )
        return v

    @validator("search_within_last", "execute_every")
    def validate_non_zero(cls, v):
        if v == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value: {v}. Must be greater than 0.",
            )
        return v


class ProvisionWazuhMonitoringAlertResponse(BaseModel):
    success: bool
    message: str


########## ! GRAYLOG WHITELIST URL CREATION ! ##########
class GraylogUrlWhitelistEntryConfig(BaseModel):
    id: str = Field(
        ...,
        description="The ID of the URL whitelist entry.",
    )
    title: str = Field(
        ...,
        description="The title of the URL whitelist entry.",
    )
    type: str = Field(
        "literal",
        description="The type of the URL whitelist entry.",
    )
    value: str = Field(
        ...,
        description="The value of the URL whitelist entry.",
    )


class GraylogUrlWhitelistEntries(BaseModel):
    entries: List[GraylogUrlWhitelistEntryConfig]
    disabled: bool


########## ! GRAYLOG WEBHOOK CREATION ! ##########
class GraylogAlertWebhookConfig(BaseModel):
    url: str = Field(
        ...,
        description="The URL to use for the webhook.",
    )
    api_key: Optional[str] = Field(
        None,
        description="The API key to use for the webhook.",
    )
    api_secret: Optional[str] = Field(
        None,
        description="The API secret to use for the webhook.",
    )
    basic_auth: Optional[str] = Field(
        None,
        description="The basic auth to use for the webhook.",
    )
    type: str = Field(
        ...,
        description="The type of the webhook.",
    )


class GraylogAlertWebhookNotificationModel(BaseModel):
    title: str
    description: str
    config: GraylogAlertWebhookConfig


########## ! GRAYLOG EVENT CREATION ! ##########
class GraylogAlertProvisionProvider(BaseModel):
    template: str
    type: str = Field(..., alias="type")
    require_values: bool


class GraylogAlertProvisionFieldSpecItem(BaseModel):
    data_type: str
    providers: List[GraylogAlertProvisionProvider]


class GraylogAlertProvisionConfig(BaseModel):
    query: str
    query_parameters: List
    streams: List
    search_within_ms: int
    execute_every_ms: int
    group_by: List
    series: List
    conditions: Dict
    type: str = Field(..., alias="type")
    event_limit: int = Field(1000, description="The event limit for the config")


class GraylogAlertProvisionNotificationSettings(BaseModel):
    grace_period_ms: int
    backlog_size: Optional[int] = None


class GraylogAlertProvisionNotification(BaseModel):
    notification_id: str


class GraylogAlertProvisionModel(BaseModel):
    title: str
    description: str
    priority: int
    config: GraylogAlertProvisionConfig
    field_spec: Dict[str, GraylogAlertProvisionFieldSpecItem]
    key_spec: List
    notification_settings: GraylogAlertProvisionNotificationSettings
    notifications: List[GraylogAlertProvisionNotification]
    alert: bool


class AlertPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3


class CustomFields(BaseModel):
    name: str
    value: str

    @validator("name")
    def replace_spaces_with_underscores(cls, v):
        return v.replace(" ", "_")


class CustomMonitoringAlertProvisionModel(BaseModel):
    alert_name: str = Field(
        ...,
        description="The name of the alert to provision.",
        example="WAZUH_SYSLOG_LEVEL_ALERT",
    )
    alert_description: str = Field(
        ...,
        description=(
            "The description of the alert to provision. This alert monitors the "
            "SYSLOG_LEVEL field in the Wazuh logs. When the level is ALERT, it "
            "triggers an alert that is created within DFIR-IRIS. Ensure that you "
            "have a pipeline rule that sets the SYSLOG_LEVEL field to ALERT when "
            "the Wazuh rule level is greater than 11."
        ),
        example=(
            "This alert monitors the SYSLOG_LEVEL field in the Wazuh logs. When "
            "the level is ALERT, it triggers an alert that is created within "
            "DFIR-IRIS. Ensure that you have a pipeline rule that sets the "
            "SYSLOG_LEVEL field to ALERT when the Wazuh rule level is greater than 11."
        ),
    )
    alert_priority: AlertPriority = Field(
        ...,
        description="The priority of the alert to provision.",
        example=2,
    )
    search_query: str = Field(
        ...,
        description="The search query to use for the alert.",
        example="syslog_type:wazuh AND syslog_level:alert",
    )
    streams: Optional[List[str]] = Field(
        [],
        description="The streams to use for the alert.",
        example=["5f3e4c3b3f37b70001f3d7b3"],
    )
    custom_fields: List[CustomFields] = Field(
        ...,
        description="The custom fields to use for the alert.",
        example=[{"name": "source", "value": "Wazuh"}],
    )
    search_within_ms: int = Field(
        ...,
        description="The time in milliseconds to search within for the alert.",
        example=300000,
    )
    execute_every_ms: int = Field(
        ...,
        description="The time in milliseconds to execute the alert search.",
        example=300000,
    )

    @root_validator
    def check_customer_code(cls, values):
        custom_fields = values.get("custom_fields")
        if custom_fields is None:
            raise HTTPException(
                status_code=400,
                detail="At least one custom field with name CUSTOMER_CODE is required",
            )
        if not any(field.name == "CUSTOMER_CODE" for field in custom_fields):
            raise HTTPException(
                status_code=400,
                detail="At least one custom field with name CUSTOMER_CODE is required",
            )
        return values
