from pydantic import BaseModel
from enum import Enum
from typing import List, Dict

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
