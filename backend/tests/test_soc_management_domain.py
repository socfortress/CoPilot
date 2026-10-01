"""SOC Management (#1187) — the pure rules: policy resolution, lifecycle milestones,
SLA evaluation, statistics, periods and report formatting. No database, no clock.

Run with: cd backend && python -m pytest tests/test_soc_management_domain.py
"""

import os
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import Increment  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleEvent  # noqa: E402
from app.soc_management.domain.lifecycle import plan_milestones  # noqa: E402
from app.soc_management.domain.lifecycle import retarget_values  # noqa: E402
from app.soc_management.domain.periods import MAX_PERIOD  # noqa: E402
from app.soc_management.domain.periods import Bucket  # noqa: E402
from app.soc_management.domain.periods import Period  # noqa: E402
from app.soc_management.domain.periods import auto_bucket  # noqa: E402
from app.soc_management.domain.periods import bucket_starts  # noqa: E402
from app.soc_management.domain.periods import floor_to  # noqa: E402
from app.soc_management.domain.periods import requested_period  # noqa: E402
from app.soc_management.domain.policy import BUILTIN_TARGETS  # noqa: E402
from app.soc_management.domain.policy import SEVERITIES_DESC  # noqa: E402
from app.soc_management.domain.policy import PolicyRow  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.policy import SlaTargets  # noqa: E402
from app.soc_management.domain.policy import TargetSource  # noqa: E402
from app.soc_management.domain.policy import effective_matrix  # noqa: E402
from app.soc_management.domain.policy import resolve_targets  # noqa: E402
from app.soc_management.domain.policy import validate_minutes  # noqa: E402
from app.soc_management.domain.sla import Compliance  # noqa: E402
from app.soc_management.domain.sla import SlaState  # noqa: E402
from app.soc_management.domain.sla import evaluate  # noqa: E402
from app.soc_management.domain.sla import summarize  # noqa: E402
from app.soc_management.domain.stats import describe  # noqa: E402
from app.soc_management.domain.stats import percentile  # noqa: E402
from app.soc_management.schema.policy import PolicyCellIn  # noqa: E402
from app.soc_management.schema.policy import PolicyUpdateRequest  # noqa: E402
from app.soc_management.services import formatting as fmt  # noqa: E402

T0 = datetime(2026, 9, 1, 8, 0, 0)
ANALYST = Actor(username="ana", is_soc=True)
CUSTOMER = Actor(username="portal-user", is_soc=False)


# ── policy ───────────────────────────────────────────────────────────────────


def _row(customer, entity, severity, ack, resolve):
    return PolicyRow(customer_code=customer, entity=entity, severity=severity, ack_minutes=ack, resolve_minutes=resolve)


def test_builtin_defaults_cover_every_entity_and_severity_and_keep_informational_untracked():
    for entity in SlaEntity:
        assert set(BUILTIN_TARGETS[entity]) == set(SEVERITIES_DESC)
        info = BUILTIN_TARGETS[entity]["Informational"]
        assert (info.ack_minutes, info.resolve_minutes) == (None, None)
        critical = BUILTIN_TARGETS[entity]["Critical"]
        assert critical.ack_minutes < BUILTIN_TARGETS[entity]["High"].ack_minutes


def test_resolution_order_is_customer_then_global_then_default():
    rows = [
        _row(None, SlaEntity.ALERT, "High", 30, 240),
        _row("ACME", SlaEntity.ALERT, "High", 10, 60),
    ]
    assert resolve_targets(SlaEntity.ALERT, "High", "ACME", rows) == SlaTargets(10, 60, TargetSource.CUSTOMER)
    assert resolve_targets(SlaEntity.ALERT, "High", "OTHER", rows) == SlaTargets(30, 240, TargetSource.GLOBAL)
    assert resolve_targets(SlaEntity.ALERT, "Low", "ACME", rows).source is TargetSource.DEFAULT
    # An entity is its own namespace: a High *alert* row says nothing about High cases.
    assert resolve_targets(SlaEntity.CASE, "High", "ACME", rows).source is TargetSource.DEFAULT


def test_a_customer_row_replaces_the_whole_cell_not_one_clock():
    """A row with no resolve target means "no resolve promise", not "inherit it"."""
    rows = [_row(None, SlaEntity.ALERT, "High", 30, 240), _row("ACME", SlaEntity.ALERT, "High", 15, None)]
    assert resolve_targets(SlaEntity.ALERT, "High", "ACME", rows) == SlaTargets(15, None, TargetSource.CUSTOMER)


def test_global_scope_ignores_customer_rows():
    rows = [_row("ACME", SlaEntity.ALERT, "High", 10, 60)]
    assert resolve_targets(SlaEntity.ALERT, "High", None, rows).source is TargetSource.DEFAULT


def test_effective_matrix_has_every_cell_labelled():
    matrix = effective_matrix("ACME", [_row("ACME", SlaEntity.CASE, "Low", 60, 600)])
    assert set(matrix) == set(SlaEntity)
    assert list(matrix[SlaEntity.ALERT]) == list(SEVERITIES_DESC)
    assert matrix[SlaEntity.CASE]["Low"].source is TargetSource.CUSTOMER
    assert matrix[SlaEntity.CASE]["High"].source is TargetSource.DEFAULT


def test_due_times_are_measured_from_opening():
    targets = SlaTargets(15, 240)
    assert targets.ack_due(T0) == T0 + timedelta(minutes=15)
    assert targets.resolve_due(T0) == T0 + timedelta(hours=4)
    assert SlaTargets(None, None).ack_due(T0) is None


@pytest.mark.parametrize("value", [0, -5, 365 * 24 * 60 + 1])
def test_minutes_out_of_range_are_rejected(value):
    with pytest.raises(ValueError):
        validate_minutes(value)


def test_minutes_accept_none_and_bounds():
    assert validate_minutes(None) is None
    assert validate_minutes(1) == 1
    assert validate_minutes(365 * 24 * 60) == 365 * 24 * 60
    with pytest.raises(ValueError):
        validate_minutes(True)


def test_policy_cell_rejects_ack_longer_than_resolve_and_unknown_severity():
    with pytest.raises(ValidationError, match="acknowledge target cannot be longer"):
        PolicyCellIn(entity="alert", severity="High", ack_minutes=500, resolve_minutes=60)
    with pytest.raises(ValidationError, match="Expected one of"):
        PolicyCellIn(entity="alert", severity="Urgent", ack_minutes=5, resolve_minutes=60)
    # An inheriting cell carries no targets worth validating against each other.
    assert PolicyCellIn(entity="alert", severity="High", inherit=True, ack_minutes=500, resolve_minutes=60).inherit


def test_policy_update_rejects_duplicate_cells():
    cell = {"entity": "case", "severity": "Low", "ack_minutes": 5, "resolve_minutes": 60}
    with pytest.raises(ValidationError, match="Duplicate cell"):
        PolicyUpdateRequest(cells=[cell, cell])


# ── lifecycle ────────────────────────────────────────────────────────────────


def _plan(action, actor=ANALYST, **kwargs):
    return plan_milestones(LifecycleEvent(action=action, actor=actor, at=T0, **kwargs))


def test_actor_from_user_recognises_the_soc_roles():
    class _User:
        def __init__(self, role_id):
            self.username, self.role_id = "u", role_id

    assert Actor.from_user(_User(1)).is_soc and Actor.from_user(_User(2)).is_soc
    assert not Actor.from_user(_User(3)).is_soc and not Actor.from_user(_User(4)).is_soc
    assert Actor.system() == Actor(username=None, is_soc=False)


@pytest.mark.parametrize("action", list(LifecycleAction))
def test_every_soc_action_claims_the_first_response(action):
    plan = _plan(action)
    ack = [step for step in plan if step.guard_column == "first_ack_at"]
    assert len(ack) == 1
    assert ack[0].guard_is_null
    assert ack[0].values == {"first_ack_at": T0, "first_ack_by": "ana", "first_ack_action": action.value}


@pytest.mark.parametrize("actor", [CUSTOMER, Actor.system()])
def test_customers_and_automation_never_acknowledge(actor):
    plan = _plan(LifecycleAction.COMMENTED, actor=actor)
    assert plan == []


def test_assignment_stamps_first_assignment_but_unassigning_does_not():
    assert any(step.guard_column == "first_assigned_at" for step in _plan(LifecycleAction.ASSIGNED, assignee="bob"))
    assert not any(step.guard_column == "first_assigned_at" for step in _plan(LifecycleAction.ASSIGNED, assignee=None))


def test_closing_resolves_once_and_keeps_the_first_resolution():
    plan = _plan(LifecycleAction.STATUS_CHANGED, to_status="CLOSED")
    resolve = next(step for step in plan if step.guard_column == "resolved_at")
    assert resolve.guard_is_null and resolve.values == {"resolved_at": T0, "resolved_by": "ana"}
    first = next(step for step in plan if step.guard_column == "first_resolved_at")
    assert first.values == {"first_resolved_at": T0}


def test_a_customer_closing_resolves_without_acknowledging():
    plan = _plan(LifecycleAction.STATUS_CHANGED, actor=CUSTOMER, to_status="CLOSED")
    columns = {step.guard_column for step in plan}
    assert columns == {"resolved_at", "first_resolved_at"}


@pytest.mark.parametrize("status", ["OPEN", "IN_PROGRESS"])
def test_reopening_clears_the_resolution_only_if_resolved_and_counts_it(status):
    plan = _plan(LifecycleAction.STATUS_CHANGED, to_status=status)
    reopen = next(step for step in plan if step.guard_column == "resolved_at")
    assert reopen.guard_is_null is False
    assert reopen.values["resolved_at"] is None and reopen.values["resolved_by"] is None
    assert reopen.values["reopen_count"] == Increment(1)


def test_retarget_moves_only_running_clocks():
    targets = SlaTargets(30, 120)
    assert retarget_values(T0, targets, ack_running=True, resolve_running=True) == {
        "ack_due_at": T0 + timedelta(minutes=30),
        "resolve_due_at": T0 + timedelta(minutes=120),
    }
    assert retarget_values(T0, targets, ack_running=False, resolve_running=True) == {"resolve_due_at": T0 + timedelta(minutes=120)}
    assert retarget_values(T0, targets, ack_running=False, resolve_running=False) == {}


# ── SLA evaluation ───────────────────────────────────────────────────────────

DUE = T0 + timedelta(hours=4)


@pytest.mark.parametrize(
    "achieved, now, expected",
    [
        (T0 + timedelta(hours=1), T0 + timedelta(days=9), SlaState.MET),
        (DUE, DUE, SlaState.MET),  # on the dot counts as met
        (DUE + timedelta(seconds=1), DUE, SlaState.BREACHED),
        (None, DUE + timedelta(seconds=1), SlaState.BREACHED),
        (None, T0 + timedelta(hours=1), SlaState.ON_TRACK),
        (None, T0 + timedelta(hours=3), SlaState.AT_RISK),  # inside the last quarter
        (None, T0 + timedelta(hours=2, minutes=59), SlaState.ON_TRACK),
    ],
)
def test_evaluate(achieved, now, expected):
    assert evaluate(T0, DUE, achieved, now) is expected


def test_no_due_time_is_not_tracked_rather_than_met():
    assert evaluate(T0, None, None, T0 + timedelta(days=99)) is SlaState.NOT_TRACKED


def test_compliance_divides_by_decided_outcomes_only():
    states = [SlaState.MET] * 3 + [SlaState.BREACHED] + [SlaState.ON_TRACK, SlaState.AT_RISK, SlaState.NOT_TRACKED]
    compliance = summarize(states)
    assert (compliance.met, compliance.breached, compliance.decided) == (3, 1, 4)
    assert compliance.rate == 75.0
    assert Compliance().rate is None


# ── stats ────────────────────────────────────────────────────────────────────


def test_percentile_interpolates():
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 0) == 10.0
    assert percentile(values, 50) == 25.0
    assert percentile(values, 100) == 40.0
    assert percentile([], 50) is None
    with pytest.raises(ValueError):
        percentile(values, 101)


def test_describe_reports_median_mean_p90_and_ignores_none_and_negative():
    stats = describe([60, 120, None, 180, -5, 3600])
    assert stats.count == 4
    assert stats.median == 150.0
    assert stats.mean == 990.0
    assert stats.p90 == pytest.approx(2574.0)  # 180 + 0.7 × (3600 − 180)
    assert describe([]).median is None


def test_median_is_robust_to_a_bulk_close_of_old_noise():
    """Why the headline is the median: 50 week-old closes swing the mean by days."""
    stats = describe([600] * 100 + [7 * 86400] * 50)
    assert stats.median == 600
    assert stats.mean > 86400


# ── periods ──────────────────────────────────────────────────────────────────


def test_period_previous_is_adjacent_and_equal_length():
    period = Period(T0, T0 + timedelta(days=30))
    assert period.previous() == Period(T0 - timedelta(days=30), T0)
    assert period.contains(T0) and not period.contains(T0 + timedelta(days=30))


def test_requested_period_enforces_order_and_cap():
    with pytest.raises(ValueError):
        requested_period(T0, T0)
    with pytest.raises(ValueError):
        requested_period(T0, T0 + MAX_PERIOD + timedelta(seconds=1))
    # The internal loader may span two periods; only requests are capped.
    assert Period(T0, T0 + MAX_PERIOD * 2).length == MAX_PERIOD * 2


@pytest.mark.parametrize(
    "days, bucket",
    [(1, Bucket.HOUR), (2, Bucket.HOUR), (7, Bucket.DAY), (31, Bucket.DAY), (90, Bucket.WEEK), (365, Bucket.MONTH)],
)
def test_auto_bucket(days, bucket):
    assert auto_bucket(Period(T0, T0 + timedelta(days=days))) is bucket


def test_floor_and_bucket_starts():
    moment = datetime(2026, 9, 17, 14, 35, 12)  # a Thursday
    assert floor_to(moment, Bucket.HOUR) == datetime(2026, 9, 17, 14)
    assert floor_to(moment, Bucket.DAY) == datetime(2026, 9, 17)
    assert floor_to(moment, Bucket.WEEK) == datetime(2026, 9, 14)  # Monday
    assert floor_to(moment, Bucket.MONTH) == datetime(2026, 9, 1)
    starts = bucket_starts(Period(datetime(2026, 11, 15), datetime(2027, 2, 2)), Bucket.MONTH)
    assert starts == [datetime(2026, 11, 1), datetime(2026, 12, 1), datetime(2027, 1, 1), datetime(2027, 2, 1)]


# ── report formatting ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "seconds, text",
    [(None, "—"), (42, "42s"), (60, "1m"), (3599, "59m"), (3600, "1h"), (4800, "1h 20m"), (86400, "1d"), (2 * 86400 + 4 * 3600, "2d 4h")],
)
def test_duration_formatting(seconds, text):
    assert fmt.duration(seconds) == text


def test_rate_and_delta_formatting():
    assert fmt.rate(None) == "n/a" and fmt.rate(96.84) == "96.8%"
    assert fmt.rate_class(96) == "rate-good" and fmt.rate_class(90) == "rate-warn" and fmt.rate_class(10) == "rate-bad"
    assert fmt.rate_class(None) == "dim"
    assert fmt.delta(120, 100) == "+20%" and fmt.delta(80, 100) == "−20%" and fmt.delta(100, 100) == "±0%"
    assert fmt.delta(5, 0) == "new" and fmt.delta(0, 0) == "" and fmt.delta(None, 1) == ""
    assert fmt.target(None) == "no target" and fmt.target(90) == "1h 30m"
