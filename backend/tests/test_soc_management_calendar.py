"""SOC Management (#1187) — business hours and waiting on the customer, pure domain.

No database, no clock: every instant is explicit naive UTC.

Pinned here:
- a business calendar adds and measures working time only, across weekends, holidays,
  lunch breaks and daylight-saving changes, in the calendar's own timezone;
- invalid calendars are refused with a readable reason;
- per-customer calendars win over the global one, which wins over the default;
- at-risk is a quarter of the *working* window;
- a paused clock is neither on track nor late, unless it was already late when it stopped;
- resuming pushes running clocks back by the pause measured on their basis, and banks it;
- the time to resolve leaves the customer's wait out;
- a case's status change moves its alerts per ``status_cascade``.
"""

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

import pytest

from app.incidents.services.status_cascade import cascade_for
from app.soc_management.domain.analytics import ItemFact
from app.soc_management.domain.analytics import workload
from app.soc_management.domain.calendar import CONTINUOUS
from app.soc_management.domain.calendar import DEFAULT_CALENDAR
from app.soc_management.domain.calendar import BusinessCalendar
from app.soc_management.domain.calendar import CalendarBook
from app.soc_management.domain.calendar import office_hours
from app.soc_management.domain.lifecycle import Actor
from app.soc_management.domain.lifecycle import LifecycleAction
from app.soc_management.domain.lifecycle import LifecycleEvent
from app.soc_management.domain.lifecycle import plan_milestones
from app.soc_management.domain.lifecycle import resume_values
from app.soc_management.domain.lifecycle import resumes
from app.soc_management.domain.lifecycle import retarget_values
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.policy import SlaTargets
from app.soc_management.domain.sla import SlaState
from app.soc_management.domain.sla import evaluate

ROME = office_hours("Europe/Rome")  # Mon–Fri 09:00–17:00 local
HOUR = 3600

# 2026-09-04 is a Friday; Rome is UTC+2 in September (CEST).
FRI_16_ROME = datetime(2026, 9, 4, 14, 0)
MON_09_ROME = datetime(2026, 9, 7, 7, 0)


# ── calendar arithmetic ──────────────────────────────────────────────────────


def test_a_target_runs_over_the_weekend_in_working_time_only():
    assert ROME.add(FRI_16_ROME, 4 * HOUR) == datetime(2026, 9, 7, 10, 0)  # Mon 12:00 Rome
    assert ROME.elapsed(FRI_16_ROME, datetime(2026, 9, 7, 10, 0)) == 4 * HOUR


def test_an_item_opened_outside_hours_starts_counting_at_the_next_window():
    saturday = datetime(2026, 9, 5, 10, 0)
    assert ROME.add(saturday, 30 * 60) == MON_09_ROME + timedelta(minutes=30)
    assert ROME.elapsed(saturday, MON_09_ROME) == 0


def test_holidays_are_closed_days():
    calendar = BusinessCalendar(timezone="Europe/Rome", week=ROME.week, holidays=frozenset({date(2026, 9, 7)}))
    assert calendar.add(FRI_16_ROME, 2 * HOUR) == datetime(2026, 9, 8, 8, 0)  # Tue 10:00 Rome


def test_a_lunch_break_is_two_windows():
    calendar = BusinessCalendar(timezone="UTC", week={0: ((time(9), time(12)), (time(13), time(17)))})
    monday_11 = datetime(2026, 9, 7, 11, 0)
    assert calendar.add(monday_11, 2 * HOUR) == datetime(2026, 9, 7, 14, 0)
    assert calendar.elapsed(monday_11, datetime(2026, 9, 7, 14, 0)) == 2 * HOUR


def test_daylight_saving_moves_the_utc_window_not_the_local_one():
    # Rome leaves CEST on 2026-10-25: 09:00 local is 07:00 UTC before, 08:00 UTC after.
    before = ROME.windows_on(date(2026, 10, 23))
    after = ROME.windows_on(date(2026, 10, 26))
    assert before == [(datetime(2026, 10, 23, 7, 0), datetime(2026, 10, 23, 15, 0))]
    assert after == [(datetime(2026, 10, 26, 8, 0), datetime(2026, 10, 26, 16, 0))]


def test_the_continuous_clock_is_wall_time():
    assert CONTINUOUS.add(FRI_16_ROME, 4 * HOUR) == FRI_16_ROME + timedelta(hours=4)
    assert CONTINUOUS.elapsed(FRI_16_ROME, FRI_16_ROME - timedelta(hours=1)) == 0


@pytest.mark.parametrize(
    "data, reason",
    [
        ({"timezone": "Mars/Olympus", "week": {"mon": [["09:00", "17:00"]]}}, "Unknown timezone"),
        ({"week": {"mon": [["17:00", "09:00"]]}}, "start before it ends"),
        ({"week": {"mon": [["09:00", "13:00"], ["12:00", "17:00"]]}}, "overlap"),
        ({"week": {"funday": [["09:00", "17:00"]]}}, "Unknown weekday"),
        ({"week": {"mon": [["9am", "5pm"]]}}, "HH:MM"),
        ({"week": {}}, "at least one working window"),
    ],
)
def test_invalid_calendars_are_refused_with_a_reason(data, reason):
    with pytest.raises(ValueError, match=reason):
        BusinessCalendar.from_dict(data)


def test_a_calendar_round_trips_through_its_stored_shape():
    calendar = BusinessCalendar(timezone="Europe/Rome", week=ROME.week, holidays=frozenset({date(2026, 12, 25)}))
    stored = calendar.to_dict()
    assert stored["week"]["mon"] == [["09:00", "17:00"]] and stored["week"]["sat"] == []
    assert stored["holidays"] == ["2026-12-25"]
    assert BusinessCalendar.from_dict(stored) == calendar


def test_calendars_resolve_customer_then_global_then_default():
    acme = office_hours("America/New_York")
    book = CalendarBook(global_calendar=ROME, by_customer={"ACME": acme})
    assert book.for_customer("ACME") is acme and book.source("ACME") == "customer"
    assert book.for_customer("GLOBEX") is ROME and book.source("GLOBEX") == "global"
    assert CalendarBook().for_customer("ACME") is DEFAULT_CALENDAR and CalendarBook().source("ACME") == "default"
    assert book.clock("ACME", business_hours=False) is CONTINUOUS


def test_business_hours_targets_use_the_calendar():
    targets = SlaTargets(ack_minutes=60, resolve_minutes=8 * 60, business_hours=True)
    assert targets.ack_due(FRI_16_ROME, ROME) == datetime(2026, 9, 4, 15, 0)  # Fri 17:00 Rome, closing time
    assert targets.resolve_due(FRI_16_ROME, ROME) == datetime(2026, 9, 7, 14, 0)  # Mon 16:00 Rome


# ── states ───────────────────────────────────────────────────────────────────


def test_at_risk_is_a_quarter_of_the_working_window():
    due = ROME.add(FRI_16_ROME, 4 * HOUR)  # Monday 12:00 Rome
    sunday_evening = datetime(2026, 9, 6, 20, 0)
    assert evaluate(FRI_16_ROME, due, None, sunday_evening, ROME) is SlaState.ON_TRACK  # 3 of 4 working hours left
    assert evaluate(FRI_16_ROME, due, None, sunday_evening, CONTINUOUS) is SlaState.AT_RISK  # 14 of 68 wall hours left


def test_a_paused_clock_is_paused_unless_it_was_already_late():
    due = FRI_16_ROME + timedelta(hours=1)
    much_later = FRI_16_ROME + timedelta(days=3)
    assert evaluate(FRI_16_ROME, due, None, much_later, paused_at=FRI_16_ROME + timedelta(minutes=30)) is SlaState.PAUSED
    assert evaluate(FRI_16_ROME, due, None, much_later, paused_at=FRI_16_ROME + timedelta(hours=2)) is SlaState.BREACHED


# ── pause and resume ─────────────────────────────────────────────────────────

SOC = Actor(username="ana", is_soc=True)


def _status(to_status, at=FRI_16_ROME):
    return LifecycleEvent(action=LifecycleAction.STATUS_CHANGED, actor=SOC, at=at, to_status=to_status)


def test_waiting_on_the_customer_stamps_the_pause_once():
    plan = plan_milestones(_status("PENDING_CUSTOMER"))
    pause = [update for update in plan if "paused_at" in update.values]
    assert len(pause) == 1 and pause[0].guard_column == "paused_at" and pause[0].guard_is_null
    assert not resumes(_status("PENDING_CUSTOMER"))
    assert resumes(_status("IN_PROGRESS")) and resumes(_status("CLOSED"))
    assert not resumes(LifecycleEvent(action=LifecycleAction.COMMENTED, actor=SOC, at=FRI_16_ROME))


def test_resuming_extends_running_clocks_by_the_pause_on_their_basis():
    resumed = MON_09_ROME + timedelta(hours=1)  # paused Fri 16:00 → Mon 10:00 Rome: 2 working hours
    values = resume_values(
        paused_at=FRI_16_ROME,
        resumed_at=resumed,
        clock=ROME,
        ack_due_at=None,
        ack_running=False,
        resolve_due_at=datetime(2026, 9, 7, 10, 0),
        resolve_running=True,
        paused_seconds=60,
        pause_credit_seconds=30,
    )
    assert values["paused_at"] is None
    assert values["paused_seconds"] == 60 + int((resumed - FRI_16_ROME).total_seconds())  # wall time, for TTR
    assert values["pause_credit_seconds"] == 30 + 2 * HOUR  # working time, for the due dates
    assert values["resolve_due_at"] == datetime(2026, 9, 7, 12, 0)
    assert "ack_due_at" not in values  # an achieved clock keeps the due it was judged against


def test_a_retarget_keeps_the_time_already_waited():
    targets = SlaTargets(ack_minutes=60, resolve_minutes=120)
    values = retarget_values(FRI_16_ROME, targets, ack_running=False, resolve_running=True, credit_seconds=HOUR)
    assert values == {"resolve_due_at": FRI_16_ROME + timedelta(hours=3)}


def _fact(**fields):
    defaults = dict(
        entity=SlaEntity.ALERT,
        id=1,
        title="t",
        customer_code="ACME",
        severity="High",
        status="IN_PROGRESS",
        assigned_to="ana",
        opened_at=FRI_16_ROME,
        tracked=True,
        ack_due_at=FRI_16_ROME + timedelta(hours=1),
        resolve_due_at=FRI_16_ROME + timedelta(hours=8),
        first_ack_at=FRI_16_ROME + timedelta(minutes=5),
    )
    defaults.update(fields)
    return ItemFact(**defaults)


def test_time_to_resolve_leaves_the_customers_wait_out():
    fact = _fact(status="CLOSED", resolved_at=FRI_16_ROME + timedelta(hours=10), paused_seconds=6 * HOUR)
    assert fact.ttr == 4 * HOUR


def test_waiting_items_are_counted_and_not_chased():
    now = FRI_16_ROME + timedelta(days=2)
    waiting = _fact(id=1, status="PENDING_CUSTOMER", paused_at=FRI_16_ROME + timedelta(minutes=10))
    late = _fact(id=2)
    assert waiting.live_state(now) is SlaState.PAUSED and late.live_state(now) is SlaState.BREACHED
    load = workload([waiting, late], [], now)
    assert load.waiting_on_customer == 1 and load.breached == 1


# ── case → alerts cascade ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "old, new, to_status, moves, stays",
    [
        ("IN_PROGRESS", "CLOSED", "CLOSED", ["OPEN", "PENDING_CUSTOMER", "IN_PROGRESS"], []),
        ("CLOSED", "IN_PROGRESS", "IN_PROGRESS", ["CLOSED"], []),
        ("CLOSED", "PENDING_CUSTOMER", "PENDING_CUSTOMER", ["CLOSED"], []),
        ("IN_PROGRESS", "PENDING_CUSTOMER", "PENDING_CUSTOMER", ["OPEN", "IN_PROGRESS"], ["CLOSED"]),
        ("PENDING_CUSTOMER", "IN_PROGRESS", "IN_PROGRESS", ["PENDING_CUSTOMER"], ["CLOSED", "OPEN"]),
    ],
)
def test_a_case_status_change_moves_its_alerts(old, new, to_status, moves, stays):
    cascade = cascade_for(old, new)
    assert cascade is not None and cascade.to_status == to_status
    assert all(cascade.applies_to(status) for status in moves)
    assert not any(cascade.applies_to(status) for status in stays)


@pytest.mark.parametrize(
    "old, new",
    [("OPEN", "IN_PROGRESS"), ("IN_PROGRESS", "OPEN"), ("CLOSED", "CLOSED"), ("PENDING_CUSTOMER", "PENDING_CUSTOMER")],
)
def test_other_case_transitions_leave_the_alerts_alone(old, new):
    assert cascade_for(old, new) is None


# ── the API shape ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "week, reason",
    [
        ({"mon": [["09:00"]]}, r"a \[start, end\] pair"),
        ({"funday": [["09:00", "17:00"]]}, "Unknown weekday"),
        ({"mon": [["9", "17:00"]]}, "HH:MM"),
        ({"mon": [["17:00", "09:00"]]}, "start before it ends"),
        ({}, "at least one working window"),
    ],
)
def test_the_calendar_payload_is_refused_with_a_reason(week, reason):
    from pydantic import ValidationError

    from app.soc_management.schema.calendar import CalendarIn

    with pytest.raises(ValidationError, match=reason):
        CalendarIn(timezone="Europe/Rome", week=week)


def test_the_calendar_payload_becomes_the_domain_calendar():
    from app.soc_management.schema.calendar import CalendarIn

    payload = CalendarIn(
        customer_code="ACME",
        timezone="Europe/Rome",
        week={"mon": [["13:00", "17:00"], ["09:00", "12:00"]], "sat": []},
        holidays=["2026-12-25"],
    )
    calendar = payload.to_domain()
    assert calendar == BusinessCalendar(
        timezone="Europe/Rome",
        week={0: ((time(9), time(12)), (time(13), time(17)))},
        holidays=frozenset({date(2026, 12, 25)}),
    )
    assert payload.apply_to_open is False  # re-timing open items is always opt-in
