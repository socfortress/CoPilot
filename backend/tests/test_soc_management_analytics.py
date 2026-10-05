"""SOC Management (#1187) — from facts to dashboard sections, with hand-built facts.

Every figure the dashboard shows is computed in ``domain/analytics.py`` from plain
facts, so these tests pin the semantics without a database:

- cohort (by opening) vs activity (by when it happened);
- only tracked items carry timings and compliance;
- "breached now" counts only clocks still running;
- analysts are SOC users, and portal users' closures are reported separately.

Run with: cd backend && python -m pytest tests/test_soc_management_analytics.py
"""

import os
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.soc_management.domain import analytics  # noqa: E402
from app.soc_management.domain.analytics import ItemFact  # noqa: E402
from app.soc_management.domain.periods import Bucket  # noqa: E402
from app.soc_management.domain.periods import Period  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.sla import SlaState  # noqa: E402

START = datetime(2026, 9, 1)
PERIOD = Period(START, START + timedelta(days=30))
NOW = START + timedelta(days=30, hours=1)
SOC = {"ana", "bob"}

H = timedelta(hours=1)


def alert(id, *, opened=START + timedelta(days=1), ack=None, resolved=None, by=None, closer=None, **kw):
    """A High alert (1h ack / 8h resolve) unless overridden."""
    defaults = dict(
        entity=SlaEntity.ALERT,
        id=id,
        title=kw.pop("title", "Brute force"),
        customer_code=kw.pop("customer", "ACME"),
        severity=kw.pop("severity", "High"),
        status=kw.pop("status", "CLOSED" if resolved else "OPEN"),
        assigned_to=kw.pop("assigned_to", None),
        opened_at=opened,
        tracked=kw.pop("tracked", True),
        ack_due_at=opened + H,
        resolve_due_at=opened + 8 * H,
        first_ack_at=opened + ack if ack is not None else None,
        first_ack_by=by,
        resolved_at=opened + resolved if resolved is not None else None,
        resolved_by=closer,
    )
    defaults.update(kw)
    return ItemFact(**defaults)


def case(id, **kw):
    return alert(id, entity=SlaEntity.CASE, title=kw.pop("title", "Case"), **kw)


# ── facts ────────────────────────────────────────────────────────────────────


def test_untracked_items_have_no_timings_and_no_states():
    fact = alert(1, ack=10 * timedelta(minutes=1), resolved=2 * H, by="ana", closer="ana", tracked=False)
    assert fact.tta is None and fact.ttr is None
    assert fact.ack_state(NOW) is SlaState.NOT_TRACKED and fact.resolve_state(NOW) is SlaState.NOT_TRACKED


def test_resolution_stops_the_response_clock_when_nobody_acknowledged():
    """A portal user closed it before the SOC touched it: no response is owed any more."""
    fact = alert(1, resolved=30 * timedelta(minutes=1), closer="portal")
    assert fact.ack_state(NOW) is SlaState.MET
    assert fact.tta is None  # but it is not a SOC response time


def test_live_state_ignores_clocks_already_achieved():
    late_ack = alert(1, ack=2 * H, by="ana", opened=NOW - 3 * H)  # ack breached, resolve still running and on track
    assert late_ack.ack_state(NOW) is SlaState.BREACHED
    assert late_ack.live_state(NOW) is SlaState.ON_TRACK


# ── headline ─────────────────────────────────────────────────────────────────


def test_headline_cohort_volumes_times_and_compliance():
    facts = [
        alert(1, ack=10 * timedelta(minutes=1), resolved=2 * H, by="ana", closer="ana"),  # both met
        alert(2, ack=2 * H, resolved=10 * H, by="bob", closer="bob"),  # both breached
        alert(3, opened=START - timedelta(days=3), resolved=timedelta(days=4), closer="ana"),  # opened before, resolved in period
        alert(4, tracked=False, resolved=H, closer="portal"),  # backfilled: counts, no timings
    ]
    head = analytics.entity_headline(facts, PERIOD, NOW, SOC)
    assert head.opened == 3  # 1, 2, 4 opened in the period
    assert head.resolved == 4  # every resolution happened in the period
    assert head.resolved_by_customer == 1
    assert head.tta.count == 2 and head.tta.median == (600 + 7200) / 2
    assert (head.sla.ack.met, head.sla.ack.breached) == (1, 1)
    assert head.sla.resolve.rate == 50.0


def test_headline_rates_divide_by_what_they_can():
    facts = [
        alert(1, verdict="FALSE_POSITIVE", in_case=True),
        alert(2, verdict="TRUE_POSITIVE"),
        alert(3),
        alert(4, escalated=True),
    ]
    head = analytics.headline(facts, [], PERIOD, NOW, SOC)
    assert head.false_positive_rate == 50.0  # of 2 reviewed, not of 4
    assert head.reviewed_alerts == 2
    assert head.case_conversion_rate == 25.0
    assert head.escalated_alerts == 1
    assert analytics.headline([], [], PERIOD, NOW, SOC).false_positive_rate is None


def test_previous_period_is_computed_from_the_same_facts():
    previous = PERIOD.previous()
    facts = [alert(1), alert(2, opened=previous.start + H), alert(3, opened=previous.start + 2 * H)]
    assert analytics.entity_headline(facts, PERIOD, NOW, SOC).opened == 1
    assert analytics.entity_headline(facts, previous, NOW, SOC).opened == 2


# ── severities & trends ──────────────────────────────────────────────────────


def test_severity_rows_cover_every_severity_most_severe_first():
    window = [alert(1, severity="Critical"), alert(2, severity="Low", resolved=H, closer="ana")]
    open_now = [alert(1, severity="Critical", opened=NOW - 9 * H)]
    rows = analytics.severity_rows(SlaEntity.ALERT, window, open_now, PERIOD, NOW)
    assert [row.severity for row in rows] == ["Critical", "High", "Medium", "Low", "Informational"]
    critical = rows[0]
    assert (critical.opened, critical.open_now, critical.breached_now) == (1, 1, 1)
    assert rows[3].resolved == 1


def test_trends_bucket_openings_and_resolutions_separately():
    facts = [
        alert(1, opened=START + H, resolved=timedelta(days=2), closer="ana"),
        alert(2, opened=START + 2 * H),
        case(3, opened=START + timedelta(days=2)),
    ]
    points = analytics.trends(facts[:2], facts[2:], PERIOD, Bucket.DAY, NOW)
    assert len(points) == 30
    assert points[0].alerts_opened == 2 and points[0].alerts_resolved == 0
    assert points[2].alerts_resolved == 1 and points[2].cases_opened == 1
    assert points[0].sla_rate == 0.0  # alert 1 resolved after 2 days (breach); alert 2 still open and overdue
    assert points[5].sla_rate is None  # nothing opened: no rate, not 0%


# ── analysts ─────────────────────────────────────────────────────────────────


def test_analyst_activity_is_attributed_to_who_did_it_in_the_period():
    alerts = [
        alert(1, ack=10 * timedelta(minutes=1), resolved=2 * H, by="ana", closer="bob"),
        alert(2, ack=20 * timedelta(minutes=1), by="ana"),
        alert(3, resolved=H, closer="portal-user"),  # not SOC
        alert(4, opened=START - timedelta(days=10), ack=timedelta(days=10, hours=1), by="bob"),  # opened before, acked inside the period
    ]
    open_alerts = [alert(2, assigned_to="ana", opened=NOW - 30 * timedelta(minutes=1), ack=None)]
    rows = {row.username: row for row in analytics.analysts(alerts, [], open_alerts, [], PERIOD, NOW, SOC)}
    assert set(rows) == {"ana", "bob"}
    assert rows["ana"].alerts_acknowledged == 2 and rows["ana"].alerts_resolved == 0
    assert rows["ana"].open_alerts == 1
    assert rows["bob"].alerts_resolved == 1 and rows["bob"].alerts_acknowledged == 1
    assert rows["bob"].sla.rate == 100.0  # alert 1 closed in 2h against an 8h target


def test_analysts_with_only_workload_still_appear():
    rows = analytics.analysts([], [], [alert(9, assigned_to="bob")], [], PERIOD, NOW, SOC)
    assert [row.username for row in rows] == ["bob"]


# ── rules ────────────────────────────────────────────────────────────────────


def test_rules_rank_by_volume_and_flag_noisy_ones():
    alerts = [alert(i, title="Noisy", verdict="FALSE_POSITIVE", source="wazuh") for i in range(5)]
    alerts += [alert(10, title="Noisy", verdict="TRUE_POSITIVE", source="graylog")]
    alerts += [alert(20 + i, title="Real", verdict="TRUE_POSITIVE", in_case=True) for i in range(3)]
    rows = analytics.rules(alerts, PERIOD, Bucket.DAY, NOW)
    noisy, real = rows
    assert (noisy.alert_name, noisy.alerts, noisy.false_positives, noisy.reviewed) == ("Noisy", 6, 5, 6)
    assert noisy.noisy and noisy.false_positive_rate == 83.3
    assert noisy.sources == ["graylog", "wazuh"]
    assert sum(noisy.series) == 6 and len(noisy.series) == 30
    assert not real.noisy and real.in_case == 3


def test_a_rule_needs_enough_reviews_to_be_called_noisy():
    rows = analytics.rules([alert(i, verdict="FALSE_POSITIVE") for i in range(4)], PERIOD, Bucket.DAY, NOW)
    assert rows[0].false_positive_rate == 100.0 and not rows[0].noisy


# ── customers & workload ─────────────────────────────────────────────────────


def test_customer_rows():
    alerts = [alert(1, customer="ACME", title="A"), alert(2, customer="ACME", title="A"), alert(3, customer="GLOBEX", title="B")]
    cases = [case(4, customer="GLOBEX")]
    open_alerts = [alert(1, customer="ACME", opened=NOW - 10 * H)]
    rows = {row.customer_code: row for row in analytics.customers(alerts, cases, open_alerts, [], PERIOD, NOW)}
    assert rows["ACME"].alerts == 2 and rows["ACME"].top_rule == "A" and rows["ACME"].breached_now == 1
    assert rows["GLOBEX"].cases == 1 and rows["GLOBEX"].open_now == 0


def test_workload_counts_open_items_by_severity_and_assignee():
    open_alerts = [
        alert(1, severity="Critical", opened=NOW - 2 * H, assigned_to="ana"),  # ack overdue
        alert(2, severity="High", opened=NOW - 50 * timedelta(minutes=1)),  # ack at risk, unassigned
        alert(3, severity="Low", opened=NOW - 10 * timedelta(minutes=1), assigned_to="ana"),
    ]
    open_cases = [case(4, severity="High", opened=NOW - 3 * H, ack=H, by="bob", assigned_to="bob")]  # acked; resolve on track
    load = analytics.workload(open_alerts, open_cases, NOW)
    assert (load.open_alerts, load.open_cases, load.unassigned_alerts, load.unassigned_cases) == (3, 1, 1, 0)
    assert load.breached == 1 and load.at_risk == 1
    assert load.oldest_unassigned_at == NOW - 50 * timedelta(minutes=1)
    by_user = {entry.username: entry for entry in load.by_assignee}
    assert by_user["ana"].alerts == 2 and by_user["ana"].breached == 1
    assert by_user["bob"].cases == 1 and by_user["bob"].breached == 0
    assert next(s for s in load.by_severity if s.severity == "High").at_risk == 1


# ── attention ────────────────────────────────────────────────────────────────


def test_attention_lists_breached_first_most_overdue_on_top_then_at_risk():
    facts = [
        alert(1, opened=NOW - 2 * H),  # ack 1h overdue
        alert(2, opened=NOW - 5 * H),  # ack 4h overdue
        alert(3, opened=NOW - 50 * timedelta(minutes=1)),  # ack at risk
        alert(4, opened=NOW - 10 * timedelta(minutes=1)),  # on track: not listed
        alert(5, opened=NOW - 2 * H, resolved=H, closer="ana"),  # closed: not listed
    ]
    items = analytics.attention_items(facts, NOW)
    assert [item.id for item in items] == [2, 1, 3]
    assert items[0].state is SlaState.BREACHED and items[0].clock == "ack"
    assert items[0].overdue_seconds == 4 * 3600
    assert items[2].state is SlaState.AT_RISK and items[2].overdue_seconds < 0


def test_attention_chases_the_resolution_once_the_response_is_done():
    fact = alert(1, opened=NOW - 9 * H, ack=10 * timedelta(minutes=1), by="ana")
    (item,) = analytics.attention_items([fact], NOW)
    assert item.clock == "resolve" and item.state is SlaState.BREACHED
