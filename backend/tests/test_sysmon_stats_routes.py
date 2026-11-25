"""The routes of the Sysmon noise statistics (routes/sysmon_stats.py): mounted before /api/sysmon_config/{customer_code},
admin only, the preview sends nothing and writes no state, Send now answers 409 while a run is in progress, the audit rows
carry no values.

Run with: cd backend && python -m pytest tests/test_sysmon_stats_routes.py
"""
import asyncio
import hashlib
import inspect
import json
import os
from datetime import datetime
from datetime import timezone

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

import app.active_response.routes.sysmon_config as config_routes  # noqa: E402
import app.active_response.routes.sysmon_stats as routes  # noqa: E402
from app.active_response.schema.sysmon_stats import StatsSharingRequest  # noqa: E402
from app.active_response.services.sysmon_stats import report  # noqa: E402
from app.active_response.services.sysmon_stats import runner  # noqa: E402
from app.active_response.services.sysmon_stats import sharing  # noqa: E402
from tests.sysmon_stats_support import Sysmonsync  # noqa: E402
from tests.sysmon_stats_support import World  # noqa: E402
from tests.sysmon_stats_support import week_docs  # noqa: E402

ADMIN = type("U", (), {"id": 7, "username": "alice", "role_id": 1})()
BASE = "/api/sysmon_config/stats"


def _app():
    import copilot

    return copilot.app


def _resolve(method, path):
    from starlette.routing import Match

    scope = {"type": "http", "method": method, "path": path, "root_path": "", "query_string": b"", "headers": []}
    for route in _app().router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "endpoint", None)
    return None


def test_the_stats_routes_are_not_taken_for_a_customer_code():
    assert _resolve("GET", BASE) is routes.get_sysmon_stats_status
    assert _resolve("PUT", f"{BASE}/customers/acme") is routes.put_sysmon_stats_customer
    assert _resolve("POST", f"{BASE}/customers/acme/preview") is routes.preview_sysmon_stats
    assert _resolve("POST", f"{BASE}/send-now") is routes.send_sysmon_stats_now
    assert _resolve("GET", "/api/sysmon_config/acme") is config_routes.get_customer_sysmon_config


def _required_scopes(dependant) -> set:
    scopes = set(getattr(dependant, "own_oauth_scopes", None) or [])
    for dependency in dependant.dependencies:
        if dependency.call is not None:
            try:
                required = inspect.getclosurevars(dependency.call).nonlocals.get("required_scopes")
            except TypeError:
                required = None
            if isinstance(required, tuple):
                scopes |= set(required)
        scopes |= _required_scopes(dependency)
    return scopes


def test_every_stats_route_is_admin_only():
    found = [r for r in _app().routes if isinstance(r, APIRoute) and r.path.startswith(BASE)]
    assert len(found) == 4
    for route in found:
        assert _required_scopes(route.dependant) == {"admin"}, route.path


NOW = datetime(2026, 11, 25, 0, 30, tzinfo=timezone.utc)


def test_the_preview_returns_the_exact_payload_and_sends_nothing(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    monkeypatch.setattr(runner, "_now", lambda: NOW)
    transports = []
    real = httpx.AsyncClient

    class Spy(real):
        def __init__(self, *a, **kw):
            transports.append(kw)
            super().__init__(*a, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", Spy)

    async def scenario():
        await world.setup()
        async with world.db.session() as session:
            return await routes.preview_sysmon_stats("contoso", week=None, session=session)

    response = asyncio.run(scenario())
    preview = response.preview
    assert preview.week == "2026-W47" and preview.would_send.ok is True
    payload = report.serialize(preview.payload)
    assert hashlib.sha256(payload).hexdigest() == preview.payload_sha256 and len(payload) == preview.payload_bytes
    assert preview.payload["customer"] == preview.customer_pseudonym
    assert preview.local.dropped_by_reason == {"dns-private-suffix": 1}
    assert transports == [] and "stats-state.json" not in world.minio.names()
    assert response.message == "Nothing was sent."


def test_the_preview_says_why_it_would_not_send(monkeypatch):
    world = World(monkeypatch, week_docs("contoso"))
    monkeypatch.setattr(runner, "_now", lambda: datetime(2026, 11, 23, 0, 30, tzinfo=timezone.utc))

    async def scenario():
        await world.setup()
        async with world.db.session() as session:
            return await routes.preview_sysmon_stats("contoso", week=None, session=session)

    preview = asyncio.run(scenario()).preview
    assert preview.would_send.ok is False and preview.would_send.why.startswith("Not due yet")
    assert preview.payload is not None


@pytest.mark.parametrize("week,status", [("2026-W40", 400), ("2026-W48", 400), ("bogus", 400)])
def test_the_preview_takes_only_an_accepted_week(monkeypatch, week, status):
    World(monkeypatch)
    monkeypatch.setattr(runner, "_now", lambda: NOW)
    with pytest.raises(HTTPException) as raised:
        asyncio.run(routes.preview_sysmon_stats("contoso", week=week, session=None))
    assert raised.value.status_code == status


def test_the_preview_refuses_while_off_running_or_for_an_unknown_customer(monkeypatch):
    world = World(monkeypatch)

    async def scenario():
        await world.setup()
        codes = []
        monkeypatch.setenv("SYSMON_STATS_SHARING", "off")
        try:
            await routes.preview_sysmon_stats("contoso", week=None, session=None)
        except HTTPException as e:
            codes.append(e.status_code)
        monkeypatch.delenv("SYSMON_STATS_SHARING")
        async with runner._RUN_LOCK:
            try:
                await routes.preview_sysmon_stats("contoso", week=None, session=None)
            except HTTPException as e:
                codes.append(e.status_code)
        async with world.db.session() as session:
            try:
                await routes.preview_sysmon_stats("nobody", week=None, session=session)
            except HTTPException as e:
                codes.append(e.status_code)
        return codes

    assert asyncio.run(scenario()) == [409, 409, 404]


def test_send_now_answers_409_while_a_run_is_in_progress(monkeypatch):
    from unittest.mock import AsyncMock

    tick = AsyncMock()
    monkeypatch.setattr(runner, "run_tick", tick)

    async def scenario():
        async with runner._RUN_LOCK:
            with pytest.raises(HTTPException) as raised:
                await routes.send_sysmon_stats_now(request=None, customer_code=None, resume=False, current_user=ADMIN, session=None)
        return raised.value

    error = asyncio.run(scenario())
    assert error.status_code == 409 and "in progress" in error.detail
    tick.assert_not_awaited()


def test_send_now_runs_as_the_admin(monkeypatch, audit_rows):
    world = World(monkeypatch, week_docs("contoso"))
    service = Sysmonsync()
    real = runner.run_tick

    async def run_tick(session, **kw):
        return await real(session, now=NOW, transport=service.transport, **kw)

    monkeypatch.setattr(runner, "run_tick", run_tick)
    monkeypatch.setattr(runner, "_now", lambda: NOW)

    async def scenario():
        await world.setup()
        async with world.db.session() as session:
            return await routes.send_sysmon_stats_now(
                request=None,
                customer_code="contoso",
                resume=False,
                current_user=ADMIN,
                session=session,
            )

    response = asyncio.run(scenario())
    assert response.result.customers[0].outcome.value == "sent"
    (status_customer,) = response.status.customers
    assert status_customer.last_sent_week == "2026-W47" and status_customer.last_sent_state.outcome.value == "sent"
    (row,) = [r for r in audit_rows if r.action == "response.sysmon_stats_send"]
    assert (row.actor_user_id, row.actor_username) == (7, "alice")
    stored = json.dumps(row.model_dump(), default=str)
    assert "telemetry.fabrikam-example.com" not in stored and "Fabrikam" not in stored and "agent.exe" not in stored


def test_the_status_and_the_sharing_route(monkeypatch, audit_rows):
    world = World(monkeypatch)
    service = Sysmonsync()
    monkeypatch.setattr(sharing.http, "post_withdraw", _withdraw_ok(service))

    async def scenario():
        await world.setup({"contoso": "Contoso Ltd", "northwind": "Northwind"})
        async with world.db.session() as session:
            status = await routes.get_sysmon_stats_status(session=session)
        async with world.db.session() as session:
            put = await routes.put_sysmon_stats_customer(
                "contoso",
                StatsSharingRequest(sharing=False, own_domains=["contoso.com"]),
                request=None,
                current_user=ADMIN,
                session=session,
            )
        return status, put

    status, put = asyncio.run(scenario())
    s = status.status
    assert s.mode.value == "on" and s.max_rule_level == 5 and s.min_endpoints == 3
    assert [c.customer_code for c in s.customers] == ["contoso", "northwind"]
    assert all(c.sharing and c.pseudonym.startswith("cust_") and c.due_at for c in s.customers)
    assert put.customer.sharing is False and put.withdraw.outcome == "withdrawn"
    assert put.customer.own_domains == ["contoso.com"] and put.customer.withdraw.withdrawn_at is not None
    for row in audit_rows:
        assert "contoso.com" not in json.dumps(row.model_dump(), default=str)


def _withdraw_ok(service):
    async def post_withdraw(base, customer, license_key, transport=None):
        from app.active_response.services.sysmon_stats.client import WithdrawResult

        return WithdrawResult(True, 200, reports_deleted=0)

    return post_withdraw
