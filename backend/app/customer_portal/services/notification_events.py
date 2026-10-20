"""Where portal user notifications come from (#1282): the events, and their emission.

The incident routes and services call the ``notify_*`` functions after the change is
committed, the way they call ``emit`` for the SOC's routes. Each one schedules the work
and returns at once: alert ingest and a status change must never wait on SMTP, and a
failure to notify must never fail the change. The work runs on a session of its own,
under a time limit, and logs rather than raises.

What each event is, and what makes it "the same" notification (its dedupe key):

- **alert_created** — a new alert, once per alert. Merges into an open alert are not
  new alerts, and ingest does not call this for them.
- **waiting_on_you** — the SOC put an alert or a case on PENDING_CUSTOMER. Once per
  pause: the key carries the SLA clock's ``paused_at``, so asking again later notifies
  again, while a repeated write of the same status does not.
- **case_closed** — once per closing, keyed on ``case_closed_time``. Closing a case
  moves its alerts too; only the case is notified.
- **report_ready** — a report the portal can show finished generating, or was shared
  with the customer afterwards. Once per report. A report a portal user asked for is
  theirs alone; one the SOC generated and shared goes to every user of the customer.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable
from typing import Callable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_portal.services import notifications as portal_notifications
from app.customer_portal.services.notifications import ENTITY_ALERT
from app.customer_portal.services.notifications import ENTITY_CASE
from app.customer_portal.services.notifications import ENTITY_REPORT
from app.customer_portal.services.notifications import EVENT_ALERT_CREATED
from app.customer_portal.services.notifications import EVENT_CASE_CLOSED
from app.customer_portal.services.notifications import EVENT_REPORT_READY
from app.customer_portal.services.notifications import EVENT_WAITING_ON_YOU
from app.customer_portal.services.notifications import PortalEvent
from app.customer_portal.services.notifications import severity_label
from app.customer_portal.services.notifications import stamp_marker
from app.db.db_session import async_engine
from app.db.universal_models import IncidentManagementCustomerReport
from app.incidents.models import Alert
from app.incidents.models import Case

WAITING_STATUS = "PENDING_CUSTOMER"
CLOSED_STATUS = "CLOSED"

#: Bodies are short: the full item is one click away in the portal.
MAX_BODY = 280

#: Ceiling for one emission, emails included.
_EMIT_TIMEOUT_S = 120.0

#: Strong references to running emissions, or asyncio may collect them mid-flight.
_IN_FLIGHT: Set[asyncio.Task] = set()


def _excerpt(text: Optional[str]) -> Optional[str]:
    text = " ".join((text or "").split())
    if not text:
        return None
    return text if len(text) <= MAX_BODY else f"{text[: MAX_BODY - 1].rstrip()}…"


# ── Building events ───────────────────────────────────────────────────────────


async def alert_created_event(alert_id: int, session: AsyncSession) -> Optional[PortalEvent]:
    from app.incidents.services.alert_severity import severity_of

    alert = await session.get(Alert, alert_id)
    if alert is None:
        return None
    severity = severity_of(alert)
    return PortalEvent(
        event=EVENT_ALERT_CREATED,
        customer_code=alert.customer_code,
        entity_type=ENTITY_ALERT,
        entity_id=alert.id,
        dedupe_key=f"{EVENT_ALERT_CREATED}:{ENTITY_ALERT}:{alert.id}",
        title=f"New {severity_label(severity)} alert: {alert.alert_name}",
        body=_excerpt(alert.alert_description),
        severity=severity,
    )


async def _paused_at(entity_type: str, entity_id: int, session: AsyncSession):
    """When the item's SLA clock was paused, the stamp that tells one wait from the next."""
    from app.soc_management.models.sla import AlertSlaTracking
    from app.soc_management.models.sla import CaseSlaTracking

    model, column = (
        (AlertSlaTracking, AlertSlaTracking.alert_id) if entity_type == ENTITY_ALERT else (CaseSlaTracking, CaseSlaTracking.case_id)
    )
    result = await session.execute(select(model.paused_at).where(column == entity_id))
    return result.scalar()


async def waiting_event(entity_type: str, entity_id: int, actor_user_id: Optional[int], session: AsyncSession) -> Optional[PortalEvent]:
    if entity_type == ENTITY_ALERT:
        item = await session.get(Alert, entity_id)
        name, status = (item.alert_name, item.status) if item else (None, None)
    else:
        item = await session.get(Case, entity_id)
        name, status = (item.case_name, item.case_status) if item else (None, None)
    # Re-read: the status may have moved on between the change and this task.
    if item is None or status != WAITING_STATUS or not item.customer_code:
        return None
    marker = stamp_marker(await _paused_at(entity_type, entity_id, session))
    return PortalEvent(
        event=EVENT_WAITING_ON_YOU,
        customer_code=item.customer_code,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=f"{EVENT_WAITING_ON_YOU}:{entity_type}:{entity_id}:{marker}",
        title=f"The SOC is waiting on your reply: {name}",
        body=f"Their response clock for this {entity_type} is paused until you answer. Reply in its comments to hand it back.",
        severity=getattr(item, "severity", None) if entity_type == ENTITY_ALERT else None,
        actor_user_id=actor_user_id,
    )


async def case_closed_event(case_id: int, actor_user_id: Optional[int], session: AsyncSession) -> Optional[PortalEvent]:
    case = await session.get(Case, case_id)
    if case is None or case.case_status != CLOSED_STATUS or not case.customer_code:
        return None
    return PortalEvent(
        event=EVENT_CASE_CLOSED,
        customer_code=case.customer_code,
        entity_type=ENTITY_CASE,
        entity_id=case.id,
        dedupe_key=f"{EVENT_CASE_CLOSED}:{ENTITY_CASE}:{case.id}:{stamp_marker(case.case_closed_time)}",
        title=f"Case closed: {case.case_name}",
        body=_excerpt(case.case_description),
        actor_user_id=actor_user_id,
    )


async def report_ready_event(report_id: int, session: AsyncSession) -> Optional[PortalEvent]:
    """A finished report the portal shows: the requester's own, or one shared by the SOC."""
    report = await session.get(IncidentManagementCustomerReport, report_id)
    if report is None or report.status != "completed":
        return None
    if report.generated_by_role == "customer_user":
        only = frozenset({report.generated_by}) if report.generated_by is not None else frozenset()
    elif report.visible_to_customer:
        only = None
    else:
        return None
    period = ""
    if report.date_from and report.date_to:
        period = f"It covers {report.date_from:%Y-%m-%d} to {report.date_to:%Y-%m-%d}."
    return PortalEvent(
        event=EVENT_REPORT_READY,
        customer_code=report.customer_code,
        entity_type=ENTITY_REPORT,
        entity_id=report.id,
        dedupe_key=f"{EVENT_REPORT_READY}:{ENTITY_REPORT}:{report.id}",
        title=f"Report ready: {report.report_name}",
        body=period or None,
        only_user_ids=only,
    )


# ── Delivering them ───────────────────────────────────────────────────────────


async def deliver(events: Sequence[Optional[PortalEvent]], session: AsyncSession) -> None:
    """Write each event's notifications, then send the immediate emails."""
    immediate: List[int] = []
    for event in events:
        if event is not None:
            immediate += await portal_notifications.fan_out(event, session)
    if immediate:
        await portal_notifications.send_immediate(immediate, session)


async def process_alert_created(alert_id: int, session: AsyncSession) -> None:
    await deliver([await alert_created_event(alert_id, session)], session)


async def process_status_change(
    entity_type: str,
    entity_ids: Sequence[int],
    to_status: str,
    actor_user_id: Optional[int],
    session: AsyncSession,
) -> None:
    events: List[Optional[PortalEvent]] = []
    for entity_id in entity_ids:
        if to_status == WAITING_STATUS:
            events.append(await waiting_event(entity_type, entity_id, actor_user_id, session))
        elif to_status == CLOSED_STATUS and entity_type == ENTITY_CASE:
            events.append(await case_closed_event(entity_id, actor_user_id, session))
    await deliver(events, session)


async def process_report_ready(report_id: int, session: AsyncSession) -> None:
    await deliver([await report_ready_event(report_id, session)], session)


# ── Scheduling ────────────────────────────────────────────────────────────────


async def _run(label: str, work: Callable[[AsyncSession], Awaitable[None]]) -> None:
    try:
        async with AsyncSession(async_engine) as session:
            await asyncio.wait_for(work(session), timeout=_EMIT_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.error(f"Portal notification [{label}] timed out after {_EMIT_TIMEOUT_S}s; abandoning.")
    except Exception as e:  # noqa: BLE001 — nothing here may reach the caller
        logger.error(f"Portal notification [{label}] failed: {type(e).__name__}: {e}")


def _schedule(label: str, work: Callable[[AsyncSession], Awaitable[None]]) -> None:
    """Run ``work`` in the background on its own session. Never raises."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(f"Portal notification [{label}] skipped: no running event loop.")
        return
    task = loop.create_task(_run(label, work))
    _IN_FLIGHT.add(task)
    task.add_done_callback(_IN_FLIGHT.discard)


async def drain() -> None:
    """Wait for every scheduled emission to finish (for tests and shutdown)."""
    while _IN_FLIGHT:
        await asyncio.gather(*list(_IN_FLIGHT), return_exceptions=True)


def notify_alert_created(alert_id: int) -> None:
    _schedule(f"alert_created alert#{alert_id}", lambda session: process_alert_created(alert_id, session))


def notify_status_change(entity_type: str, entity_ids: Sequence[int], to_status: str, actor_user_id: Optional[int] = None) -> None:
    """After an alert's or a case's status changed. Only waiting and (case) closed notify."""
    ids = [entity_id for entity_id in entity_ids if entity_id is not None]
    if not ids or (to_status != WAITING_STATUS and not (to_status == CLOSED_STATUS and entity_type == ENTITY_CASE)):
        return
    _schedule(
        f"status {to_status} {entity_type}#{','.join(map(str, ids))}",
        lambda session: process_status_change(entity_type, ids, to_status, actor_user_id, session),
    )


def notify_report_ready(report_id: int) -> None:
    _schedule(f"report_ready report#{report_id}", lambda session: process_report_ready(report_id, session))
