"""Scope semantics on routes, and the agent healthcheck routes' tenancy.

``Security(get_current_user, scopes=[...])`` requires *every* scope listed (FastAPI also
adds the scopes of the dependencies above it), and a token carries one role's scopes,
so two different roles in one list make a route nobody can call: that is what kept
``POST /healthcheck/logs`` dead. "Any of these roles" is ``require_any_scope``.

Making that route reachable also made its missing tenant check reachable, and the agent
healthcheck routes next to it listed every customer's agents and served any agent id:
they now narrow to the caller's customers like the rest of the app.
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "unit-test-secret-not-the-default")

from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

import app.healthchecks.agents.routes.agents as healthcheck_routes  # noqa: E402
from app.healthchecks.agents.schema.agents import HostLogsSearchBody  # noqa: E402
from app.middleware.customer_access import verify_agent_id_access  # noqa: E402

ANALYST = SimpleNamespace(id=7, username="analyst1", role_id=2)


def _routes():
    import copilot

    return [route for route in copilot.app.routes if isinstance(route, APIRoute)]


def _current_user_scopes(dependant, inherited=()):
    """Every scope set ``get_current_user`` is resolved with, accumulated the way FastAPI does."""
    scopes = tuple(dict.fromkeys([*inherited, *(getattr(dependant, "own_oauth_scopes", None) or [])]))
    if getattr(dependant.call, "__name__", "") == "get_current_user":
        yield scopes
    for dependency in dependant.dependencies:
        yield from _current_user_scopes(dependency, scopes)


def test_no_route_requires_two_scopes_at_once():
    offenders = sorted(
        (route.path, sorted(route.methods), list(scopes))
        for route in _routes()
        for scopes in _current_user_scopes(route.dependant)
        if len(scopes) > 1
    )
    assert offenders == [], "use require_any_scope(...) for 'any of these roles': " + repr(offenders)


def test_host_logs_admits_admin_and_analyst():
    import inspect

    (route,) = [r for r in _routes() if r.path == "/api/healthcheck/logs" and "POST" in r.methods]
    required = set()
    for dependency in route.dependant.dependencies:
        try:
            found = inspect.getclosurevars(dependency.call).nonlocals.get("required_scopes")
        except TypeError:
            found = None
        if isinstance(found, tuple):
            required |= set(found)
    assert required == {"admin", "analyst"}


def _logs_body(host="host-b"):
    return HostLogsSearchBody(agent_name=host, timerange="1h")


def test_host_logs_refuses_another_customers_host_before_searching():
    search = AsyncMock()
    refused = AsyncMock(side_effect=HTTPException(status_code=403, detail="no"))
    with patch.object(healthcheck_routes, "enforce_hostname_access", refused), patch.object(healthcheck_routes, "host_logs", search):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(healthcheck_routes.get_host_logs(_logs_body(), current_user=ANALYST, session=MagicMock()))
    assert exc.value.status_code == 403
    refused.assert_awaited_once()
    assert refused.await_args.args[1] == "host-b"
    search.assert_not_awaited()


def test_host_logs_searches_an_allowed_host():
    search = AsyncMock(return_value="logs")
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: SimpleNamespace(hostname="host-a"))))
    with patch.object(healthcheck_routes, "enforce_hostname_access", AsyncMock()), patch.object(healthcheck_routes, "host_logs", search):
        result = asyncio.run(healthcheck_routes.get_host_logs(_logs_body("host-a"), current_user=ANALYST, session=session))
    assert result == "logs"


def _capturing_session(rows):
    session = MagicMock()
    session.statements = []

    async def execute(statement):
        session.statements.append(statement)
        return MagicMock(scalars=lambda: MagicMock(all=lambda: rows))

    session.execute = execute
    return session


def test_a_caller_who_sees_no_customer_gets_no_agent_and_no_query():
    session = _capturing_session(["should not be read"])
    with patch.object(healthcheck_routes, "scoped_customer_codes", AsyncMock(return_value=[])):
        agents = asyncio.run(healthcheck_routes._visible_agents(ANALYST, session))
    assert agents == []
    assert session.statements == []


def test_a_scoped_caller_gets_only_their_customers_agents():
    session = _capturing_session(["a1"])
    with patch.object(healthcheck_routes, "scoped_customer_codes", AsyncMock(return_value=["A"])):
        agents = asyncio.run(healthcheck_routes._visible_agents(ANALYST, session))
    assert agents == ["a1"]
    (statement,) = session.statements
    assert "customer_code IN" in str(statement)
    assert statement.compile().params["customer_code_1"] == ["A"]


def test_a_deployment_wide_caller_gets_every_agent():
    session = _capturing_session(["a1", "b1"])
    with patch.object(healthcheck_routes, "scoped_customer_codes", AsyncMock(return_value=None)):
        agents = asyncio.run(healthcheck_routes._visible_agents(ANALYST, session))
    assert agents == ["a1", "b1"]
    assert "WHERE" not in str(session.statements[0])


@pytest.mark.parametrize("path", ["/api/healthcheck/wazuh/{agent_id}", "/api/healthcheck/velociraptor/{agent_id}"])
def test_agent_healthcheck_by_id_checks_the_agents_tenant(path):
    (route,) = [r for r in _routes() if r.path == path]
    assert verify_agent_id_access in [dependency.call for dependency in route.dependant.dependencies]
