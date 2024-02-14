from enum import Enum
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


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
    EDR_WAZUH_INVENOTRY = ("Wazuh", "edr_wazuh_inventory.json")
    EDR_USERS_AND_GROUPS = ("Wazuh", "edr_users_and_groups.json")
    EDR_SYSTEM_VULNERABILITIES = ("Wazuh", "edr_system_vulnerabilities.json")
    EDR_SYSTEM_SECURITY_AUDIT = ("Wazuh", "edr_system_security_audit.json")
    EDR_SYSTEM_PROCESSES = ("Wazuh", "edr_system_processes.json")
    EDR_PROCESS_INJECTION = ("Wazuh", "edr_process_injection.json")
    EDR_OPEN_AUDIT = ("Wazuh", "edr_open_audit.json")
    EDR_NETWORK_SCAN = ("Wazuh", "edr_network_scan.json")
    EDR_MITRE = ("Wazuh", "edr_mitre.json")
    EDR_FIM = ("Wazuh", "edr_fim.json")
    EDR_DOCKER_MONITORING = ("Wazuh", "edr_docker_monitoring.json")
    EDR_DNS_REQUESTS = ("Wazuh", "edr_dns_requests.json")
    EDR_DLL_SIDE_LOADING = ("Wazuh", "edr_dll_side_loading.json")
    EDR_COMPLIANCE = ("Wazuh", "edr_compliance.json")
    EDR_AV_MALWARE_IOC = ("Wazuh", "edr_av_malware_ioc.json")
    EDR_AGENT_INVENTORY = ("Wazuh", "edr_agent_inventory.json")
    EDR_AD_INVENOTRY = ("Wazuh", "edr_ad_inventory.json")


class Office365Dashboard(Enum):
    ACTIVE_DIRECTORY = ("Office365", "active_directory.json")
    APPLICATIONS = ("Office365", "applications.json")
    COMPLIANCE_CENTER = ("Office365", "compliance_center.json")
    DEFENDER_FOR_IDENTITIY = ("Office365", "defender_for_identity.json")
    DLP = ("Office365", "dlp.json")
    ENDPOINT = ("Office365", "endpoint.json")
    EXCHANGE = ("Office365", "exchange.json")
    FORMS = ("Office365", "forms.json")
    MITRE = ("Office365", "mitre.json")
    ONEDRIVE = ("Office365", "onedrive.json")
    POWERBI = ("Office365", "powerbi.json")
    SHAREPOINT = ("Office365", "sharepoint.json")
    SUMMARY = ("Office365", "summary.json")
    TEAMS = ("Office365", "teams.json")
    THREAT_INTELLIGENCE = ("Office365", "threat_intelligence.json")


class MimecastDashboard(Enum):
    SUMMARY = ("Mimecast", "summary.json")

class SapSiemDashboard(Enum):
    USER_AUTH = ("SapSiem", "users_auth.json")


class DashboardProvisionRequest(BaseModel):
    dashboards: List[str] = Field(
        ...,
        description="List of dashboard identifiers to provision",
    )
    organizationId: int = Field(
        0,
        description="Organization ID to provision dashboards to",
    )
    folderId: int = Field(0, description="Folder ID to provision dashboards to")
    datasourceUid: str = Field(
        "uid-to-be-replaced",
        description="Datasource UID to use for dashboards",
    )

    @validator("dashboards", each_item=True)
    def check_dashboard_exists(cls, e):
        valid_dashboards = {item.name: item for item in list(WazuhDashboard) + list(Office365Dashboard)}
        if e not in valid_dashboards:
            raise ValueError(f'Dashboard identifier "{e}" is not recognized.')
        return e
