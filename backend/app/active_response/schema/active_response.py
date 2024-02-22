from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator
from pydantic import validator


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

    class Config:
        json_encoders = {str: lambda v: v.encode("utf-8", "ignore").decode("utf-8")}


class ActiveResponseDetailsResponse(BaseModel):
    success: bool
    message: str
    active_response: ActiveResponseDetails


# ! Invoke Active Response ! #
class AlertAction(str, Enum):
    unblock = "unblock"
    block = "block"


class BaseModelWithEnum(BaseModel):
    class Config:
        use_enum_values = True


class WindowsFirewallAlert(BaseModelWithEnum):
    action: AlertAction
    ip: str


class LinuxFirewallAlert(BaseModelWithEnum):
    action: AlertAction
    ip: str


class ActiveResponseCommand(str, Enum):
    windows_firewall = "windows_firewall"
    linux_firewall = "linux_firewall"

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
    agents_list: Optional[List[str]]

    @validator("agents_list", pre=True)
    def check_agents_list(cls, v):
        if v == ["*"]:
            return []
        return v


class InvokeActiveResponseRequest(BaseModel):
    endpoint: str = Field("active-response", const=True)
    arguments: list[str] = Field(default_factory=list)
    command: ActiveResponseCommand
    custom: bool = Field(True, const=True)
    alert: Dict[str, Any]
    params: ParamsModel

    @root_validator(pre=True)
    def create_alert(cls, values):
        command = values.get("command")
        alert = values.get("alert")
        if command == ActiveResponseCommand.windows_firewall:
            values["alert"] = WindowsFirewallAlert(**alert)
        elif command == ActiveResponseCommand.linux_firewall:
            values["alert"] = LinuxFirewallAlert(**alert)
        else:
            raise HTTPException(status_code=400, detail="Invalid command for alert")

        return values


class InvokeActiveResponseResponse(BaseModel):
    success: bool
    message: str
