"""The Talon health dashboard (``GET /api/talon/health``): one payload for the AI Analyst page's
Overview tab, whatever the "Talon v2" setting says.

Two halves:

- **CoPilot's own view**, measured here: the connector row (configured, verified, its URL with
  user-info stripped), ``GET {url}/health`` (reachable, latency), whether Talon accepts the API key,
  the v2 setting, and from CoPilot's tables the newest alert sent, job and report, the jobs failed in
  24 h and the customers with the AI trigger on.
- **talon-analyst's** ``/v2/health``, ``/v2/health/history`` and ``/v2/health/metrics``, asked with
  the connector's key. Each is a section with its own ``error``, so one failing never blanks the
  others; a 404 means a Talon older than the health API (``unsupported``).

Rules that hold the page safe to show every analyst (decision (a): the same detail for everyone who
can open the page, never a secret):

- The API key goes to Talon and nowhere else. Every talon-analyst string is bounded, stripped of
  user-info in URLs and of the key itself should it appear; every field is copied one by one into
  ``schema/talon_health.py`` (``_health``, ``_history``, ``_metrics``), so an unknown field never
  reaches the browser and a malformed one is ``None`` rather than a failed page.
- Errors are fixed texts plus at most an exception's class name (``utils/health_client``).
- **Tenancy**: per-customer items (``config.live_customers``, the newest job, report and alert sent,
  the failed count, the AI trigger count) cover only the caller's customers unless they are an admin
  (``get_user_accessible_customers``; #1219: no assignment, no customer).

Talon is asked at most once per 30 s per ``hours`` value and connector (``_CACHE``, one request in
flight per key); the per-user scoping is applied after the cache, on every request. The request's
database session is closed before Talon is asked, so no pooled connection waits on it.
"""
import asyncio
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from loguru import logger
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger
from app.connectors.talon.schema.talon_health import TalonConnectorState
from app.connectors.talon.schema.talon_health import TalonCopilotView
from app.connectors.talon.schema.talon_health import TalonHealthBudgets
from app.connectors.talon.schema.talon_health import TalonHealthComponent
from app.connectors.talon.schema.talon_health import TalonHealthConfig
from app.connectors.talon.schema.talon_health import TalonHealthData
from app.connectors.talon.schema.talon_health import TalonHealthModels
from app.connectors.talon.schema.talon_health import TalonHealthResponse
from app.connectors.talon.schema.talon_health import TalonHealthSection
from app.connectors.talon.schema.talon_health import TalonHistoryBucket
from app.connectors.talon.schema.talon_health import TalonHistoryData
from app.connectors.talon.schema.talon_health import TalonHistorySection
from app.connectors.talon.schema.talon_health import TalonJobSummary
from app.connectors.talon.schema.talon_health import TalonMetricsBucket
from app.connectors.talon.schema.talon_health import TalonMetricsData
from app.connectors.talon.schema.talon_health import TalonMetricsSection
from app.connectors.talon.schema.talon_health import TalonProbe
from app.connectors.talon.services.talon_v2 import is_v2_enabled
from app.connectors.talon.utils import health_client
from app.connectors.talon.utils.health_client import Probe
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.utils import get_connector_info_from_db
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import AiAnalystReport
from app.incidents.models import AIAnalystTriggerEnabled
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

DEFAULT_HOURS = 24
MIN_HOURS = 1
MAX_HOURS = 168
CACHE_SECONDS = 30.0

#: Shown when talon-analyst answers 404 for its health routes (a release before the health API, or
#: NanoClaw). The version is decided at release; keep the frontend's copy the same.
OLD_TALON = "This Talon version has no health endpoint; upgrade to talon-analyst 0.1.3 or later"
NOT_CONFIGURED = "The Talon connector has no URL in CoPilot"
NO_CONNECTOR = "There is no Talon connector in CoPilot"
KEY_REFUSED = "Talon refused CoPilot's API key (401)"
NOT_JSON = "Talon's answer was not valid JSON"
WRONG_SHAPE = "Talon's answer was not in the expected shape"

#: Body caps per route: the health snapshot is a few KB; a week of 5-minute buckets for 12
#: components is a few hundred KB.
MAX_HEALTH_BYTES = 256 * 1024
MAX_SERIES_BYTES = 2 * 1024 * 1024
MAX_PROBE_BYTES = 4096

MAX_COMPONENTS = 64
MAX_BUCKETS = 2100  # 168 h of 5-minute buckets is 2016
MAX_LIVE_CUSTOMERS = 1000
COMPONENT_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")
AMOUNT = re.compile(r"-?\d{1,15}(\.\d{1,12})?")
#: ``scheme://user:password@`` inside any text: the user-info is dropped, the rest kept.
_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]{0,31}://)[^/\s@]{1,512}@")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f  ]")

OVERALL = ("ok", "degraded", "down")
COMPONENT_STATUSES = ("ok", "warn", "fail", "off")
GROUPS = ("core", "mcp", "model")
SWITCHES = ("v2_api", "action_tools", "endpoint_actions", "intel", "workspace_tools", "chat_browser")
METRIC_FIELDS = (
    "investigations_completed",
    "investigations_failed",
    "queue_depth_max",
    "duration_p50_s",
    "duration_p95_s",
    "tool_calls",
    "tool_errors",
    "model_errors",
)


# ── strings and numbers from talon-analyst ────────────────────────────────────


def strip_url(url: Any) -> Optional[str]:
    """``url`` without user-info, query or fragment (any of them may carry a secret); None when it
    isn't a URL."""
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
        port = parts.port
    except ValueError:
        return None
    if not parts.scheme or not host:
        return None
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def make_scrub(secrets: Sequence[str]) -> Callable[[Any, int], Optional[str]]:
    """A text cleaner for talon-analyst's strings: one line, user-info dropped from URLs, any of
    ``secrets`` (the API key) replaced, at most ``cap`` characters. Not a string: None."""
    hidden = [s for s in secrets if isinstance(s, str) and len(s) >= 6]

    def scrub(value: Any, cap: int) -> Optional[str]:
        if not isinstance(value, str):
            return None
        text = _CONTROL.sub(" ", value)
        text = _URL_USERINFO.sub(r"\1", text)
        for secret in hidden:
            text = text.replace(secret, "[redacted]")
        text = text.strip()
        if not text:
            return None
        return text if len(text) <= cap else text[: cap - 1] + "…"

    return scrub


def _number(value: Any, *, minimum: float = 0.0) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        return None
    return number


def _count(value: Any) -> Optional[int]:
    number = _number(value)
    if number is None or number != int(number):
        return None
    return int(number)


def _amount(value: Any) -> Optional[str]:
    """A decimal string as talon-analyst sends amounts (a number is written out), or ``unlimited``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # Written out in full (talon-analyst rounds amounts to 6 places): 1e-06 is "0.000001".
        return format(Decimal(repr(value)), "f") if math.isfinite(value) else None
    if isinstance(value, str):
        text = value.strip()
        if text.lower() == "unlimited":
            return "unlimited"
        if AMOUNT.fullmatch(text):
            return text
    return None


def _enum(value: Any, allowed: Sequence[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


# ── talon-analyst's payloads, field by field ──────────────────────────────────


def _component(raw: Any, scrub) -> Optional[TalonHealthComponent]:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not COMPONENT_ID.fullmatch(raw["id"]):
        return None
    return TalonHealthComponent(
        id=raw["id"],
        name=scrub(raw.get("name"), 128) or raw["id"],
        group=_enum(raw.get("group"), GROUPS, "other"),
        status=_enum(raw.get("status"), COMPONENT_STATUSES, "unknown"),
        latency_ms=_number(raw.get("latency_ms")),
        detail=scrub(raw.get("detail"), 500),
        fix=scrub(raw.get("fix"), 2000),
        checked_at=scrub(raw.get("checked_at"), 64),
    )


def _switch(value: Any, scrub):
    if isinstance(value, bool):
        return value
    return scrub(value, 32)


def _config(raw: Any, scrub) -> Optional[TalonHealthConfig]:
    if not isinstance(raw, dict):
        return None
    live = raw.get("live_customers")
    customers: List[str] = []
    if isinstance(live, list):
        for code in live[:MAX_LIVE_CUSTOMERS]:
            text = scrub(code, 64)
            if text and text not in customers:
                customers.append(text)
    level = _count(raw.get("automation_max_level"))
    models, budgets = _dict(raw.get("models")), _dict(raw.get("budgets"))
    return TalonHealthConfig(
        writeback_mode=scrub(raw.get("writeback_mode"), 32),
        live_customers=customers,
        automation_max_level=level if level is not None and level <= 10 else None,
        automation_policy_source=scrub(raw.get("automation_policy_source"), 64),
        models=TalonHealthModels(chat=scrub(models.get("chat"), 128), investigation=scrub(models.get("investigation"), 128)),
        budgets=TalonHealthBudgets(**{name: _amount(budgets.get(name)) for name in TalonHealthBudgets.model_fields}),
        **{name: _switch(raw.get(name), scrub) for name in SWITCHES},
    )


def parse_health(raw: Any, scrub) -> Optional[TalonHealthData]:
    if not isinstance(raw, dict):
        return None
    components: List[TalonHealthComponent] = []
    seen = set()
    for item in raw.get("components") if isinstance(raw.get("components"), list) else []:
        component = _component(item, scrub)
        if component is not None and component.id not in seen and len(components) < MAX_COMPONENTS:
            seen.add(component.id)
            components.append(component)
    image_browser = raw.get("image_browser")
    return TalonHealthData(
        status=_enum(raw.get("status"), OVERALL, "unknown"),
        version=scrub(raw.get("version"), 64),
        image_browser=image_browser if isinstance(image_browser, bool) else None,
        uptime_seconds=_number(raw.get("uptime_seconds")),
        checked_at=scrub(raw.get("checked_at"), 64),
        components=components,
        config=_config(raw.get("config"), scrub),
    )


def _bucket_minutes(value: Any) -> Optional[int]:
    minutes = _count(value)
    return minutes if minutes is not None and 0 < minutes <= 7 * 24 * 60 else None


def parse_history(raw: Any, scrub) -> Optional[TalonHistoryData]:
    if not isinstance(raw, dict):
        return None
    components: Dict[str, List[TalonHistoryBucket]] = {}
    for component_id, buckets in _dict(raw.get("components")).items():
        if len(components) >= MAX_COMPONENTS:
            break
        if not isinstance(component_id, str) or not COMPONENT_ID.fullmatch(component_id) or not isinstance(buckets, list):
            continue
        rows = []
        for bucket in buckets[:MAX_BUCKETS]:
            t = scrub(bucket.get("t"), 64) if isinstance(bucket, dict) else None
            if t is not None:
                rows.append(
                    TalonHistoryBucket(t=t, ok=_count(bucket.get("ok")), warn=_count(bucket.get("warn")), fail=_count(bucket.get("fail"))),
                )
        components[component_id] = rows
    return TalonHistoryData(bucket_minutes=_bucket_minutes(raw.get("bucket_minutes")), components=components)


def parse_metrics(raw: Any, scrub) -> Optional[TalonMetricsData]:
    if not isinstance(raw, dict):
        return None
    series = []
    for bucket in raw.get("series")[:MAX_BUCKETS] if isinstance(raw.get("series"), list) else []:
        t = scrub(bucket.get("t"), 64) if isinstance(bucket, dict) else None
        if t is None:
            continue
        values = {name: _number(bucket.get(name)) for name in METRIC_FIELDS}
        series.append(TalonMetricsBucket(t=t, cost_usd=_amount(bucket.get("cost_usd")), **values))
    return TalonMetricsData(bucket_minutes=_bucket_minutes(raw.get("bucket_minutes")), series=series)


# ── asking Talon ──────────────────────────────────────────────────────────────


@dataclass
class Upstream:
    """Everything CoPilot learnt from Talon in one go: what the cache keeps (unscoped)."""

    reachable: TalonProbe
    auth: TalonProbe
    health: TalonHealthSection
    history: TalonHistorySection
    metrics: TalonMetricsSection
    checked_at: datetime = field(default_factory=lambda: now_utc())


def _json(probe: Probe) -> Tuple[Any, Optional[str]]:
    try:
        return json.loads(probe.body), None
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        return None, NOT_JSON


def _section(probe: Probe, parse, section_cls, scrub):
    status = probe.status
    if status is None or (probe.error and 200 <= status < 300):
        return section_cls(error=probe.error, status_code=status)
    if status == 404:
        return section_cls(error=OLD_TALON, status_code=404, unsupported=True)
    if status == 401:
        return section_cls(error=KEY_REFUSED, status_code=401)
    if not 200 <= status < 300:
        return section_cls(error=f"Talon answered {status}", status_code=status)
    raw, problem = _json(probe)
    if problem:
        return section_cls(error=problem, status_code=status)
    data = parse(raw, scrub)
    if data is None:
        return section_cls(error=WRONG_SHAPE, status_code=status)
    return section_cls(data=data, status_code=status)


def _reachable(probe: Probe) -> TalonProbe:
    if probe.status is None:
        return TalonProbe(ok=False, error=probe.error)
    if 200 <= probe.status < 300:
        return TalonProbe(ok=True, latency_ms=probe.latency_ms, status_code=probe.status)
    return TalonProbe(ok=False, latency_ms=probe.latency_ms, status_code=probe.status, error=f"Talon's /health answered {probe.status}")


def _auth_from(probe: Probe) -> Optional[TalonProbe]:
    """A verdict on the key from one authenticated answer, or None when it can't tell."""
    if probe.status is not None and 200 <= probe.status < 300:
        return TalonProbe(ok=True, status_code=probe.status)
    if probe.status == 401:
        return TalonProbe(ok=False, status_code=401, error=KEY_REFUSED)
    return None


async def _ask_talon(url: str, api_key: str, hours: int, scrub) -> Upstream:
    async def keyed(path: str, cap: int) -> Probe:
        return await health_client.get(url, path, api_key=api_key, max_body_bytes=cap)

    alive, health, history, metrics = await asyncio.gather(
        health_client.get(url, "/health", api_key=None, max_body_bytes=MAX_PROBE_BYTES),
        keyed("/v2/health", MAX_HEALTH_BYTES),
        keyed(f"/v2/health/history?hours={hours}", MAX_SERIES_BYTES),
        keyed(f"/v2/health/metrics?hours={hours}", MAX_SERIES_BYTES),
    )
    auth = _auth_from(health)
    if auth is None and health.status is not None:
        # No verdict from /v2/health (an older Talon's 404, a 5xx): ask a route every Talon has
        # always authenticated, read-only and small.
        templates = await keyed("/templates", MAX_PROBE_BYTES)
        auth = _auth_from(templates) or TalonProbe(
            ok=None,
            status_code=templates.status,
            error=templates.error or (f"Talon answered {templates.status}" if templates.status else None),
        )
    if auth is None:
        auth = TalonProbe(ok=None, error=health.error)
    return Upstream(
        reachable=_reachable(alive),
        auth=auth,
        health=_section(health, parse_health, TalonHealthSection, scrub),
        history=_section(history, parse_history, TalonHistorySection, scrub),
        metrics=_section(metrics, parse_metrics, TalonMetricsSection, scrub),
    )


def _not_asked(reason: str) -> Upstream:
    return Upstream(
        reachable=TalonProbe(ok=None, error=reason),
        auth=TalonProbe(ok=None, error=reason),
        health=TalonHealthSection(error=reason),
        history=TalonHistorySection(error=reason),
        metrics=TalonMetricsSection(error=reason),
    )


_CACHE: Dict[Tuple[str, int], Tuple[float, Upstream]] = {}
_LOCKS: Dict[Tuple[str, int], asyncio.Lock] = {}


def clear_cache() -> None:
    _CACHE.clear()
    _LOCKS.clear()


def _cache_key(attributes: Mapping[str, Any], hours: int) -> Tuple[str, int]:
    """Per ``hours`` and per connector state: a changed URL, key or save is a different entry, so
    an admin's fix shows at once. A digest, so the key itself isn't held in the dict's keys."""
    material = "\x00".join(
        str(attributes.get(name) or "") for name in ("connector_name", "connector_url", "connector_api_key", "connector_last_updated")
    )
    return hashlib.sha256(material.encode()).hexdigest(), hours


async def _upstream(attributes: Optional[Mapping[str, Any]], hours: int) -> Upstream:
    if attributes is None:
        return _not_asked(NO_CONNECTOR)
    url = strip_url(attributes.get("connector_url"))
    if not url:
        return _not_asked(NOT_CONFIGURED)
    key = _cache_key(attributes, hours)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] > time.monotonic():
        return cached[1]
    lock = _LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _CACHE.get(key)
        if cached is not None and cached[0] > time.monotonic():
            return cached[1]
        api_key = str(attributes.get("connector_api_key") or "")
        # Asked at the stripped URL: Talon authenticates by the API key alone, and a stored query
        # or fragment would swallow the path.
        upstream = await _ask_talon(url, api_key, hours, make_scrub([api_key]))
        for stale in [k for k, (expires, _) in _CACHE.items() if expires <= time.monotonic()]:
            _CACHE.pop(stale, None)
        _CACHE[key] = (time.monotonic() + CACHE_SECONDS, upstream)
        return upstream


# ── CoPilot's own tables, scoped to the caller ────────────────────────────────


def _naive_utc_now() -> datetime:
    return now_utc().astimezone(timezone.utc).replace(tzinfo=None)


def _scoped(column, customers: Optional[List[str]]):
    """``None``: every customer (an admin); otherwise only ``customers``."""
    return true() if customers is None else column.in_(customers)


async def _copilot_tables(session: AsyncSession, customers: Optional[List[str]]) -> Dict[str, Any]:
    if customers is not None and not customers:
        return {}
    sent = (
        (
            await session.execute(
                select(TalonInvestigationTrigger)
                .where(_scoped(TalonInvestigationTrigger.customer_code, customers))
                .order_by(TalonInvestigationTrigger.sent_at.desc(), TalonInvestigationTrigger.id.desc())
                .limit(1),
            )
        )
        .scalars()
        .first()
    )
    job = (
        (
            await session.execute(
                select(AiAnalystJob)
                .where(_scoped(AiAnalystJob.customer_code, customers))
                .order_by(AiAnalystJob.created_at.desc())
                .limit(1),
            )
        )
        .scalars()
        .first()
    )
    report = (
        (
            await session.execute(
                select(AiAnalystReport)
                .where(_scoped(AiAnalystReport.customer_code, customers))
                .order_by(AiAnalystReport.created_at.desc())
                .limit(1),
            )
        )
        .scalars()
        .first()
    )
    since = _naive_utc_now() - timedelta(hours=24)
    failed = await session.scalar(
        select(func.count())
        .select_from(AiAnalystJob)
        .where(
            _scoped(AiAnalystJob.customer_code, customers),
            AiAnalystJob.status == "failed",
            or_(AiAnalystJob.completed_at >= since, and_(AiAnalystJob.completed_at.is_(None), AiAnalystJob.created_at >= since)),
        ),
    )
    triggers = await session.scalar(
        select(func.count())
        .select_from(AIAnalystTriggerEnabled)
        .where(_scoped(AIAnalystTriggerEnabled.customer_code, customers), AIAnalystTriggerEnabled.enabled.is_(True)),
    )
    return {
        "last_sent": TalonJobSummary(customer_code=sent.customer_code, status=sent.source, at=sent.sent_at) if sent else None,
        "last_job": TalonJobSummary(customer_code=job.customer_code, status=job.status, at=job.created_at) if job else None,
        "last_report": TalonJobSummary(customer_code=report.customer_code, at=report.created_at) if report else None,
        "jobs_failed_24h": int(failed or 0),
        "ai_trigger_customers": int(triggers or 0),
    }


def _connector_state(attributes: Optional[Mapping[str, Any]]) -> TalonConnectorState:
    if attributes is None:
        return TalonConnectorState(exists=False)
    url = strip_url(attributes.get("connector_url"))
    return TalonConnectorState(
        exists=True,
        configured=bool(url) and bool(attributes.get("connector_configured", True)),
        verified=bool(attributes.get("connector_verified")),
        url=url,
    )


def _scoped_health(section: TalonHealthSection, customers: Optional[List[str]]) -> TalonHealthSection:
    """A copy of the cached section with ``live_customers`` cut to the caller's customers."""
    if customers is None or section.data is None or section.data.config is None:
        return section
    allowed = set(customers)
    config = section.data.config.model_copy(update={"live_customers": [c for c in section.data.config.live_customers if c in allowed]})
    return section.model_copy(update={"data": section.data.model_copy(update={"config": config})})


async def get_talon_health(
    user: User,
    session: AsyncSession,
    hours: int = DEFAULT_HOURS,
    connector_name: str = TALON_CONNECTOR,
) -> TalonHealthResponse:
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    admin = user.role_id == RoleEnum.admin or "*" in accessible
    customers: Optional[List[str]] = None if admin else [c for c in accessible if c != "*"]

    attributes = await get_connector_info_from_db(connector_name, session)
    v2_enabled = await is_v2_enabled(session, connector_name)
    tables = await _copilot_tables(session, customers)
    # Everything from the database has been read: no pooled connection waits on Talon.
    await session.close()

    upstream = await _upstream(attributes, hours)
    copilot = TalonCopilotView(
        connector=_connector_state(attributes),
        reachable=upstream.reachable,
        auth=upstream.auth,
        v2_enabled=v2_enabled,
        scope="deployment" if admin else "assigned",
        **tables,
    )
    logger.debug(f"Talon health for user {user.id}: reachable={upstream.reachable.ok} auth={upstream.auth.ok}")
    return TalonHealthResponse(
        success=True,
        message="Talon health retrieved",
        hours=hours,
        checked_at=upstream.checked_at,
        copilot=copilot,
        health=_scoped_health(upstream.health, customers),
        history=upstream.history,
        metrics=upstream.metrics,
    )
