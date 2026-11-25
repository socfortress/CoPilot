"""Shapes of the weekly Sysmon noise statistics (app/active_response/services/sysmon_stats/)."""
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class SharingMode(str, Enum):
    """SYSMON_STATS_SHARING: "on" sends each customer's weekly report (unless the customer is opted out), "off" sends nothing."""

    ON = "on"
    OFF = "off"


class StatsOutcome(str, Enum):
    """What a report attempt, a customer's week or a tick ended with. Recorded in stats-state.json and shown on the
    Sysmon Config page."""

    # Terminal for a (week, customer): the week is not sent again
    SENT = "sent"
    WITHDRAWN = "withdrawn"
    REFUSED = "refused"
    LOCAL_REFUSED = "local_refused"
    REFUSED_BAD_REQUEST = "refused_bad_request"
    REFUSED_CONTENT_TYPE = "refused_content_type"
    TOO_LARGE = "too_large"
    WEEK_NOT_ACCEPTED = "week_not_accepted"
    WEEK_BEFORE_FIRST_SEEN = "week_before_first_seen"
    CUSTOMER_LIMIT = "customer_limit"
    STORAGE_QUOTA = "storage_quota"
    WAF_REFUSED = "waf_refused"
    NO_SYSMON_EVENTS = "no_sysmon_events"
    AMBIGUOUS_LABEL = "ambiguous_label"
    # Pending: tried again on a later tick
    UNAUTHORIZED = "unauthorized"
    LICENSE_REJECTED = "license_rejected"
    LICENSE_BLOCKED = "license_blocked"
    SERVICE_NOT_ACCEPTING = "service_not_accepting"
    HTTP_ERROR = "http_error"
    REDIRECT_REFUSED = "redirect_refused"
    BODY_TIMEOUT = "body_timeout"
    BUSY = "busy"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    STORAGE_FULL = "storage_full"
    NETWORK_ERROR = "network_error"
    INDEXER_ERROR = "indexer_error"
    INDEXER_TIMEOUT = "indexer_timeout"
    STORE_ERROR = "store_error"
    ERROR = "error"
    # A tick as a whole
    SHARING_OFF = "sharing_off"
    NOTHING_DUE = "nothing_due"
    LATCHED = "latched"
    NO_LICENSE = "no_license"
    INVALID_URL = "invalid_url"
    INDEXER_FIELDS_UNAVAILABLE = "indexer_fields_unavailable"
    INDEXER_UNREACHABLE = "indexer_unreachable"
    LOCKED = "locked"
    RUNNING = "running"
    COMPLETED = "completed"


TERMINAL_OUTCOMES = frozenset(
    {
        StatsOutcome.SENT,
        StatsOutcome.WITHDRAWN,
        StatsOutcome.REFUSED,
        StatsOutcome.LOCAL_REFUSED,
        StatsOutcome.REFUSED_BAD_REQUEST,
        StatsOutcome.REFUSED_CONTENT_TYPE,
        StatsOutcome.TOO_LARGE,
        StatsOutcome.WEEK_NOT_ACCEPTED,
        StatsOutcome.WEEK_BEFORE_FIRST_SEEN,
        StatsOutcome.CUSTOMER_LIMIT,
        StatsOutcome.STORAGE_QUOTA,
        StatsOutcome.WAF_REFUSED,
        StatsOutcome.NO_SYSMON_EVENTS,
        StatsOutcome.AMBIGUOUS_LABEL,
    },
)


class StatsWeekState(BaseModel):
    """One customer's report of one ISO week, as stats-state.json keeps it: counts and hashes, never a value."""

    status: str = Field("pending", description='"terminal" (the week is done for this customer) or "pending".')
    outcome: StatsOutcome
    message: Optional[str] = None
    attempts: int = 0
    last_attempt_at: Optional[str] = None
    not_before: Optional[str] = None
    http_status: Optional[int] = None
    reason: Optional[str] = None
    sent_at: Optional[str] = None
    payload_sha256: Optional[str] = None
    payload_bytes: Optional[int] = None
    patterns: Optional[int] = None
    truncated: Optional[bool] = None
    endpoints: Optional[int] = None
    config: Optional[Union[int, str]] = None
    accepted: Optional[int] = None
    rejected: Optional[int] = None
    rejected_by_reason: Dict[str, int] = Field(default_factory=dict)
    replaced: Optional[bool] = None
    local_drops: Dict[str, int] = Field(default_factory=dict)


class StatsServiceState(BaseModel):
    accepting: Optional[bool] = Field(None, description="Whether SOCFortress accepts reports (None: not known yet).")
    checked_at: Optional[str] = None
    last_status: Optional[int] = None
    not_before: Optional[str] = Field(None, description="No report or withdraw is sent before this time (Retry-After).")


class StatsLastTick(BaseModel):
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    outcome: Optional[StatsOutcome] = None
    message: Optional[str] = None
    sent: int = 0
    pending: int = 0
    terminal: int = 0
    week: Optional[str] = None


class StatsLatch(BaseModel):
    """Reports are paused: SOCFortress refused one for its content. Lifted by a CoPilot version change or an admin."""

    set_at: str
    reason: str
    copilot_version: str


class StatsRelease(BaseModel):
    content_sha256: str
    content_sha256_crlf: Optional[str] = None


class StatsState(BaseModel):
    """stats-state.json. Written only under the named lock; never holds a value, a payload or the license key."""

    schema_version: int = Field(1, alias="schema")
    service: StatsServiceState = Field(default_factory=StatsServiceState)
    last_tick: Optional[StatsLastTick] = None
    latch: Optional[StatsLatch] = None
    releases: Dict[str, StatsRelease] = Field(default_factory=dict)
    weeks: Dict[str, Dict[str, StatsWeekState]] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class StatsWithdrawRequest(BaseModel):
    """stats-withdraw/<pseudonym>.json: a withdraw still to be sent. Deleted once SOCFortress confirms it."""

    customer: str
    customer_code: Optional[str] = None
    requested_at: str
    attempts: int = 0
    last_status: Optional[int] = None
    not_before: Optional[str] = None


class StatsWithdrawStatus(BaseModel):
    queued: bool = False
    requested_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    last_status: Optional[int] = None


class StatsCustomerStatus(BaseModel):
    customer_code: str
    customer_name: Optional[str] = None
    pseudonym: Optional[str] = Field(None, description="The customer's id in this CoPilot's reports (cust_ + 32 hex).")
    sharing: bool = True
    install_dir_name: Optional[str] = None
    own_domains: List[str] = Field(default_factory=list)
    withdraw: StatsWithdrawStatus = Field(default_factory=StatsWithdrawStatus)
    due_at: Optional[str] = Field(None, description="When this CoPilot sends the target week's report (UTC).")
    target_week_state: Optional[StatsWeekState] = None
    last_sent_week: Optional[str] = None
    last_sent_state: Optional[StatsWeekState] = None


class StatsStatus(BaseModel):
    mode: SharingMode
    mode_setting: Optional[str] = Field(None, description="SYSMON_STATS_SHARING as set, when CoPilot does not know it (then: off).")
    service_url: str
    service: StatsServiceState = Field(default_factory=StatsServiceState)
    last_tick: Optional[StatsLastTick] = None
    latch: Optional[StatsLatch] = None
    target_week: str
    max_rule_level: int
    min_endpoints: int
    customers: List[StatsCustomerStatus] = Field(default_factory=list)
    read_error: Optional[str] = None


class StatsStatusResponse(BaseModel):
    success: bool
    message: str
    status: StatsStatus


class StatsSharingRequest(BaseModel):
    sharing: bool
    install_dir_name: Optional[str] = Field(
        None,
        description="The customer's installer InstallDirName, when it is not its code. null clears it.",
    )
    own_domains: Optional[List[str]] = Field(None, description="The customer's own DNS domains (at most 20). null or [] clears them.")


class StatsWithdrawResult(BaseModel):
    outcome: str = Field(..., description='"withdrawn", "queued" or "failed".')
    reports_deleted: Optional[int] = None
    message: Optional[str] = None


class StatsSharingResponse(BaseModel):
    success: bool
    message: str
    customer: StatsCustomerStatus
    withdraw: Optional[StatsWithdrawResult] = None


class StatsWouldSend(BaseModel):
    ok: bool
    why: Optional[str] = None


class StatsPreviewLocal(BaseModel):
    raw_patterns: int = 0
    sent: int = 0
    dropped_by_reason: Dict[str, int] = Field(default_factory=dict)
    merged: int = 0
    truncated: bool = False


class StatsPreview(BaseModel):
    week: str
    customer_pseudonym: str
    would_send: StatsWouldSend
    payload: Optional[Dict[str, Any]] = Field(None, description="The exact report whose compact UTF-8 JSON would be sent.")
    payload_sha256: Optional[str] = None
    payload_bytes: Optional[int] = None
    local: StatsPreviewLocal = Field(default_factory=StatsPreviewLocal)
    outcome: Optional[StatsOutcome] = Field(
        None,
        description="Set when no report could be built (no Sysmon events, an indexer error, ...).",
    )
    message: Optional[str] = None
    ms: int = 0


class StatsPreviewResponse(BaseModel):
    success: bool
    message: str
    preview: StatsPreview


class StatsCustomerRun(BaseModel):
    customer_code: str
    outcome: StatsOutcome
    message: Optional[str] = None


class StatsRunResult(BaseModel):
    outcome: StatsOutcome
    message: str
    week: Optional[str] = None
    customers: List[StatsCustomerRun] = Field(default_factory=list)


class StatsRunResponse(BaseModel):
    success: bool
    message: str
    result: StatsRunResult
    status: StatsStatus
