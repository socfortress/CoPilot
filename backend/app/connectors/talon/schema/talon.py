from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class TalonMessageRequest(BaseModel):
    message: str = Field(..., description="The message to send to Talon")
    sender: str = Field(default="copilot", description="The sender identifier")


class TalonMessageResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class TalonInvestigateRequest(BaseModel):
    alert_id: int = Field(..., description="The CoPilot alert ID to investigate")
    customer_code: str = Field(..., max_length=64, description="Customer code for the alert")
    sender: str = Field(default="copilot", description="The sender identifier")


class TalonInvestigateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class TalonStatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class TalonJobResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class TalonTemplate(BaseModel):
    filename: str = Field(..., description="Template filename, e.g. sysmon_event_1.txt")
    size_bytes: int = Field(..., description="File size in bytes")
    modified_at: str = Field(..., description="Last modification ISO timestamp")
    first_line: Optional[str] = Field(None, description="First non-empty line (preview, ≤200 chars)")


class TalonTemplatesResponse(BaseModel):
    success: bool
    message: str
    templates: List[TalonTemplate] = Field(default_factory=list)
