"""The "Talon v2" setting (talon-analyst SPEC §5.3, D54; plan M5-5a, decision a), the mirror of
talon-analyst's action proposals (``talon_action_request``, plan M5-11a), and CoPilot's own record of
every alert it sends to Talon (``talon_investigation_trigger``, talon-analyst plan AP-2a), and the
per-customer automation policy with its start records (``talon_automation_policy``,
``talon_automation_start``, talon-analyst plan AP-2).

One row per Talon connector, keyed by the connector's name, so a second connector (the pilot's
"Talon Next", D53) gets a row of its own. A missing row reads as off: every declared v2 proxy route answers 404
and CoPilot's Talon UI and proxy stay exactly as they are without it.

A typed table rather than ``connectors.connector_extra_data`` (free text) or a new ``connectors``
column (that table is cached in-process, ``app/connectors/cache.py``). Read and written only
through ``app/connectors/talon/services/talon_v2.py``.
"""
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Index
from sqlalchemy import Text
from sqlalchemy import false
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
    # held to the gate whatever this says; ``talon_service_account``). ``collect_allowed_artifacts``: the auto-run artifacts that
    # user may start, a JSON list of names from ``talon_catalogue.TALON_AUTO_RUN``; unset (null) means
    # none, so the service account starts nothing until an admin sets it.
    collect_service_username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    # The id of the one user with that name (or ``talon-analyst``) when an admin last saved the
    # setting: held to the gate too, so a rename doesn't take the account out of it.
    collect_service_user_id: Optional[int] = Field(default=None, nullable=True)
    collect_allowed_artifacts: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    # ``{artifact: {definition name: SHA-256}}`` for each allowed artifact and its dependencies, read
    # from Velociraptor when an admin saved the allowlist: a start whose definitions differ is refused
    # until an admin reviews them and saves again (``collection_policy.definition_hashes``).
    collect_definition_hashes: Optional[Dict[str, Dict[str, str]]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    # The global automation kill switch (talon-analyst plan AP-2, SPEC D85): off, every automated
    # start and dry run by the Talon service account is refused, whatever the per-customer
    # ``talon_automation_policy`` rows say (``services/talon_automation.py``). Off by default.
    automation_enabled: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default=false()))
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


# ── what CoPilot sent to Talon (talon-analyst plan AP-2a; SPEC D85 (l), D86 (j)) ──────────────────

#: Who sent an alert to Talon, set by the calling code path (never parsed from ``sender``):
#: CoPilot's alert pipeline, an analyst's "Investigate with AI Analyst", the customer portal
#: (#1215), or a report replay. Only the first two may lead to an automated endpoint action.
TRIGGER_SOURCES = ("pipeline", "analyst", "portal", "replay")
#: The sources an automated collection may be bound to; a portal request or a replay never is.
AUTOMATION_SOURCES = frozenset({"pipeline", "analyst"})


class TalonInvestigationTrigger(SQLModel, table=True):
    """One row per ``POST /investigate`` CoPilot sends to Talon, written by CoPilot itself before the
    call (``services/talon_triggers.py``). It is what binds the Talon service account's automated
    collections to an alert (``/api/artifacts/collect/start``): never ``ai_analyst_job`` or its
    ``triggered_by``, which talon-analyst writes. ``customer_code`` is the alert's, not a foreign key
    (the record outlives the customer, like ``audit_log``)."""

    __tablename__ = "talon_investigation_trigger"
    #: The newest row for an alert is ``ORDER BY id DESC`` on this index (InnoDB appends the key).
    __table_args__ = (Index("ix_talon_investigation_trigger_alert_id", "alert_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(nullable=False)
    customer_code: str = Field(max_length=64, nullable=False)
    #: One of ``TRIGGER_SOURCES``; ``replay`` marks a replay.
    source: str = Field(max_length=16, nullable=False)
    #: The CoPilot user who asked (an analyst, a portal user, whoever replayed); null for the pipeline.
    user_id: Optional[int] = Field(default=None, nullable=True)
    username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    #: The alert's assets when it was sent, ``[{"asset_name", "velociraptor_id"}]``: the only hosts an
    #: automated collection bound to this record may target (an asset added later, by anyone, isn't).
    assets: List[Dict[str, Optional[str]]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    #: Naive UTC, as the ``DATETIME`` columns hold.
    sent_at: datetime = Field(nullable=False)


class TalonAutomationAlertCap(SQLModel, table=True):
    """The per-alert cap on the Talon service account's bound collections (talon-analyst plan AP-2a;
    ``services/talon_triggers.py:reserve``): one row per alert, its window and the starts in it.
    A start takes a slot with one guarded ``UPDATE`` (only while ``starts`` is under the cap, or the
    window has passed), committed before the flow starts; no slot, no start. Never the audit log,
    whose writes are best-effort. AP-2's ``talon_automation_start`` keeps the per-start detail."""

    __tablename__ = "talon_automation_alert_cap"

    alert_id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": False})
    customer_code: str = Field(max_length=64, nullable=False)
    #: Before ``window_started_at`` in the table, so MySQL's left-to-right ``SET`` reads the old window.
    starts: int = Field(default=0, nullable=False)
    #: Naive UTC: the first start of the current window.
    window_started_at: datetime = Field(nullable=False)


# ── the per-customer automation policy (talon-analyst plan AP-2; SPEC D85, D86, INV-ACT-1) ────────

#: A level's mode, from the strictest. ``shadow`` is "would-have-run" (D86 g: "automation shadow" in
#: code, never write-back shadow): recorded through the dry-run route, nothing runs. ``propose``: a
#: card a D47 approver decides (talon-analyst AP-5). Only ``auto`` starts anything.
AUTOMATION_MODES = ("off", "shadow", "propose", "auto")
#: The levels (D85): 1 auto-run catalogue collections, 2 admin-chosen collections and files,
#: 3 read-only commands, 4 free-form commands. Level 0 is every level ``off``.
AUTOMATION_LEVELS = (1, 2, 3, 4)


class TalonAutomationPolicy(SQLModel, table=True):
    """One customer's automation policy (``services/talon_automation.py``): what talon-analyst's
    automatic investigations may run on the customer's endpoints, level by level. Set by one admin
    (``PUT /api/talon/v2/automation/{customer_code}``), enforced by CoPilot on every automated start
    as the Talon service account. **No row means every level off** (fail closed). ``customer_code``
    is not a foreign key: the policy row is the record of what was allowed, as ``audit_log`` is."""

    __tablename__ = "talon_automation_policy"

    customer_code: str = Field(primary_key=True, max_length=64)
    level_1_mode: str = Field(default="off", max_length=16, nullable=False)
    level_2_mode: str = Field(default="off", max_length=16, nullable=False)
    level_3_mode: str = Field(default="off", max_length=16, nullable=False)
    level_4_mode: str = Field(default="off", max_length=16, nullable=False)
    #: Level 2's admin-chosen artifacts (names from ``talon_catalogue.TALON_CATALOGUE``), stored for
    #: AP-6, which adds their definition pins and starts them; nothing reads them for a start yet.
    level_2_artifacts: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    #: Level 2's file allow globs per OS (``{"windows": [...], "linux": [...]}``), stored for AP-6.
    file_allow_globs: Optional[Dict[str, List[str]]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    #: Cap overrides by name (``talon_automation.CAP_DEFAULTS``), each at most its default.
    caps: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    #: The admin who last acknowledged the honest-risk text to raise level 3 or 4 (Q7: one admin).
    risk_acknowledged_by_user_id: Optional[int] = Field(default=None, nullable=True)
    risk_acknowledged_by_username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    risk_acknowledged_at: Optional[datetime] = Field(default=None, nullable=True)
    #: The optional "reviewed" mark per level on the would-have-run list (AP-4; a review aid, never a
    #: gate): ``{"1": {"user_id", "username", "at"}}``. Nothing writes it yet.
    shadow_reviewed: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    #: Starts at 1 and grows with every change: the audit's and talon-analyst's record of which
    #: policy a run read.
    version: int = Field(default=1, nullable=False)
    updated_by_user_id: Optional[int] = Field(default=None, nullable=True)
    updated_by_username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)

    def mode(self, level: int) -> str:
        value = getattr(self, f"level_{level}_mode", None)
        return value if value in AUTOMATION_MODES else "off"


#: ``talon_automation_start.verdict``: an ``auto`` start is ``reserved`` (its caps' slots taken and
#: committed before the flow starts), then ``started`` (with its flow id), ``failed`` (refused after
#: the reservation, nothing started) or ``unknown`` (it may have started; no usable flow id). A dry
#: run (``mode = shadow``) is ``would_start`` or ``refused``.
START_VERDICTS = ("reserved", "started", "failed", "unknown", "would_start", "refused")


class TalonAutomationStart(SQLModel, table=True):
    """One row per automated start the Talon service account was given a slot for, and per dry run
    (talon-analyst plan AP-2; ``services/talon_automation.py``). The caps count these rows (never the
    audit log, whose writes are best-effort); the dry-run rows (``mode = shadow``) are the
    would-have-run list and don't count against the ``auto`` caps. Never row contents, never a
    command's text (its SHA-256 and length, from AP-7)."""

    __tablename__ = "talon_automation_start"
    __table_args__ = (
        Index("ix_talon_automation_start_customer_created", "customer_code", "created_at"),
        Index("ix_talon_automation_start_client_created", "velociraptor_id", "created_at"),
        Index("ix_talon_automation_start_alert_created", "alert_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(max_length=64, nullable=False)
    alert_id: int = Field(nullable=False)
    hostname: str = Field(max_length=256, nullable=False)
    #: The host's canonical Velociraptor client id.
    velociraptor_id: str = Field(max_length=64, nullable=False)
    #: CoPilot's own classification of the request (D86 d); null when it isn't one of a level's.
    level: Optional[int] = Field(default=None, nullable=True)
    #: ``auto`` (a start) or ``shadow`` (a dry run).
    mode: str = Field(max_length=16, nullable=False)
    artifact: Optional[str] = Field(default=None, max_length=256, nullable=True)
    #: The request's parameters as validated, ``[[key, value], ...]``.
    parameters: Optional[List[List[str]]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    #: Levels 3-4 (AP-7): the command's SHA-256 and length, never its text.
    command_sha256: Optional[str] = Field(default=None, max_length=64, nullable=True)
    command_length: Optional[int] = Field(default=None, nullable=True)
    #: Level 2 files (AP-6): the bytes collected.
    file_bytes: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    trigger_id: Optional[int] = Field(default=None, nullable=True)
    trigger_source: Optional[str] = Field(default=None, max_length=16, nullable=True)
    trigger_user_id: Optional[int] = Field(default=None, nullable=True)
    trigger_username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    #: talon-analyst's job id as sent: recorded, never trusted.
    job_id: Optional[str] = Field(default=None, max_length=64, nullable=True)
    flow_id: Optional[str] = Field(default=None, max_length=80, nullable=True)
    #: One of ``START_VERDICTS``.
    verdict: str = Field(max_length=16, nullable=False)
    #: Why a dry run was refused, or a start failed (``talon_automation.REFUSAL_CODES``).
    code: Optional[str] = Field(default=None, max_length=32, nullable=True)
    #: The policy row's ``version`` the start or dry run was checked against.
    policy_version: Optional[int] = Field(default=None, nullable=True)
    #: The caller (the Talon service account).
    user_id: Optional[int] = Field(default=None, nullable=True)
    username: Optional[str] = Field(default=None, max_length=256, nullable=True)
    #: Naive UTC, as the ``DATETIME`` columns hold.
    created_at: datetime = Field(nullable=False)
    finished_at: Optional[datetime] = Field(default=None, nullable=True)
