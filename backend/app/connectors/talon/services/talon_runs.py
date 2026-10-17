"""The run view: one investigation's timeline, read from Phoenix (talon-analyst SPEC §5.4 FR-PHX-1/2,
D51; plan M5-9a, the run view's steps 1-6, decisions E and F).

``GET /api/talon/v2/runs/{job_id}/timeline``, behind the "Talon v2" setting, for admins and
analysts (a responder's token carries ``analyst``). In order, on every request:

1. **Authorize from CoPilot's own rows, before any Phoenix call.** The ``ai_analyst_job`` row must
   exist; its alert must pass ``_ensure_alert_access`` (customer *and* tags) and belong to the
   job's customer; ``enforce_customer_access`` on that customer, and the user's role must be one
   talon-analyst serves (``talon_role``). An unknown job and a refused one answer the same 404, so
   a job id tells nothing. Then the request's session is closed: Phoenix may take seconds.
2. **The project is ``talon-<job.customer_code>``** and only when the code passes
   talon-analyst's ``project_for`` rule (``PROJECT_CUSTOMER``); otherwise 409. Never
   ``talon-chat``, and nothing from the request names it. A Phoenix viewer key reads every
   project, so this is the only thing that keeps one customer's traces from another's.
3. **The query:** ``attribute=job_id:<json>`` and ``attribute=customer_code:<json>`` (Phoenix
   JSON-decodes the value, so both are JSON-quoted), a window from the job's ``created_at`` minus
   2 minutes to its ``completed_at`` (or now) plus 15 minutes, in UTC with ``Z``, sorted by start
   time ascending, 100 spans a page, at most 10 pages; ``truncated`` past either cap.
4. **Every span is checked again**: its ``job_id`` and ``customer_code`` attributes must be the
   job's, exactly; any other span is dropped and counted (``dropped``), as is one that doesn't parse.
5. **The allowlist DTO** (``schema/talon_runs.py``): ids, kind, a known name, times, status code,
   stage, role, model, a known tool and integer token counts. Never ``status_message``, events,
   ``input.*``, ``output.*``, ``llm.*_messages``, ``talon.scrub_*`` or any other attribute; a name
   that isn't one of the known span-name patterns is shown as ``"<kind> span"``.
6. **Phoenix's answers:** its 404 (no project yet) is an empty timeline with ``note: "no trace
   data"``; 401/403, a 5xx, a transport error, an unexpected body, a key that isn't a VIEWER's or
   an unconfigured connector is 502 ``Phoenix request failed``. Phoenix's own text is never relayed.

Every answer is ``no-store``.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.connectors.talon.schema.talon_runs import RunTimeline
from app.connectors.talon.schema.talon_runs import TimelineSpan
from app.connectors.talon.services.identity import talon_role
from app.connectors.talon.services.talon_v2 import NO_STORE
from app.connectors.talon.utils import phoenix_client
from app.db.universal_models import AiAnalystJob
from app.incidents.routes import db_operations as incident_routes
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

#: talon-analyst's ``tracing.project_for`` rule, mirrored: a customer's spans go to
#: ``talon-<code>`` only when the code matches this; anything else goes to the shared ``talon-chat``
#: project, which CoPilot never reads (FR-PHX-2). talon-analyst M5-9t is widening its rule to the
#: customer grammar (dotted codes, ``acme.io``); change this one constant to follow it then, and no
#: earlier (decision F: until then a dotted code's run view is refused). Matched with ``fullmatch``,
#: stricter than ``re.match`` with ``$`` (which lets a trailing newline through).
PROJECT_CUSTOMER = re.compile(r"[A-Za-z0-9_-]{1,64}")
CHAT_PROJECT = "talon-chat"

FAILED = "Phoenix request failed"
NOT_FOUND = "investigation not found"
NO_PROJECT = "this customer's runs are not traced to a project of its own"
NO_TRACE_DATA = "no trace data"
PAGE_TOO_LARGE = "a page of trace data was too large to read"

PAGE_SIZE = 100
MAX_PAGES = 10
WINDOW_BEFORE = timedelta(minutes=2)
WINDOW_AFTER = timedelta(minutes=15)
MAX_JOB_ID = 64  # ``ai_analyst_job.id``
MAX_CURSOR = 1024


def project_for(customer_code: object) -> Optional[str]:
    """The customer's own Phoenix project, or None when talon-analyst wouldn't route its spans there."""
    if isinstance(customer_code, str) and PROJECT_CUSTOMER.fullmatch(customer_code):
        project = f"talon-{customer_code}"
        return None if project == CHAT_PROJECT else project
    return None


def answer(status: int, content: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(content, status_code=status, headers=dict(NO_STORE))


def refusal(status: int, detail: str) -> JSONResponse:
    return answer(status, {"detail": detail})


# ── step 1: CoPilot's own rows ────────────────────────────────────────────────


@dataclass(frozen=True)
class JobFacts:
    """What the timeline needs from the job, read before the session is closed."""

    job_id: str
    customer_code: str
    created_at: datetime
    completed_at: Optional[datetime]


class JobRefused(Exception):
    """The caller may not see this job (or it doesn't exist): the same answer either way."""


async def authorize_job(user: User, session: AsyncSession, job_id: str) -> JobFacts:
    """The job, if ``user`` may see it now: its alert's customer and tags, and its customer.

    Raises ``JobRefused`` for an unknown job and for every refusal alike; ``HTTPException`` 403
    only for a role talon-analyst doesn't serve (which the route's scopes already exclude).
    """
    talon_role(user)
    if not isinstance(job_id, str) or not 0 < len(job_id) <= MAX_JOB_ID:
        raise JobRefused()
    result = await session.execute(select(AiAnalystJob).where(AiAnalystJob.id == job_id))
    job = result.scalars().first()
    if job is None or job.id != job_id:  # MySQL compares case-insensitively; job ids don't
        raise JobRefused()
    try:
        alert = await incident_routes._ensure_alert_access(job.alert_id, user, session)
        if getattr(alert, "customer_code", None) != job.customer_code:
            raise JobRefused()
        await customer_access_handler.enforce_customer_access(user, job.customer_code, session)
    except HTTPException:
        raise JobRefused() from None
    return JobFacts(job_id=job.id, customer_code=job.customer_code, created_at=job.created_at, completed_at=job.completed_at)


# ── step 3: the query ─────────────────────────────────────────────────────────


def _utc(value: datetime) -> datetime:
    """CoPilot's datetimes are naive UTC; an aware one is converted."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _z(value: datetime) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def time_window(job: JobFacts, now: Optional[datetime] = None) -> Tuple[str, str]:
    start = _utc(job.created_at) - WINDOW_BEFORE
    end = _utc(job.completed_at if job.completed_at is not None else (now or now_utc())) + WINDOW_AFTER
    return _z(start), _z(end)


def span_query(job: JobFacts, cursor: Optional[str] = None, now: Optional[datetime] = None) -> List[Tuple[str, str]]:
    """``getSpans``' parameters. The attribute values are JSON strings: Phoenix 20.20
    ``_parse_attribute`` JSON-decodes them, so an unquoted id that looks like a number would match
    as one."""
    start, end = time_window(job, now)
    params = [
        ("attribute", f"job_id:{json.dumps(job.job_id)}"),
        ("attribute", f"customer_code:{json.dumps(job.customer_code)}"),
        ("start_time", start),
        ("end_time", end),
        ("sort", "start_time"),
        ("order", "asc"),
        ("limit", str(PAGE_SIZE)),
    ]
    if cursor is not None:
        params.append(("cursor", cursor))
    return params


# ── steps 4 and 5: the allowlist ──────────────────────────────────────────────

#: Phoenix's span kinds (``getSpans``' ``span_kind`` values); anything else is UNKNOWN.
SPAN_KINDS = frozenset(
    {"LLM", "CHAIN", "TOOL", "RETRIEVER", "EMBEDDING", "AGENT", "RERANKER", "GUARDRAIL", "EVALUATOR", "DECISION", "UNKNOWN"},
)
STATUS_CODES = frozenset({"OK", "ERROR", "UNSET"})
#: talon-analyst's agents (their ``name=``; DBOS step names derive from them, so they don't change).
AGENT_NAMES = frozenset(
    {"analyst-investigation", "analyst-template-chooser", "reviewer", "analyst-chat", "analyst-chat-memory"},
)
#: talon-analyst's tools (``talon/tools/*.py`` ``@bound_tool`` functions, the capability tools
#: ``read_tool_result``, ``duckduckgo_search``, ``web_fetch`` and ``run_command``) and Pydantic AI's
#: output tool. A tool name is shown only when it is one of these: Pydantic AI also names a span
#: after a tool the model *asked for* that doesn't exist (``execute_tool <name>``, "invalid tool
#: call"), and that name is model-written. A tool talon-analyst adds later shows as "TOOL span"
#: until it is listed here.
TOOL_NAMES = frozenset(
    {
        "assign_alert",
        "comment_on_alert",
        "cve_attack_mapping",
        "cve_triage",
        "cve_vendor_advisories",
        "intel_lookup",
        "ioc_sightings",
        "prior_reports",
        "quarantine_host",
        "recall",
        "release_host",
        "remember",
        "set_alert_status",
        "siem_count",
        "siem_get",
        "siem_search",
        "vr_client_info",
        "vr_collection_results",
        "vr_hunt_results",
        "vr_hunts",
        "wazuh_agent",
        "wazuh_agent_packages",
        "wazuh_agent_ports",
        "wazuh_agent_processes",
        "read_tool_result",
        "duckduckgo_search",
        "web_fetch",
        "run_command",
        "final_result",
    },
)
#: A model name as an operator configures it (``anthropic:claude-…``, ``claude-sonnet-5-5``,
#: ``qwen3:32b``): never model-written, and still held to these characters.
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}")
STAGE = re.compile(r"S[0-9]{1,2}(-[a-z]{1,16})?")
ROLE = re.compile(r"[a-z][a-z_-]{0,31}")
TRACE_ID = re.compile(r"[0-9a-f]{32}")
SPAN_ID = re.compile(r"[0-9a-f]{16}")
#: The span names Pydantic AI 2.x gives talon-analyst's spans, each with what may follow.
_AGENT_SPAN = re.compile(r"invoke_agent (?P<agent>.+)")
_TOOL_SPAN = re.compile(r"execute_tool (?P<tool>.+)")
_MODEL_SPAN = re.compile(r"(?:chat|model request attempt) (?P<model>.+)")
_FIXED_NAMES = frozenset({"agent run", "running tool", "running tools", "running output function"})
#: The largest token count believed (a count past it is not one).
MAX_TOKENS = 10**12


def known_name(name: object, kind: str) -> str:
    """``name`` when it is one of the known span-name patterns, else ``"<kind> span"``."""
    fallback = f"{kind} span"
    if not isinstance(name, str) or len(name) > 200:
        return fallback
    if name in _FIXED_NAMES:
        return name
    match = _AGENT_SPAN.fullmatch(name)
    if match:
        return name if match.group("agent") in AGENT_NAMES else fallback
    match = _TOOL_SPAN.fullmatch(name)
    if match:
        return name if match.group("tool") in TOOL_NAMES else fallback
    match = _MODEL_SPAN.fullmatch(name)
    if match:
        return name if MODEL_NAME.fullmatch(match.group("model")) else fallback
    return fallback


def _member(value: object, allowed: frozenset) -> Optional[str]:
    return value if isinstance(value, str) and value in allowed else None


def _matching(value: object, pattern: "re.Pattern[str]") -> Optional[str]:
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _tokens(attributes: Mapping[str, Any], *keys: str) -> Optional[int]:
    for key in keys:
        value = attributes.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int) and 0 <= value <= MAX_TOKENS:
            return value
        if isinstance(value, float) and value.is_integer() and 0 <= value <= MAX_TOKENS:
            return int(value)
    return None


def _time(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def to_dto(span: Mapping[str, Any]) -> Optional[TimelineSpan]:
    """One Phoenix span (``getSpans``' ``Span``) as the allowlist DTO, or None if it doesn't parse.
    Reads only the named fields; everything else in ``span`` is never looked at."""
    context = span.get("context")
    attributes = span.get("attributes")
    if not isinstance(context, Mapping) or not isinstance(attributes, Mapping):
        return None
    trace_id = _matching(context.get("trace_id"), TRACE_ID)
    span_id = _matching(context.get("span_id"), SPAN_ID)
    start, end = _time(span.get("start_time")), _time(span.get("end_time"))
    if trace_id is None or span_id is None or start is None or end is None:
        return None
    parent = span.get("parent_id")
    parent_id = _matching(parent, SPAN_ID)
    if parent is not None and parent_id is None:
        return None
    kind = _member(span.get("span_kind"), SPAN_KINDS) or "UNKNOWN"
    status = _member(span.get("status_code"), STATUS_CODES) or "UNSET"
    tool = attributes.get("tool.name", attributes.get("gen_ai.tool.name"))
    model = attributes.get("llm.model_name", attributes.get("gen_ai.response.model", attributes.get("gen_ai.request.model")))
    return TimelineSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        kind=kind,
        name=known_name(span.get("name"), kind),
        start_time=_iso(start),
        end_time=_iso(end),
        duration_ms=max(0, int((end - start).total_seconds() * 1000)),
        status_code=status,
        stage=_matching(attributes.get("stage"), STAGE),
        role=_matching(attributes.get("role"), ROLE),
        model=_matching(model, MODEL_NAME),
        tool=_member(tool, TOOL_NAMES),
        prompt_tokens=_tokens(attributes, "llm.token_count.prompt", "gen_ai.usage.input_tokens"),
        completion_tokens=_tokens(attributes, "llm.token_count.completion", "gen_ai.usage.output_tokens"),
        total_tokens=_tokens(attributes, "llm.token_count.total"),
        cache_read_tokens=_tokens(attributes, "llm.token_count.prompt_details.cache_read"),
        cache_write_tokens=_tokens(attributes, "llm.token_count.prompt_details.cache_write"),
    )


def belongs(span: Mapping[str, Any], job: JobFacts) -> bool:
    """Whether Phoenix's span is this job's and this customer's, by its own attributes."""
    attributes = span.get("attributes")
    if not isinstance(attributes, Mapping):
        return False
    return attributes.get("job_id") == job.job_id and attributes.get("customer_code") == job.customer_code


# ── step 6: reading Phoenix ───────────────────────────────────────────────────


class PhoenixFailed(Exception):
    """No usable answer from Phoenix: 502 with the fixed text."""


def _page(body: bytes) -> Tuple[List[Any], Optional[str]]:
    """``{"data": [...], "next_cursor": str | null}`` (Phoenix ``SpansResponseBody``), or PhoenixFailed."""
    try:
        payload = json.loads(body)
    except ValueError:
        raise PhoenixFailed("not JSON") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise PhoenixFailed("not a page of spans")
    cursor = payload.get("next_cursor")
    if cursor is not None and (not isinstance(cursor, str) or not 0 < len(cursor) <= MAX_CURSOR):
        raise PhoenixFailed("a cursor that isn't one")
    return payload["data"], cursor


async def read_timeline(job: JobFacts, project: str) -> RunTimeline:
    """Every page of the job's spans (at most ``MAX_PAGES``), filtered and mapped. Raises
    ``PhoenixFailed`` for anything but a usable answer, and 503 (``HTTPException``) when busy."""
    async with phoenix_client.reading():
        conn = await phoenix_client.connector()
        if conn is None:
            raise PhoenixFailed("no usable connector")
        if not await phoenix_client.is_viewer(conn):
            raise PhoenixFailed("not a viewer key")
        spans: List[TimelineSpan] = []
        dropped = 0
        truncated = False
        note: Optional[str] = None
        cursor: Optional[str] = None
        path = f"/v1/projects/{project}/spans"
        for page_number in range(MAX_PAGES):
            got = await phoenix_client.get(conn, path, span_query(job, cursor), max_bytes=phoenix_client.MAX_PAGE_BYTES)
            if got.status == 404 and page_number == 0:  # no project yet: nothing traced for this customer
                return RunTimeline(
                    job_id=job.job_id,
                    customer_code=job.customer_code,
                    spans=[],
                    truncated=False,
                    dropped=0,
                    note=NO_TRACE_DATA,
                )
            if got.status != 200:
                raise PhoenixFailed(f"HTTP {got.status}")
            if got.over_cap:
                truncated, note = True, PAGE_TOO_LARGE
                break
            data, next_cursor = _page(got.body or b"")
            for raw in data:
                if not isinstance(raw, Mapping) or not belongs(raw, job):
                    dropped += 1
                    continue
                dto = to_dto(raw)
                if dto is None:
                    dropped += 1
                    continue
                spans.append(dto)
            if next_cursor is None:
                break
            if next_cursor == cursor:  # a cursor that doesn't move would page forever
                raise PhoenixFailed("the cursor did not move")
            cursor = next_cursor
        else:
            truncated = True  # MAX_PAGES read and Phoenix still has more
        if dropped:
            logger.warning(f"Talon run view: dropped {dropped} span(s) of job {job.job_id} that weren't its own or didn't parse")
        if not spans and note is None:
            note = NO_TRACE_DATA
        return RunTimeline(job_id=job.job_id, customer_code=job.customer_code, spans=spans, truncated=truncated, dropped=dropped, note=note)


async def run_timeline(user: User, session: AsyncSession, job_id: str) -> JSONResponse:
    """``GET /talon/v2/runs/{job_id}/timeline`` (module docstring, steps 1-6)."""
    try:
        job = await authorize_job(user, session, job_id)
    except JobRefused:
        return refusal(404, NOT_FOUND)
    except HTTPException as e:
        return refusal(e.status_code, "This role may not see Talon runs")
    finally:
        await session.close()  # nothing more is read from CoPilot's database
    project = project_for(job.customer_code)
    if project is None:
        return refusal(409, NO_PROJECT)
    try:
        timeline = await read_timeline(job, project)
    except HTTPException as e:  # busy
        return refusal(e.status_code, str(e.detail))
    except PhoenixFailed as e:
        logger.error(f"Talon run view of job {job.job_id}: Phoenix gave no usable answer ({e})")
        return refusal(502, FAILED)
    return answer(200, timeline.model_dump(mode="json"))
