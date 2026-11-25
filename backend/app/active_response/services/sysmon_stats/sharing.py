"""Per-customer opt-out, its withdraw, and the customer decommission and deletion hooks.

Sharing is on by default (no settings row). An admin's opt-out writes the row, audits it, queues a withdraw for the
customer's pseudonym (a MinIO object, so it outlives the customer's row) and, when sharing is on and SOCFortress is not
asking CoPilot to wait, sends it at once. Every tick sends the queued withdraws before any report. With the kill switch
off nothing is sent, withdraws included: they stay queued and go out when sharing is on again (owner decision D5).
Opting in again keeps the row (for its hints); reports resume no sooner than 180 s after the last confirmed withdraw,
since SOCFortress drops a withdrawn customer's reports for 120 s.
"""
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_stats import StatsSharingRequest
from app.active_response.schema.sysmon_stats import StatsState
from app.active_response.schema.sysmon_stats import StatsWithdrawRequest
from app.active_response.schema.sysmon_stats import StatsWithdrawResult
from app.active_response.services.sysmon_default_sync import _parse_utc
from app.active_response.services.sysmon_default_sync import _utc_text
from app.active_response.services.sysmon_stats import client as http
from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats import state as store
from app.active_response.services.sysmon_stats.identity import customer_pseudonym
from app.active_response.services.sysmon_stats.identity import load_secret
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.db.universal_models import Customers
from app.db.universal_models import SysmonStatsCustomerSettings
from app.middleware.license import get_license

SYSTEM_ACTOR = "system"
INSTALL_DIR_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
DOMAIN_RE = re.compile(r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+")
MAX_OWN_DOMAINS = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


def validate_hints(body: StatsSharingRequest) -> Tuple[Optional[str], Optional[List[str]]]:
    """The hints as stored, or a 400 naming the field (never echoing what was sent)."""
    install_dir = body.install_dir_name.strip() if isinstance(body.install_dir_name, str) else None
    if install_dir == "":
        install_dir = None
    if install_dir is not None and (not INSTALL_DIR_RE.fullmatch(install_dir) or install_dir == "__INSTALLDIRNAME__"):
        raise HTTPException(status_code=400, detail="install_dir_name must be 1-64 of A-Z, a-z, 0-9, '.', '_', '-'")
    domains: Optional[List[str]] = None
    if body.own_domains is not None:
        if len(body.own_domains) > MAX_OWN_DOMAINS:
            raise HTTPException(status_code=400, detail=f"own_domains: at most {MAX_OWN_DOMAINS}")
        domains = []
        for value in body.own_domains:
            d = value.strip().lower().rstrip(".") if isinstance(value, str) else ""
            if not DOMAIN_RE.fullmatch(d):
                raise HTTPException(status_code=400, detail="own_domains: each must be an ASCII DNS name with at least two labels")
            if d not in domains:
                domains.append(d)
        domains = domains or None
    return install_dir, domains


async def queue_withdraw(customer: str, customer_code: Optional[str], now: Optional[datetime] = None) -> None:
    """Queue a withdraw for one pseudonym (kept if one is queued already). Raises when MinIO cannot store it."""
    existing = await store.read_withdraw(customer)
    if existing is not None:
        return
    await store.write_withdraw(
        StatsWithdrawRequest(customer=customer, customer_code=customer_code, requested_at=_utc_text(now or _now())),
    )


async def _set_withdrawn_at(session: Optional[AsyncSession], customer_code: Optional[str], moment: datetime) -> None:
    if session is None or not customer_code:
        return
    try:
        row = (
            (await session.execute(select(SysmonStatsCustomerSettings).where(SysmonStatsCustomerSettings.customer_code == customer_code)))
            .scalars()
            .first()
        )
        if row is not None:
            row.withdrawn_at = moment.astimezone(timezone.utc).replace(tzinfo=None)
            await session.commit()
        else:
            await session.rollback()
    except Exception as e:  # noqa: BLE001 - the withdraw itself succeeded
        logger.error(f"Sysmon stats: could not record a confirmed withdraw ({type(e).__name__})")
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass


async def send_withdraw(
    session: Optional[AsyncSession],
    customer: str,
    license_key: str,
    base: str,
    *,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    actor=None,
    request: Optional[Request] = None,
    state: Optional[StatsState] = None,
    now: Optional[datetime] = None,
) -> http.WithdrawResult:
    """Send one queued withdraw: on SOCFortress's 200 the queue object goes and the customer's ``withdrawn_at`` is set;
    otherwise it stays queued, with its attempt and any Retry-After recorded."""
    now = now or _now()
    queued = await store.read_withdraw(customer)
    result = await http.post_withdraw(base, customer, license_key, transport)
    code = queued.customer_code if queued else None
    await record_audit_event(
        action=AuditAction.SYSMON_STATS_WITHDRAW,
        actor_user_id=getattr(actor, "id", None),
        actor_username=getattr(actor, "username", None) or SYSTEM_ACTOR,
        customer_code=code,
        entity_type="sysmon_stats_customer",
        entity_id=customer,
        result=AuditResult.SUCCESS if result.withdrawn else (AuditResult.UNKNOWN if result.http_status is None else AuditResult.FAILURE),
        new_value={
            "customer_pseudonym": customer,
            "http_status": result.http_status,
            "outcome": "withdrawn" if result.withdrawn else "queued",
            "reports_deleted": result.reports_deleted,
        },
        request=request,
    )
    if result.withdrawn:
        logger.info(f"Sysmon stats: withdraw of {customer[:13]} confirmed (deleted {result.reports_deleted})")
        try:
            await store.delete_withdraw(customer)
        except Exception as e:  # noqa: BLE001 - sent again next tick: a withdraw is idempotent
            logger.error(f"Sysmon stats: could not delete a confirmed withdraw from the queue ({type(e).__name__})")
        await _set_withdrawn_at(session, code, now)
        return result
    log = logger.error if result.bug else logger.warning
    log(f"Sysmon stats: withdraw of {customer[:13]} not confirmed: {result.message}")
    update = queued or StatsWithdrawRequest(customer=customer, customer_code=None, requested_at=_utc_text(now))
    update.attempts += 1
    update.last_status = result.http_status
    if result.retry_seconds:
        update.not_before = _utc_text(now + timedelta(seconds=result.retry_seconds))
        if state is not None:
            state.service.not_before = update.not_before
    try:
        await store.write_withdraw(update)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Sysmon stats: could not update a queued withdraw ({type(e).__name__})")
    return result


async def process_withdraw_queue(
    session: Optional[AsyncSession],
    license_key: str,
    base: str,
    customers: List[str],
    *,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    state: Optional[StatsState] = None,
    now: Optional[datetime] = None,
) -> int:
    """Send the queued withdraws (only with sharing on). Stops at the first answer that says to wait. Returns how many
    were confirmed."""
    if not settings.sharing_on() or not customers:
        return 0
    now = now or _now()
    confirmed = 0
    for customer in customers:
        queued = await store.read_withdraw(customer)
        waiting = _parse_utc(queued.not_before) if queued else None
        if waiting is not None and waiting > now:
            continue
        result = await send_withdraw(session, customer, license_key, base, transport=transport, state=state, now=now)
        if result.withdrawn:
            confirmed += 1
        elif result.stop:
            break
    return confirmed


async def set_sharing(
    session: AsyncSession,
    customer_code: str,
    body: StatsSharingRequest,
    *,
    actor,
    request: Optional[Request] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    now: Optional[datetime] = None,
) -> Optional[StatsWithdrawResult]:
    """Turn a customer's sharing off or on and store its hints. Opting out queues a withdraw and, when it may be sent,
    sends it at once. Returns the withdraw's result on an opt-out."""
    now = now or _now()
    customer = (await session.execute(select(Customers).where(Customers.customer_code == customer_code))).scalars().first()
    if customer is None:
        await session.rollback()
        raise HTTPException(status_code=404, detail="Customer not found")
    install_dir, domains = validate_hints(body)
    row = (
        (await session.execute(select(SysmonStatsCustomerSettings).where(SysmonStatsCustomerSettings.customer_code == customer_code)))
        .scalars()
        .first()
    )
    old = {
        "sharing": True if row is None else bool(row.sharing_enabled),
        "install_dir_name": row.install_dir_name if row else None,
        "own_domains_count": len(row.own_domains or []) if row else 0,
    }
    if row is None:
        row = SysmonStatsCustomerSettings(customer_code=customer_code, sharing_enabled=body.sharing)
        session.add(row)
    row.sharing_enabled = body.sharing
    if "install_dir_name" in body.model_fields_set:
        row.install_dir_name = install_dir
    if "own_domains" in body.model_fields_set:
        row.own_domains = domains
    row.updated_at = now.astimezone(timezone.utc).replace(tzinfo=None)
    row.updated_by = getattr(actor, "id", None)
    new = {"sharing": body.sharing, "install_dir_name": row.install_dir_name, "own_domains_count": len(row.own_domains or [])}
    opting_out = old["sharing"] and not body.sharing
    secret = await load_secret(session, create=True) if opting_out else None
    license_row = await get_license(session, raise_on_missing=False) if opting_out else None
    # Read before the commit, which may expire the row
    license_key = (getattr(license_row, "license_key", None) or "").strip()
    await session.commit()
    await record_audit_event(
        action=AuditAction.SYSMON_STATS_SHARING,
        actor_user_id=getattr(actor, "id", None),
        actor_username=getattr(actor, "username", None) or SYSTEM_ACTOR,
        customer_code=customer_code,
        entity_type="sysmon_stats_customer",
        entity_id=customer_code,
        old_value=old,
        new_value=new,
        request=request,
    )
    if not opting_out:
        return None
    if secret is None:
        return StatsWithdrawResult(outcome="failed", message="This CoPilot's report secret could not be read: nothing to withdraw.")
    pseudonym = customer_pseudonym(secret, customer_code)
    try:
        await queue_withdraw(pseudonym, customer_code, now=now)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Sysmon stats: could not queue the withdraw of an opted-out customer ({type(e).__name__})")
        return StatsWithdrawResult(outcome="failed", message="The withdraw could not be queued (MinIO); the opt-out is saved.")
    if not settings.sharing_on() or not license_key:
        return StatsWithdrawResult(outcome="queued", message="Queued: it is sent once noise statistics are on.")
    try:
        state = await store.read_state()
    except Exception:  # noqa: BLE001
        state = None
    waiting = _parse_utc(state.service.not_before) if state else None
    if waiting is not None and waiting > now:
        return StatsWithdrawResult(outcome="queued", message=f"Queued: SOCFortress asked to wait until {_utc_text(waiting)}.")
    result = await send_withdraw(
        session,
        pseudonym,
        license_key,
        settings.base_url(),
        transport=transport,
        actor=actor,
        request=request,
        now=now,
    )
    if result.withdrawn:
        return StatsWithdrawResult(
            outcome="withdrawn",
            reports_deleted=result.reports_deleted,
            message="SOCFortress deleted the reports already sent.",
        )
    return StatsWithdrawResult(outcome="queued", message=f"Queued: {result.message} It is sent again with the next tick.")


def _new_session() -> AsyncSession:
    from app.db.db_session import AsyncSessionLocal

    return AsyncSessionLocal()


# The hooks use a session of their own, so the caller's transaction is never committed or rolled back here. Tests point
# this at their own database.
new_session = _new_session


async def on_customer_deleted(customer_code: str) -> None:
    """Before a customer row is deleted: queue a withdraw for its pseudonym (its settings row cascades away). Best effort."""
    try:
        async with new_session() as session:
            secret = await load_secret(session, create=False)
            await session.rollback()
        if secret is not None:
            await queue_withdraw(customer_pseudonym(secret, customer_code), customer_code)
    except Exception as e:  # noqa: BLE001 - deleting the customer must not fail on this
        logger.warning(f"Sysmon stats: could not queue the withdraw of a deleted customer ({type(e).__name__})")


async def on_customer_decommissioned(customer_code: str) -> None:
    """A decommissioned customer: queue a withdraw for its pseudonym and drop its settings row. Best effort."""
    await on_customer_deleted(customer_code)
    try:
        async with new_session() as session:
            await session.execute(delete(SysmonStatsCustomerSettings).where(SysmonStatsCustomerSettings.customer_code == customer_code))
            await session.commit()
    except Exception as e:  # noqa: BLE001 - decommission must not fail on this
        logger.warning(f"Sysmon stats: could not delete a decommissioned customer's settings ({type(e).__name__})")
