from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class Artifacts(BaseModel):
    description: str = Field(..., description="Description of the artifact.")
    name: str = Field(..., description="Name of the artifact.")


class ArtifactsResponse(BaseModel):
    message: str = Field(...)
    # make artifacts optional
    artifacts: Optional[List[Artifacts]]
    success: str = Field(...)


class OSPrefixEnum(Enum):
    LINUX = "Linux."
    WINDOWS = "Windows."
    MACOS = "MacOS."


class OSPrefixModel(BaseModel):
    os_name: Optional[str]
    os_prefix_mapping: Dict[str, str] = {
        "windows": "Windows",
        "linux": "Linux",
        "mac": "MacOS",
        "ubuntu": "Linux",  # Add more mappings as needed
    }

    def get_os_prefix(self) -> Optional[str]:
        if self.os_name is None:
            return None
        return self._map_os_name_to_prefix()

    def _map_os_name_to_prefix(self) -> Optional[str]:
        os_name_lower = self.os_name.lower()
        for keyword, prefix in self.os_prefix_mapping.items():
            if keyword in os_name_lower:
                return prefix
        return None


class OperationEnum(str, Enum):
    collect_artifact = "collect_artifact"
    run_command = "run_command"
    quarantine = "quarantine"


class ActionEnum(str, Enum):
    quarantine = "quarantine"
    remove_quarantine = "remove_quarantine"


class CommandArtifactsEnum(str, Enum):
    windows_powershell = "Windows.System.PowerShell"
    windows_cmd = "Windows.System.CmdShell"
    linux_bash = "Linux.Sys.BashShell"


class QuarantineArtifactsEnum(str, Enum):
    windows_quarantine = "Windows.Remediation.Quarantine"
    linux_quarantine = "Linux.Remediation.Quarantine"


class BaseBody(BaseModel):
    hostname: str = Field(..., description="Name of the client")
    velociraptor_id: Optional[str] = Field(None, description="Client ID of the client")
    velociraptor_org: Optional[str] = Field(None, description="Organization of the client")


class CollectArtifactBody(BaseBody):
    artifact_name: Optional[str] = Field(
        None,
        description="Name of the artifact for collection or command running",
    )


class RunCommandBody(BaseBody):
    command: Optional[str] = Field(None, description="Command to run")
    artifact_name: CommandArtifactsEnum = Field(
        None,
        description="Name of the artifact for command running",
    )


class QuarantineBody(BaseBody):
    action: ActionEnum = Field(..., description="Action to perform")
    artifact_name: QuarantineArtifactsEnum = Field(
        None,
        description="Name of the artifact for quarantine or removal of quarantine",
    )


class BaseResponse(BaseModel):
    message: str = Field(...)
    success: bool = Field(...)  # Changed from str to bool based on your sample data
    results: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Results of the operation",
    )


class CollectArtifactResponse(BaseResponse):
    pass  # If you have additional fields, you can define them here


class RunCommandResponse(BaseResponse):
    pass  # If you have additional fields, you can define them here


class QuarantineResponse(BaseResponse):
    pass  # If you have additional fields, you can define them here


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


class OS(str, Enum):
    Windows = "Windows"
    Linux = "Linux"
    MacOS = "MacOS"


class ArtifactReccomendationAIRequest(BaseModel):
    os: OS = Field(..., description="Operating system of the client")
    prompt: dict = Field(..., example=payload)


class ArtifactReccomendationRequest(BaseModel):
    artifacts: List[Artifacts] = Field(..., description="List of artifacts to be recommended")
    os: str = Field(..., description="Operating system of the client")
    prompt: dict = Field(..., example=payload)


class VelociraptorArtifactRecommendation(BaseModel):
    name: str = Field(..., description="The name of the artifact.")
    description: str = Field(..., description="A description of the artifact.")
    explanation: str = Field(..., description="A detailed explanation of the purpose and why the artifact was selected.")


class ArtifactReccomendationResponse(BaseModel):
    message: str = Field(...)
    success: bool = Field(...)
    recommendations: list[VelociraptorArtifactRecommendation]
