"""Shapes of the Talon v2 action routes (plan M5-11a; talon-analyst SPEC §8 "v2 API" Actions).

``TalonActionBody`` is what talon-analyst's ``GET /v2/actions/{id}`` (and its outcome answer)
returns; it is the only source of the mirror. ``reason``, ``args`` (a comment included) and
``target`` are kept as talon-analyst sent them: plain data, never markup.

``ActionOut`` is what CoPilot's own routes answer: the mirror row, plus ``can_decide`` and
``is_requester`` for the caller.
"""
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictStr

TalonStatus = Literal["pending", "approved", "denied", "expired", "executed", "failed", "withdrawn"]


class TalonActionBody(BaseModel):
    """talon-analyst's ``talon.actions.action_body``. Unknown fields are ignored; a missing or
    mistyped one makes the whole answer unusable (the caller treats it as no answer)."""

    model_config = ConfigDict(extra="ignore")

    id: StrictStr
    thread_id: StrictStr = Field(..., min_length=1, max_length=36)
    tool_call_id: StrictStr = Field(..., min_length=1, max_length=255)
    customer_code: StrictStr = Field(..., min_length=1, max_length=64)
    user_id: StrictStr = Field(..., min_length=1, max_length=64)
    action: StrictStr = Field(..., max_length=64)
    side_effect: Optional[StrictStr] = None
    executes_through: Optional[StrictStr] = Field(default=None, max_length=128)
    target: Dict[str, Any]
    args: Dict[str, Any]
    reason: StrictStr = ""
    links: StrictBool = False
    provenance: Dict[str, Any] = Field(default_factory=dict)
    status: TalonStatus
    decided_by: Optional[StrictStr] = Field(default=None, max_length=64)
    decided_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    reported_at: Optional[datetime] = None
    copilot_ref: Optional[StrictStr] = Field(default=None, max_length=255)
    created_at: Optional[datetime] = None
    expires_at: datetime
    result_due_by: Optional[datetime] = None


class TalonOutcomeAnswer(TalonActionBody):
    """talon-analyst's answer to ``POST /v2/actions/{id}/outcome``: the record, plus ``claimed`` for
    a claim (true only for the request that moved it off ``pending``) or ``recorded`` for a result."""

    claimed: Optional[StrictBool] = None
    recorded: Optional[StrictBool] = None


class ActionOut(BaseModel):
    """One mirrored proposal, as CoPilot's action routes show it."""

    id: str
    thread_id: str
    customer_code: str
    requester_user_id: str
    action: str
    side_effect: str
    executes_through: Optional[str] = None
    target: Dict[str, Any]
    args: Dict[str, Any]
    #: The model's reason, untrusted plain text: show it as text, never render it.
    reason: str
    #: A comment that holds a link: show the text raw, with the links highlighted, not clickable.
    links: bool
    provenance: Dict[str, Any]
    talon_status: str
    state: str
    state_reason: Optional[str] = None
    #: Whether ``expires_at`` has passed while nobody decided it (shown locally, M5-11 "Expiry").
    expired: bool
    expires_at: datetime
    created_at: Optional[datetime] = None
    decision: Optional[str] = None
    approver_user_id: Optional[int] = None
    approver_username: Optional[str] = None
    decided_at: Optional[datetime] = None
    execution_result: Optional[Dict[str, Any]] = None
    executed_at: Optional[datetime] = None
    #: Whether talon-analyst has the result (``executed`` or ``failed``).
    outcome_reported: bool
    can_decide: bool
    is_requester: bool


class ActionResponse(BaseModel):
    success: bool
    message: str
    action: ActionOut


class ActionListResponse(BaseModel):
    success: bool
    message: str
    actions: List[ActionOut]
