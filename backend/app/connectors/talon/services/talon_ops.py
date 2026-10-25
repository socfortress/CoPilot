"""The Talon Ops tab (``/api/talon/ops/...``): talon-analyst's ops jobs and their findings (endpoints
gone quiet, log sources gone silent), relayed from its ``/v2/ops`` API (talon-analyst SPEC §5.7,
FR-API-22 to -30, D96; plan OJ-5).

Unlike the Memory tab, talon-analyst holds these requests to the user: every call carries the five
identity headers (``identity.py``), computed from the signed-in user exactly as v2 chat computes them,
and talon-analyst answers only that user's customers. CoPilot checks everything again, and fails
closed:

- **Who.** Admins and analysts by token (a responder's token carries ``analyst``), the roles that see
  the Memory tab, then the "Talon v2" setting (``require_talon_v2``, at the router). Run now is an
  admin's, by ``role_id`` (the database's role, not the token's scope), and talon-analyst checks the
  ``X-Talon-Role`` it is sent as well.
- **Customers.** A customer finding is shown only for a customer in the caller's
  ``X-Talon-Customers``; a **platform finding** (``customer_code`` null) only to a caller allowed every
  customer (``*``, an admin). A list item that breaks this is dropped (counted, logged); a detail or an
  action's answer that breaks it is a 404, the same 404 as an unknown id.
- **The stored customer.** An action first reads the finding as the caller, then sends its stored
  ``customer_code`` to talon-analyst (``?customer_code=``), which refuses the action (404) if the
  finding's stored customer isn't that one; the answer must name it again. A ``customer_code`` the
  browser names must equal the stored one (404 otherwise).
- **The actor** sent with an action is the signed-in user's username, never a field of the request
  (the bodies forbid extra fields). Every action sent to talon-analyst is audited
  (``talon_ops.acknowledge|mute|reopen|run``), its refusals as failures and no answer as unknown;
  a run now refused for a non-admin is audited too.

**Answers** are copied one field at a time into ``schema/talon_ops.py``: strings bounded, the
connector's key and password and URL user-info scrubbed (``make_scrub``), the evidence a bounded JSON
object of scalars, so an unknown field never reaches the browser and a malformed finding is dropped.
``why`` and ``recommendation`` are a model's text: kept as plain text (newlines kept, controls
dropped), never Markdown or HTML, in CoPilot as in talon-analyst. Errors are ``{"detail", "code"}``
with fixed texts (talon-analyst's own one-line reasons for a 400, 403, 409 or 503, cleaned). An
upstream 401 is CoPilot's key and is a 502, never the user's session.

The request's database session is closed before talon-analyst is asked.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.schema.talon_ops import TalonOpsArtifact
from app.connectors.talon.schema.talon_ops import TalonOpsFinding
from app.connectors.talon.schema.talon_ops import TalonOpsFindingPage
from app.connectors.talon.schema.talon_ops import TalonOpsFindingResponse
from app.connectors.talon.schema.talon_ops import TalonOpsJob
from app.connectors.talon.schema.talon_ops import TalonOpsJobs
from app.connectors.talon.schema.talon_ops import TalonOpsRun
from app.connectors.talon.schema.talon_ops import TalonOpsRunNow
from app.connectors.talon.schema.talon_ops import TalonOpsRuns
from app.connectors.talon.services.identity import ALL
from app.connectors.talon.services.identity import CUSTOMERS_HEADER
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.identity import talon_identity_headers
from app.connectors.talon.services.talon_health import make_scrub
from app.connectors.talon.services.talon_memory import make_text_scrub
from app.connectors.talon.utils.universal import refusal_reason
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import v2_request
from app.connectors.utils import get_connector_info_from_db

NO_STORE = {"Cache-Control": "no-store"}

SEVERITIES = ("info", "low", "medium", "high")
STATUSES = ("open", "acknowledged", "muted", "resolved")
#: An ops job's name (talon-analyst ``OpsJob.name``: ``quiet_endpoints``); never more than a path segment.
JOB_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
#: talon-analyst's keyset cursor (``api/ops.py:_cursor``): microseconds, a dot, the id.
CURSOR = re.compile(r"-?\d{1,20}\.\d{1,20}")
FINDING_ID_MAX = 2**63 - 1
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
RUNS_DEFAULT_LIMIT = 50
#: talon-analyst refuses a mute past 90 days (``MUTE_MAX``); CoPilot refuses it first, with its text.
MUTE_MAX = timedelta(days=90)
#: talon-analyst's ``acted_by``: at most 128 printable characters.
ACTOR_MAX = 128

MAX_TITLE = 500
MAX_LABEL = 64
MAX_ID_TEXT = 255
MAX_WHY = 2000
MAX_RECOMMENDATION = 3000
MAX_ARTIFACT_BODY = 20_000
MAX_REASON = 300
#: The evidence object, as compact JSON; larger is dropped (``evidence_truncated``).
MAX_EVIDENCE_BYTES = 32 * 1024
MAX_EVIDENCE_KEYS = 64
MAX_EVIDENCE_LIST = 64
MAX_EVIDENCE_TEXT = 500
MAX_EVIDENCE_DEPTH = 3
MAX_JOBS = 50
MAX_RUNS = 500
MAX_SETTINGS = 50
#: The largest answer read from talon-analyst: a page of 200 findings with their evidence.
MAX_BODY_BYTES = 4 * 1024 * 1024

# ── fixed texts ───────────────────────────────────────────────────────────────

OLD_TALON = "This Talon has no ops API: upgrade talon-analyst, and check that its v2 API (TALON_V2_API) is on"
NOT_FOUND = "There is no such ops finding, or it isn't one of your customers'"
UNKNOWN_JOB = "Talon has no such ops job"
INVALID_CUSTOMER = "customer_code is not a valid customer code"
NOT_ACCESSIBLE = "You don't have access to this customer"
PLATFORM_ONLY = "Platform findings are only for users with access to every customer"
PLATFORM_AND_CUSTOMER = "Ask for platform findings or for one customer's, not both"
INVALID_JOB = "job is not an ops job name"
INVALID_STATUS = "status must be open, acknowledged, muted or resolved"
INVALID_SEVERITY = "severity must be info, low, medium or high"
INVALID_CURSOR = "cursor is not a page cursor CoPilot can send"
INVALID_LIMIT = f"limit must be between 1 and {MAX_LIMIT}"
INVALID_UNTIL = "until must be in the future and at most 90 days away"
ADMIN_ONLY = "Only an admin may run an ops job now"
INVALID_REQUEST = "Talon refused the request as invalid"
KEY_REFUSED = "Talon refused CoPilot's API key"
UNREACHABLE = "Talon could not be reached"
NOT_JSON = "Talon's answer was not valid JSON"
WRONG_SHAPE = "Talon's answer was not in the expected shape"
FAILED = "Talon request failed"
UNAVAILABLE = "Talon's ops jobs are unavailable right now; try again shortly"


def problem(status: int, detail: str, code: str) -> JSONResponse:
    """One of CoPilot's answers that isn't data: ``{"detail", "code"}``, never stored."""
    return JSONResponse({"detail": detail, "code": code}, status_code=status, headers=dict(NO_STORE))


class Refused(Exception):
    """A request CoPilot refuses before talon-analyst is asked; ``response`` is the answer."""

    def __init__(self, response: JSONResponse) -> None:
        super().__init__(response.status_code)
        self.response = response


# ── who is asking ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Caller:
    """The identity sent upstream, and what it lets the caller see (the same headers decide both)."""

    identity: Dict[str, str]
    all_customers: bool
    customers: frozenset

    def sees(self, customer_code: Any) -> bool:
        """Whether a finding or run of ``customer_code`` may be shown: a platform one (None) only to
        a caller allowed every customer, a customer one only for a customer the caller has."""
        if customer_code is None:
            return self.all_customers
        if not isinstance(customer_code, str):
            return False
        return self.all_customers or customer_code in self.customers


def caller_from_identity(identity: Mapping[str, str]) -> Caller:
    raw = identity.get(CUSTOMERS_HEADER, "")
    if raw == ALL:
        return Caller(dict(identity), True, frozenset())
    return Caller(dict(identity), False, frozenset(code for code in raw.split(",") if code))


@dataclass(frozen=True)
class Cleaners:
    scrub: Callable[[Any, int], Optional[str]]
    scrub_text: Callable[[Any, int], Optional[str]]


def cleaners_for(attributes: Optional[Mapping[str, Any]]) -> Cleaners:
    attributes = attributes or {}
    secrets = [str(attributes.get("connector_api_key") or ""), str(attributes.get("connector_password") or "")]
    return Cleaners(scrub=make_scrub(secrets), scrub_text=make_text_scrub(secrets))


async def _caller_then_release(user: User, session: AsyncSession) -> tuple:
    """The caller's identity and the cleaners, then the request's session closed: no pooled
    connection waits on talon-analyst."""
    identity = await talon_identity_headers(user, session)
    attributes = await get_connector_info_from_db(TALON_CONNECTOR, session)
    await session.close()
    return caller_from_identity(identity), cleaners_for(attributes)


# ── checks on what the browser sent ───────────────────────────────────────────


def check_customer_code(code: Optional[str]) -> Optional[str]:
    if code is None or code == "":
        return None
    if not is_talon_customer_code(code):
        raise Refused(problem(400, INVALID_CUSTOMER, "invalid"))
    return code


def check_job(job: Optional[str]) -> Optional[str]:
    if job is None or job == "":
        return None
    if not isinstance(job, str) or not JOB_NAME.fullmatch(job):
        raise Refused(problem(400, INVALID_JOB, "invalid"))
    return job


def _choice(value: Optional[str], allowed, text: str) -> Optional[str]:
    if value is None or value == "":
        return None
    if value not in allowed:
        raise Refused(problem(400, text, "invalid"))
    return value


def _limit(value: Optional[int], default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_LIMIT:
        raise Refused(problem(400, INVALID_LIMIT, "invalid"))
    return value


def _cursor(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if not CURSOR.fullmatch(value):
        raise Refused(problem(400, INVALID_CURSOR, "invalid"))
    return value


def check_finding_id(finding_id: int) -> int:
    if isinstance(finding_id, bool) or not isinstance(finding_id, int) or not 1 <= finding_id <= FINDING_ID_MAX:
        raise Refused(problem(404, NOT_FOUND, "not_found"))
    return finding_id


def check_until(until: datetime, now: Optional[datetime] = None) -> datetime:
    """A mute's end: aware (naive reads as UTC), in the future and at most 90 days away."""
    now = now or datetime.now(timezone.utc)
    aware = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
    if not now < aware <= now + MUTE_MAX:
        raise Refused(problem(400, INVALID_UNTIL, "invalid"))
    return aware.astimezone(timezone.utc)


def actor_for(user: User) -> str:
    """The CoPilot username, as talon-analyst stores it in ``acted_by`` (printable, at most 128)."""
    name = "".join(c for c in str(user.username or "") if c.isprintable()).strip()
    return (name or f"user {user.id}")[:ACTOR_MAX]


# ── talon-analyst's answers ───────────────────────────────────────────────────


def answer_problem(answer: V2Answer, cleaners: Optional[Cleaners] = None) -> Optional[JSONResponse]:
    """The answer as CoPilot's refusal, or None for a usable 2xx.

    talon-analyst's errors (``api/ops.py``): 400 a fixed reason, 403 (run now for a non-admin, a role
    it refuses), 404 ``finding not found`` / ``unknown job`` (any other 404 is a Talon without the ops
    API, or with its v2 API off), 409 a state the action doesn't allow or a job not enabled, 422
    ``invalid request``, 503 run now without DBOS or a worker. A 401 is CoPilot's key: a 502."""
    status = answer.status
    if status is None:
        return problem(502, UNREACHABLE, "unavailable")
    if 200 <= status < 300:
        return None
    detail = refusal_reason(status, answer.body) if 400 <= status < 500 else _reason_5xx(answer)
    reason = cleaners.scrub(detail, MAX_REASON) if cleaners is not None and detail else None
    if status == 404:
        if detail == "finding not found":
            return problem(404, NOT_FOUND, "not_found")
        if detail == "unknown job":
            return problem(404, UNKNOWN_JOB, "not_found")
        return problem(404, OLD_TALON, "unsupported")
    if status == 401:
        logger.error("Talon ops: talon-analyst refused CoPilot's API key (401)")
        return problem(502, KEY_REFUSED, "unavailable")
    if status == 400:
        return problem(400, f"Talon refused the request: {reason}" if reason else INVALID_REQUEST, "invalid")
    if status == 422:
        return problem(400, INVALID_REQUEST, "invalid")
    if status == 403:
        return problem(403, reason or "Talon refused the request", "forbidden")
    if status == 409:
        return problem(409, reason or "Talon refused the request in the finding's current state", "conflict")
    if status == 503:
        return problem(503, reason or UNAVAILABLE, "unavailable")
    logger.error(f"Talon ops: talon-analyst answered {status}")
    return problem(502, FAILED, "unavailable")


def _reason_5xx(answer: V2Answer) -> Optional[str]:
    """talon-analyst's 503 reasons for run now are its own fixed one-liners: read like a 4xx's."""
    if answer.status == 503:
        return refusal_reason(400, answer.body)
    return None


def _json(answer: V2Answer) -> Union[Any, JSONResponse]:
    try:
        return json.loads(answer.body)
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        return problem(502, NOT_JSON, "bad_answer")


def _int(value: Any, *, minimum: int = 0, maximum: int = FINDING_ID_MAX) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        return None
    return value


def _bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _time(value: Any) -> Optional[datetime]:
    """An ISO 8601 time as talon-analyst writes it (aware), in UTC; anything else None."""
    if not isinstance(value, str) or not 10 <= len(value) <= 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _label(value: Any, cleaners: Cleaners, cap: int = MAX_LABEL) -> Optional[str]:
    """A short identifier-like string talon-analyst wrote in code (a job, a kind, a status), or None:
    no unseen characters and nothing the scrubber would change."""
    if not isinstance(value, str) or not value or len(value) > cap:
        return None
    return value if cleaners.scrub(value, cap) == value else None


def _scalar(value: Any, cleaners: Cleaners) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= FINDING_ID_MAX else None
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    if isinstance(value, str):
        return cleaners.scrub(value, MAX_EVIDENCE_TEXT)
    return None


def _evidence_value(value: Any, cleaners: Cleaners, depth: int) -> Any:
    if isinstance(value, Mapping):
        if depth >= MAX_EVIDENCE_DEPTH:
            return None
        out: Dict[str, Any] = {}
        for key, item in list(value.items())[:MAX_EVIDENCE_KEYS]:
            name = _label(key, cleaners)
            if name is not None:
                out[name] = _evidence_value(item, cleaners, depth + 1)
        return out
    if isinstance(value, list):
        if depth >= MAX_EVIDENCE_DEPTH:
            return None
        return [_evidence_value(item, cleaners, depth + 1) for item in value[:MAX_EVIDENCE_LIST]]
    return _scalar(value, cleaners)


def parse_evidence(raw: Any, cleaners: Cleaners) -> tuple:
    """``(evidence, truncated)``: a bounded copy of talon-analyst's evidence object (keys short labels,
    strings cleaned, at most three levels), or None when it isn't an object or is still too large."""
    if raw is None:
        return None, False
    if not isinstance(raw, Mapping):
        return None, True
    evidence = _evidence_value(raw, cleaners, 0)
    if len(json.dumps(evidence, separators=(",", ":")).encode()) > MAX_EVIDENCE_BYTES:
        return None, True
    return evidence, False


def parse_artifact(raw: Any, cleaners: Cleaners) -> Optional[TalonOpsArtifact]:
    if not isinstance(raw, Mapping):
        return None
    kind = _label(raw.get("type"), cleaners)
    body = cleaners.scrub_text(raw.get("body"), MAX_ARTIFACT_BODY)
    if kind is None or body is None:
        return None
    return TalonOpsArtifact(type=kind, body=body)


def parse_finding(raw: Any, cleaners: Cleaners) -> Optional[TalonOpsFinding]:
    """One finding, field by field; None when a field the page needs is missing or malformed."""
    if not isinstance(raw, Mapping):
        return None
    finding_id = _int(raw.get("id"), minimum=1)
    job = _label(raw.get("job"), cleaners)
    kind = _label(raw.get("kind"), cleaners)
    severity = raw.get("severity")
    status = raw.get("status")
    title = cleaners.scrub(raw.get("title"), MAX_TITLE)
    code = raw.get("customer_code")
    if code is not None and not is_talon_customer_code(code):
        return None
    if finding_id is None or job is None or kind is None or title is None or severity not in SEVERITIES or status not in STATUSES:
        return None
    evidence, truncated = parse_evidence(raw.get("evidence"), cleaners)
    priority = _int(raw.get("priority"), minimum=1, maximum=5)
    return TalonOpsFinding(
        id=finding_id,
        fingerprint=cleaners.scrub(raw.get("fingerprint"), MAX_ID_TEXT),
        job=job,
        job_version=_int(raw.get("job_version"), maximum=1_000_000),
        customer_code=code,
        kind=kind,
        severity=severity,
        title=title,
        evidence=evidence,
        evidence_truncated=truncated,
        artifact=parse_artifact(raw.get("artifact"), cleaners),
        why=cleaners.scrub_text(raw.get("why"), MAX_WHY),
        recommendation=cleaners.scrub_text(raw.get("recommendation"), MAX_RECOMMENDATION),
        priority=priority,
        explained=_bool(raw.get("explained")),
        status=status,
        first_seen=_time(raw.get("first_seen")),
        last_seen=_time(raw.get("last_seen")),
        resolved_at=_time(raw.get("resolved_at")),
        resolved_reason=_label(raw.get("resolved_reason"), cleaners),
        stale_since=_time(raw.get("stale_since")),
        muted_until=_time(raw.get("muted_until")),
        acted_by=cleaners.scrub(raw.get("acted_by"), ACTOR_MAX),
        acted_at=_time(raw.get("acted_at")),
        notified_at=_time(raw.get("notified_at")),
        updated_at=_time(raw.get("updated_at")),
    )


def parse_run(raw: Any, cleaners: Cleaners) -> Optional[TalonOpsRun]:
    if not isinstance(raw, Mapping):
        return None
    run_id = cleaners.scrub(raw.get("id"), MAX_ID_TEXT)
    job = _label(raw.get("job"), cleaners)
    status = _label(raw.get("status"), cleaners)
    code = raw.get("customer_code")
    if code is not None and not is_talon_customer_code(code):
        return None
    if run_id is None or job is None or status is None:
        return None
    cost = raw.get("cost_usd")
    return TalonOpsRun(
        id=run_id,
        job=job,
        job_version=_int(raw.get("job_version"), maximum=1_000_000),
        customer_code=code,
        tick=_time(raw.get("tick")),
        triggered_by=_label(raw.get("triggered_by"), cleaners),
        status=status,
        collected=_bool(raw.get("collected")),
        explained=_label(raw.get("explained"), cleaners),
        candidates=_int(raw.get("candidates")),
        new=_int(raw.get("new")),
        updated=_int(raw.get("updated")),
        resolved=_int(raw.get("resolved")),
        error=cleaners.scrub(raw.get("error"), MAX_REASON),
        cost_usd=cost if isinstance(cost, str) and re.fullmatch(r"\d{1,15}(\.\d{1,12})?", cost) else None,
        duration_ms=_int(raw.get("duration_ms")),
        started_at=_time(raw.get("started_at")),
        finished_at=_time(raw.get("finished_at")),
    )


def _settings(raw: Any, cleaners: Cleaners) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for key, value in list(raw.items())[:MAX_SETTINGS]:
        name = _label(key, cleaners)
        if name is None or isinstance(value, (Mapping, list)):
            continue
        out[name] = _scalar(value, cleaners)
    return out


def parse_job(raw: Any, cleaners: Cleaners, caller: Caller) -> Optional[TalonOpsJob]:
    if not isinstance(raw, Mapping):
        return None
    name = raw.get("name")
    enabled = raw.get("enabled")
    if not isinstance(name, str) or not JOB_NAME.fullmatch(name) or not isinstance(enabled, bool):
        return None
    runs = [parse_run(item, cleaners) for item in (raw.get("last_runs") or [])[:MAX_RUNS]] if isinstance(raw.get("last_runs"), list) else []
    last_runs = [run for run in runs if run is not None and caller.sees(run.customer_code)]
    last = parse_run(raw.get("last_run"), cleaners)
    scope = raw.get("scope") if raw.get("scope") in ("platform", "customer") else None
    needs = raw.get("needs") if isinstance(raw.get("needs"), list) else []
    return TalonOpsJob(
        name=name,
        title=cleaners.scrub(raw.get("title"), MAX_TITLE),
        version=_int(raw.get("version"), maximum=1_000_000),
        scope=scope,
        enabled=enabled,
        schedule=cleaners.scrub(raw.get("schedule"), 128),
        schedule_status=_label(raw.get("schedule_status"), cleaners),
        last_fired_at=_time(raw.get("last_fired_at")),
        needs=[n for n in (_label(item, cleaners) for item in needs[:20]) if n],
        settings=_settings(raw.get("settings"), cleaners),
        last_run=last if last is not None and caller.sees(last.customer_code) else (last_runs[0] if last_runs else None),
        last_runs=last_runs,
        next_run=_time(raw.get("next_run")),
    )


async def _ask(method: str, path: str, caller: Caller, **kwargs) -> V2Answer:
    return await v2_request(method, path, caller.identity, max_body_bytes=MAX_BODY_BYTES, **kwargs)


def _finding_answer(answer: V2Answer, caller: Caller, cleaners: Cleaners, expected_id: int, stored: Any = "unchecked"):
    """A one-finding answer, or the refusal. Fails closed with the 404 an unknown id gets when the
    finding isn't the one asked for, isn't the caller's to see, or (``stored``) isn't of that customer."""
    refused = answer_problem(answer, cleaners)
    if refused is not None:
        return refused
    raw = _json(answer)
    if isinstance(raw, JSONResponse):
        return raw
    finding = parse_finding(raw, cleaners)
    if finding is None:
        return problem(502, WRONG_SHAPE, "bad_answer")
    if finding.id != expected_id or not caller.sees(finding.customer_code):
        logger.warning(f"Talon ops: finding {expected_id}'s answer is not the caller's to see; refused")
        return problem(404, NOT_FOUND, "not_found")
    if stored != "unchecked" and finding.customer_code != stored:
        logger.warning(f"Talon ops: finding {expected_id}'s answer names another customer; refused")
        return problem(404, NOT_FOUND, "not_found")
    return finding


# ── the routes' work ──────────────────────────────────────────────────────────


async def list_findings(
    user: User,
    session: AsyncSession,
    *,
    job: Optional[str] = None,
    customer_code: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    platform: bool = False,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
):
    try:
        params: Dict[str, Any] = {
            "job": check_job(job),
            "customer_code": check_customer_code(customer_code),
            "status": _choice(status, STATUSES, INVALID_STATUS),
            "severity": _choice(severity, SEVERITIES, INVALID_SEVERITY),
            "limit": _limit(limit, DEFAULT_LIMIT),
            "cursor": _cursor(cursor),
        }
        if platform and params["customer_code"]:
            raise Refused(problem(400, PLATFORM_AND_CUSTOMER, "invalid"))
    except Refused as e:
        await session.close()
        return e.response
    caller, cleaners = await _caller_then_release(user, session)
    if platform and not caller.all_customers:
        return problem(403, PLATFORM_ONLY, "forbidden")
    if params["customer_code"] and not caller.sees(params["customer_code"]):
        return problem(403, NOT_ACCESSIBLE, "forbidden")
    if platform:
        params["platform"] = "true"
    answer = await _ask("GET", "/v2/ops/findings", caller, params={k: v for k, v in params.items() if v is not None})
    refused = answer_problem(answer, cleaners)
    if refused is not None:
        return refused
    raw = _json(answer)
    if isinstance(raw, JSONResponse):
        return raw
    if not isinstance(raw, Mapping) or not isinstance(raw.get("items"), list):
        return problem(502, WRONG_SHAPE, "bad_answer")
    items: List[TalonOpsFinding] = []
    dropped = 0
    for item in raw["items"][:MAX_LIMIT]:
        finding = parse_finding(item, cleaners)
        wanted = finding is not None and caller.sees(finding.customer_code)
        if wanted and params["customer_code"] and finding.customer_code != params["customer_code"]:
            wanted = False
        if wanted and platform and finding.customer_code is not None:
            wanted = False
        if wanted:
            items.append(finding)
        else:
            dropped += 1
    if dropped:
        logger.warning(f"Talon ops: dropped {dropped} finding(s) of a page that the caller may not see or that were malformed")
    next_cursor = raw.get("next_cursor")
    return TalonOpsFindingPage(
        items=items,
        next_cursor=next_cursor if isinstance(next_cursor, str) and CURSOR.fullmatch(next_cursor) else None,
        dropped=dropped,
    )


async def get_finding(user: User, session: AsyncSession, finding_id: int, customer_code: Optional[str] = None):
    try:
        check_finding_id(finding_id)
        code = check_customer_code(customer_code)
    except Refused as e:
        await session.close()
        return e.response
    caller, cleaners = await _caller_then_release(user, session)
    if code is not None and not caller.sees(code):
        return problem(404, NOT_FOUND, "not_found")
    params = {"customer_code": code} if code else None
    answer = await _ask("GET", f"/v2/ops/findings/{finding_id}", caller, params=params)
    finding = _finding_answer(answer, caller, cleaners, finding_id, stored=code if code else "unchecked")
    if isinstance(finding, JSONResponse):
        return finding
    return TalonOpsFindingResponse(finding=finding)


#: The action path segment, its audit action and the past tense for messages.
ACTIONS = {
    "acknowledge": (AuditAction.TALON_OPS_ACKNOWLEDGE, "acknowledged"),
    "mute": (AuditAction.TALON_OPS_MUTE, "muted"),
    "reopen": (AuditAction.TALON_OPS_REOPEN, "reopened"),
}


async def act(
    user: User,
    session: AsyncSession,
    finding_id: int,
    action: str,
    *,
    until: Optional[datetime] = None,
    customer_code: Optional[str] = None,
    request: Optional[Request] = None,
):
    """Acknowledge, mute (until a time) or reopen a finding, as the signed-in user.

    In order: the id and the named customer's grammar, the mute's end; then the finding read as the
    caller (its stored customer must be one the caller sees, and equal the named one); then the
    action, sent with the stored ``customer_code`` so talon-analyst refuses it if the finding's
    stored customer is another; the answer must name the same finding and customer. Audited."""
    audit_action, done = ACTIONS[action]
    username = user.username
    user_id = user.id
    try:
        check_finding_id(finding_id)
        code = check_customer_code(customer_code)
        when = check_until(until) if action == "mute" else None
    except Refused as e:
        await session.close()
        return e.response
    caller, cleaners = await _caller_then_release(user, session)
    audit = {
        "action": audit_action,
        "actor_user_id": user_id,
        "actor_username": username,
        "entity_type": "talon_ops_finding",
        "entity_id": str(finding_id),
        "request": request,
    }
    if code is not None and not caller.sees(code):
        return problem(404, NOT_FOUND, "not_found")

    current = _finding_answer(
        await _ask("GET", f"/v2/ops/findings/{finding_id}", caller, params={"customer_code": code} if code else None),
        caller,
        cleaners,
        finding_id,
        stored=code if code else "unchecked",
    )
    if isinstance(current, JSONResponse):
        return current
    stored = current.customer_code
    audit["customer_code"] = stored
    audit["old_value"] = {"status": current.status, "muted_until": current.muted_until.isoformat() if current.muted_until else None}

    body: Dict[str, Any] = {"actor": actor_for(user)}
    if when is not None:
        body["until"] = when.isoformat()
    answer = await _ask(
        "POST",
        f"/v2/ops/findings/{finding_id}/{action}",
        caller,
        params={"customer_code": stored} if stored is not None else None,
        json_body=body,
    )
    finding = _finding_answer(answer, caller, cleaners, finding_id, stored=stored)
    if isinstance(finding, JSONResponse):
        result = AuditResult.UNKNOWN if answer.status is None else AuditResult.FAILURE
        await record_audit_event(
            **audit,
            result=result,
            details=f"Talon ops finding {finding_id} not {done}: {json.loads(finding.body).get('detail')}",
        )
        return finding
    await record_audit_event(
        **audit,
        new_value={"status": finding.status, "muted_until": finding.muted_until.isoformat() if finding.muted_until else None},
        details=f"Talon ops finding {finding_id} ({finding.job}) {done}",
    )
    return TalonOpsFindingResponse(message=f"The finding was {done}", finding=finding)


async def list_jobs(user: User, session: AsyncSession):
    caller, cleaners = await _caller_then_release(user, session)
    answer = await _ask("GET", "/v2/ops/jobs", caller)
    refused = answer_problem(answer, cleaners)
    if refused is not None:
        return refused
    raw = _json(answer)
    if isinstance(raw, JSONResponse):
        return raw
    if not isinstance(raw, Mapping) or not isinstance(raw.get("items"), list):
        return problem(502, WRONG_SHAPE, "bad_answer")
    jobs = [job for job in (parse_job(item, cleaners, caller) for item in raw["items"][:MAX_JOBS]) if job is not None]
    return TalonOpsJobs(items=jobs, any_enabled=any(job.enabled for job in jobs))


async def list_runs(
    user: User,
    session: AsyncSession,
    *,
    job: Optional[str] = None,
    customer_code: Optional[str] = None,
    limit: Optional[int] = None,
):
    try:
        params = {"job": check_job(job), "customer_code": check_customer_code(customer_code), "limit": _limit(limit, RUNS_DEFAULT_LIMIT)}
    except Refused as e:
        await session.close()
        return e.response
    caller, cleaners = await _caller_then_release(user, session)
    if params["customer_code"] and not caller.sees(params["customer_code"]):
        return problem(403, NOT_ACCESSIBLE, "forbidden")
    answer = await _ask("GET", "/v2/ops/runs", caller, params={k: v for k, v in params.items() if v is not None})
    refused = answer_problem(answer, cleaners)
    if refused is not None:
        return refused
    raw = _json(answer)
    if isinstance(raw, JSONResponse):
        return raw
    if not isinstance(raw, Mapping) or not isinstance(raw.get("items"), list):
        return problem(502, WRONG_SHAPE, "bad_answer")
    runs: List[TalonOpsRun] = []
    dropped = 0
    for item in raw["items"][:MAX_LIMIT]:
        run = parse_run(item, cleaners)
        if run is not None and caller.sees(run.customer_code):
            runs.append(run)
        else:
            dropped += 1
    return TalonOpsRuns(items=runs, dropped=dropped)


async def run_now(user: User, session: AsyncSession, name: str, request: Optional[Request] = None):
    """Run an enabled job now (admin only, by ``role_id``; talon-analyst checks the role it is sent).
    Audited, refusals included."""
    audit = {
        "action": AuditAction.TALON_OPS_RUN,
        "actor_user_id": user.id,
        "actor_username": user.username,
        "entity_type": "talon_ops_job",
        "entity_id": name if isinstance(name, str) and JOB_NAME.fullmatch(name) else "<invalid job name>",
        "request": request,
    }
    if user.role_id != RoleEnum.admin:
        await session.close()
        await record_audit_event(**audit, result=AuditResult.FAILURE, details=ADMIN_ONLY)
        return problem(403, ADMIN_ONLY, "forbidden")
    try:
        check_job(name)
    except Refused as e:
        await session.close()
        return e.response
    caller, cleaners = await _caller_then_release(user, session)
    answer = await _ask("POST", f"/v2/ops/jobs/{name}/run", caller)
    refused = answer_problem(answer, cleaners)
    if refused is not None:
        await record_audit_event(
            **audit,
            result=AuditResult.UNKNOWN if answer.status is None else AuditResult.FAILURE,
            details=f"Talon ops job {name} not run now: {json.loads(refused.body).get('detail')}",
        )
        return refused
    raw = _json(answer)
    workflow_id = cleaners.scrub(raw.get("workflow_id"), MAX_ID_TEXT) if isinstance(raw, Mapping) else None
    status = _label(raw.get("status"), cleaners) if isinstance(raw, Mapping) else None
    await record_audit_event(**audit, details=f"Talon ops job {name} queued to run now")
    return TalonOpsRunNow(job=name, workflow_id=workflow_id, status=status or "queued")
