"""A tick of the weekly Sysmon noise statistics, an admin's Send now, and the preview. None of them ever raises.

A tick (every 6 hours, the ``send_sysmon_stats`` job):

1. SYSMON_STATS_SHARING off: nothing at all (no database lock, no indexer query, no request).
2. One run per process (``_RUN_LOCK``: a Send now or a preview may be running) and one per deployment (a MySQL named
   lock: only one replica sends).
3. Short database reads (license key, customers, settings rows, the report secret), whose transaction ends before any
   network call; then the MinIO state and the queued withdraws, which go first.
4. The pause (a report SOCFortress refused for its content) stops reports until the CoPilot version changes or an
   admin resumes them.
5. The target week is the previous complete ISO week (UTC). A customer is due unless opted out, withdrawn less than
   180 s ago, already done for the week, waiting out a Retry-After, or before its jittered send time.
6. Nothing due: stop (no probe, no indexer). Else the unauthenticated probe: SOCFortress answering "reports are not
   enabled" is a quiet state, not an error (no indexer query, no audit row, one INFO line when it changes).
7. Indexer: field discovery and the labels once, then per due customer (at most N, by due time, within the tick's
   deadline) stage 1 and 2, the redaction context (its agents' host names, a short read), the report, a fresh opt-out
   check, the POST, the state, an audit row and one log line. A 200 is followed by another opt-out check: a customer
   opted out meanwhile is withdrawn again.
"""
import asyncio
import re
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from fastapi import Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_stats import TERMINAL_OUTCOMES
from app.active_response.schema.sysmon_stats import StatsCustomerRun
from app.active_response.schema.sysmon_stats import StatsLastTick
from app.active_response.schema.sysmon_stats import StatsLatch
from app.active_response.schema.sysmon_stats import StatsOutcome
from app.active_response.schema.sysmon_stats import StatsPreview
from app.active_response.schema.sysmon_stats import StatsPreviewLocal
from app.active_response.schema.sysmon_stats import StatsRelease
from app.active_response.schema.sysmon_stats import StatsRunResult
from app.active_response.schema.sysmon_stats import StatsState
from app.active_response.schema.sysmon_stats import StatsWeekState
from app.active_response.schema.sysmon_stats import StatsWouldSend
from app.active_response.services.sysmon_default_sync import _parse_utc
from app.active_response.services.sysmon_default_sync import _utc_text
from app.active_response.services.sysmon_default_sync import key_fingerprint
from app.active_response.services.sysmon_default_sync import read_applied
from app.active_response.services.sysmon_stats import client as http
from app.active_response.services.sysmon_stats import collector
from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats import sharing
from app.active_response.services.sysmon_stats import state as store
from app.active_response.services.sysmon_stats.config_state import config_value
from app.active_response.services.sysmon_stats.identity import customer_pseudonym
from app.active_response.services.sysmon_stats.identity import due_time
from app.active_response.services.sysmon_stats.identity import load_secret
from app.active_response.services.sysmon_stats.identity import week_label
from app.active_response.services.sysmon_stats.redaction import build_context
from app.active_response.services.sysmon_stats.redaction import user_values
from app.active_response.services.sysmon_stats.report import BuiltReport
from app.active_response.services.sysmon_stats.report import LocalRefusal
from app.active_response.services.sysmon_stats.report import build_report
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.data_store.data_store_operations import download_sysmon_config
from app.db import named_lock
from app.db.universal_models import Agents
from app.db.universal_models import Customers
from app.db.universal_models import SysmonStatsCustomerSettings
from app.middleware.license import get_license
from app.version.services.version import CURRENT_VERSION

LOCK_PREFIX = "copilot.sysmon_stats:"
SYSTEM_ACTOR = "system"
# Send now and the preview never wait behind a tick, and a tick never runs while either does
_RUN_LOCK = asyncio.Lock()
_monotonic: Callable[[], float] = time.monotonic


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def target_week(now: datetime) -> Tuple[str, date]:
    """The previous complete ISO week (UTC): its label and Monday."""
    today = now.astimezone(timezone.utc).date()
    monday = today - timedelta(days=today.weekday()) - timedelta(days=7)
    return week_label(monday), monday


def accepted_weeks(now: datetime) -> Dict[str, date]:
    """The two weeks SOCFortress accepts: the previous complete week and the one before it."""
    label, monday = target_week(now)
    older = monday - timedelta(days=7)
    return {label: monday, week_label(older): older}


async def make_indexer_client():
    from app.connectors.wazuh_indexer.utils.universal import (
        create_wazuh_indexer_client_async,
    )

    return await create_wazuh_indexer_client_async()


def running() -> bool:
    """Whether a tick, a Send now or a preview runs in this process. Nothing is awaited between this test and taking the
    lock."""
    return _RUN_LOCK.locked()


async def _end(session: Optional[AsyncSession]) -> None:
    """End the session's read transaction, so no pooled connection stays checked out across a network call."""
    if session is None:
        return
    try:
        await session.rollback()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Sysmon stats: could not end a database read's transaction ({type(e).__name__})")


@dataclass
class CustomerRow:
    code: str
    name: Optional[str]
    sharing: bool = True
    install_dir_name: Optional[str] = None
    own_domains: List[str] = field(default_factory=list)
    withdrawn_at: Optional[datetime] = None


async def read_customers(session: AsyncSession) -> Dict[str, CustomerRow]:
    rows = (await session.execute(select(Customers.customer_code, Customers.customer_name))).all()
    customers = {code: CustomerRow(code=code, name=name) for code, name in rows if code}
    for row in (await session.execute(select(SysmonStatsCustomerSettings))).scalars().all():
        c = customers.get(row.customer_code)
        if c is None:
            continue
        c.sharing = bool(row.sharing_enabled)
        c.install_dir_name = row.install_dir_name
        c.own_domains = list(row.own_domains or [])
        c.withdrawn_at = row.withdrawn_at
    return customers


async def read_setting(session: AsyncSession, code: str) -> Optional[SysmonStatsCustomerSettings]:
    return (
        (await session.execute(select(SysmonStatsCustomerSettings).where(SysmonStatsCustomerSettings.customer_code == code)))
        .scalars()
        .first()
    )


async def _still_sharing(session: AsyncSession, code: str) -> bool:
    """A fresh read of the customer's opt-out and of the kill switch, right before a POST."""
    if not settings.sharing_on():
        return False
    try:
        row = await read_setting(session, code)
        # Read before the transaction ends: ending it expires the row
        sharing_enabled = True if row is None else bool(row.sharing_enabled)
    finally:
        await _end(session)
    return sharing_enabled


async def _hostnames(session: AsyncSession, code: str) -> List[str]:
    try:
        rows = (await session.execute(select(Agents.hostname).where(Agents.customer_code == code))).all()
    finally:
        await _end(session)
    return [h for (h,) in rows if isinstance(h, str)]


def _releases(state: StatsState, applied) -> Dict[int, Tuple[str, Optional[str]]]:
    if applied is not None:
        state.releases[str(applied.sequence)] = StatsRelease(
            content_sha256=applied.content_sha256,
            content_sha256_crlf=applied.content_sha256_crlf,
        )
    out: Dict[int, Tuple[str, Optional[str]]] = {}
    for key, release in state.releases.items():
        if key.isdigit():
            out[int(key)] = (release.content_sha256, release.content_sha256_crlf)
    return out


async def _stored_config(code: str) -> Optional[bytes]:
    try:
        return await download_sysmon_config(code)
    except Exception:  # noqa: BLE001 - no stored config: "unknown"
        return None


def _discovered_install_dirs(stored: Optional[bytes], template: Optional[bytes]) -> List[str]:
    r"""Install folders found in the customer's stored config: for each \Program Files\__INSTALLDIRNAME__\<segment>\ of the
    default template, the folder the customer's config has in its place."""
    if not stored or not template:
        return []
    try:
        text, templ = stored.decode("utf-8"), template.decode("utf-8")
    except UnicodeDecodeError:
        return []
    segments = set(re.findall(r"\\Program Files\\__INSTALLDIRNAME__\\([A-Za-z0-9._ -]{1,64})\\", templ))
    found: List[str] = []
    for segment in sorted(segments)[:20]:
        for m in re.finditer(r"(?i)\\Program Files\\([A-Za-z0-9._-]{1,64})\\" + re.escape(segment) + r"\\", text):
            if m.group(1) not in found and m.group(1) != "__INSTALLDIRNAME__":
                found.append(m.group(1))
    return found[:5]


async def _template() -> Optional[bytes]:
    from app.data_store.data_store_operations import read_default_sysmon_config

    try:
        return await read_default_sysmon_config()
    except Exception:  # noqa: BLE001
        return None


@dataclass
class Prepared:
    """One customer's report, ready to send (or why there is none)."""

    built: Optional[BuiltReport] = None
    outcome: Optional[StatsOutcome] = None
    message: Optional[str] = None
    config: Any = None
    endpoints: int = 0


async def prepare_customer(
    session: AsyncSession,
    client: Any,
    index: str,
    maps,
    labels: Dict[str, List[str]],
    customer: CustomerRow,
    secret: bytes,
    week: str,
    monday: date,
    releases: Dict[int, Tuple[str, Optional[str]]],
    template: Optional[bytes],
    today: date,
) -> Prepared:
    """Collect, redact and build one customer's report. Indexer failures are outcomes."""
    level_max, min_endpoints, timeout = settings.max_rule_level(), settings.min_endpoints(), settings.query_timeout()
    try:
        async with asyncio.timeout(settings.CUSTOMER_DEADLINE):
            collection = await collector.collect_customer(client, index, maps, labels, monday, level_max, min_endpoints, timeout)
    except (collector.IndexerTimeout, TimeoutError):
        return Prepared(
            outcome=StatsOutcome.INDEXER_TIMEOUT,
            message="An indexer search did not finish in time; the next tick tries again.",
        )
    except collector.IndexerFailure as e:
        return Prepared(outcome=StatsOutcome.INDEXER_ERROR, message=f"An indexer search failed ({e}); the next tick tries again.")
    if collection.endpoints < 1:
        return Prepared(outcome=StatsOutcome.NO_SYSMON_EVENTS, message="No Sysmon events from this customer's agents that week.")
    stored = await _stored_config(customer.code)
    install_dirs = [d for d in [customer.install_dir_name] if d] + _discovered_install_dirs(stored, template)
    config = config_value(stored, releases, install_dirs + [customer.code])
    hostnames = await _hostnames(session, customer.code)
    ctx = build_context(
        customer_code=customer.code,
        customer_name=customer.name,
        install_dirs=install_dirs,
        own_domains=customer.own_domains,
        hostnames=hostnames,
        accounts=user_values(collection.patterns),
    )
    try:
        built = build_report(
            customer=customer_pseudonym(secret, customer.code),
            week=week,
            config=config,
            endpoints=collection.endpoints,
            raw_patterns=collection.patterns,
            ctx=ctx,
            min_endpoints=min_endpoints,
            pairs_left_out=collection.pairs_left_out,
            cut_tails=collection.cut_tails,
            today=today,
        )
    except LocalRefusal as e:
        logger.error(
            f"Sysmon stats: {customer.code} {week}: CoPilot's own report failed the contract check ({e.reason}, {e.problems[:20]}); not sent",
        )
        return Prepared(
            outcome=StatsOutcome.LOCAL_REFUSED,
            message=f"CoPilot's report failed the contract check ({e.reason}): not sent.",
            config=config,
        )
    return Prepared(built=built, config=config, endpoints=collection.endpoints)


def _week_state(
    previous: Optional[StatsWeekState],
    outcome: StatsOutcome,
    message: str,
    now: datetime,
    **kw,
) -> StatsWeekState:
    attempts = (previous.attempts if previous else 0) + (1 if kw.pop("attempted", False) else 0)
    return StatsWeekState(
        status="terminal" if outcome in TERMINAL_OUTCOMES else "pending",
        outcome=outcome,
        message=message,
        attempts=attempts,
        last_attempt_at=_utc_text(now),
        **kw,
    )


async def _audit_send(
    *,
    code: str,
    week: str,
    pseudonym: str,
    built: BuiltReport,
    config: Any,
    result: http.ReportResult,
    base: str,
    actor,
    request: Optional[Request],
) -> None:
    if result.outcome is StatsOutcome.SENT:
        outcome = AuditResult.SUCCESS
    elif result.uncertain:
        outcome = AuditResult.UNKNOWN
    else:
        outcome = AuditResult.FAILURE
    await record_audit_event(
        action=AuditAction.SYSMON_STATS_SEND,
        actor_user_id=getattr(actor, "id", None),
        actor_username=getattr(actor, "username", None) or SYSTEM_ACTOR,
        customer_code=code,
        entity_type="sysmon_stats_report",
        entity_id=f"{week}/{pseudonym}",
        result=outcome,
        new_value={
            "week": week,
            "customer_pseudonym": pseudonym,
            "payload_sha256": built.sha256,
            "payload_bytes": len(built.payload),
            "patterns": len(built.doc["patterns"]),
            "truncated": built.doc["truncated"],
            "endpoints": built.doc["endpoints"],
            "config": config,
            "http_status": result.http_status,
            "outcome": result.outcome.value,
            "reason": result.reason,
            "accepted": result.accepted,
            "rejected": result.rejected,
            "rejected_by_reason": result.rejected_by_reason,
            "replaced": result.replaced,
            "service_url": base,
        },
        details="Send now" if actor is not None else f"Scheduled send ({settings.JOB_ID})",
        request=request,
    )


@dataclass
class _Run:
    """What one run needs once its database reads are done."""

    license_key: str
    fingerprint: str
    base: str
    secret: bytes
    customers: Dict[str, CustomerRow]
    state: StatsState
    releases: Dict[int, Tuple[str, Optional[str]]]
    queued: List[str]


def _log_send(fp: str, code: str, week: str, result: http.ReportResult, built: Optional[BuiltReport]) -> None:
    patterns = len(built.doc["patterns"]) if built else 0
    sha = built.sha256[:12] if built else "-"
    line = (
        f"Sysmon stats (license {fp}): {code} {week} {result.outcome.value} http={result.http_status} patterns={patterns} "
        f"accepted={result.accepted} rejected={result.rejected} sha256={sha}"
    )
    if result.outcome is StatsOutcome.REFUSED:
        line += f" reason={result.reason} problems={result.problems[:20]}"
        logger.error(line)
    elif result.outcome is StatsOutcome.SENT and result.rejected:
        logger.warning(line + f" rejected_by_reason={result.rejected_by_reason} (CoPilot's copy of the rules has drifted)")
    elif result.outcome in (StatsOutcome.SENT, StatsOutcome.WITHDRAWN):
        logger.info(line)
    else:
        logger.warning(line)


async def _read_run(session: AsyncSession) -> Tuple[Optional[_Run], Optional[StatsOutcome], str]:
    base = settings.base_url()
    url, url_error = settings.endpoint_url(base, settings.REPORT_PATH)
    try:
        license_row = await get_license(session, raise_on_missing=False)
        license_key = (getattr(license_row, "license_key", None) or "").strip()
        customers = await read_customers(session)
        secret = await load_secret(session, create=True) if license_key else None
    finally:
        await _end(session)
    if url is None:
        return None, StatsOutcome.INVALID_URL, f"{url_error} Nothing was sent."
    if not license_key:
        return None, StatsOutcome.NO_LICENSE, "This CoPilot has no license, which SOCFortress requires. Nothing was sent."
    if secret is None:
        return None, StatsOutcome.ERROR, "This CoPilot's report secret could not be read. Nothing was sent."
    state = await store.read_state()
    try:
        applied = await read_applied()
    except Exception:  # noqa: BLE001 - only the "config" field needs it
        applied = None
    releases = _releases(state, applied)
    queued = await store.list_withdraws()
    return (
        _Run(
            license_key=license_key,
            fingerprint=key_fingerprint(license_key),
            base=base,
            secret=secret,
            customers=customers,
            state=state,
            releases=releases,
            queued=queued,
        ),
        None,
        "",
    )


def _service_waiting(state: StatsState, now: datetime) -> Optional[datetime]:
    moment = _parse_utc(state.service.not_before)
    return moment if moment is not None and moment > now else None


def _due(
    run: _Run,
    customer: CustomerRow,
    week: str,
    monday: date,
    now: datetime,
    ignore_jitter: bool,
) -> Tuple[bool, Optional[str]]:
    if not customer.sharing:
        return False, "opted out"
    if customer.withdrawn_at is not None and _naive(now) < customer.withdrawn_at + timedelta(seconds=settings.REOPTIN_DELAY):
        return False, "withdrawn less than 3 minutes ago"
    if customer_pseudonym(run.secret, customer.code) in run.queued:
        return False, "a withdraw is still queued"
    previous = run.state.weeks.get(week, {}).get(customer.code)
    if previous is not None and previous.status == "terminal":
        return False, f"already done for {week} ({previous.outcome.value})"
    waiting = _parse_utc(previous.not_before) if previous else None
    if waiting is not None and waiting > now:
        return False, f"waiting until {_utc_text(waiting)}"
    if not ignore_jitter and due_time(run.secret, customer.code, week, monday) > now:
        return False, "not due yet"
    return True, None


async def run_tick(
    session: AsyncSession,
    *,
    now: Optional[datetime] = None,
    actor=None,
    request: Optional[Request] = None,
    customer_code: Optional[str] = None,
    ignore_jitter: bool = False,
    resume: bool = False,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> StatsRunResult:
    """One tick (``actor`` None) or an admin's Send now (jitter ignored, optionally one customer). Never raises."""
    mode, _ = settings.sharing_mode()
    if mode.value != "on":
        return StatsRunResult(
            outcome=StatsOutcome.SHARING_OFF,
            message="Noise statistics are off on this CoPilot (SYSMON_STATS_SHARING). Nothing was sent.",
        )
    if _RUN_LOCK.locked():
        return StatsRunResult(outcome=StatsOutcome.RUNNING, message="A run is already in progress on this CoPilot.")
    async with _RUN_LOCK:
        try:
            async with named_lock.mysql_named_lock(LOCK_PREFIX, "Sysmon stats") as held:
                if not held:
                    return StatsRunResult(outcome=StatsOutcome.LOCKED, message="Another CoPilot replica is sending; nothing was done here.")
                return await _locked_run(session, now or _now(), actor, request, customer_code, ignore_jitter, resume, transport)
        except Exception as e:  # noqa: BLE001 - a run never raises into the scheduler or a route
            logger.error(f"Sysmon stats: the run failed ({type(e).__name__})")
            return StatsRunResult(outcome=StatsOutcome.ERROR, message=f"The run failed ({type(e).__name__}).")


async def _locked_run(
    session: AsyncSession,
    now: datetime,
    actor,
    request: Optional[Request],
    only: Optional[str],
    ignore_jitter: bool,
    resume: bool,
    transport: Optional[httpx.AsyncBaseTransport],
) -> StatsRunResult:
    started = _monotonic()
    week, monday = target_week(now)
    run, outcome, message = await _read_run(session)
    if run is None:
        return StatsRunResult(outcome=outcome, message=message, week=week)
    state = run.state
    tick = StatsLastTick(started_at=_utc_text(now), week=week)
    result = await _run_body(session, run, now, started, week, monday, actor, request, only, ignore_jitter, resume, transport, tick)
    tick.finished_at = _utc_text(now + timedelta(seconds=max(0.0, _monotonic() - started)))
    tick.outcome = result.outcome
    tick.message = result.message
    state.last_tick = tick
    try:
        await store.write_state(state)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Sysmon stats: could not record the run in its state ({type(e).__name__})")
    return result


async def _run_body(
    session: AsyncSession,
    run: _Run,
    now: datetime,
    started: float,
    week: str,
    monday: date,
    actor,
    request: Optional[Request],
    only: Optional[str],
    ignore_jitter: bool,
    resume: bool,
    transport: Optional[httpx.AsyncBaseTransport],
    tick: StatsLastTick,
) -> StatsRunResult:
    state = run.state
    waiting = _service_waiting(state, now)
    if waiting is not None:
        return StatsRunResult(
            outcome=StatsOutcome.RATE_LIMITED,
            message=f"SOCFortress asked to wait until {_utc_text(waiting)}.",
            week=week,
        )

    # Withdraws first: an opt-out's deletion never waits behind a report
    await sharing.process_withdraw_queue(session, run.license_key, run.base, run.queued, transport=transport, state=state, now=now)
    run.queued = await store.list_withdraws()
    if _service_waiting(state, now) is not None:
        return StatsRunResult(outcome=StatsOutcome.RATE_LIMITED, message="SOCFortress asked to wait.", week=week)

    if state.latch is not None:
        if resume:
            await record_audit_event(
                action=AuditAction.SYSMON_STATS_RESUME,
                actor_user_id=getattr(actor, "id", None),
                actor_username=getattr(actor, "username", None) or SYSTEM_ACTOR,
                entity_type="sysmon_stats",
                entity_id="latch",
                old_value={"latch_reason": state.latch.reason},
                request=request,
            )
            state.latch = None
        elif state.latch.copilot_version != CURRENT_VERSION:
            logger.info("Sysmon stats: CoPilot was updated since SOCFortress refused a report; reports resume")
            state.latch = None
        else:
            return StatsRunResult(
                outcome=StatsOutcome.LATCHED,
                message=f"Reports are paused: SOCFortress refused one ({state.latch.reason}). Update CoPilot, or resume.",
                week=week,
            )

    due: List[Tuple[datetime, CustomerRow]] = []
    for code, customer in sorted(run.customers.items()):
        if only is not None and code != only:
            continue
        ok, _ = _due(run, customer, week, monday, now, ignore_jitter)
        if ok:
            due.append((due_time(run.secret, code, week, monday), customer))
    if not due:
        return StatsRunResult(outcome=StatsOutcome.NOTHING_DUE, message=f"No customer's {week} report is due.", week=week)
    due.sort(key=lambda item: (item[0], item[1].code))

    verdict = await http.probe(run.base, transport)
    previous_accepting = state.service.accepting
    state.service.checked_at = _utc_text(now)
    if verdict == http.Probe.NOT_ACCEPTING:
        state.service.accepting = False
        state.service.last_status = 404
        line = "Sysmon stats: SOCFortress is not accepting noise reports yet; the next tick asks again"
        if previous_accepting is not False:
            logger.info(line)
        else:
            logger.debug(line)
        return StatsRunResult(
            outcome=StatsOutcome.SERVICE_NOT_ACCEPTING,
            message="SOCFortress is not accepting noise reports yet.",
            week=week,
        )
    if verdict == http.Probe.ACCEPTING:
        if previous_accepting is False:
            logger.info("Sysmon stats: SOCFortress accepts noise reports now")
        state.service.accepting = True
        state.service.last_status = 401

    try:
        client = await make_indexer_client()
    except Exception as e:  # noqa: BLE001
        return StatsRunResult(
            outcome=StatsOutcome.INDEXER_UNREACHABLE,
            message=f"The Wazuh indexer client could not be created ({type(e).__name__}).",
            week=week,
        )
    runs: List[StatsCustomerRun] = []
    try:
        return await _collect_and_send(session, client, run, now, started, week, monday, due, actor, request, transport, tick, runs)
    finally:
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            pass


async def _collect_and_send(
    session: AsyncSession,
    client: Any,
    run: _Run,
    now: datetime,
    started: float,
    week: str,
    monday: date,
    due: List[Tuple[datetime, CustomerRow]],
    actor,
    request: Optional[Request],
    transport: Optional[httpx.AsyncBaseTransport],
    tick: StatsLastTick,
    runs: List[StatsCustomerRun],
) -> StatsRunResult:
    state = run.state
    index, timeout = settings.index_pattern(), settings.query_timeout()
    try:
        maps = await collector.discover_fields(client, index)
        if not maps:
            return StatsRunResult(
                outcome=StatsOutcome.INDEXER_FIELDS_UNAVAILABLE,
                message="The Wazuh indexer maps no usable Sysmon fields (customer label, agent, rule level, event ID, channel, time).",
                week=week,
            )
        labels_by_shape, _ = await collector.stage0(client, index, maps, monday, timeout)
    except collector.IndexerUnreachable as e:
        return StatsRunResult(outcome=StatsOutcome.INDEXER_UNREACHABLE, message=f"The Wazuh indexer cannot be reached ({e}).", week=week)
    except (collector.IndexerTimeout, collector.IndexerFailure) as e:
        return StatsRunResult(
            outcome=StatsOutcome.INDEXER_ERROR,
            message=f"The Wazuh indexer's labels could not be read ({type(e).__name__}).",
            week=week,
        )
    labels = collector.map_labels(labels_by_shape, list(run.customers))
    template = await _template()
    week_states = state.weeks.setdefault(week, {})
    waf_streak = 0
    stop_outcome: Optional[StatsOutcome] = None
    stop_message = ""
    processed = 0
    remaining = list(due)
    while remaining:
        _, customer = remaining.pop(0)
        code = customer.code
        if processed >= settings.max_customers_per_tick() or _monotonic() - started >= settings.TICK_DEADLINE:
            break
        previous = week_states.get(code)
        if code in labels.ambiguous:
            week_states[code] = _week_state(
                previous,
                StatsOutcome.AMBIGUOUS_LABEL,
                "Another customer's code differs from this one only in case: not reported.",
                now,
            )
            runs.append(StatsCustomerRun(customer_code=code, outcome=StatsOutcome.AMBIGUOUS_LABEL))
            continue
        customer_labels = labels.by_customer.get(code)
        if not customer_labels:
            week_states[code] = _week_state(
                previous,
                StatsOutcome.NO_SYSMON_EVENTS,
                "No Sysmon events with this customer's label that week.",
                now,
            )
            tick.terminal += 1
            runs.append(StatsCustomerRun(customer_code=code, outcome=StatsOutcome.NO_SYSMON_EVENTS))
            continue
        if not await _still_sharing(session, code):
            continue
        processed += 1
        try:
            prepared = await prepare_customer(
                session,
                client,
                index,
                maps,
                customer_labels,
                customer,
                run.secret,
                week,
                monday,
                run.releases,
                template,
                now.date(),
            )
        except collector.IndexerUnreachable as e:
            stop_outcome, stop_message = StatsOutcome.INDEXER_UNREACHABLE, f"The Wazuh indexer cannot be reached ({e})."
            week_states[code] = _week_state(previous, StatsOutcome.INDEXER_ERROR, stop_message, now)
            break
        if prepared.built is None:
            week_states[code] = _week_state(previous, prepared.outcome, prepared.message or "", now, config=prepared.config)
            runs.append(StatsCustomerRun(customer_code=code, outcome=prepared.outcome, message=prepared.message))
            if prepared.outcome in TERMINAL_OUTCOMES:
                tick.terminal += 1
            else:
                tick.pending += 1
            await _save(state)
            continue
        built = prepared.built
        # The opt-out and the kill switch once more, right before the POST
        if not await _still_sharing(session, code):
            continue
        pseudonym = built.doc["customer"]
        result = await http.post_report(run.base, built.payload, run.license_key, transport)
        if run.license_key in result.message:
            result.message = result.message.replace(run.license_key, f"[license key {run.fingerprint}]")
        if result.outcome is StatsOutcome.SERVICE_NOT_ACCEPTING:
            state.service.accepting = False
            state.service.last_status = 404
            stop_outcome, stop_message = result.outcome, result.message
            break
        await _audit_send(
            code=code,
            week=week,
            pseudonym=pseudonym,
            built=built,
            config=prepared.config,
            result=result,
            base=run.base,
            actor=actor,
            request=request,
        )
        _log_send(run.fingerprint, code, week, result, built)
        state.service.last_status = result.http_status
        if result.http_status is not None and result.http_status < 500 and result.http_status != 404:
            state.service.accepting = True
        not_before = None
        if result.customer_retry_seconds:
            not_before = _utc_text(now + timedelta(seconds=result.customer_retry_seconds))
        if result.service_retry_seconds:
            state.service.not_before = _utc_text(now + timedelta(seconds=result.service_retry_seconds))
        week_states[code] = _week_state(
            previous,
            result.outcome,
            result.message,
            now,
            attempted=True,
            not_before=not_before,
            http_status=result.http_status,
            reason=result.reason,
            sent_at=_utc_text(now) if result.outcome is StatsOutcome.SENT else None,
            payload_sha256=built.sha256,
            payload_bytes=len(built.payload),
            patterns=len(built.doc["patterns"]),
            truncated=built.doc["truncated"],
            endpoints=built.doc["endpoints"],
            config=prepared.config,
            accepted=result.accepted,
            rejected=result.rejected,
            rejected_by_reason=result.rejected_by_reason,
            replaced=result.replaced,
            local_drops=built.stats.dropped_by_reason,
        )
        runs.append(StatsCustomerRun(customer_code=code, outcome=result.outcome, message=result.message))
        if result.outcome is StatsOutcome.SENT:
            tick.sent += 1
        elif result.terminal:
            tick.terminal += 1
        else:
            tick.pending += 1
        if result.latch:
            state.latch = StatsLatch(set_at=_utc_text(now), reason=result.reason or "refused", copilot_version=CURRENT_VERSION)
        await _save(state)
        if result.outcome is StatsOutcome.SENT:
            # A customer opted out while its report was on its way: withdraw again (the service's rule)
            if not await _still_sharing(session, code) and settings.sharing_on():
                await sharing.queue_withdraw(pseudonym, code, now=now)
                await sharing.process_withdraw_queue(
                    session,
                    run.license_key,
                    run.base,
                    [pseudonym],
                    transport=transport,
                    state=state,
                    now=now,
                )
        waf_streak = waf_streak + 1 if result.outcome is StatsOutcome.WAF_REFUSED else 0
        if result.week_wide:
            for _, other in remaining:
                week_states[other.code] = _week_state(week_states.get(other.code), result.outcome, result.message, now)
            remaining = []
        if result.stop or waf_streak >= 2:
            stop_outcome, stop_message = result.outcome, result.message
            break
    await _save(state)
    if stop_outcome is not None:
        return StatsRunResult(outcome=stop_outcome, message=stop_message, week=week, customers=runs)
    sent = sum(1 for r in runs if r.outcome is StatsOutcome.SENT)
    message = f"{week}: {sent} report(s) sent, {len(runs) - sent} other outcome(s)."
    return StatsRunResult(outcome=StatsOutcome.COMPLETED if runs else StatsOutcome.NOTHING_DUE, message=message, week=week, customers=runs)


async def _save(state: StatsState) -> None:
    try:
        await store.write_state(state)
    except Exception as e:  # noqa: BLE001 - the next write tries again; the outcome is still returned
        logger.error(f"Sysmon stats: could not write its state ({type(e).__name__})")


# --------------------------------------------------------------------------------------------------------------------
# Preview
# --------------------------------------------------------------------------------------------------------------------


async def preview(session: AsyncSession, customer_code: str, week: Optional[str] = None, now: Optional[datetime] = None) -> StatsPreview:
    """Run the collector for one customer and return the exact report it would send. Sends nothing and writes no state.
    The caller checks the kill switch and the run lock first."""
    now = now or _now()
    started = _monotonic()
    weeks = accepted_weeks(now)
    target, _ = target_week(now)
    week = week or target
    monday = weeks[week]
    async with _RUN_LOCK:
        try:
            license_row = await get_license(session, raise_on_missing=False)
            license_key = (getattr(license_row, "license_key", None) or "").strip()
            customers = await read_customers(session)
            secret = await load_secret(session, create=True)
        finally:
            await _end(session)
        customer = customers.get(customer_code)
        pseudonym = customer_pseudonym(secret, customer_code) if secret else ""
        out = StatsPreview(week=week, customer_pseudonym=pseudonym, would_send=StatsWouldSend(ok=False))
        if customer is None or secret is None:
            out.outcome, out.message = StatsOutcome.ERROR, "Unknown customer, or no report secret."
            return out
        try:
            state = await store.read_state()
        except Exception:  # noqa: BLE001
            state = StatsState()
        try:
            applied = await read_applied()
        except Exception:  # noqa: BLE001
            applied = None
        releases = _releases(state, applied)
        queued = await _safe_list_withdraws()
        run = _Run(
            license_key,
            key_fingerprint(license_key) if license_key else "",
            settings.base_url(),
            secret,
            customers,
            state,
            releases,
            queued,
        )
        why = _why_not(run, customer, week, monday, now, license_key)
        out.would_send = StatsWouldSend(ok=why is None, why=why)
        try:
            client = await make_indexer_client()
        except Exception as e:  # noqa: BLE001
            out.outcome, out.message = (
                StatsOutcome.INDEXER_UNREACHABLE,
                f"The Wazuh indexer client could not be created ({type(e).__name__}).",
            )
            return out
        try:
            index, timeout = settings.index_pattern(), settings.query_timeout()
            try:
                maps = await collector.discover_fields(client, index)
                if not maps:
                    out.outcome, out.message = StatsOutcome.INDEXER_FIELDS_UNAVAILABLE, "The Wazuh indexer maps no usable Sysmon fields."
                    return out
                labels_by_shape, _ = await collector.stage0(client, index, maps, monday, timeout)
            except collector.IndexerUnreachable as e:
                out.outcome, out.message = StatsOutcome.INDEXER_UNREACHABLE, f"The Wazuh indexer cannot be reached ({e})."
                return out
            except (collector.IndexerTimeout, collector.IndexerFailure) as e:
                out.outcome, out.message = StatsOutcome.INDEXER_ERROR, f"The Wazuh indexer's labels could not be read ({type(e).__name__})."
                return out
            labels = collector.map_labels(labels_by_shape, list(customers))
            if customer_code in labels.ambiguous:
                out.outcome, out.message = StatsOutcome.AMBIGUOUS_LABEL, "Another customer's code differs from this one only in case."
                return out
            customer_labels = labels.by_customer.get(customer_code)
            if not customer_labels:
                out.outcome, out.message = StatsOutcome.NO_SYSMON_EVENTS, "No Sysmon events with this customer's label that week."
                return out
            try:
                prepared = await prepare_customer(
                    session,
                    client,
                    index,
                    maps,
                    customer_labels,
                    customer,
                    secret,
                    week,
                    monday,
                    releases,
                    await _template(),
                    now.date(),
                )
            except collector.IndexerUnreachable as e:
                out.outcome, out.message = StatsOutcome.INDEXER_UNREACHABLE, f"The Wazuh indexer cannot be reached ({e})."
                return out
        finally:
            try:
                await client.close()
            except Exception:  # noqa: BLE001
                pass
        if prepared.built is None:
            out.outcome, out.message = prepared.outcome, prepared.message
            if prepared.outcome is StatsOutcome.NO_SYSMON_EVENTS:
                out.would_send = StatsWouldSend(ok=False, why=prepared.message)
            return out
        built = prepared.built
        out.payload = built.doc
        out.payload_sha256 = built.sha256
        out.payload_bytes = len(built.payload)
        out.local = StatsPreviewLocal(
            raw_patterns=built.stats.raw_patterns,
            sent=built.stats.sent,
            dropped_by_reason=built.stats.dropped_by_reason,
            merged=built.stats.merged,
            truncated=built.stats.truncated,
        )
        out.ms = int((_monotonic() - started) * 1000)
        return out


async def _safe_list_withdraws() -> List[str]:
    try:
        return await store.list_withdraws()
    except Exception:  # noqa: BLE001
        return []


def _why_not(run: _Run, customer: CustomerRow, week: str, monday: date, now: datetime, license_key: str) -> Optional[str]:
    if not settings.sharing_on():
        return "Noise statistics are off on this CoPilot (SYSMON_STATS_SHARING)."
    if not license_key:
        return "This CoPilot has no license."
    if run.state.latch is not None and run.state.latch.copilot_version == CURRENT_VERSION:
        return f"Reports are paused: SOCFortress refused one ({run.state.latch.reason})."
    if run.state.service.accepting is False:
        return "SOCFortress is not accepting noise reports yet."
    ok, why = _due(run, customer, week, monday, now, ignore_jitter=False)
    if not ok and why == "not due yet":
        return f"Not due yet: sent after {_utc_text(due_time(run.secret, customer.code, week, monday))}."
    return None if ok else why[0].upper() + why[1:] + "."
