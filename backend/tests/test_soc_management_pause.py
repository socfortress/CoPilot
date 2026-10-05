"""SOC Management (#1187) — business hours and waiting on the customer, on a real database.

In-memory SQLite, the recorder on the test session factory (see test_soc_management_lifecycle).

Pinned here:
- a business-hours cell opens on the customer's calendar, else the global one;
- waiting on the customer stamps the pause once; any later status change resumes it and
  pushes the running clocks back by the pause, on their basis;
- closing a waiting item resumes it first, so the wait never counts against the SOC;
- a re-target after a pause keeps the credit;
- calendars: replace, resolve and clear, through the service.
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402
from app.soc_management.models.sla import SlaCalendar  # noqa: E402
from app.soc_management.models.sla import SlaPolicy  # noqa: E402
from app.soc_management.schema.calendar import CalendarIn  # noqa: E402
from app.soc_management.services import calendars as calendar_service  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from app.soc_management.services.lifecycle import retarget_open  # noqa: E402
from tests.soc_management_support import T0  # noqa: E402
from tests.soc_management_support import AlertSlaTracking  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402

ANA = Actor(username="ana", is_soc=True)
WEEKDAYS_9_17 = {day: [["09:00", "17:00"]] for day in ("mon", "tue", "wed", "thu", "fri")}

# T0 is Tuesday 2026-09-01 08:00 UTC.
FRIDAY_16_UTC = datetime(2026, 9, 4, 16, 0)


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now

    def at(self, moment):
        self.now = moment
        return moment


def run(scenario):
    async def _inner():
        db = await Db().create()
        try:
            return await scenario(db)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


async def _tracking(db, key):
    async with db.session() as session:
        return await session.get(AlertSlaTracking, key)


async def _business_hours_policy(session, customer_code=None, ack=60, resolve=240):
    session.add(
        SlaPolicy(
            customer_code=customer_code,
            entity_type="alert",
            severity="High",
            ack_minutes=ack,
            resolve_minutes=resolve,
            business_hours=True,
        ),
    )
    await session.commit()


def test_a_business_hours_cell_opens_on_the_customer_calendar_else_the_global_one():
    async def scenario(db):
        async with db.session() as session:
            await _business_hours_policy(session)
            session.add(SlaCalendar(customer_code=None, timezone="UTC", week=WEEKDAYS_9_17, holidays=[]))
            session.add(SlaCalendar(customer_code="ACME", timezone="Europe/Rome", week=WEEKDAYS_9_17, holidays=[]))
            await session.commit()
            acme = await add_alert(session, customer="ACME")
            globex = await add_alert(session, customer="GLOBEX")
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock(FRIDAY_16_UTC))
        await recorder.alert_opened(acme)
        await recorder.alert_opened(globex)
        return await _tracking(db, acme.id), await _tracking(db, globex.id)

    acme, globex = run(scenario)
    # Fri 16:00 UTC is 18:00 in Rome — closed; the hour runs Monday 09:00–10:00 Rome.
    assert acme.business_hours and acme.ack_due_at == datetime(2026, 9, 7, 8, 0)
    # Global UTC calendar: one working hour left on Friday.
    assert globex.ack_due_at == datetime(2026, 9, 4, 17, 0)
    assert globex.resolve_due_at == datetime(2026, 9, 7, 12, 0)  # 1h Friday + 3h Monday


def test_waiting_on_the_customer_pauses_and_resuming_pushes_the_due_back():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        clock = Clock()
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.alert_opened(alert)
        clock.at(T0 + timedelta(minutes=10))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="PENDING_CUSTOMER")
        paused = await _tracking(db, alert.id)
        clock.at(T0 + timedelta(minutes=20))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="PENDING_CUSTOMER")  # already paused
        clock.at(T0 + timedelta(hours=3, minutes=10))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="IN_PROGRESS")
        return paused, await _tracking(db, alert.id)

    paused, resumed = run(scenario)
    assert paused.paused_at == T0 + timedelta(minutes=10)
    assert resumed.paused_at is None
    assert resumed.paused_seconds == 3 * 3600 and resumed.pause_credit_seconds == 3 * 3600
    assert resumed.resolve_due_at == T0 + timedelta(hours=8 + 3)  # High default: 8h, plus the wait
    assert resumed.ack_due_at == T0 + timedelta(hours=1)  # acknowledged at the pause: not moved


def test_closing_a_waiting_item_banks_the_wait_before_resolving():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        clock = Clock()
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.alert_opened(alert)
        clock.at(T0 + timedelta(hours=1))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="PENDING_CUSTOMER")
        clock.at(T0 + timedelta(hours=11))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="CLOSED")
        return await _tracking(db, alert.id)

    row = run(scenario)
    assert row.paused_at is None and row.paused_seconds == 10 * 3600
    assert row.resolved_at == T0 + timedelta(hours=11)
    assert row.resolved_at <= row.resolve_due_at  # 11h wall, 1h of it the SOC's: met


def test_a_retarget_after_a_pause_keeps_the_credit():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        clock = Clock()
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.alert_opened(alert)
        clock.at(T0 + timedelta(minutes=5))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="PENDING_CUSTOMER")
        clock.at(T0 + timedelta(hours=2, minutes=5))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="IN_PROGRESS")
        async with db.session() as session:
            session.add(SlaPolicy(customer_code=None, entity_type="alert", severity="High", ack_minutes=30, resolve_minutes=60))
            await session.commit()
            moved = await retarget_open(session, now=clock())
            await session.commit()
        return moved, await _tracking(db, alert.id)

    moved, row = run(scenario)
    assert moved == 1
    assert row.resolve_due_at == T0 + timedelta(hours=1 + 2)  # the new 1h target, plus the 2h already waited


def test_calendars_are_replaced_resolved_and_cleared():
    async def scenario(db):
        async with db.session() as session:
            empty = await calendar_service.get_calendar(session, "ACME")
            await calendar_service.replace_calendar(session, CalendarIn(timezone="Europe/Rome", week=WEEKDAYS_9_17), "ana")
            await calendar_service.replace_calendar(
                session,
                CalendarIn(customer_code="ACME", timezone="America/New_York", week={"mon": [["08:00", "12:00"]]}, holidays=["2026-12-25"]),
                "ana",
            )
            await session.commit()
            own = await calendar_service.get_calendar(session, "ACME")
            listed = await calendar_service.customers_with_calendar(session)
            removed = await calendar_service.clear_calendar(session, "ACME")
            await session.commit()
            inherited = await calendar_service.get_calendar(session, "ACME")
            return empty, own, listed, removed, inherited

    empty, own, listed, removed, inherited = run(scenario)
    assert empty.source == "default" and empty.timezone == "UTC"
    assert own.source == "customer" and own.timezone == "America/New_York" and own.holidays == ["2026-12-25"]
    assert own.week["mon"] == [["08:00", "12:00"]] and own.week["tue"] == []
    assert listed == ["ACME"] and removed == 1
    assert inherited.source == "global" and inherited.timezone == "Europe/Rome"
