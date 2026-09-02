from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class TalonMessageRequest(BaseModel):
    message: str = Field(..., description="The message to send to Talon")
    sender: str = Field(default="copilot", description="The sender identifier")
    # NOTE: the Talon conversation lane (user_id / user_name) is deliberately
    # NOT part of this schema. It is stamped server-side from the JWT, because
    # a caller able to name its own user_id could read or reset a colleague's
    # conversation.


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


class TalonSessionResetResponse(BaseModel):
    success: bool
    message: str
    lanes_cleared: int = Field(default=0, description="Number of Talon conversation lanes cleared")


class TalonSessionContextResponse(BaseModel):
    success: bool
    message: str
    input_tokens: Optional[int] = Field(default=None, description="Size of the caller's Talon conversation, in tokens")
    updated_at: Optional[str] = Field(default=None, description="When that figure was last recorded")


class TalonTemplatesResponse(BaseModel):
    success: bool
    message: str
    templates: List[TalonTemplate] = Field(default_factory=list)
