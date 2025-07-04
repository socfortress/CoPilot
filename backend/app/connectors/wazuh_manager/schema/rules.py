from typing import List
from typing import Optional
from typing import Union

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class RuleDisable(BaseModel):
    rule_id: str
    reason_for_disabling: str
    length_of_time: str


class RuleDisableResponse(BaseModel):
    previous_level: Optional[str]
    message: str
    success: bool


class RuleEnable(BaseModel):
    rule_id: str
    reason_for_enabling: str


class RuleEnableResponse(BaseModel):
    new_level: Optional[str]
    message: str
    success: bool


class AllDisabledRule(BaseModel):
    rule_id: str
    previous_level: str
    new_level: str
    reason_for_disabling: str
    length_of_time: str
    disabled_by: str


class AllDisabledRuleResponse(BaseModel):
    disabled_rules: List[AllDisabledRule]
    success: bool
    message: str


# Simplified and more efficient rule models
class WazuhRule(BaseModel):
    """Represents a single Wazuh rule from the API."""

    filename: str
    relative_dirname: str
    id: int
    level: int
    status: str
    description: str
    groups: List[str] = []
    pci_dss: List[str] = []
    gpg13: List[str] = []
    gdpr: List[str] = []
    hipaa: List[str] = []
    nist_800_53: List[str] = Field(default=[], alias="nist-800-53")
    tsc: List[str] = []
    mitre: List[str] = []
    details: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"  # Ignore extra fields from API


class WazuhRulesResponse(BaseModel):
    """Response model for Wazuh rules listing."""

    success: bool
    message: str
    results: List[WazuhRule] = []
    total_items: Optional[int] = None


class WazuhRuleFile(BaseModel):
    """Represents a single Wazuh rule file from the API."""

    filename: str = Field(..., description="Rule file name")
    relative_dirname: str = Field(..., description="Relative directory path")
    status: str = Field(..., description="File status (enabled/disabled)")

    class Config:
        extra = "ignore"  # Ignore extra fields from API


class WazuhRuleFilesResponse(BaseModel):
    """Response model for Wazuh rule files listing."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    results: List[WazuhRuleFile] = Field(default=[], description="List of rule files")
    total_items: Optional[int] = Field(None, description="Total number of files")


class WazuhRuleFileContentResponse(BaseModel):
    """Response model for Wazuh rule file content."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    filename: str = Field(..., description="The requested filename")
    content: Union[dict, str] = Field(..., description="File content (structured or raw)")
    is_raw: bool = Field(False, description="Whether the content is raw text")
    total_items: Optional[int] = Field(None, description="Total affected items from API")


class WazuhRuleFileUploadResponse(BaseModel):
    """Response model for Wazuh rule file upload/update."""

    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    filename: str = Field(..., description="The uploaded/updated filename")
    details: Optional[dict] = Field(None, description="Additional response details from API")
    total_items: Optional[int] = Field(None, description="Total affected items from API")


payload = {
    "data_win_system_eventRecordID": "521098",
    "data_win_eventdata_user": "WIN-HFOU106TD7K\\Administrator",
    "agent_id": "111",
    "agent_name": "WIN-HFO106TD7K",
    "gl2_remote_ip": "10.255.255.13",
    "data_win_system_eventID": "22",
    "agent_labels_customer": "00002",
    "source": "10.255.255.13",
    "gl2_source_input": "660320f176ca320e8393f030",
    "rule_level": 3,
    "data_win_system_task": "22",
    "timestamp_utc": "2024-04-17T15:06:54.742Z",
    "syslog_type": "wazuh",
    "data_win_system_threadID": "2888",
    "rule_description": "Sysmon - Event 22: DNS Request by C:\\Windows\\system32\\PING.EXE",
    "gl2_source_node": "3b68efa4-3319-4885-a38f-c944f0fcf191",
    "id": "1713366415.56188571",
    "rule_mitre_tactic": "Command and Control",
    "process_image": "C:\\Windows\\system32\\PING.EXE",
    "data_win_eventdata_utcTime": "2024-04-17 15:06:28.457",
    "streams": ["661555f676ca320e837b14cc", "660320f176ca320e8393f057"],
    "rule_mitre_id": "T1071",
    "gl2_message_id": "01HVP9HG8YE31EQH1878V50H89",
    "data_win_system_computer": "WIN-HFOU106TD7K",
    "agent_ip": "192.168.200.3",
    "data_win_eventdata_image": "C:\\Windows\\system32\\PING.EXE",
    "threat_intel_value": "evil.socfortress.co",
    "data_win_eventdata_queryName": "evil.socfortress.co",
    "rule_groups": "windows, sysmon, sysmon_event_22",
    "data_win_system_keywords": "0x8000000000000000",
    "data_win_system_level": "4",
    "process_id": "6072",
    "data_win_eventdata_queryStatus": "0",
    "data_win_system_severityValue": "INFORMATION",
    "dns_response_code": "0",
    "dns_query": "evil.socfortress.co",
    "data_win_eventdata_processGuid": "{691ff406-e58c-661f-b401-000000002300}",
    "rule_mitre_technique": "Application Layer Protocol",
    "rule_firedtimes": 2,
    "data_win_system_systemTime": "2024-04-17T15:06:54.742696000Z",
    "decoder_name": "windows_eventchannel",
    "data_win_system_processID": "2180",
    "data_win_system_channel": "Microsoft-Windows-Sysmon/Operational",
    "syslog_level": "ALERT",
    "threat_intel_comment": "This is a test IoC",
    "data_win_system_providerName": "Microsoft-Windows-Sysmon",
    "data_win_eventdata_processId": "6072",
    "data_win_system_version": "5",
    "data_win_system_providerGuid": "{5770385f-c22a-43e0-bf4c-06f5698ffbd9}",
    "timestamp": "2024-04-17 15:06:57.694",
    "threat_intel_ioc_source": "test",
    "rule_group1": "windows",
    "data_win_system_opcode": "0",
}


class RuleExcludeRequest(BaseModel):
    integration: str = Field(..., example="wazuh-rule-exclusion")
    prompt: dict = Field(..., example=payload)

    @validator("integration")
    def check_integration(cls, v):
        if v != "wazuh-rule-exclusion":
            raise HTTPException(
                status_code=400,
                detail="Invalid integration. Only 'wazuh-rule-exclusion' is supported.",
            )
        return v

    @validator("prompt")
    def check_rule_group(cls, v):
        if "rule_group3" in v:
            if "rule_group1" not in v and "rule_group3" not in v:
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'rule_group1' or 'rule_group3' in prompt.",
                )
            if ("rule_group1" in v and v["rule_group1"] != "windows") and ("rule_group3" in v and v["rule_group3"] != "windows"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid 'rule_group1' or 'rule_group3'. At least one must be 'windows'.",
                )
        else:
            if "rule_group1" not in v:
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'rule_group1' in prompt.",
                )
            if v["rule_group1"] != "windows":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid 'rule_group1'. Only 'windows' is supported.",
                )
        return v


class RuleExcludeResponse(BaseModel):
    wazuh_rule: str
    explanation: str
    message: str
    success: bool
