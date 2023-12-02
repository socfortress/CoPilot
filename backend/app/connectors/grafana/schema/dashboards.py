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
