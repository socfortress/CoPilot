"""SOC Management (#1187) — SLA at-risk / breached notifications.

Pinned here:
- the domain owes one notice per clock and state, never one for a paused clock, and
  stamps a long-past breach silently;
- the notifier claims before it sends, so a second pass (or a racing worker) sends nothing;
- a breach settles the at-risk notice of the same clock;
- events go to internal routes only, carry the item's severity and assignee, and
  dedupe per clock;
- the default body says which target, how late and whose it is.

Run with: cd backend && python -m pytest tests/test_soc_management_notifier.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import sla_event  # noqa: E402
from app.notifications.services.notifications import (  # noqa: E402
    _format_default_body_core,
)
from app.soc_management.domain.analytics import ItemFact  # noqa: E402
from app.soc_management.domain.notices import STALE_AFTER  # noqa: E402
from app.soc_management.domain.notices import NoticeKind  # noqa: E402
from app.soc_management.domain.notices import SlaClock  # noqa: E402
from app.soc_management.domain.notices import notices_for  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.services.notifier import SlaNotifier  # noqa: E402
from tests.soc_management_support import T0  # noqa: E402
from tests.soc_management_support import AlertSlaTracking  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import tracking_row  # noqa: E402

# ── domain ───────────────────────────────────────────────────────────────────


def _fact(**fields):
    defaults = dict(
        entity=SlaEntity.ALERT,
        id=1,
        title="Brute force",
        customer_code="ACME",
        severity="High",
        status="OPEN",
        assigned_to="ana",
        opened_at=T0,
        tracked=True,
        ack_due_at=T0 + timedelta(hours=1),
        resolve_due_at=T0 + timedelta(hours=8),
    )
    defaults.update(fields)
    return ItemFact(**defaults)


def _kinds(notices):
    return [(n.clock, n.kind, n.silent) for n in notices]


def test_a_clock_in_its_last_quarter_owes_an_at_risk_notice_once():
    now = T0 + timedelta(minutes=50)
    assert _kinds(notices_for(_fact(), {}, now)) == [(SlaClock.ACK, NoticeKind.AT_RISK, False)]
    assert notices_for(_fact(), {"ack_at_risk_notified_at": now}, now) == []


def test_a_breach_is_owed_even_after_the_at_risk_notice_and_old_ones_are_silent():
    late = T0 + timedelta(hours=2)
    assert _kinds(notices_for(_fact(), {"ack_at_risk_notified_at": T0}, late)) == [(SlaClock.ACK, NoticeKind.BREACHED, False)]
    stale = T0 + timedelta(hours=1) + STALE_AFTER + timedelta(minutes=1)
    owed = notices_for(_fact(first_ack_at=T0 + timedelta(minutes=5), resolve_due_at=T0 + timedelta(hours=1)), {}, stale)
    assert _kinds(owed) == [(SlaClock.RESOLVE, NoticeKind.BREACHED, True)]
    assert owed[0].settles == ("resolve_at_risk_notified_at",)


def test_paused_closed_untracked_and_achieved_clocks_owe_nothing():
    late = T0 + timedelta(hours=10)
    assert notices_for(_fact(status="PENDING_CUSTOMER", paused_at=T0 + timedelta(minutes=5)), {}, late) == []
    assert notices_for(_fact(status="CLOSED", resolved_at=late), {}, late) == []
    assert notices_for(_fact(tracked=False), {}, late) == []
    acknowledged = _fact(first_ack_at=T0 + timedelta(minutes=5))
    assert [n.clock for n in notices_for(acknowledged, {}, late)] == [SlaClock.RESOLVE]


# ── events and wording ───────────────────────────────────────────────────────


def test_sla_triggers_are_internal_route_triggers():
    for trigger in (NotificationTrigger.SLA_AT_RISK, NotificationTrigger.SLA_BREACHED):
        assert trigger in DISPATCH_TRIGGERS and trigger.value in INTERNAL_TRIGGERS


def test_the_event_carries_severity_assignee_and_a_per_clock_dedupe_key():
    event = sla_event(
        breached=True,
        entity_type=EntityType.CASE,
        entity_id=42,
        title="Ransomware",
        severity="Critical",
        customer_code="ACME",
        assignee="ana",
        clock="acknowledge",
        due_at=T0,
        opened_at=T0 - timedelta(minutes=30),
        now=T0 + timedelta(minutes=20),
    )
    assert event.trigger is NotificationTrigger.SLA_BREACHED and event.severity.value == "Critical"
    assert event.assignee_username == "ana" and event.actor_username is None
    assert event.dedupe_key == "case:42:sla_breached:acknowledge"
    assert event.context["overdue_minutes"] == 20 and event.context["remaining_minutes"] is None
    body = _format_default_body_core(event)
    assert "*SLA breached* — acknowledge target, severity *Critical* (20 min overdue)" in body
    assert "Case: #42 — Ransomware" in body and "Assigned to: ana" in body


# ── the notifier on a real database ──────────────────────────────────────────


def run(scenario):
    async def _inner():
        db = await Db().create()
        try:
            return await scenario(db)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def test_the_notifier_sends_each_notice_once_and_a_breach_settles_the_at_risk_notice():
    sent = []

    async def scenario(db):
        async with db.session() as session:
            risky = await add_alert(session, name="Risky", assigned_to="ana")
            late = await add_alert(session, name="Late")
            calm = await add_alert(session, name="Calm")
            waiting = await add_alert(session, name="Waiting", status="PENDING_CUSTOMER")
            session.add_all(
                [
                    tracking_row(AlertSlaTracking, risky.id, ack_due_at=T0 + timedelta(hours=4)),
                    tracking_row(AlertSlaTracking, late.id),
                    tracking_row(AlertSlaTracking, calm.id, ack_due_at=T0 + timedelta(days=2), resolve_due_at=T0 + timedelta(days=3)),
                    tracking_row(AlertSlaTracking, waiting.id, paused_at=T0 + timedelta(minutes=5)),
                ],
            )
            await session.commit()
        now = T0 + timedelta(hours=3, minutes=30)
        notifier = SlaNotifier(db.factory, send=sent.append, clock=lambda: now)
        first = await notifier.run()
        second = await notifier.run()
        async with db.session() as session:
            late_row = await session.get(AlertSlaTracking, late.id)
        return first, second, late_row

    first, second, late_row = run(scenario)
    assert first == {"sent": 2, "silenced": 0, "lost_race": 0}
    assert second == {"sent": 0, "silenced": 0, "lost_race": 0}
    by_title = {event.context["title"]: event for event in sent}
    assert set(by_title) == {"Risky", "Late"}
    assert by_title["Risky"].trigger is NotificationTrigger.SLA_AT_RISK and by_title["Risky"].assignee_username == "ana"
    assert by_title["Late"].trigger is NotificationTrigger.SLA_BREACHED and by_title["Late"].context["clock"] == "acknowledge"
    assert late_row.ack_breached_notified_at is not None
    assert late_row.ack_at_risk_notified_at is not None  # settled by the breach: never sent afterwards
    assert late_row.resolve_at_risk_notified_at is None  # the resolve clock still has its own story


def test_a_notice_already_claimed_is_not_sent_again():
    sent = []

    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
            session.add(tracking_row(AlertSlaTracking, alert.id, ack_breached_notified_at=datetime(2026, 9, 1, 9, 5)))
            await session.commit()
        return await SlaNotifier(db.factory, send=sent.append, clock=lambda: T0 + timedelta(hours=2)).run()

    assert run(scenario) == {"sent": 0, "silenced": 0, "lost_race": 0} and sent == []
