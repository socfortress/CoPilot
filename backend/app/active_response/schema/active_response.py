import ipaddress
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


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


class FirewallAlert(BaseModelWithEnum):
    """Shared shape for the firewall active responses — an action plus the IP it targets."""

    action: AlertAction
    ip: str

    @field_validator("ip")
    @classmethod
    def check_ip(cls, v: str) -> str:
        # The value is forwarded verbatim to the agent-side script, which builds
        # a firewall rule out of it. Reject anything that isn't an address here
        # so the analyst gets a message naming the field instead of a silent
        # no-op logged on the endpoint hours later.
        try:
            ipaddress.ip_address(v.strip())
        except ValueError:
            raise ValueError(f"'{v}' is not a valid IP address")
        return v.strip()


class WindowsFirewallAlert(FirewallAlert):
    pass


class LinuxFirewallAlert(FirewallAlert):
    pass


class SysmonConfigReloadAlert(BaseModelWithEnum):
    action: Literal[AlertAction.sysmon_config_reload] = AlertAction.sysmon_config_reload


class ActiveResponseCommand(str, Enum):
    windows_firewall = "windows_firewall"
    linux_firewall = "linux_firewall"
    sysmon_config_reload = "sysmon_config_reload"

    @classmethod
    def _missing_(cls, value):
        # Accept the name as the UI displays it ("WINDOWS_FIREWALL", "Windows_Firewall")
        # as well as the canonical lowercase value. The trailing "0" Wazuh expects is
        # appended at invoke time by the route, never here.
        if isinstance(value, str):
            for member in cls:
                if member.name.lower() == value.lower():
                    return member

        raise HTTPException(
            status_code=400,
            detail=f"Invalid command: {value}, must be one of {', '.join([member.name for member in cls])}",
        )


# Which alert shape each command expects. A command missing from this map has no
# validated payload and is rejected rather than forwarded to Wazuh unchecked.
ALERT_MODEL_BY_COMMAND = {
    ActiveResponseCommand.windows_firewall: WindowsFirewallAlert,
    ActiveResponseCommand.linux_firewall: LinuxFirewallAlert,
    ActiveResponseCommand.sysmon_config_reload: SysmonConfigReloadAlert,
}


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
        if not isinstance(values, dict):
            return values

        command = values.get("command")
        if command is None:
            # Nothing to pick an alert shape with. Fall through so the `command`
            # field reports itself as missing, which names the field; a 400 from
            # here would not.
            return values

        alert = values.get("alert") or {}
        if not isinstance(alert, dict):
            raise ValueError("'alert' must be an object")

        alert_model = ALERT_MODEL_BY_COMMAND.get(ActiveResponseCommand(command))
        if alert_model is None:
            raise HTTPException(status_code=400, detail="Invalid command for alert")

        # `alert` is typed `Dict[str, Any]` and the route json.dumps() it straight
        # onto the wire, so the per-command model is used to *validate* the payload
        # and then dumped back to a plain dict. Leaving the model instance in place
        # made Pydantic 2 reject the field outright ("Input should be a valid
        # dictionary"), which surfaced in the UI as a bare "Invalid value." on
        # perfectly good input — issue #960.
        values["alert"] = alert_model(**alert).model_dump(mode="json")

        return values

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "endpoint": "/active-response",
                "arguments": [],
                "command": "windows_firewall",
                "custom": True,
                "alert": {"action": "block", "ip": "1.1.1.1"},
                "params": {"wait_for_complete": True, "agents_list": ["032"]},
            },
        },
    )


class InvokeActiveResponseResponse(BaseModel):
    success: bool
    message: str
