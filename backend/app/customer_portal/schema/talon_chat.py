"""Talon chat in the Customer Portal (talon-analyst SPEC D97, §5.3 "Portal chat: CoPilot's side").

The settings and availability shapes are CoPilot's. The proxy routes' answers are talon-analyst's,
passed through (FR-API-33 to -42), so they have no response model here. Every request body is read
with ``model_validate`` in the routes rather than as a FastAPI body, so a body that doesn't
validate is the contract's ``{"detail": "invalid request", "code": "invalid_request"}``, not
CoPilot's own validation shape. No body carries a user or an identity (``extra="forbid"``).
"""
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictInt

from app.customer_portal.services.talon_chat import LIMIT_MAX
from app.customer_portal.services.talon_chat import LIMIT_MIN
from app.customer_portal.services.talon_chat import PROPOSED_DAILY_MESSAGE_LIMIT
from app.customer_portal.services.talon_chat import PROPOSED_USER_DAILY_MESSAGE_LIMIT

#: A thread title as talon-analyst stores it.
MAX_TITLE_CHARS = 200
#: A message's text as CoPilot forwards it; talon-analyst holds the portal to its own, lower
#: ``TALON_PORTAL_CHAT_MAX_MESSAGE_CHARS`` (``message_too_long``).
MAX_MESSAGE_CHARS = 200_000


# ── the settings (SOC-facing) ─────────────────────────────────────────────────


class PortalChatSettings(BaseModel):
    customer_code: str
    portal_chat_enabled: bool
    log_search_enabled: bool
    daily_message_limit: Optional[int] = None
    user_daily_message_limit: Optional[int] = None
    version: Optional[int] = Field(None, description="Bumped by every write; null before the first")
    updated_at: Optional[str] = None
    updated_by: Optional[int] = None


class ProposedLimits(BaseModel):
    daily_message_limit: int = PROPOSED_DAILY_MESSAGE_LIMIT
    user_daily_message_limit: int = PROPOSED_USER_DAILY_MESSAGE_LIMIT


class PortalChatSettingsResponse(BaseModel):
    settings: PortalChatSettings
    ai_reports_enabled: bool
    proposed: ProposedLimits = ProposedLimits()
    success: bool = True
    message: str = "Portal chat settings retrieved"


class UpdatePortalChatSettingsRequest(BaseModel):
    """``PUT /customer_portal/talon_chat/settings/{customer_code}``. Strict types: a string ``"200"``
    or ``1`` for a switch is an invalid request, not a guess."""

    model_config = ConfigDict(extra="forbid")

    portal_chat_enabled: StrictBool
    log_search_enabled: StrictBool
    daily_message_limit: Optional[StrictInt] = Field(None, description=f"{LIMIT_MIN} to {LIMIT_MAX}; required to turn the chat on")
    user_daily_message_limit: Optional[StrictInt] = Field(None, description="1 to daily_message_limit")


class PortalChatAvailabilityResponse(BaseModel):
    customer_code: Optional[str] = None
    enabled: bool
    log_search: bool
    can_draft: bool
    can_request_analysis: bool
    success: bool = True
    message: str = ""


# ── the portal proxy (portal-facing) ──────────────────────────────────────────


class ThreadCreate(BaseModel):
    """FR-API-34 as the portal sends it. ``language`` is the locale the portal shows (the browser's
    when the user never picked one); CoPilot keeps it only when it is one of the user's available
    portal languages, else uses the user's portal language (``talon_chat_proxy.thread_language``)."""

    model_config = ConfigDict(extra="forbid")

    customer_code: str = Field(..., min_length=1, max_length=64)
    title: Optional[str] = Field(None, max_length=MAX_TITLE_CHARS)
    alert_id: Optional[StrictInt] = Field(None, ge=1, le=2_147_483_647)
    language: Optional[str] = Field(None, max_length=16)


class ThreadRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(..., max_length=MAX_TITLE_CHARS)


class Feedback(BaseModel):
    """FR-API-42."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    rating: Optional[Literal["up", "down"]] = None


class ChatMessage(BaseModel):
    """CoPilot's own chat body, as the SOC's v2 proxy takes it: one message's text."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., max_length=MAX_MESSAGE_CHARS)
    message_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]{1,128}$")


class SubmitMessagePart(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    text: Optional[str] = None


class SubmitMessageItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    role: str
    parts: List[SubmitMessagePart] = Field(default_factory=list, max_length=100)


class SubmitMessage(BaseModel):
    """The AI SDK's ``SubmitMessage`` (FR-API-38's request), for a portal that sends it as is. Only
    the newest message's text parts are read; CoPilot rebuilds the request from them."""

    model_config = ConfigDict(extra="allow")

    trigger: Literal["submit-message"]
    id: Optional[str] = None
    messages: List[SubmitMessageItem] = Field(..., min_length=1)


class DraftSubmit(BaseModel):
    """``POST /customer_portal/talon_chat/drafts/{id}/submit``: the customer's edited question, the
    urgency they picked, and for an alert draft where it is filed (default ``case``). The target and
    the customer are the draft's, read back from talon-analyst, never the body's."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., max_length=4000)
    urgency: Literal["low", "normal", "high"]
    file_on: Optional[Literal["case", "alert"]] = None


class DraftSubmitResponse(BaseModel):
    request_id: int
