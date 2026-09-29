"""Customer Portal dashboard cards (``routes/dashboard.py``).

The cards must count exactly what the lists show, so they delegate to the same
``*_for_user`` helpers as the alerts/cases lists (whose visibility rules are pinned
by tests/test_alert_visibility_filters.py). These tests pin the delegation and the
agent count, which the route builds itself. Mocked session; no database.

Run with: cd backend && python -m pytest tests/test_customer_portal_dashboard.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal.routes.dashboard as dashboard  # noqa: E402
from app.incidents.services.db_operations import StatusCounts  # noqa: E402

USER = SimpleNamespace(id=1, username="customer1", role_id=4)


def _session(agent_count: int):
    result = MagicMock()
    result.scalar_one.return_value = agent_count
    return AsyncMock(execute=AsyncMock(return_value=result))


def _stats(accessible, customer_codes=None, agent_count=3):
    session = _session(agent_count)
    alert_total = AsyncMock(return_value=5)
    case_total = AsyncMock(return_value=2)
    with patch.object(
        dashboard.customer_access_handler,
        "resolve_effective_customers",
        AsyncMock(return_value=accessible),
    ), patch.object(
        dashboard,
        "alert_total_for_user",
        alert_total,
    ), patch.object(dashboard, "case_total_for_user", case_total):
        response = asyncio.run(dashboard.get_customer_dashboard_stats(customer_codes=customer_codes, current_user=USER, db=session))
    sql = str(session.execute.await_args.args[0])
    return response, sql, alert_total, case_total


def test_stats_take_alert_and_case_totals_from_the_list_helpers():
    response, _, alert_total, case_total = _stats(["ACME"], customer_codes=["ACME"])
    assert (response.total_alerts, response.total_cases, response.total_agents) == (5, 2, 3)
    alert_total.assert_awaited_once_with(USER, alert_total.await_args.args[1], customer_codes=["ACME"])
    case_total.assert_awaited_once_with(USER, case_total.await_args.args[1], customer_codes=["ACME"])


def test_agents_are_counted_within_the_users_customers():
    _, sql, _, _ = _stats(["ACME", "BETA"])
    assert "agents.customer_code IN" in sql


def test_a_deployment_wide_user_counts_every_agent():
    _, sql, _, _ = _stats(["*"])
    assert "customer_code" not in sql


def test_a_user_who_sees_no_customer_counts_no_agent():
    # An empty IN () matches nothing: the count is scoped, never widened to "all".
    _, sql, _, _ = _stats([], agent_count=0)
    assert "agents.customer_code IN" in sql


def test_alert_and_case_cards_forward_the_status_counts():
    counts = StatusCounts(total=9, open=4, in_progress=3, closed=2)
    with patch.object(dashboard, "alert_status_counts_for_user", AsyncMock(return_value=counts)) as alerts, patch.object(
        dashboard,
        "case_status_counts_for_user",
        AsyncMock(return_value=counts),
    ) as cases:
        alert_card = asyncio.run(dashboard.get_customer_dashboard_alert_stats(customer_codes=["ACME"], current_user=USER, db=AsyncMock()))
        case_card = asyncio.run(dashboard.get_customer_dashboard_case_stats(customer_codes=["ACME"], current_user=USER, db=AsyncMock()))

    for card in (alert_card, case_card):
        assert (card.total, card.open, card.in_progress, card.closed) == (9, 4, 3, 2)
    assert alerts.await_args.kwargs == {"customer_codes": ["ACME"]}
    assert cases.await_args.kwargs == {"customer_codes": ["ACME"]}


def test_empty_counts_are_zero_cards():
    with patch.object(dashboard, "alert_status_counts_for_user", AsyncMock(return_value=StatusCounts())):
        card = asyncio.run(dashboard.get_customer_dashboard_alert_stats(customer_codes=None, current_user=USER, db=AsyncMock()))
    assert (card.total, card.open, card.in_progress, card.closed) == (0, 0, 0, 0)
