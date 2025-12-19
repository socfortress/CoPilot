from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class AvailableMonitoringAlerts(str, Enum):
    """
    The available monitoring alerts.
    """

    WAZUH_SYSLOG_LEVEL_ALERT = (
        "This alert monitors the SYSLOG_LEVEL field in the Wazuh logs. When the level is ALERT, "
        "it triggers an alert that is created within CoPilot. Ensure that you have a pipeline "
        "rule that sets the SYSLOG_LEVEL field to ALERT when the Wazuh rule level is greater than 11."
    )
    SURICATA_ALERT_SEVERITY_1 = (
        "This alert monitors the Suricata logs. When an the alert_severity field is 1, it triggers "
        "an alert that is created within CoPilot. Ensure that you have a pipeline rule that sets "
    )
    OFFICE365_EXCHANGE_ONLINE = (
        "This alert monitors the Office365 Exchange events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Office365 alert is detected."
    )
    OFFICE365_THREAT_INTEL = (
        "This alert monitors the Office365 Threat Intelligence events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Office365 alert is detected."
    )
    CROWDSTRIKE_ALERT = (
        "This alert monitors the CrowdStrike events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the CrowdStrike alert is detected."
    )
    # ! --- Fortinet / FortiGate alerts ---
    FORTINET_SYSTEM = (
        "This alert monitors the Fortinet System events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Fortinet alert is detected."
    )
    FORTINET_UTM = (
        "This alert monitors the Fortinet UTM events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the Fortinet alert is detected."
    )
    FORTINET_FORTIWEB_PATH_TRAVERSAL_VULNERABILITY_EXPLOITATION_ATTEMPT = (
        "Detects potential exploitation attempts targeting CVE-2025-64446, a critical path traversal vulnerability "
        "affecting Fortinet FortiWeb Web Application Firewalls (WAF). "
        "An adversary can abuse this flaw, which requires no authentication, to create new, unauthorized "
        "administrative user accounts on the exposed device. "
        "This provides the threat actor with full administrative control over the security appliance, allowing "
        "them to bypass security policies, neutralize the WAF, and establish a persistent backdoor for further "
        "network intrusions."
    )
    FORTINET_WIDS_WIRELESS_VALID_CLIENT_MISASSOCIATION_DETECTED = (
        "Detects when FortiGate Wireless IDS identifies an incident where a legitimate wireless client associates "
        "with a rogue or unauthorized access point (AP), a behavior known as valid client misassociation. "
        "Attackers may set up malicious APs to impersonate trusted networks, tricking legitimate clients into "
        "connecting. "
        "This tactic is commonly used in evil twin attacks to intercept traffic, harvest credentials, or inject "
        "malicious payloads. Identifying such associations is essential to safeguarding wireless network integrity "
        "and preventing data leakage."
    )
    FORTINET_WIDS_WIRELESS_MANAGEMENT_FLOODING_DETECTED = (
        "Detects when FortiGate Wireless IDS identifies abnormal surges of wireless management frames, such as "
        "authentication, association, or probe requests, which may indicate a management frame flooding attack. "
        "Adversaries use this technique to disrupt wireless network operations, exhaust access point resources, or "
        "perform denial-of-service (DoS) attacks. "
        "Continuous monitoring of management frame activity helps with the early identification and mitigation of "
        "wireless network disruptions."
    )
    FORTINET_WIDS_WIRELESS_EAPOL_PACKET_FLOODING_DETECTED = (
        "Detects a flood of EAPOL (Extensible Authentication Protocol over LAN) packets on the wireless network "
        "identified by FortiGate Wireless IDS. "
        "Such flooding can exhaust network resources, disrupt normal authentication processes, or exploit "
        "weaknesses in WPA/WPA2 handshakes. "
        "Monitoring for this behavior is crucial to maintaining secure and stable wireless authentication services "
        "in enterprise environments."
    )
    FORTINET_WIDS_ROGUE_ACCESS_POINT_DETECTED = (
        "Detects the rogue access point (AP) in the network as reported by FortiGate Wireless IDS. "
        "Rogue APs are unauthorized wireless access points connected to a network, often used by attackers to "
        "bypass security controls, capture sensitive data, or conduct man-in-the-middle attacks. "
        "Detection of rogue APs is critical to maintaining wireless network integrity and preventing unauthorized "
        "access."
    )
    FORTINET_WIDS_WIRELESS_LONG_DURATION_ATTACK_DETECTED = (
        "Detects a long duration attack on the wireless network identified by FortiGate Wireless IDS. "
        "These attacks often involve persistent connections to rogue access points or the use of compromised "
        "clients to maintain unauthorized access over an extended period. "
        "Such activity may be used by adversaries for sustained data exfiltration, network reconnaissance, or to "
        "establish footholds in the environment. "
        "Monitoring these patterns is crucial to detecting stealthy and persistent wireless threats."
    )
    FORTINET_FIREWALL_VIRUS_DETECTED = (
        "Detects the virus in the network identified by FortiGate Firewall. "
        "This may indicate the presence of malware or a malicious file attempting to execute or transfer within "
        "the network. "
        "Threat actors may use malware to gain access, maintain persistence, or exfiltrate data. Monitoring such "
        "events can help identify compromised systems or prevent further infection spread."
    )
    FORTINET_WIDS_WIRELESS_THREAT_DETECTED = (
        "Detects potential wireless-based security threats as identified by FortiGate Wireless IDS. "
        "These threats may include spoofed access points, EAPOL flooding, deauthentication attacks, or other "
        "suspicious wireless behaviors. "
        "Monitoring such events is critical to protecting against wireless intrusion attempts, maintaining the "
        "integrity of the Wi-Fi network, and preventing unauthorized access or denial-of-service conditions caused "
        "by malicious actors."
    )
    FORTINET_WIDS_WIRELESS_INVALID_MAC_OUI_DETECTED = (
        "Detects instances where a FortiGate Wireless IDS identifies a client with an invalid or unrecognized MAC "
        "Organizationally Unique Identifier (OUI). "
        "This may indicate the presence of unauthorized, rogue, or potentially malicious devices attempting to "
        "connect to the wireless network. "
        "Monitoring for invalid MAC OUIs helps strengthen network access controls and prevent unauthorized access."
    )
    FORTINET_WIDS_WIRELESS_ASLEAP_ATTACK_DETECTED = (
        "Detects the presence of an Asleap attack in a wireless network identified by FortiGate Wireless IDS. "
        "Asleap is a tool used to exploit weak authentication in LEAP (Lightweight Extensible Authentication "
        "Protocol), potentially allowing attackers to capture and crack wireless credentials. "
        "Monitoring for this activity helps identify unauthorized attempts to compromise wireless network security "
        "and protect sensitive credentials."
    )
    FORTINET_IPS_MALICIOUS_URL_DETECTED = (
        "Detects when FortiGate Intrusion Prevention System (IPS) identifies access to a known malicious URL. "
        "This activity may indicate attempts to connect to command and control infrastructure, deliver malware, or "
        "exfiltrate data. "
        "Monitoring these detections helps identify potential threats, prevent compromise, and maintain network "
        "security."
    )
    FORTINET_IPS_BOTNET_ACTIVITY_DETECTED = (
        "Detects botnet-related activity identified by FortiGate Intrusion Prevention System (IPS). This may "
        "indicate that a host within the network is communicating with known botnet command and control servers or "
        "exhibiting behavior consistent with botnet infections. Monitoring these events helps identify compromised "
        "systems, prevent data exfiltration, and mitigate the spread of malicious activity within the environment."
    )
    FORTINET_ADMIN_USER_CREATED_FROM_PUBLIC_IP = (
        "Detects the creation of a new administrator user account on a Fortinet FortiGate device originating from "
        "a public IP address. "
        "An adversary who gains access to the management interface may create unauthorized admin accounts to "
        "establish persistent, privileged control over the firewall. "
        "By creating these accounts from external or atypical network locations, attackers can maintain long-term "
        "access, modify security policies, exfiltrate sensitive data, or prepare the environment for additional "
        "malicious activity."
    )
    FORTINET_SUSPICIOUS_CONFIG_FILE_ACCESS_FROM_EXTERNAL_NETWORK = (
        "Detects attempts to download a FortiGate configuration file from an external or publicly accessible "
        "network source. "
        "Adversaries may abuse this behavior to obtain sensitive configuration data, including administrative "
        "credentials, network topology details, VPN settings, or firewall policies. "
        "Access to this information can enable further compromise through targeted lateral movement, privilege "
        "escalation, or tailored exploitation of exposed services."
    )
    FORTINET_WIDS_WIRELESS_WEAK_ENCRYPTION_DETECTED = (
        "Detects wireless access points using weak or deprecated encryption protocols, as reported by FortiGate "
        "Wireless IDS. "
        "Risky encryption methods, such as WEP or misconfigured WPA settings, may allow adversaries to eavesdrop "
        "on network traffic or perform cryptographic attacks to gain unauthorized access. "
        "Identifying and remediating such vulnerabilities is essential to ensure wireless network confidentiality "
        "and compliance with security best practices."
    )
    FORTINET_SUSPICIOUS_SUPER_ADMIN_LOGIN_DETECTED = (
        "Detects a super admin login attempt to a FortiGate firewall originating from a suspicious or public IP "
        "address. "
        "This may indicate an attempt to exploit CVE-2025-24472 which allows unauthenticated attackers to gain "
        "super admin privileges on vulnerable FortiOS devices (<7.0.16) with exposed management interfaces."
    )
    # ! --- Palo Alto Networks (PANW) alerts ---
    PALOALTO_ALERT = (
        "This alert monitors the PaloAlto events. When an alert is detected, it triggers an "
        "alert that is created within CoPilot. Ensure that you have a pipeline rule that sets the "
        "alert_severity field to 1 when the PaloAlto alert is detected."
    )
    PALOALTO_FIREWALL_TRAFFIC_TO_PHISHING_URL_ALLOWED = (
        "Detects when the Palo Alto Networks firewall does not block traffic to a URL known to be used in phishing "
        "attacks. "
        "An adversary can abuse this by directing victims to the phishing site, potentially stealing credentials, "
        "deploying malware, or conducting other malicious activities."
    )
    PALOALTO_FIREWALL_TRAFFIC_TO_MALICIOUS_URL_ALLOWED = (
        "Detects when the Palo Alto Networks firewall does not block traffic to a URL associated with malware "
        "distribution or operation. "
        "This typically indicates a lapse in the firewall's threat intelligence or a misconfiguration. "
        "An adversary can abuse this by using the unblocked URL to download malware onto a target system, establish "
        "a command and control channel, or exfiltrate data."
    )
    PALOALTO_FIREWALL_VIRUS_ALLOWED = (
        "Detects active network communication associated with known malware that is being allowed by the Palo Alto "
        "Networks firewall. "
        "This may indicate an ongoing security threat, where malicious traffic is bypassing firewall protections, "
        "potentially leading to system compromise, data exfiltration, or further infiltration within the network."
    )
    PALOALTO_FIREWALL_TOR_TRAFFIC_ALLOWED = (
        "Detects allowed network traffic to the TOR network. Adversaries can use TOR to anonymize their network "
        "activity, bypass security controls, and evade detection while conducting malicious operations. "
        "This could lead to unauthorized access, data exfiltration, and compliance violations if deemed malicious."
    )
    PALOALTO_FIREWALL_MEDIUM_SEVERITY_CORRELATION_EVENT_DETECTED = (
        "Detects medium severity correlation events generated by Palo Alto Networks firewall's automated correlation "
        "engine. "
        "The correlation engine connects isolated network events and looks for patterns that indicate a more "
        "significant event. "
        "This helps identify suspicious traffic patterns and network anomalies which, when correlated, indicate with "
        "a high probability that a host on the network has been compromised."
    )
    # ! --- SentinelOne alerts ---
    SENTINELONE_NEW_ACTIVE_THREAT_MALICIOUS_DETECTED = "Threat with confidence level malicious detected"
    SENTINELONE_NEW_ACTIVE_THREAT_SUSPICIOUS_DETECTED = "Threat with confidence level suspicious detected"
    SENTINELONE_NEW_MITIGATION_KILL_PERFORMED_SUCCESSFULLY = "Kill performed successfully"
    SENTINELONE_NEW_MITIGATION_QUARANTINE_PERFORMED_SUCCESSFULLY = "Quarantine performed successfully"
    SENTINELONE_NEW_EXCLUSION_WAS_ADDED_OR_MODIFIED_BY_USER = "Exclusion was added/modified by user"
    SENTINELONE_NEW_PATH_EXCLUSION_ADDED = "Path Exclusion added"
    SENTINELONE_ANALYST_VERDICT_CHANGED_TO_TRUE_POSITIVE = 'A management user changed the analyst verdict to "True Positive".'
    SENTINELONE_ANALYST_VERDICT_CHANGED_TO_FALSE_POSITIVE = 'A management user changed the analyst verdict to "False Positive".'


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
    notifications: Optional[List[GraylogAlertProvisionNotification]] = []
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
    custom_fields: Optional[List[CustomFields]] = Field(
        None,
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

    # ! I think I can remove the requirement for the CUSTOMER_CODE field.
    # ! The new incident management doesnt require the CUSTOMER_CODE to be preset but
    # ! rather looks for valid CustomerCodeKeys(Enum) # !
    # @root_validator
    # def check_customer_code(cls, values):
    #     custom_fields = values.get("custom_fields")
    #     if custom_fields is None:
    #         raise HTTPException(
    #             status_code=400,
    #             detail="At least one custom field with name CUSTOMER_CODE is required",
    #         )
    #     if not any(field.name == "CUSTOMER_CODE" for field in custom_fields):
    #         raise HTTPException(
    #             status_code=400,
    #             detail="At least one custom field with name CUSTOMER_CODE is required",
    #         )
    #     return values
