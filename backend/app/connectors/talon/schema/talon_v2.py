"""Request and response shapes of CoPilot's Talon v2 routes (plan M5-5a).

The thread and chat bodies take only what CoPilot forwards: no ``user_id``, no scope and no
identity of any kind (``extra="forbid"``). The thread routes' answers are talon-analyst's, passed
through, so they have no response model here.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

#: talon-analyst's limit on the newest message's text (``vercel.MAX_MESSAGE_CHARS``).
MAX_MESSAGE_CHARS = 200_000
#: A thread title as talon-analyst stores it (it checks the characters itself).
MAX_TITLE_CHARS = 200


class TalonV2AvailabilityResponse(BaseModel):
    success: bool
    message: str
    enabled: bool = Field(..., description="Whether the Talon v2 chat (threads and the v2 stream) is turned on")


class TalonV2SettingsResponse(BaseModel):
    success: bool
    message: str
    connector_name: str
    v2_enabled: bool
    updated_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class TalonV2SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v2_enabled: bool


class TalonV2ThreadCreate(BaseModel):
    """``POST /talon/v2/threads``. No customer means a general thread, with no customer data (D39)."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, max_length=MAX_TITLE_CHARS)
    customer_code: Optional[str] = Field(default=None, max_length=64)


class TalonV2ThreadRename(BaseModel):
    """``PATCH /talon/v2/threads/{id}``. ``title: null`` clears the title."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(..., max_length=MAX_TITLE_CHARS)


class TalonV2ChatRequest(BaseModel):
    """``POST /talon/v2/chat/{thread_id}``: one user message. CoPilot builds the AI SDK's
    ``SubmitMessage`` from it; the browser never sends one. An empty message is allowed: it is how
    a thread resumes after an action's outcome (M5-11)."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., max_length=MAX_MESSAGE_CHARS)
    message_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]{1,128}$")
