from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Optional

class AvailableMonitoringAlerts(str, Enum):
    """
    The available monitoring alerts.
    """
    WAZUH = (
    "This alert monitors the SYSLOG_LEVEL field in the Wazuh logs. When the level is ALERT, "
    "it triggers an alert that is created within DFIR-IRIS. Ensure that you have a pipeline "
    "rule that sets the SYSLOG_LEVEL field to ALERT when the Wazuh rule level is greater than 11."
)


class AvailableMonitoringAlertsResponse(BaseModel):
    """
    The available monitoring alerts response.
    """
    success: bool
    message: str
    available_monitoring_alerts: List[Dict[str, str]]


class ProvisionWazuhMonitoringAlertResponse(BaseModel):
    success: bool
    message: str

########## ! GRAYLOG WEBHOOK CREATION ! ##########
class GraylogAlertWebhookConfig(BaseModel):
    url: str
    api_key: str
    api_secret: Optional[str] = None
    basic_auth: Optional[str] = None
    type: str

class GraylogAlertWebhookNotificationModel(BaseModel):
    title: str
    description: str
    config: GraylogAlertWebhookConfig



########## ! GRAYLOG EVENT CREATION ! ##########
class GraylogAlertProvisionProvider(BaseModel):
    template: str
    type: str = Field(..., alias='type')
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
    type: str = Field(..., alias='type')

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
