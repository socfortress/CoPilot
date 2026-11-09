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
