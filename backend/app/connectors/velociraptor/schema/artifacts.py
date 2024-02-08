from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
