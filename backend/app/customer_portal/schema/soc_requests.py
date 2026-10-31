"""'Ask the SOC' from the Customer Portal (#1305): a portal user's question about an alert or a case.

The portal sees its own questions (who asked, when, how urgently, whether the SOC answered),
never who answered: the SOC is the SOC. CoPilot's analysts see every open question of their
customers, with the asker, so they can answer it.
"""

from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

Urgency = Literal["low", "normal", "high"]
RequestStatus = Literal["open", "answered"]
AlertTarget = Literal["case", "alert"]

QUESTION_MAX = 2000

# Characters a question must not carry: controls other than tab and newline, and the
# formatting ones (bidi overrides, zero-width) that would make the SOC read something else.
_FORBIDDEN = {chr(c) for c in range(0x00, 0x20) if chr(c) not in "\t\n"} | {"\x7f"}
_FORMAT = set("​‌‍‎‏‪‫‬‭‮⁦⁧⁨⁩﻿؜")


def clean_question(value: str) -> str:
    """The question as typed, trimmed; refused when empty, too long or carrying hidden characters."""
    text = (value or "").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("Write your question for the SOC")
    if len(text) > QUESTION_MAX:
        raise ValueError(f"Keep the question under {QUESTION_MAX} characters")
    if any(ch in _FORBIDDEN or ch in _FORMAT for ch in text):
        raise ValueError("The question contains characters that cannot be sent")
    return text


class AskOnCaseRequest(BaseModel):
    question: str = Field(..., max_length=QUESTION_MAX * 2)
    urgency: Urgency = "normal"

    @field_validator("question")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_question(value)


class AskOnAlertRequest(AskOnCaseRequest):
    target: AlertTarget = Field(
        "case",
        description="case: on the alert's open case (or a new case from the alert); alert: on the alert itself",
    )


# ── the switch ────────────────────────────────────────────────────────────────


class SocRequestSettings(BaseModel):
    customer_code: str
    enabled: bool
    daily_request_limit: Optional[int] = None
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class SocRequestSettingsResponse(BaseModel):
    settings: SocRequestSettings
    success: bool
    message: str


class UpdateSocRequestSettingsRequest(BaseModel):
    enabled: bool
    daily_request_limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Questions per customer over any 24 hours; null = unlimited",
    )


class SocRequestAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool
    success: bool
    message: str


# ── what the portal sees ──────────────────────────────────────────────────────


class PortalSocRequest(BaseModel):
    id: int
    case_id: Optional[int] = None
    alert_id: Optional[int] = None
    origin_alert_id: Optional[int] = None
    question: str
    urgency: Urgency
    status: RequestStatus
    requested_by: str
    requested_at: str = Field(..., description="ISO 8601, UTC")
    answered_at: Optional[str] = Field(None, description="ISO 8601, UTC")


class PortalSocRequestsResponse(BaseModel):
    requests: List[PortalSocRequest]
    #: For an alert: its open case, where a question filed "on a case" goes.
    open_case_id: Optional[int] = None
    success: bool
    message: str


class AskResponse(BaseModel):
    request: PortalSocRequest
    success: bool
    message: str


# ── what the SOC sees ─────────────────────────────────────────────────────────


class SocRequestOut(PortalSocRequest):
    customer_code: str
    title: Optional[str] = Field(None, description="The case's or the alert's name")
    answered_by: Optional[str] = None
    answered_via: Optional[Literal["comment", "manual"]] = None
    #: Drafted with Talon in the portal chat, then edited and sent by the customer (talon-analyst D97).
    drafted_with_talon: bool = False


class SocRequestsResponse(BaseModel):
    requests: List[SocRequestOut]
    total: int
    open: int
    success: bool
    message: str


class SocRequestResponse(BaseModel):
    request: SocRequestOut
    success: bool
    message: str
