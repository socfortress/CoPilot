"""Server-side agents list and searchable alert asset filter for the Customer Portal (#1185).

Unit tests with a mocked session: the SQL itself is exercised by
tests/e2e/customer_portal_overview_e2e.py against a real MySQL.

Run with: cd backend && python -m pytest tests/test_customer_portal_agents_and_filters.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi.routing import APIRoute  # noqa: E402

import app.customer_portal.routes.agents as agents_routes  # noqa: E402
import app.customer_portal.services.agents as agents_service  # noqa: E402
import app.incidents.services.db_operations as dbo  # noqa: E402

USER = SimpleNamespace(id=1, username="customer1", role_id=4)


def _sql(clauses):
    return " ".join(str(clause) for clause in clauses)


# ── agents: filters and scope ─────────────────────────────────────────────


def test_no_filters_add_no_clauses():
    assert agents_service._filter_clauses(agents_service.AgentFilters()) == []


def test_every_filter_becomes_a_clause():
    clauses = agents_service._filter_clauses(agents_service.AgentFilters(search=" web ", status="active", os="Linux", critical=True))
    sql = _sql(clauses)
    assert len(clauses) == 4
    for column in ("hostname", "ip_address", "agent_id", "wazuh_agent_status", "os", "critical_asset"):
        assert column in sql


def test_a_user_who_sees_no_customer_gets_an_empty_page_without_querying():
    session = AsyncMock()
    with patch.object(agents_service.customer_access_handler, "resolve_effective_customers", AsyncMock(return_value=[])):
        page = asyncio.run(agents_service.list_portal_agents(USER, session, agents_service.AgentFilters(), 1, 25))
    assert page.agents == [] and page.total == 0 and page.stats.total == 0
    session.execute.assert_not_awaited()


def test_export_of_nothing_is_just_the_header():
    session = AsyncMock()
    with patch.object(agents_service.customer_access_handler, "resolve_effective_customers", AsyncMock(return_value=[])):
        csv = asyncio.run(agents_service.export_portal_agents_csv(USER, session, agents_service.AgentFilters()))
    assert csv.strip() == ",".join(agents_service.CSV_HEADERS)
    session.execute.assert_not_awaited()


def test_page_size_is_capped():
    route = next(r for r in agents_routes.customer_portal_agents_router.routes if isinstance(r, APIRoute) and r.path == "/agents")
    page_size = next(p for p in route.dependant.query_params if p.name == "page_size")
    assert any(getattr(m, "le", None) == agents_routes.MAX_PAGE_SIZE for m in page_size.field_info.metadata)


def test_export_route_is_declared_before_any_agents_wildcard():
    paths = [r.path for r in agents_routes.customer_portal_agents_router.routes]
    assert paths.index("/agents/export") < paths.index("/agents")


# ── alert filter options ──────────────────────────────────────────────────


def _sees_no_alert():
    return patch.object(dbo, "alert_visibility_filters_for_user", AsyncMock(return_value=None))


def test_a_user_who_sees_no_alert_gets_no_filter_options_without_querying():
    session = AsyncMock()
    with _sees_no_alert():
        assert asyncio.run(dbo.get_alert_filter_options(USER, session)) == {"sources": [], "assets": [], "tags": []}
    session.execute.assert_not_awaited()


def test_a_user_who_sees_no_alert_finds_no_asset_without_querying():
    session = AsyncMock()
    with _sees_no_alert():
        assert asyncio.run(dbo.search_alert_asset_names(USER, session, "x", 20)) == []
    session.execute.assert_not_awaited()


def test_filter_options_can_leave_the_asset_names_out():
    session = AsyncMock()
    asset_names = AsyncMock(return_value=["host-1"])
    session.execute = AsyncMock(return_value=[])
    with patch.object(dbo, "alert_visibility_filters_for_user", AsyncMock(return_value=[])), patch.object(dbo, "_asset_names", asset_names):
        without = asyncio.run(dbo.get_alert_filter_options(USER, session, include_assets=False))
        with_assets = asyncio.run(dbo.get_alert_filter_options(USER, session))
    assert without["assets"] == [] and with_assets["assets"] == ["host-1"]
    asset_names.assert_awaited_once()  # only the default call reads them


def test_asset_search_is_bounded_and_uses_the_shared_visibility():
    visibility = ["<visibility>"]
    asset_names = AsyncMock(return_value=["web-01"])
    with patch.object(dbo, "alert_visibility_filters_for_user", AsyncMock(return_value=visibility)), patch.object(
        dbo,
        "_asset_names",
        asset_names,
    ):
        assert asyncio.run(dbo.search_alert_asset_names(USER, AsyncMock(), "  web ", 20)) == ["web-01"]
    asset_names.assert_awaited_once()
    args, kwargs = asset_names.await_args
    assert args[1] is visibility and kwargs == {"search": "web", "limit": 20}


# ── case filter options ───────────────────────────────────────────────────


def _case_options(accessible):
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[[("OPEN",), ("CLOSED",), (None,)], [("alice",)]])
    with patch.object(dbo.customer_access_handler, "get_user_accessible_customers", AsyncMock(return_value=accessible)):
        result = asyncio.run(dbo.get_case_filter_options(USER, session))
    return result, [str(call.args[0]) for call in session.execute.await_args_list]


def test_case_filter_options_are_scoped_to_the_users_customers():
    (statuses, assigned_to), sql = _case_options(["ACME"])
    assert statuses == ["OPEN", "CLOSED"] and assigned_to == ["alice"]
    assert all("customer_code IN" in statement for statement in sql)


def test_case_filter_options_are_unscoped_for_the_wildcard():
    _, sql = _case_options(["*"])
    assert not any("customer_code" in statement for statement in sql)
