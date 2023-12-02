from enum import Enum
from pydantic import BaseModel

class GrafanaDashboard(BaseModel):
    id: int
    slug: str
    status: str
    uid: str
    url: str
    version: int

class GrafanaDashboardResponse(BaseModel):
    provisioned_dashboards: list[GrafanaDashboard]
    success: bool
    message: str


# ! DASHBOARD CLASSES NEED TO BE DEFINED HERE !
class WazuhDashboard(Enum):
    SUMMARY = ("Wazuh", "summary.json")
    EDR_WINDOWS_EVENT_LOGS = ("Wazuh", "edr_windows_event_logs.json")
