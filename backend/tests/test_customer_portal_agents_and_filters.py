"""Server-side agents list for the Customer Portal (#1185).

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
