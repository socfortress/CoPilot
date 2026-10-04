"""SOC Management (#1187) — the dashboard service on a real database.

Seeds alerts and cases through the recorder (as the routes do), then reads the dashboard
as different users. What must hold:

- figures are the seeded ones;
- an analyst assigned to one customer counts only that customer — in every section;
- per-analyst rows are the admin's view: an analyst sees only their own;
- severity and source filters narrow what is counted;
- the attention list, the per-item SLA and the PDF report read the same snapshot.

Run with: cd backend && python -m pytest tests/test_soc_management_metrics.py
"""

import asyncio
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.services.customer_report_branding import (  # noqa: E402
    _socfortress_theme,
)
from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402
from app.soc_management.domain.periods import Period  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.sla import SlaState  # noqa: E402
from app.soc_management.services import metrics  # noqa: E402
from app.soc_management.services import report  # noqa: E402
from app.soc_management.services.datasets import FactFilters  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from tests.soc_management_support import T0  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

ADMIN = SimpleNamespace(id=1, username="admin", role_id=1)
ANA = SimpleNamespace(id=2, username="ana", role_id=2)  # assigned to ACME only
BOB = SimpleNamespace(id=3, username="bob", role_id=2)  # unassigned: deployment-wide
PERIOD = Period(T0 - timedelta(days=1), T0 + timedelta(days=6))
NOW = T0 + timedelta(days=5)


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


async def _seed(db: Db) -> dict:
    """ACME: three alerts (one acked+closed in SLA, one breached open, one Low), one case.
    GLOBEX: one Critical alert closed late by bob."""
    async with db.session() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                User(id=3, username="bob", password="x" * 8, email="bob@example.com", role_id=2),
                User(id=4, username="portal", password="x" * 8, email="portal@example.com", role_id=4),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add(UserCustomerAccess(user_id=2, customer_code="ACME"))
        await session.commit()
        a1 = await add_alert(session, name="Brute force", customer="ACME", status="CLOSED", verdict="TRUE_POSITIVE")
        a2 = await add_alert(session, name="Brute force", customer="ACME", assigned_to="ana", verdict="FALSE_POSITIVE")
        a3 = await add_alert(session, name="Port scan", customer="ACME", severity="Low", source="graylog")
        g1 = await add_alert(session, name="Ransomware", customer="GLOBEX", severity="Critical", status="CLOSED")
        c1 = await add_case(session, customer="ACME", assigned_to="ana")
        session.add(CaseAlertLink(case_id=c1.id, alert_id=a1.id))
        await session.commit()

    clock = Clock(T0)
    recorder = SlaLifecycleRecorder(db.factory, clock=clock)
    for alert in (a1, a2, a3, g1):
        await recorder.alert_opened(alert)
    await recorder.case_opened(c1)
    ana, bob = Actor("ana", True), Actor("bob", True)

    clock.now = T0 + timedelta(minutes=10)
    await recorder.alert_action(a1.id, LifecycleAction.ASSIGNED, ana, assignee="ana")
    await recorder.case_action(c1.id, LifecycleAction.ASSIGNED, ana, assignee="ana")
    clock.now = T0 + timedelta(hours=2)
    await recorder.alert_action(a1.id, LifecycleAction.STATUS_CHANGED, ana, to_status="CLOSED")
    clock.now = T0 + timedelta(hours=6)  # Critical: 15m ack / 4h resolve → both breached
    await recorder.alert_action(g1.id, LifecycleAction.STATUS_CHANGED, bob, to_status="CLOSED")
    return {"a1": a1.id, "a2": a2.id, "a3": a3.id, "g1": g1.id, "c1": c1.id}


def run(scenario):
    async def _inner():
        db = await Db().create()
        try:
            ids = await _seed(db)
            async with db.session() as session:
                with patch("app.soc_management.services.metrics.utc_now", lambda: NOW):
                    return await scenario(session, ids)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def _dashboard(user, **query):
    return lambda session, ids: metrics.build_dashboard(session, user, metrics.DashboardQuery(period=PERIOD, **query))


def test_admin_sees_every_customer_with_the_seeded_figures():
    dash = run(_dashboard(ADMIN))
    alerts = dash.headline.alerts
    assert alerts.opened == 4 and alerts.resolved == 2
    # a1 met; g1 closed late; a2 (High, 8h) and a3 (Low, 3d) still open past due
    assert alerts.sla.resolve.met == 1 and alerts.sla.resolve.breached == 3
    assert alerts.tta.median == 10 * 60 + (6 * 3600 - 10 * 60) / 2  # a1 10m, g1 6h
    assert dash.headline.false_positive_rate == 50.0 and dash.headline.reviewed_alerts == 2
    assert dash.headline.case_conversion_rate == 25.0
    assert {row.customer_code: row.customer_name for row in dash.customers} == {"ACME": "Acme Corp", "GLOBEX": "Globex"}
    assert {row.username for row in dash.analysts} == {"ana", "bob"}
    assert dash.viewer.sees_all_analysts and dash.customer_codes is None
    assert dash.tracking_since == T0


def test_workload_and_attention_are_the_same_snapshot():
    dash = run(_dashboard(ADMIN))
    assert dash.workload.open_alerts == 2 and dash.workload.open_cases == 1
    assert dash.workload.unassigned_alerts == 1
    attention_ids = {(item.entity, item.id) for item in dash.attention}
    breached_open = {(item.entity, item.id) for item in dash.attention if item.state is SlaState.BREACHED}
    assert len(breached_open) == dash.workload.breached
    assert (SlaEntity.ALERT, 1) not in attention_ids  # closed in time


def test_a_scoped_analyst_counts_only_their_customer_and_sees_only_their_row():
    dash = run(_dashboard(ANA))
    assert dash.headline.alerts.opened == 3
    assert {row.customer_code for row in dash.customers} == {"ACME"}
    assert [row.username for row in dash.analysts] == ["ana"]
    assert [load.username for load in dash.workload.by_assignee] == ["ana"]
    assert not dash.viewer.sees_all_analysts
    assert dash.customer_codes == ["ACME"]
    assert dash.policy.customer_code == "ACME"  # one customer in scope: its policy is shown


def test_an_unassigned_analyst_is_deployment_wide_but_still_sees_only_their_row():
    dash = run(_dashboard(BOB))
    assert dash.headline.alerts.opened == 4
    assert [row.username for row in dash.analysts] == ["bob"]


def test_an_admin_can_narrow_to_customers():
    dash = run(_dashboard(ADMIN, customer_codes=["GLOBEX"]))
    assert dash.headline.alerts.opened == 1 and dash.headline.cases.opened == 0
    assert [row.username for row in dash.analysts] == ["bob"]


def test_severity_and_source_filters():
    critical = run(_dashboard(ADMIN, filters=FactFilters(severities=("Critical",))))
    assert critical.headline.alerts.opened == 1
    graylog = run(_dashboard(ADMIN, filters=FactFilters(sources=("graylog",))))
    assert graylog.headline.alerts.opened == 1
    assert graylog.headline.cases.opened == 1  # cases carry no source and are not narrowed by it


def test_rules_section():
    dash = run(_dashboard(ADMIN))
    by_name = {rule.alert_name: rule for rule in dash.rules}
    assert by_name["Brute force"].alerts == 2 and by_name["Brute force"].in_case == 1
    assert by_name["Brute force"].false_positive_rate == 50.0


def test_attention_endpoint_filters_by_entity_and_state():
    async def scenario(session, ids):
        everything = await metrics.build_attention(session, ADMIN, None, FactFilters(), None, None, 50)
        alerts_only = await metrics.build_attention(session, ADMIN, None, FactFilters(), SlaEntity.ALERT, SlaState.BREACHED, 50)
        scoped = await metrics.build_attention(session, ANA, ["GLOBEX"], FactFilters(), None, None, 50)
        return everything, alerts_only, scoped

    everything, alerts_only, scoped = run(scenario)
    assert everything.total >= alerts_only.total >= 1
    assert all(item.entity is SlaEntity.ALERT and item.state is SlaState.BREACHED for item in alerts_only.items)
    assert scoped.total == 0  # ana asked for a customer she cannot see


def test_item_sla_is_visible_only_within_scope():
    async def scenario(session, ids):
        own = await metrics.item_sla(session, ANA, SlaEntity.ALERT, ids["a1"])
        foreign = await metrics.item_sla(session, ANA, SlaEntity.ALERT, ids["g1"])
        admin_view = await metrics.item_sla(session, ADMIN, SlaEntity.ALERT, ids["g1"])
        case = await metrics.item_sla(session, ANA, SlaEntity.CASE, ids["c1"])
        return own, foreign, admin_view, case

    own, foreign, admin_view, case = run(scenario)
    assert foreign is None
    assert own.ack.state is SlaState.MET and own.ack.by == "ana" and own.ack.action == "assigned"
    assert own.resolve.state is SlaState.MET and own.resolve.target_minutes == 8 * 60
    assert admin_view.resolve.state is SlaState.BREACHED
    assert case.ack.state is SlaState.MET


def test_report_context_and_html_render_from_the_snapshot():
    async def scenario(session, ids):
        snapshot = await metrics.snapshot_for_user(session, ADMIN, metrics.DashboardQuery(period=PERIOD))

        async def static_theme(*args, **kwargs):
            return _socfortress_theme()  # the portal branding tables are not in this database

        chart = "data:image/png;base64,AA"
        with patch.object(report, "line_png", lambda *a, **k: chart), patch.object(report, "hbar_png", lambda *a, **k: chart), patch.object(
            report,
            "resolve_theme",
            static_theme,
        ):
            context = await report.build_report_context(session, snapshot)
        return context, report.render_html(context)

    context, html = run(scenario)
    assert context["scope"] == "All customers"
    assert context["alerts"]["opened"] == 4
    assert [row["severity"] for row in context["alert_severities"]][0] == "Critical"
    assert "Service Performance &amp; SLA" in html
    assert "Brute force" in html and "Acme Corp" in html
    assert "<script" not in html


def test_customer_sla_context_is_one_customer_and_names_no_analyst():
    async def scenario(session, ids):
        return await report.customer_sla_context(session, "ACME", PERIOD.start, PERIOD.end)

    sla = run(scenario)
    assert sla["has_data"] is True
    assert sla["alerts"]["opened"] == 3
    assert sla["alerts"]["resolve"]["rate"] == "33.3%"  # a1 met; a2 and a3 overdue
    assert "analysts" not in sla


# ── business hours and waiting on the customer ───────────────────────────────

ROME_WEEK = {day: [["09:00", "17:00"]] for day in ("mon", "tue", "wed", "thu", "fri")}


async def _rome_business_hours_and_paused(session, alert_id):
    """ACME on Rome business hours; ``alert_id`` acked on that basis, waiting on the customer
    for the last hour after an earlier 10-minute wait that banked 30 working minutes."""
    from sqlalchemy import update

    from app.incidents.models import Alert
    from app.soc_management.models.sla import AlertSlaTracking
    from app.soc_management.models.sla import SlaCalendar

    session.add(SlaCalendar(customer_code="ACME", timezone="Europe/Rome", week=ROME_WEEK, holidays=[]))
    await session.execute(
        update(AlertSlaTracking)
        .where(AlertSlaTracking.alert_id == alert_id)
        .values(
            business_hours=True,
            # T0 is Tue 08:00 UTC = 10:00 Rome; 60 working minutes + 30 of credit → 11:30 Rome.
            ack_due_at=T0 + timedelta(minutes=90),
            resolve_due_at=NOW + timedelta(days=1),  # still running when the wait began
            paused_at=NOW - timedelta(hours=1),
            paused_seconds=600,
            pause_credit_seconds=1800,
        ),
    )
    await session.execute(update(Alert).where(Alert.id == alert_id).values(status="PENDING_CUSTOMER"))
    await session.commit()


def test_item_sla_reads_business_hours_and_the_wait_on_their_basis():
    async def scenario(session, ids):
        await _rome_business_hours_and_paused(session, ids["a2"])
        return await metrics.item_sla(session, ADMIN, SlaEntity.ALERT, ids["a2"]), await metrics.item_sla(
            session,
            ADMIN,
            SlaEntity.ALERT,
            ids["a3"],
        )

    paused, plain = run(scenario)
    assert paused.business_hours and paused.calendar_timezone == "Europe/Rome"
    assert paused.ack.target_minutes == 60  # working minutes to the due time, less the banked wait
    assert paused.paused_at is not None
    assert paused.paused_seconds == 600 + 3600  # the banked wait plus the current one
    assert paused.resolve.state is SlaState.PAUSED
    assert not plain.business_hours and plain.calendar_timezone is None and plain.paused_seconds == 0


def test_facts_carry_the_customers_clock_and_the_wait():
    from app.soc_management.domain.calendar import CONTINUOUS
    from app.soc_management.domain.calendar import BusinessCalendar
    from app.soc_management.services import calendars as calendar_service
    from app.soc_management.services import datasets

    async def scenario(session, ids):
        await _rome_business_hours_and_paused(session, ids["a2"])
        book = await calendar_service.load_book(session)
        everything = datasets.Visibility(alert_filters=[], case_codes=None)
        facts = {fact.id: fact for fact in await datasets.open_alerts(session, everything, FactFilters(), book)}
        return facts[ids["a2"]], facts[ids["a3"]]

    paused, plain = run(scenario)
    assert isinstance(paused.clock, BusinessCalendar) and paused.clock.timezone == "Europe/Rome"
    assert paused.is_paused and paused.paused_seconds == 600
    assert plain.clock is CONTINUOUS and not plain.is_paused


def test_the_report_counts_what_waits_on_the_customer():
    async def scenario(session, ids):
        await _rome_business_hours_and_paused(session, ids["a2"])
        snapshot = await metrics.snapshot_for_user(session, ADMIN, metrics.DashboardQuery(period=PERIOD))

        async def static_theme(*args, **kwargs):
            return _socfortress_theme()

        chart = "data:image/png;base64,AA"
        with patch.object(report, "line_png", lambda *a, **k: chart), patch.object(report, "hbar_png", lambda *a, **k: chart), patch.object(
            report,
            "resolve_theme",
            static_theme,
        ):
            context = await report.build_report_context(session, snapshot)
        return snapshot, context, report.render_html(context)

    snapshot, context, html = run(scenario)
    assert snapshot.workload.waiting_on_customer == 1
    assert context["workload"]["waiting_on_customer"] == 1
    assert "Waiting on the customer (clocks stopped)" in html


# ── source filter options ────────────────────────────────────────────────────


def test_source_options_are_the_sources_the_caller_can_see_busiest_first():
    async def scenario(session, _ids):
        everything = await metrics.build_sources(session, ADMIN, None)
        scoped = await metrics.build_sources(session, ANA, None)
        narrowed = await metrics.build_sources(session, ADMIN, ["GLOBEX"])
        foreign = await metrics.build_sources(session, ANA, ["GLOBEX"])
        return everything, scoped, narrowed, foreign

    everything, scoped, narrowed, foreign = run(scenario)
    pairs = lambda response: [(option.source, option.alerts) for option in response.sources]  # noqa: E731
    # ACME: wazuh ×2, graylog ×1; GLOBEX: wazuh ×1 — taken from the alerts, not from a configuration.
    assert pairs(everything) == [("wazuh", 3), ("graylog", 1)]
    assert pairs(scoped) == [("wazuh", 2), ("graylog", 1)]  # ana sees ACME only
    assert pairs(narrowed) == [("wazuh", 1)]
    assert pairs(foreign) == []  # asking for another tenant widens nothing
