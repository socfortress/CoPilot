"""What the Sysmon Config page shows about the noise statistics: database and MinIO reads only (no indexer, no network)."""
from datetime import datetime
from datetime import timezone
from typing import List
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_stats import StatsCustomerStatus
from app.active_response.schema.sysmon_stats import StatsState
from app.active_response.schema.sysmon_stats import StatsStatus
from app.active_response.schema.sysmon_stats import StatsWithdrawStatus
from app.active_response.services.sysmon_default_sync import _utc_text
from app.active_response.services.sysmon_stats import runner
from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats import state as store
from app.active_response.services.sysmon_stats.identity import customer_pseudonym
from app.active_response.services.sysmon_stats.identity import due_time
from app.active_response.services.sysmon_stats.identity import load_secret
from app.active_response.services.sysmon_stats.runner import CustomerRow
from app.active_response.services.sysmon_stats.runner import _end
from app.active_response.services.sysmon_stats.runner import read_customers
from app.active_response.services.sysmon_stats.runner import target_week
from app.db import named_lock


def _customer_status(
    customer: CustomerRow,
    secret: Optional[bytes],
    state: StatsState,
    queued: dict,
    week: str,
    monday,
) -> StatsCustomerStatus:
    pseudonym = customer_pseudonym(secret, customer.code) if secret else None
    request = queued.get(pseudonym) if pseudonym else None
    out = StatsCustomerStatus(
        customer_code=customer.code,
        customer_name=customer.name,
        pseudonym=pseudonym,
        sharing=customer.sharing,
        install_dir_name=customer.install_dir_name,
        own_domains=customer.own_domains,
        withdraw=StatsWithdrawStatus(
            queued=pseudonym in queued if pseudonym else False,
            requested_at=request.requested_at if request else None,
            withdrawn_at=_utc_text(customer.withdrawn_at.replace(tzinfo=timezone.utc)) if customer.withdrawn_at else None,
            last_status=request.last_status if request else None,
        ),
        due_at=_utc_text(due_time(secret, customer.code, week, monday)) if secret else None,
        target_week_state=state.weeks.get(week, {}).get(customer.code),
    )
    for sent_week in sorted(state.weeks, reverse=True):
        entry = state.weeks[sent_week].get(customer.code)
        if entry is not None and entry.sent_at:
            out.last_sent_week, out.last_sent_state = sent_week, entry
            break
    return out


async def get_status(session: AsyncSession, now: Optional[datetime] = None) -> StatsStatus:
    now = now or datetime.now(timezone.utc)
    mode, raw = settings.sharing_mode()
    week, monday = target_week(now)
    status = StatsStatus(
        mode=mode,
        mode_setting=raw,
        service_url=settings.base_url(),
        target_week=week,
        max_rule_level=settings.max_rule_level(),
        min_endpoints=settings.min_endpoints(),
    )
    errors: List[str] = []
    try:
        customers = await read_customers(session)
        secret = await load_secret(session, create=True)
    finally:
        await _end(session)
    state = StatsState()
    try:
        state = await store.read_state()
    except Exception as e:  # noqa: BLE001 - shown as a read error
        errors.append(f"the state ({type(e).__name__})")
    queued = {}
    try:
        for pseudonym in await store.list_withdraws():
            queued[pseudonym] = await store.read_withdraw(pseudonym)
    except Exception as e:  # noqa: BLE001
        errors.append(f"the withdraw queue ({type(e).__name__})")
    status.service = state.service
    status.last_tick = state.last_tick
    status.latch = state.latch
    status.customers = [_customer_status(c, secret, state, queued, week, monday) for _, c in sorted(customers.items())]
    status.running = runner.running() or await named_lock.lock_in_use(runner.LOCK_PREFIX)
    if errors:
        status.read_error = f"Could not read {', '.join(errors)} from this CoPilot's data store (MinIO)."
    return status
