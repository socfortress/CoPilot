"""The "Talon v2" setting (talon-analyst SPEC §5.3, D54; plan M5-5a, decision a), and the mirror of
talon-analyst's action proposals (``talon_action_request``, plan M5-11a).

One row per Talon connector, keyed by the connector's name, so a second connector (the pilot's
"Talon Next", D53) gets a row of its own. A missing row reads as off: every declared v2 proxy route answers 404
and CoPilot's Talon UI and proxy stay exactly as they are without it.

A typed table rather than ``connectors.connector_extra_data`` (free text) or a new ``connectors``
column (that table is cached in-process, ``app/connectors/cache.py``). Read and written only
through ``app/connectors/talon/services/talon_v2.py``.
"""
from datetime import datetime
from typing import List
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import Column
from sqlalchemy import Text
from sqlmodel import Field
from sqlmodel import SQLModel

from app.time_utils import now_utc


class TalonConnectorSettings(SQLModel, table=True):
    __tablename__ = "talon_connector_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    # ``connectors.connector_name`` (not an FK: that column isn't unique).
    connector_name: str = Field(max_length=256, unique=True, index=True, nullable=False)
    # Off by default: the v2 chat proxy exists only once an admin turns it on.
    v2_enabled: bool = Field(default=False, nullable=False)
    # The collection start route's second gate for talon-analyst's service account (talon-analyst
    # EA-4b, D77; ``services/talon_collections.py``). ``collect_service_username``: the CoPilot user
    # talon-analyst logs in as (unset: ``talon-analyst``, the name CoPilot's docs give it; that name is
    # held to the gate whatever this says). ``collect_allowed_artifacts``: the auto-run artifacts that
    # user may start, a JSON list of names from ``talon_catalogue.TALON_AUTO_RUN``; unset (null) means
    # none, so the service account starts nothing until an admin sets it.
    collect_service_username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    collect_allowed_artifacts: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    updated_by_user_id: Optional[int] = Field(default=None, nullable=True)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)


# ── action proposals (talon-analyst SPEC §5.3 M5-11, §8 "v2 API" Actions, §9.5, D46, D47) ─────────

#: CoPilot's own state of a mirrored proposal. Only ``pending`` may be decided; the approve request
#: moves it through ``claiming`` → ``claimed`` → ``executing`` → ``executed`` | ``failed`` with
#: guarded updates, so one proposal runs at most once (INV-ACT-1).
ACTION_STATES = (
    "pending",  # mirrored, nobody has decided it here
    "claiming",  # an approve or deny is posting its claim to talon-analyst
    "claimed",  # talon-analyst answered ``claimed: true``: this request may run it once
    "executing",  # the route handler is running
    "executed",  # it ran
    "failed",  # it was claimed but did not run, or ran and failed
    "denied",  # denied (here, or as talon-analyst's record says)
    "expired",  # nobody decided it before ``expires_at``
    "withdrawn",  # the requester withdrew it, or the thread was archived
    "refused",  # talon-analyst refused the claim, or its record no longer matches the mirror
    "claim_lost",  # the claim's answer never came: never run, ``failed`` is posted (decision f)
    "unreported",  # the result could not be posted within 24 h of the approval
)
#: States after which nothing about the proposal changes here.
FINAL_ACTION_STATES = frozenset({"executed", "failed", "denied", "expired", "withdrawn", "refused", "unreported"})


class TalonActionRequest(SQLModel, table=True):
    """CoPilot's mirror of one talon-analyst action proposal (plan M5-11a).

    Filled only from talon-analyst's ``GET /v2/actions/{id}``, read with a CoPilot user's own
    identity headers (``services/talon_action_sync.py``), never from the chat stream or the model's
    text. ``customer_code`` is the record's, not a foreign key: like ``audit_log``, this is the
    INV-ACT-1 record of who approved what, and it outlives the customer. ``reason``, ``args`` and a
    comment are stored exactly as talon-analyst sent them and are never interpreted as markup here.
    """

    __tablename__ = "talon_action_request"

    #: talon-analyst's ``action_request`` id (the stream card's ``approvalId``), a UUID.
    id: str = Field(primary_key=True, max_length=36)
    thread_id: str = Field(max_length=36, index=True)
    tool_call_id: str = Field(max_length=255)
    customer_code: str = Field(max_length=64, index=True)
    #: talon-analyst's ``user_id``: ``str(user.id)`` of the CoPilot user who chatted (X-Talon-User).
    requester_user_id: str = Field(max_length=64, index=True)

    # The proposal, as talon-analyst's GET returned it.
    action: str = Field(max_length=64)
    side_effect: str = Field(max_length=32)
    executes_through: Optional[str] = Field(default=None, max_length=128)
    target: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    args: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    #: The model's reason: untrusted plain text, shown as such.
    reason: str = Field(default="", sa_column=Column(Text, nullable=False))
    links: bool = Field(default=False, nullable=False)
    provenance: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    # talon-analyst's view, refreshed by every sync.
    talon_status: str = Field(max_length=16)
    talon_decided_by: Optional[str] = Field(default=None, max_length=64)
    talon_decided_at: Optional[datetime] = Field(default=None)
    talon_reported_at: Optional[datetime] = Field(default=None)
    talon_created_at: Optional[datetime] = Field(default=None)
    expires_at: datetime = Field(nullable=False)
    result_due_by: Optional[datetime] = Field(default=None)

    # CoPilot's own decision and execution.
    state: str = Field(default="pending", max_length=16, index=True)
    decision: Optional[str] = Field(default=None, max_length=16)  # "approve" or "deny"
    approver_user_id: Optional[int] = Field(default=None, index=True)
    approver_username: Optional[str] = Field(default=None, max_length=256)
    decided_at: Optional[datetime] = Field(default=None)
    #: CoPilot's reference for its claim (``POST /v2/actions/{id}/outcome``), unique.
    copilot_ref: Optional[str] = Field(default=None, max_length=255, unique=True)
    #: Why the state is what it is, in CoPilot's or talon-analyst's fixed words.
    state_reason: Optional[str] = Field(default=None, max_length=255)
    #: ``{success, message, status_code}``: what CoPilot posts as the result.
    execution_result: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    executed_at: Optional[datetime] = Field(default=None)

    # Posting the result (``executed`` or ``failed``) to talon-analyst.
    outcome_posted_at: Optional[datetime] = Field(default=None)
    outcome_attempts: int = Field(default=0, nullable=False)
    next_attempt_at: Optional[datetime] = Field(default=None, index=True)
    last_outcome_error: Optional[str] = Field(default=None, max_length=255)

    #: When ``state`` last changed (only state changes set it, never a sync): what the job's
    #: "left by a dead request" check reads.
    state_changed_at: datetime = Field(default_factory=now_utc, nullable=False, index=True)
    synced_at: datetime = Field(default_factory=now_utc, nullable=False)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)
