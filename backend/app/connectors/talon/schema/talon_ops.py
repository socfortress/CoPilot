"""Shapes of the Talon Ops tab (``/api/talon/ops/...``): talon-analyst's ops findings, jobs and runs
(talon-analyst SPEC §5.7, FR-API-22 to -30, D96), copied field by field by ``services/talon_ops.py``.

Every string is bounded and cleaned there; an unknown field never reaches the browser. ``why`` and
``recommendation`` are a model's explanation: untrusted plain text, never Markdown or HTML.
"""
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict

OpsSeverity = Literal["info", "low", "medium", "high"]
OpsStatus = Literal["open", "acknowledged", "muted", "resolved"]


class TalonOpsArtifact(BaseModel):
    """A recommendation artifact talon-analyst built in code from a template (a command, an XML
    snippet). None in phase 1. Shown in a code block, never run."""

    type: str
    body: str


class TalonOpsFinding(BaseModel):
    id: int
    fingerprint: Optional[str] = None
    job: str
    job_version: Optional[int] = None
    #: None: a platform finding (only for a caller who may see every customer).
    customer_code: Optional[str] = None
    kind: str
    severity: OpsSeverity
    title: str
    #: Numbers, ids and times the job measured (code's, never log text); None when it was too large.
    evidence: Optional[Dict[str, Any]] = None
    evidence_truncated: bool = False
    artifact: Optional[TalonOpsArtifact] = None
    #: A model's explanation: plain text.
    why: Optional[str] = None
    #: A model's recommendation, or the job's own hint when there is no explanation: plain text.
    recommendation: Optional[str] = None
    priority: Optional[int] = None
    explained: Optional[bool] = None
    status: OpsStatus
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_reason: Optional[str] = None
    stale_since: Optional[datetime] = None
    muted_until: Optional[datetime] = None
    acted_by: Optional[str] = None
    acted_at: Optional[datetime] = None
    notified_at: Optional[datetime] = None
    #: Rises each time talon-analyst clears ``notified_at`` (new or reopened, a severity rise, an
    #: expired mute; its migration 0024). None from a talon-analyst before it.
    notify_epoch: Optional[int] = None
    updated_at: Optional[datetime] = None


class TalonOpsFindingPage(BaseModel):
    success: bool = True
    message: str = "Ops findings retrieved"
    items: List[TalonOpsFinding]
    next_cursor: Optional[str] = None
    #: Items talon-analyst sent that CoPilot didn't show: not one of the caller's customers, or not
    #: in the shape the contract promises. Logged; never expected.
    dropped: int = 0


class TalonOpsFindingResponse(BaseModel):
    success: bool = True
    message: str = "Ops finding retrieved"
    finding: TalonOpsFinding


class TalonOpsRun(BaseModel):
    id: str
    job: str
    job_version: Optional[int] = None
    customer_code: Optional[str] = None
    tick: Optional[datetime] = None
    triggered_by: Optional[str] = None
    status: str
    collected: Optional[bool] = None
    explained: Optional[str] = None
    candidates: Optional[int] = None
    new: Optional[int] = None
    updated: Optional[int] = None
    resolved: Optional[int] = None
    error: Optional[str] = None
    #: A decimal string, shown as it came.
    cost_usd: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    #: The run's own record (``store.run_json``'s ``detail``), a bounded copy cleaned as the evidence is;
    #: on ``/runs`` only (the jobs list leaves it out), None when Talon sent none or it was too large.
    detail: Optional[Dict[str, Any]] = None


class TalonOpsJob(BaseModel):
    name: str
    title: Optional[str] = None
    version: Optional[int] = None
    scope: Optional[Literal["platform", "customer"]] = None
    enabled: bool
    schedule: Optional[str] = None
    schedule_status: Optional[str] = None
    last_fired_at: Optional[datetime] = None
    needs: List[str] = []
    #: The job's thresholds (numbers and short labels only).
    settings: Dict[str, Any] = {}
    last_run: Optional[TalonOpsRun] = None
    last_runs: List[TalonOpsRun] = []
    next_run: Optional[datetime] = None


class TalonOpsJobs(BaseModel):
    success: bool = True
    message: str = "Ops jobs retrieved"
    items: List[TalonOpsJob]
    #: False: no job is enabled in talon-analyst (``TALON_OPS_JOBS`` is empty).
    any_enabled: bool


class TalonOpsRuns(BaseModel):
    success: bool = True
    message: str = "Ops runs retrieved"
    items: List[TalonOpsRun]
    dropped: int = 0


class TalonOpsRunNow(BaseModel):
    success: bool = True
    message: str = "The job was queued"
    job: str
    workflow_id: Optional[str] = None
    status: str


class TalonOpsCounts(BaseModel):
    """Open findings by severity, and how many of them a job couldn't measure lately (``stale``)."""

    total: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    stale: int = 0


class TalonOpsJobCounts(TalonOpsCounts):
    job: str


class TalonOpsCustomerCounts(TalonOpsCounts):
    #: None: platform findings (only for a caller who may see every customer).
    customer_code: Optional[str] = None


class TalonOpsSummary(BaseModel):
    """Open finding counts (talon-analyst ``GET /v2/ops/summary``), as ``services/talon_ops.py`` checked them.

    When CoPilot dropped a ``by_customer`` row (not one of the caller's customers, or malformed), or the
    rows didn't add up to the totals, ``open`` is recomputed from the rows kept, and ``by_job``,
    ``acknowledged`` and ``muted`` (which can't be split by customer) are withheld: empty and None."""

    success: bool = True
    message: str = "Ops summary retrieved"
    open: TalonOpsCounts
    acknowledged: Optional[int] = None
    muted: Optional[int] = None
    by_job: List[TalonOpsJobCounts] = []
    by_customer: List[TalonOpsCustomerCounts] = []
    #: ``by_customer`` rows talon-analyst sent that CoPilot didn't show. Logged; never expected.
    dropped: int = 0
    #: True when the counts were recomputed and the per-job, acknowledged and muted counts withheld.
    withheld: bool = False
    #: True when, at talon-analyst's 50-row cap, the rows didn't add up to its totals for a caller
    #: without every customer: the counts are the top 50 customers' only, a lower bound.
    partial: bool = False


class TalonOpsMuteRequest(BaseModel):
    """``until`` only: the actor is the signed-in user, never a field of the body."""

    model_config = ConfigDict(extra="forbid")

    until: datetime


class TalonOpsActionRequest(BaseModel):
    """Acknowledge and reopen take no body fields at all (the actor is the signed-in user)."""

    model_config = ConfigDict(extra="forbid")
