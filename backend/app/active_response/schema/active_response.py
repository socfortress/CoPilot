from enum import Enum
from typing import Literal, Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import field_validator, model_validator, ConfigDict, BaseModel
from pydantic import Field


class ActiveResponsesSupported(Enum):
    WINDOWS_FIREWALL = "Block or unblock any outbound traffic to the defined IP address via the Windows Firewall"
    # Add more active responses here as needed


class ActiveResponse(BaseModel):
    name: str
    description: str


class ActiveResponsesSupportedResponse(BaseModel):
    supported_active_responses: List[ActiveResponse]
    success: bool
    message: str


class ActiveResponseDetails(BaseModel):
    name: str
    description: str
    markdown_content: str
    # TODO[pydantic]: The following keys were removed: `json_encoders`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(json_encoders={str: lambda v: v.encode("utf-8", "ignore").decode("utf-8")})


class ActiveResponseDetailsResponse(BaseModel):
    success: bool
    message: str
    active_response: ActiveResponseDetails


# ! Invoke Active Response ! #
class AlertAction(str, Enum):
    unblock = "unblock"
    block = "block"
    sysmon_config_reload = "sysmon_config_reload"


class BaseModelWithEnum(BaseModel):
    model_config = ConfigDict(use_enum_values=True)


class WindowsFirewallAlert(BaseModelWithEnum):
    action: AlertAction
    ip: str


class LinuxFirewallAlert(BaseModelWithEnum):
    action: AlertAction
    ip: str


class SysmonConfigReloadAlert(BaseModelWithEnum):
    action: Literal[AlertAction.sysmon_config_reload] = AlertAction.sysmon_config_reload


class ActiveResponseCommand(str, Enum):
    windows_firewall = "windows_firewall"
    linux_firewall = "linux_firewall"
    sysmon_config_reload = "sysmon_config_reload"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.name == value:
                return member

        for active_response in ActiveResponsesSupported:
            if active_response.name.lower() == value.lower():
                return cls[f"{value}0"]

        raise HTTPException(
            status_code=400,
            detail=f"Invalid command: {value}, must be one of {', '.join([member.name for member in cls])}",
        )


class ParamsModel(BaseModel):
    wait_for_complete: bool
    agents_list: Optional[List[str]] = None

    @field_validator("agents_list", mode="before")
    @classmethod
    def check_agents_list(cls, v):
        if v == ["*"]:
            return []
        return v


class InvokeActiveResponseRequest(BaseModel):
    endpoint: Literal["/active-response"] = "/active-response"
    arguments: list[str] = Field(default_factory=list)
    command: ActiveResponseCommand
    custom: Literal[True] = True
    alert: Dict[str, Any]
    params: ParamsModel

    @model_validator(mode="before")
    @classmethod
    def create_alert(cls, values):
        command = values.get("command")
        alert = values.get("alert")
        if command == ActiveResponseCommand.windows_firewall:
            values["alert"] = WindowsFirewallAlert(**alert)
        elif command == ActiveResponseCommand.linux_firewall:
            values["alert"] = LinuxFirewallAlert(**alert)
        elif command == ActiveResponseCommand.sysmon_config_reload:
            values["alert"] = SysmonConfigReloadAlert(**alert)
        else:
            raise HTTPException(status_code=400, detail="Invalid command for alert")

        return values
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "endpoint": "/active-response",
            "arguments": [],
            "command": "windows_firewall",
            "custom": True,
            "alert": {"action": "block", "ip": "1.1.1.1"},
            "params": {"wait_for_complete": True, "agents_list": ["032"]},
        },
    })


class InvokeActiveResponseResponse(BaseModel):
    success: bool
    message: str
