from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.active_response.schema.sysmon_health import SysmonHealthApplyResult


class SysmonConfigDataStoreCreation(BaseModel):
    customer_code: str
    content_type: str = "application/xml"
    bucket_name: str = "sysmon-configs"


class SysmonConfigUploadResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    filename: str
    overwritten: bool


class SysmonConfigListResponse(BaseModel):
    success: bool
    message: str
    customer_codes: List[str]


class SysmonConfigContentResponse(BaseModel):
    success: bool
    message: str
    customer_code: str
    config_content: str


class SysmonConfigDeploymentResult(BaseModel):
    success: bool
    message: str
    customer_code: str
    worker_success: bool = False
    worker_message: Optional[str] = None
    error_detail: Optional[str] = None
    sysmon_health: Optional[SysmonHealthApplyResult] = Field(
        None,
        description="The Sysmon health apply run after a successful deploy (admins only), which enables the sysmon-reload wodle.",
    )
    sysmon_health_warning: Optional[str] = Field(
        None,
        description="Set when the endpoints will not (or may not) apply the deployed config yet, and why.",
    )


class SysmonDefaultConfigResponse(BaseModel):
    success: bool
    message: str
    present: bool = Field(..., description="Whether this CoPilot has a default Sysmon config.")
    config_content: Optional[str] = Field(None, description="The default, rendered for rendered_for when a customer code was given.")
    rendered_for: Optional[str] = Field(
        None,
        description=(
            "The customer code that replaced each __INSTALLDIRNAME__ placeholder. Unset when no customer code was given, or "
            "when the default has no placeholder: then it comes back as stored."
        ),
    )
    placeholders: int = Field(
        0,
        description="How many times __INSTALLDIRNAME__ occurs in the stored default. Each was replaced when rendered_for is set.",
    )


class SysmonDefaultConfigSaveRequest(BaseModel):
    config_content: str
    customer_code: Optional[str] = Field(
        None,
        description="The customer the content was rendered for: its install-folder paths are turned back into __INSTALLDIRNAME__.",
    )


class SysmonDefaultConfigSaveResponse(BaseModel):
    success: bool
    message: str
    placeholders: int = Field(..., description="How many times __INSTALLDIRNAME__ occurs in what was saved.")
    restored: int = Field(..., description="How many of the customer's install-folder paths were turned back into the placeholder.")
