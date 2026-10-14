"""``GET /agents/{agent_hostname}/cases``: the cases of an agent, for its own tenants only (#1256).

The route checked that the caller could see *an* agent with that hostname, then listed
every case with an alert on that asset name — across tenants. Hostnames are not unique
across customers (two of them can each have a ``web-01``), so a portal user saw another
customer's cases. The cases are now narrowed to the customers of the agents the caller
may see, and each case comes back once however many of its alerts name the asset.

Mocked session; no database. The SQL runs for real in tests/e2e/agent_tabs_e2e.py.

Run with: cd backend && python -m pytest tests/test_agent_cases_scoping.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.agents.routes.agents as agent_routes  # noqa: E402
import app.incidents.services.db_operations as dbo  # noqa: E402

PORTAL_USER = SimpleNamespace(id=7, username="acme.viewer", role_id=4)


def _empty_session():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    return session


def _sql(session) -> str:
    return str(session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))


# ── the service ───────────────────────────────────────────────────────────


def test_cases_are_narrowed_to_the_given_customers():
    session = _empty_session()
    asyncio.run(dbo.list_cases_by_asset_name("web-01", session, customer_codes=["ACME"]))
    sql = _sql(session)
    assert "incident_management_case.customer_code IN ('ACME')" in sql
    assert "asset_name = 'web-01'" in sql


def test_each_case_once_newest_first_through_a_subquery_not_a_join():
    session = _empty_session()
    asyncio.run(dbo.list_cases_by_asset_name("web-01", session, customer_codes=["ACME"]))
    sql = _sql(session)
    # The case table is read once and matched against the linked ids: a case with two
    # alerts on the asset can no longer come back twice.
    assert "incident_management_case.id IN (SELECT" in sql
    assert sql.count("FROM incident_management_case ") + sql.count("FROM incident_management_case\n") == 1
    assert "ORDER BY incident_management_case.id DESC" in sql


def test_no_customer_filter_unless_asked():
    """Admins on the incidents route still read every tenant's cases on that name."""
    session = _empty_session()
    asyncio.run(dbo.list_cases_by_asset_name("web-01", session))
    assert "customer_code IN" not in _sql(session)


# ── the route ─────────────────────────────────────────────────────────────


def _route_session(customer_codes):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = customer_codes
    session.execute = AsyncMock(return_value=result)
    return session


def _call(customer_codes):
    session = _route_session(customer_codes)
    listed = AsyncMock(return_value=[])
    with (
        patch.object(agent_routes.customer_access_handler, "filter_query_by_customer_access", AsyncMock(side_effect=lambda u, s, q, f: q)),
        patch.object(agent_routes, "list_cases_by_asset_name", listed),
    ):
        response = asyncio.run(agent_routes.get_agent_soc_cases(agent_hostname="web-01", current_user=PORTAL_USER, session=session))
    return response, listed


def test_the_route_lists_only_the_customers_of_the_agents_the_caller_sees():
    _, listed = _call(["ACME", "ACME"])
    assert listed.await_args.kwargs == {"asset_name": "web-01", "db": listed.await_args.kwargs["db"], "customer_codes": ["ACME"]}


def test_an_agent_the_caller_cannot_see_is_a_404_and_lists_nothing():
    with pytest.raises(HTTPException) as exc:
        _call([])
    assert exc.value.status_code == 404
