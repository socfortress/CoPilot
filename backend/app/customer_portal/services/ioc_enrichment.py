"""Threat Intel enrichment of a customer's own IOCs in the Customer Portal (#1318).

A portal user sees what VirusTotal and OpenCTI say about the IOCs of their alerts. The sources
themselves (what a value is, the requests, the projections) are ``ioc_enrichment_sources.py``;
this module holds the rules.

- **Only an IOC on an alert the caller may see**: the alert's customer and tag visibility
  (``ensure_alert_visible``), then the IOC linked to that alert. The customer is the alert's,
  never one the browser names.
- **Opt-in per customer** (``customer_portal_ioc_enrichment_settings``, a missing row = off),
  with an optional daily limit on lookups that reach a source.
- **On request, cached per customer.** Opening an alert's IOCs reads only the cache
  (``customer_portal_ioc_enrichment``, one row per customer, value and source); a source is
  asked when the user checks an IOC whose answer is missing or older than ``CACHE_TTL``. Keyed
  per customer, so no tenant can tell from a date that another met the same IOC.
- **Two clicks are one lookup.** The rules run under a lock on the customer's settings row and
  write a ``customer_portal_ioc_lookup`` row before any source is asked: the daily limit counts
  those rows, and a value with a lookup still running is refused (409). The lock is released
  before the sources are asked; the row is removed when no source answered, so a failure costs
  the customer nothing.
- A user who may only read a customer's data (#1312) may check its IOCs: a lookup changes
  nothing of the customer's.
"""

import asyncio
import hashlib
import os
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.customer_portal.schema.ioc_enrichment import IocEnrichment
from app.customer_portal.schema.ioc_enrichment import OpenCtiDetails
from app.customer_portal.schema.ioc_enrichment import SourceResult
from app.customer_portal.schema.ioc_enrichment import VirusTotalDetails
from app.customer_portal.services import ioc_enrichment_sources as sources
from app.customer_portal.services.ai_reports import ensure_alert_visible
from app.db.universal_models import CustomerPortalIocEnrichment
from app.db.universal_models import CustomerPortalIocEnrichmentSettings
from app.db.universal_models import CustomerPortalIocLookup
from app.incidents.models import AlertToIoC
from app.incidents.models import IoC
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc


def _cache_hours() -> int:
    try:
        hours = int(os.getenv("IOC_ENRICHMENT_CACHE_HOURS", "24"))
    except ValueError:
        hours = 24
    return min(max(hours, 1), 720)


#: How long an answer is shown before the user may ask the source again.
CACHE_TTL = timedelta(hours=_cache_hours())
#: The window a customer's daily limit counts over.
LIMIT_WINDOW = timedelta(hours=24)
#: A lookup still running this long after it started is taken as dead.
IN_PROGRESS = timedelta(minutes=2)
#: Lookup rows are kept this long (the limit reads the last 24 hours).
LOOKUP_RETENTION = timedelta(days=7)

NOT_ENABLED = "IOC enrichment is not enabled for your organization"
NOT_ON_ALERT = "IOC not found on this alert"
BEING_CHECKED = "This IOC is already being checked. Try again in a moment."
LIMIT_REACHED = "Your organization has reached its daily limit of IOC checks. Please try again later."

#: Worst first: the overall verdict is the worst a source gave.
VERDICT_RANK = {"malicious": 5, "suspicious": 4, "known": 3, "clean": 2, "unknown": 1}


def _now() -> datetime:
    return now_utc().replace(tzinfo=None)


def _iso(moment: Optional[datetime]) -> Optional[str]:
    return moment.replace(microsecond=0).isoformat() + "Z" if moment else None


def value_digest(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ── the switch ────────────────────────────────────────────────────────────────


async def get_settings(customer_code: str, session: AsyncSession, *, lock: bool = False) -> Optional[CustomerPortalIocEnrichmentSettings]:
    query = select(CustomerPortalIocEnrichmentSettings).where(CustomerPortalIocEnrichmentSettings.customer_code == customer_code)
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).scalars().first()


async def upsert_settings(
    customer_code: str,
    enabled: bool,
    daily_lookup_limit: Optional[int],
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalIocEnrichmentSettings:
    """Create or replace a customer's switch and limit. Caller commits."""
    settings = await get_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalIocEnrichmentSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.daily_lookup_limit = daily_lookup_limit
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def enabled_customer_codes(user: User, session: AsyncSession) -> List[str]:
    """The customers ``user`` may see that have IOC enrichment switched on."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalIocEnrichmentSettings.customer_code).where(CustomerPortalIocEnrichmentSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalIocEnrichmentSettings.customer_code.in_(accessible))
    return sorted((await session.execute(query)).scalars().all())


async def availability(user: User, session: AsyncSession, customer_code: Optional[str] = None) -> Tuple[Optional[str], bool, List[str]]:
    """Whether the portal offers enrichment: for one customer the caller may see, else for any.

    On only when switched on *and* a source can be asked: a switch with no verified connector
    behind it would offer a button that can never answer.
    """
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        settings = await get_settings(customer_code, session)
        switched_on = bool(settings and settings.enabled)
    else:
        switched_on = bool(await enabled_customer_codes(user, session))
    available = await sources.available_sources() if switched_on else []
    return customer_code, bool(available), available


# ── reading the cache into what the portal shows (pure) ───────────────────────


def _details(source: str, row: CustomerPortalIocEnrichment) -> dict:
    """A cached row's details, validated again: a row a later version cannot read shows none."""
    if row.status != "found" or not isinstance(row.details, dict):
        return {}
    try:
        if source == sources.VIRUSTOTAL:
            return {"virustotal": VirusTotalDetails.model_validate(row.details)}
        return {"opencti": OpenCtiDetails.model_validate(row.details)}
    except ValidationError:
        return {}


def stale(row: CustomerPortalIocEnrichment, now: datetime) -> bool:
    return now - row.checked_at >= CACHE_TTL


def build_enrichment(
    ioc: IoC,
    rows: Dict[str, CustomerPortalIocEnrichment],
    available: Iterable[str],
    now: datetime,
    failures: Optional[Dict[str, sources.Outcome]] = None,
) -> IocEnrichment:
    """What the portal shows for one IOC, from the cache and this request's failures. Pure."""
    kind, _ = sources.classify(ioc.value)
    available = list(available)
    failures = failures or {}
    results: List[SourceResult] = []
    used: List[CustomerPortalIocEnrichment] = []
    askable: List[str] = []
    for source in sources.SOURCES:
        row = rows.get(source)
        if source not in available:
            results.append(SourceResult(source=source, status="not_configured"))
            continue
        if not sources.applicable(source, kind):
            status = "internal" if kind == "internal" else "unsupported"
            results.append(SourceResult(source=source, status=status))
            continue
        askable.append(source)
        if row is not None and row.status in ("found", "not_found"):
            # A failed refresh keeps the older answer on screen, with the failure beside it.
            used.append(row)
            failure = failures.get(source)
            results.append(
                SourceResult(
                    source=source,
                    status=row.status,
                    verdict=row.verdict if row.status == "found" and row.verdict in VERDICT_RANK else None,
                    checked_at=_iso(row.checked_at),
                    error=(failure.error or "unavailable") if failure else None,
                    **_details(source, row),
                ),
            )
        elif source in failures:
            results.append(SourceResult(source=source, status="error", error=failures[source].error or "unavailable"))
        else:
            results.append(SourceResult(source=source, status="not_checked"))

    found = [result.verdict for result in results if result.status == "found" and result.verdict]
    if found:
        verdict = max(found, key=lambda v: VERDICT_RANK[v])
    elif any(result.status == "not_found" for result in results):
        verdict = "not_found"
    else:
        verdict = None

    by_source = {row.source: row for row in used}
    due = [source for source in askable if source not in by_source or stale(by_source[source], now)]
    next_check = min((row.checked_at for row in used), default=None)
    return IocEnrichment(
        ioc_id=ioc.id,
        value=ioc.value,
        type=ioc.type,
        kind=kind,
        verdict=verdict,
        checked_at=_iso(max((row.checked_at for row in used), default=None)),
        can_check=bool(due),
        next_check_at=_iso(next_check + CACHE_TTL) if askable and not due and next_check else None,
        sources=results,
    )


# ── reads ─────────────────────────────────────────────────────────────────────


async def _cached_rows(
    customer_code: str,
    digests: Iterable[str],
    session: AsyncSession,
) -> Dict[str, Dict[str, CustomerPortalIocEnrichment]]:
    """The cache rows of these values for this customer: digest → source → row."""
    digests = sorted(set(digests))
    if not digests:
        return {}
    row = CustomerPortalIocEnrichment
    found = (await session.execute(select(row).where(row.customer_code == customer_code, row.value_sha256.in_(digests)))).scalars().all()
    rows: Dict[str, Dict[str, CustomerPortalIocEnrichment]] = {}
    for item in found:
        rows.setdefault(item.value_sha256, {})[item.source] = item
    return rows


def _digest_of(ioc: IoC) -> str:
    return value_digest(sources.classify(ioc.value)[1])


async def _ensure_enabled(customer_code: str, session: AsyncSession) -> None:
    settings = await get_settings(customer_code, session)
    if settings is None or not settings.enabled:
        raise HTTPException(status_code=403, detail=NOT_ENABLED)


async def list_for_alert(alert_id: int, user: User, session: AsyncSession) -> Tuple[List[IocEnrichment], List[str]]:
    """What is known about every IOC of an alert, from the cache only: no source is asked."""
    alert = await ensure_alert_visible(alert_id, user, session)
    await _ensure_enabled(alert.customer_code, session)
    iocs = (
        (
            await session.execute(
                select(IoC).join(AlertToIoC, AlertToIoC.ioc_id == IoC.id).where(AlertToIoC.alert_id == alert_id).order_by(IoC.id),
            )
        )
        .scalars()
        .all()
    )
    cache = await _cached_rows(alert.customer_code, (_digest_of(ioc) for ioc in iocs), session)
    available = await sources.available_sources()
    now = _now()
    return [build_enrichment(ioc, cache.get(_digest_of(ioc), {}), available, now) for ioc in iocs], available


# ── checking an IOC ───────────────────────────────────────────────────────────


def refusal(
    settings: Optional[CustomerPortalIocEnrichmentSettings],
    running: bool,
    recent_lookups: int,
) -> Optional[HTTPException]:
    """Why a lookup cannot start now, or ``None``. Pure, so the rules test without a DB."""
    if settings is None or not settings.enabled:
        return HTTPException(status_code=403, detail=NOT_ENABLED)
    if running:
        return HTTPException(status_code=409, detail=BEING_CHECKED)
    if settings.daily_lookup_limit is not None and recent_lookups >= settings.daily_lookup_limit:
        return HTTPException(status_code=429, detail=LIMIT_REACHED)
    return None


async def _reserve(user: User, customer_code: str, digest: str, session: AsyncSession) -> int:
    """Check the rules under the customer's settings lock and write the lookup row, or raise.

    The transaction of the reads before (the visibility checks) ends first: under MySQL's
    REPEATABLE READ a transaction reads the snapshot of its first plain read, so a request that
    waited for the lock would otherwise count the lookups as they were before it waited.
    """
    await session.commit()
    now = _now()
    settings = await get_settings(customer_code, session, lock=True)
    lookup = CustomerPortalIocLookup
    await session.execute(delete(lookup).where(lookup.customer_code == customer_code, lookup.requested_at < now - LOOKUP_RETENTION))
    running = (
        await session.execute(
            select(func.count(lookup.id)).where(
                lookup.customer_code == customer_code,
                lookup.value_sha256 == digest,
                lookup.completed_at.is_(None),
                lookup.requested_at >= now - IN_PROGRESS,
            ),
        )
    ).scalar_one() > 0
    recent = 0
    if settings is not None and settings.daily_lookup_limit is not None:
        recent = (
            await session.execute(
                select(func.count(lookup.id)).where(lookup.customer_code == customer_code, lookup.requested_at >= now - LIMIT_WINDOW),
            )
        ).scalar_one()
    refused = refusal(settings, running, recent)
    if refused is not None:
        await session.rollback()
        raise refused
    row = CustomerPortalIocLookup(
        customer_code=customer_code,
        value_sha256=digest,
        requested_by_user_id=getattr(user, "id", None),
        requested_at=now,
    )
    session.add(row)
    await session.commit()  # releases the settings lock before any source is asked
    return row.id


async def _store(
    customer_code: str,
    digest: str,
    normalized: str,
    lookup_id: int,
    outcomes: Dict[str, sources.Outcome],
    session: AsyncSession,
) -> None:
    """Cache what the sources answered and close the lookup; drop it when none answered."""
    now = _now()
    answered = {source: outcome for source, outcome in outcomes.items() if outcome.status in ("found", "not_found")}
    existing = (await _cached_rows(customer_code, [digest], session)).get(digest, {})
    for source, outcome in answered.items():
        row = existing.get(source)
        if row is None:
            row = CustomerPortalIocEnrichment(customer_code=customer_code, value_sha256=digest, value=normalized, source=source)
            session.add(row)
        row.value = normalized
        row.status = outcome.status
        row.verdict = outcome.verdict if outcome.status == "found" else None
        row.details = outcome.details if outcome.status == "found" else None
        row.checked_at = now
    lookup = await session.get(CustomerPortalIocLookup, lookup_id)
    if lookup is not None:
        if answered:
            lookup.completed_at = now
        else:
            await session.delete(lookup)
    await session.commit()


async def check(alert_id: int, ioc_id: int, user: User, session: AsyncSession) -> IocEnrichment:
    """Look up one IOC of one of the caller's alerts: the sources whose answer is missing or stale."""
    alert = await ensure_alert_visible(alert_id, user, session)
    customer_code = alert.customer_code
    ioc = (
        (
            await session.execute(
                select(IoC).join(AlertToIoC, AlertToIoC.ioc_id == IoC.id).where(AlertToIoC.alert_id == alert_id, IoC.id == ioc_id),
            )
        )
        .scalars()
        .first()
    )
    if ioc is None:
        raise HTTPException(status_code=404, detail=NOT_ON_ALERT)
    await _ensure_enabled(customer_code, session)

    kind, normalized = sources.classify(ioc.value)
    digest = value_digest(normalized)
    available = await sources.available_sources()
    askable = [source for source in available if sources.applicable(source, kind)]
    cached = (await _cached_rows(customer_code, [digest], session)).get(digest, {})
    now = _now()
    due = [source for source in askable if source not in cached or stale(cached[source], now)]
    if not due:
        return build_enrichment(ioc, cached, available, now)

    lookup_id = await _reserve(user, customer_code, digest, session)
    # Nothing of the request's transaction is open here: the sources may take seconds.
    answers = await asyncio.gather(*(sources.ask(source, kind, normalized) for source in due))
    outcomes = dict(zip(due, answers))
    try:
        await _store(customer_code, digest, normalized, lookup_id, outcomes, session)
    except Exception:
        await session.rollback()
        logger.exception(f"IOC enrichment: could not store the lookup of IOC {ioc.id} for customer {customer_code}")
        raise

    statuses = {source: outcome.status if outcome.status != "error" else f"error:{outcome.error}" for source, outcome in outcomes.items()}
    answered = any(outcome.status != "error" for outcome in outcomes.values())
    await record_audit_event(
        action=AuditAction.IOC_ENRICHMENT_LOOKUP,
        actor_user_id=getattr(user, "id", None),
        actor_username=getattr(user, "username", None),
        customer_code=customer_code,
        entity_type="ioc",
        entity_id=ioc.id,
        result=AuditResult.SUCCESS if answered else AuditResult.FAILURE,
        new_value={"alert_id": alert_id, "value": normalized[:256], "sources": statuses},
        details=None if answered else "No Threat Intel source answered",
    )
    cache = (await _cached_rows(customer_code, [digest], session)).get(digest, {})
    failures = {source: outcome for source, outcome in outcomes.items() if outcome.status == "error"}
    return build_enrichment(ioc, cache, available, _now(), failures)
