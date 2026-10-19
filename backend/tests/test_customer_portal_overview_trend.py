"""The Customer Portal Overview's trend (#1273): opened and closed per hour, in SQL.

``GET /customer_portal/overview/trend`` counts alerts and cases opened (the SLA tracking
row's immutable ``opened_at``) and closed (its ``resolved_at``) per UTC hour, under the
lists' own visibility, and how many were open when the window starts; the portal sums the
hours into the viewer's local days, and from that anchor how many were open at each day's
end (the absolute Net, beside the relative opened − closed). This file
pins what is decided before the database: the window, the statements, the merge, and that
alerts and cases fail on their own. The real queries run in
tests/e2e/customer_portal_overview_trend_e2e.py.

Run with: cd backend && python -m pytest tests/test_customer_portal_overview_trend.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

from sqlalchemy.dialects import mysql

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.customer_portal.services import overview_trend as trend  # noqa: E402
from app.incidents.models import Alert  # noqa: E402

NOW = datetime(2026, 10, 17, 9, 41, 12)


def _sql(statement) -> str:
    return str(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


class TestWindow:
    def test_whole_hours_the_range_plus_a_day_up_to_the_current_hour(self):
        assert trend.trend_window("7d", NOW) == (datetime(2026, 10, 9, 10, 0), datetime(2026, 10, 17, 10, 0))
        assert trend.trend_window("30d", NOW) == (datetime(2026, 9, 16, 10, 0), datetime(2026, 10, 17, 10, 0))


class TestStatements:
    def test_alerts_are_counted_per_hour_from_their_tracking_row_under_the_lists_visibility(self):
        visibility = [Alert.customer_code.in_(["A"])]
        sql = _sql(trend.alert_hours_statement(visibility, *trend.trend_window("7d", NOW)))
        assert "UNION ALL" in sql and "GROUP BY events.hour" in sql
        assert sql.count("date_format(") == 2 and "%%Y-%%m-%%d %%H:00:00" in sql
        # opened_at and resolved_at, never alert_creation_time (ingest moves it to the last trigger).
        assert "soc_sla_alert_tracking.opened_at >= '2026-10-09 10:00:00'" in sql
        assert "soc_sla_alert_tracking.resolved_at < '2026-10-17 10:00:00'" in sql
        assert "alert_creation_time" not in sql
        # The visibility is in both halves of the union.
        assert sql.count("incident_management_alert.customer_code IN ('A')") == 2

    def test_cases_are_narrowed_to_the_callers_customers_and_not_at_all_deployment_wide(self):
        window = trend.trend_window("30d", NOW)
        scoped = _sql(trend.case_hours_statement(["A", "B"], *window))
        assert scoped.count("incident_management_case.customer_code IN ('A', 'B')") == 2
        assert "soc_sla_case_tracking.opened_at" in scoped and "case_creation_time" not in scoped
        assert "customer_code IN" not in _sql(trend.case_hours_statement(["*"], *window))

    def test_open_at_the_start_counts_what_was_opened_before_and_not_resolved_before(self):
        since, _ = trend.trend_window("30d", NOW)
        sql = _sql(trend.alert_open_at_statement([Alert.customer_code.in_(["A"])], since))
        assert "count(*)" in sql
        assert "soc_sla_alert_tracking.opened_at < '2026-09-16 10:00:00'" in sql
        assert "soc_sla_alert_tracking.resolved_at >= '2026-09-16 10:00:00'" in sql
        assert "incident_management_alert.customer_code IN ('A')" in sql

    def test_an_item_closed_without_resolved_at_is_never_counted_opened(self):
        # Counted opened but never closed, it would keep the absolute Net above zero for ever.
        sql = _sql(trend.alert_hours_statement([], *trend.trend_window("7d", NOW)))
        assert "NOT (soc_sla_alert_tracking.resolved_at IS NULL AND incident_management_alert.status = 'CLOSED')" in sql
        cases = _sql(trend.case_hours_statement(["*"], *trend.trend_window("7d", NOW)))
        assert "NOT (soc_sla_case_tracking.resolved_at IS NULL AND incident_management_case.case_status = 'CLOSED')" in cases

    def test_a_row_without_resolved_at_is_open_only_while_the_item_is_not_closed(self):
        # The SLA migration backfilled resolved_at from time_closed, which some closed items never had.
        since, _ = trend.trend_window("7d", NOW)
        alerts = _sql(trend.alert_open_at_statement([], since))
        assert "soc_sla_alert_tracking.resolved_at IS NULL AND incident_management_alert.status != 'CLOSED'" in alerts
        cases = _sql(trend.case_open_at_statement(["A"], since))
        assert "soc_sla_case_tracking.resolved_at IS NULL AND incident_management_case.case_status != 'CLOSED'" in cases
        assert "incident_management_case.customer_code IN ('A')" in cases
        assert "customer_code IN" not in _sql(trend.case_open_at_statement(["*"], since))


class TestMerge:
    def test_hours_from_both_come_together_oldest_first_in_utc(self):
        merged = trend.merge_hours(
            {"2026-10-16 08:00:00": (3, 1), "2026-10-15 23:00:00": (1, 0)},
            {"2026-10-16 08:00:00": (0, 2), "2026-10-17 00:00:00": (1, 1)},
        )
        assert [h.model_dump() for h in merged] == [
            {"hour": "2026-10-15T23:00:00Z", "alerts_opened": 1, "alerts_closed": 0, "cases_opened": 0, "cases_closed": 0},
            {"hour": "2026-10-16T08:00:00Z", "alerts_opened": 3, "alerts_closed": 1, "cases_opened": 0, "cases_closed": 2},
            {"hour": "2026-10-17T00:00:00Z", "alerts_opened": 0, "alerts_closed": 0, "cases_opened": 1, "cases_closed": 1},
        ]


class FakeSession:
    def __init__(self, fail_first=False):
        self.statements = []
        self.fail_first = fail_first
        self.rollback = AsyncMock()

    async def execute(self, statement):
        self.statements.append(statement)
        if self.fail_first and len(self.statements) == 1:
            raise RuntimeError("Lost connection to MySQL server during query")
        # The hours statement, then the open-at-the-start count, per entity.
        return SimpleNamespace(all=lambda: [("2026-10-16 08:00:00", 2, 1)], scalar_one=lambda: 7)


def _run(session, visibility, customers):
    with (
        patch.object(trend, "alert_visibility_filters_for_user", AsyncMock(return_value=visibility)),
        patch.object(trend.customer_access_handler, "resolve_effective_customers", AsyncMock(return_value=customers)),
    ):
        return asyncio.run(trend.get_overview_trend(SimpleNamespace(), session, "7d", NOW))


class TestTrend:
    def test_answers_the_window_the_hours_and_what_was_open_at_the_start_of_both(self):
        session = FakeSession()
        result = _run(session, [Alert.customer_code.in_(["A"])], ["A"])
        assert (result.since, result.until, result.range) == ("2026-10-09T10:00:00Z", "2026-10-17T10:00:00Z", "7d")
        assert result.hours[0].model_dump() == {
            "hour": "2026-10-16T08:00:00Z",
            "alerts_opened": 2,
            "alerts_closed": 1,
            "cases_opened": 2,
            "cases_closed": 1,
        }
        assert (result.alerts_open_at_since, result.cases_open_at_since) == (7, 7)
        assert len(session.statements) == 4

    def test_a_caller_who_sees_nothing_never_reaches_the_database(self):
        session = FakeSession()
        result = _run(session, None, [])
        assert (result.hours, session.statements) == ([], [])
        # Nothing visible is nothing open, not an unknown.
        assert (result.alerts_open_at_since, result.cases_open_at_since) == (0, 0)

    def test_alerts_and_cases_fail_on_their_own_without_saying_why_to_the_customer(self):
        session = FakeSession(fail_first=True)
        result = _run(session, [Alert.customer_code.in_(["A"])], ["A"])
        assert result.alerts_error == "Failed to load the alert trend"
        assert "MySQL" not in result.alerts_error
        assert result.cases_error is None and result.hours[0].cases_opened == 2
        # A failed entity has no anchor either: the portal must not show an absolute Net for it.
        assert (result.alerts_open_at_since, result.cases_open_at_since) == (None, 7)
        session.rollback.assert_awaited_once()
