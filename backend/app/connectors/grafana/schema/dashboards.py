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
    WAZUH_SUMMARY = ("Wazuh", "summary.json")
    EDR_WINDOWS_EVENT_LOGS = ("Wazuh", "edr_windows_event_logs.json")
    EDR_WAZUH_INVENOTRY = ("Wazuh", "edr_wazuh_inventory.json")
    EDR_USERS_AND_GROUPS = ("Wazuh", "edr_users_and_groups.json")
    EDR_SYSTEM_VULNERABILITIES = ("Wazuh", "edr_system_vulnerabilities.json")
    EDR_SYSTEM_SECURITY_AUDIT = ("Wazuh", "edr_system_security_audit.json")
    EDR_SYSTEM_PROCESSES = ("Wazuh", "edr_system_processes.json")
    EDR_PROCESS_INJECTION = ("Wazuh", "edr_process_injection.json")
    EDR_OPEN_AUDIT = ("Wazuh", "edr_open_audit.json")
    EDR_NETWORK_SCAN = ("Wazuh", "edr_network_scan.json")
    EDR_NETWORK_CONNECTIONS = ("Wazuh", "edr_network_connections.json")
    EDR_MITRE = ("Wazuh", "edr_mitre.json")
    EDR_FIM = ("Wazuh", "edr_fim.json")
    EDR_DOCKER_MONITORING = ("Wazuh", "edr_docker_monitoring.json")
    EDR_DNS_REQUESTS = ("Wazuh", "edr_dns_requests.json")
    EDR_DLL_SIDE_LOADING = ("Wazuh", "edr_dll_side_loading.json")
    EDR_COMPLIANCE = ("Wazuh", "edr_compliance.json")
    EDR_AV_MALWARE_IOC = ("Wazuh", "edr_av_malware_ioc.json")
    EDR_AGENT_INVENTORY = ("Wazuh", "edr_agent_inventory.json")
    EDR_AD_INVENOTRY = ("Wazuh", "edr_ad_inventory.json")
    EDR_SYSTEM_VULNERABILITIES_NEW = ("Wazuh", "edr_system_vulnerabilities_new.json")


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
    OFFICE365_SUMMARY = ("Office365", "summary.json")
    TEAMS = ("Office365", "teams.json")
    THREAT_INTELLIGENCE = ("Office365", "threat_intelligence.json")


class MimecastDashboard(Enum):
    MIMECAST_SUMMARY = ("Mimecast", "summary.json")


class SapSiemDashboard(Enum):
    USERS_AUTH = ("SapSiem", "users_auth.json")


class HuntressDashboard(Enum):
    HUNTRESS_SUMMARY = ("Huntress", "summary.json")


class CarbonBlackDashboard(Enum):
    CARBONBLACK_SUMMARY = ("CarbonBlack", "summary.json")


class FortinetDashboard(Enum):
    FORTINET_SYSTEM_LOGS = ("Fortinet", "fortinet_system_logs.json")
    FORTINET_UTM_ANOMALIES = ("Fortinet", "fortinet_utm_anomalies.json")
    FORTINET_UTM_APP_CONTROL = ("Fortinet", "fortinet_utm_app_control.json")
    FOTINET_UTM_DLP = ("Fortinet", "fortinet_utm_dlp.json")
    FORTINET_UTM_DNS = ("Fortinet", "fortinet_utm_dns.json")
    FORTINET_UTM_IPS = ("Fortinet", "fortinet_utm_ips.json")
    FORTINET_UTM_SSL = ("Fortinet", "fortinet_utm_ssl.json")
    FORTINET_UTM_SUMMARY = ("Fortinet", "fortinet_utm_summary.json")
    FORTINET_UTM_VIRUS = ("Fortinet", "fortinet_utm_virus.json")
    FORTINET_UTM_WEBFILTER = ("Fortinet", "fortinet_utm_webfilter.json")
    FORTINET_VPN = ("Fortinet", "fortinet_vpn.json")


class CrowdstrikeDashboard(Enum):
    CROWDSTRIKE_SUMMARY = ("Crowdstrike", "summary.json")


class DuoDashboard(Enum):
    DUO_AUTH = ("Duo", "duo_auth.json")


class DarktraceDashboard(Enum):
    DARKTRACE_SUMMARY = ("Darktrace", "summary.json")


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
    grafana_url: str = Field(
        "https://grafana.company.local",
        description="URL of the Grafana instance for the links within the dashboards.",
    )

    @validator("dashboards", each_item=True)
    def check_dashboard_exists(cls, e):
        valid_dashboards = {
            item.name: item
            for item in list(WazuhDashboard)
            + list(Office365Dashboard)
            + list(MimecastDashboard)
            + list(SapSiemDashboard)
            + list(HuntressDashboard)
            + list(CarbonBlackDashboard)
            + list(FortinetDashboard)
            + list(CrowdstrikeDashboard)
            + list(DuoDashboard)
            + list(DarktraceDashboard)
        }
        if e not in valid_dashboards:
            raise ValueError(f'Dashboard identifier "{e}" is not recognized.')
        return e
