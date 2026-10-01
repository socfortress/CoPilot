"""SOC Management (#1187) — the HTTP surface: scopes, validation and responses.

Real router, real in-memory database, real request parsing. Only token decoding and
user lookup are replaced, so a request authenticates as the user named in its bearer
token — the scope checks themselves run unchanged.

Run with: cd backend && python -m pytest tests/test_soc_management_routes.py
"""

import asyncio
import inspect
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.middleware.exception_handlers import validation_exception_handler  # noqa: E402
from app.soc_management.services import report as report_service  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from tests.soc_management_support import T0  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"]}
PERIOD = {"date_from": (T0 - timedelta(days=1)).isoformat(), "date_to": (T0 + timedelta(days=6)).isoformat()}


def _scopes_of(route: APIRoute) -> set:
    found = set()

    def walk(dependant):
        for dependency in dependant.dependencies:
            if dependency.call is not None:
                try:
                    scopes = inspect.getclosurevars(dependency.call).nonlocals.get("required_scopes")
                except TypeError:
                    scopes = None
                if isinstance(scopes, tuple):
                    found.update(scopes)
            walk(dependency)

    walk(route.dependant)
    return found


def _soc_routes():
    import copilot

    return {
        (method, route.path): _scopes_of(route)
        for route in copilot.app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/soc_management")
        for method in route.methods
    }


def test_every_route_is_soc_only_and_policy_writes_are_admin_only():
    routes = _soc_routes()
    assert routes, "no SOC Management route found — is the router included in copilot.py?"
    for (method, path), scopes in routes.items():
        assert "customer_user" not in scopes, f"{method} {path} admits portal users"
        if method in ("PUT", "DELETE"):
            assert scopes == {"admin"}, f"{method} {path} must be admin only, got {scopes}"
        else:
            assert scopes == {"admin", "analyst"}, f"{method} {path} must be admin/analyst, got {scopes}"


# ── functional ───────────────────────────────────────────────────────────────


def _app(db: Db) -> FastAPI:
    from fastapi.exceptions import RequestValidationError

    from app.routers import soc_management

    app = FastAPI()
    app.include_router(soc_management.router)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db) -> int:
    async with db.session() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add(UserCustomerAccess(user_id=2, customer_code="ACME"))
        await session.commit()
        await add_alert(session, customer="ACME")
        foreign = await add_alert(session, customer="GLOBEX")
    recorder = SlaLifecycleRecorder(db.factory, clock=lambda: T0)
    for alert_id in (1, 2):
        async with db.session() as session:
            from app.incidents.models import Alert

            await recorder.alert_opened(await session.get(Alert, alert_id))
    return foreign.id


def call(scenario):
    async def _inner():
        db = await Db().create()
        try:
            foreign_id = await _seed(db)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client, foreign_id)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def test_dashboard_returns_every_section():
    async def scenario(client, _):
        return await client.get("/soc_management/dashboard", params=PERIOD, headers=as_user("admin"))

    response = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()
    for section in ("headline", "previous", "severities", "trends", "analysts", "rules", "customers", "workload", "attention", "policy"):
        assert section in body
    assert body["headline"]["alerts"]["opened"] == 2
    assert body["period"]["bucket"] == "day"
    assert len(body["severities"]) == 10


def test_dashboard_accepts_axios_bracket_arrays_and_scopes_the_analyst():
    async def scenario(client, _):
        narrowed = await client.get(
            "/soc_management/dashboard",
            params={**PERIOD, "customer_codes[]": "GLOBEX", "severities[]": "High"},
            headers=as_user("admin"),
        )
        analyst = await client.get("/soc_management/dashboard", params=PERIOD, headers=as_user("ana"))
        return narrowed.json(), analyst.json()

    narrowed, analyst = call(scenario)
    assert narrowed["headline"]["alerts"]["opened"] == 1 and narrowed["customer_codes"] == ["GLOBEX"]
    assert analyst["headline"]["alerts"]["opened"] == 1 and analyst["customer_codes"] == ["ACME"]
    assert analyst["viewer"] == {"username": "ana", "is_admin": False, "sees_all_analysts": False}


def test_invalid_periods_are_rejected_with_a_reason():
    async def scenario(client, _):
        backwards = await client.get(
            "/soc_management/dashboard",
            params={"date_from": PERIOD["date_to"], "date_to": PERIOD["date_from"]},
            headers=as_user("admin"),
        )
        too_long = await client.get(
            "/soc_management/dashboard",
            params={"date_from": (T0 - timedelta(days=400)).isoformat(), "date_to": T0.isoformat()},
            headers=as_user("admin"),
        )
        missing = await client.get("/soc_management/dashboard", headers=as_user("admin"))
        return backwards, too_long, missing

    backwards, too_long, missing = call(scenario)
    assert backwards.status_code == 400 and "start before" in backwards.json()["detail"]
    assert too_long.status_code == 400 and "366 days" in too_long.json()["detail"]
    assert missing.status_code in (400, 422)


def test_timezone_aware_periods_are_converted_to_utc():
    async def scenario(client, _):
        return await client.get(
            "/soc_management/dashboard",
            params={"date_from": "2026-09-01T02:00:00+02:00", "date_to": "2026-09-08T02:00:00+02:00"},
            headers=as_user("admin"),
        )

    response = call(scenario)
    assert response.status_code == 200
    assert response.json()["period"]["date_from"] == "2026-09-01T00:00:00"


def test_portal_users_are_refused():
    async def scenario(client, _):
        return await client.get("/soc_management/dashboard", params=PERIOD, headers=as_user("portal"))

    assert call(scenario).status_code == 403


def test_policy_round_trip_and_admin_only_writes():
    cells = [{"entity": "alert", "severity": "High", "ack_minutes": 20, "resolve_minutes": 90}]

    async def scenario(client, _):
        denied = await client.put("/soc_management/policies", json={"cells": cells}, headers=as_user("ana"))
        saved = await client.put(
            "/soc_management/policies",
            json={"customer_code": "ACME", "cells": cells, "apply_to_open": True},
            headers=as_user("admin"),
        )
        read = await client.get("/soc_management/policies", params={"customer_code": "ACME"}, headers=as_user("ana"))
        overrides = await client.get("/soc_management/policies/overrides", headers=as_user("ana"))
        foreign = await client.get("/soc_management/policies", params={"customer_code": "GLOBEX"}, headers=as_user("ana"))
        cleared = await client.delete("/soc_management/policies/ACME", headers=as_user("admin"))
        return denied, saved, read, overrides, foreign, cleared

    denied, saved, read, overrides, foreign, cleared = call(scenario)
    assert denied.status_code == 403
    assert saved.status_code == 200, saved.text
    assert saved.json()["retargeted"] == 1  # the open ACME alert moved to the new targets
    cell = next(c for c in read.json()["policy"]["cells"] if c["entity"] == "alert" and c["severity"] == "High")
    assert (cell["ack_minutes"], cell["resolve_minutes"], cell["source"]) == (20, 90, "customer")
    assert [o["customer_code"] for o in overrides.json()["overrides"]] == ["ACME"]
    assert foreign.status_code == 403  # ana is not assigned to GLOBEX
    assert cleared.status_code == 200 and "follows the global policy" in cleared.json()["message"]


def test_policy_validation_errors_name_the_problem():
    async def scenario(client, _):
        return await client.put(
            "/soc_management/policies",
            json={"cells": [{"entity": "alert", "severity": "High", "ack_minutes": 600, "resolve_minutes": 60}]},
            headers=as_user("admin"),
        )

    response = call(scenario)
    assert response.status_code in (400, 422)
    assert "acknowledge target cannot be longer" in response.text


def test_calendar_round_trip_validation_and_admin_only_writes():
    week = {"mon": [["09:00", "17:00"]], "fri": [["09:00", "13:00"]]}

    async def scenario(client, _):
        default = await client.get("/soc_management/calendars", params={"customer_code": "ACME"}, headers=as_user("ana"))
        denied = await client.put("/soc_management/calendars", json={"week": week}, headers=as_user("ana"))
        invalid = await client.put(
            "/soc_management/calendars",
            json={"timezone": "Mars/Olympus", "week": week},
            headers=as_user("admin"),
        )
        saved = await client.put(
            "/soc_management/calendars",
            json={"customer_code": "ACME", "timezone": "Europe/Rome", "week": week, "holidays": ["2026-12-25"], "apply_to_open": True},
            headers=as_user("admin"),
        )
        foreign = await client.get("/soc_management/calendars", params={"customer_code": "GLOBEX"}, headers=as_user("ana"))
        cleared = await client.delete("/soc_management/calendars/ACME", headers=as_user("admin"))
        return default, denied, invalid, saved, foreign, cleared

    default, denied, invalid, saved, foreign, cleared = call(scenario)
    assert default.status_code == 200 and default.json()["calendar"]["source"] == "default"
    assert denied.status_code == 403
    assert invalid.status_code in (400, 422) and "Unknown timezone" in invalid.text
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["calendar"]["source"] == "customer" and body["calendar"]["week"]["fri"] == [["09:00", "13:00"]]
    assert body["customers_with_calendar"] == ["ACME"]
    assert body["retargeted"] == 0  # the open alert runs 24/7: a calendar does not move it
    assert foreign.status_code == 403
    assert cleared.status_code == 200 and cleared.json()["calendar"]["source"] == "default"


def test_item_sla_is_404_outside_the_callers_scope():
    async def scenario(client, foreign_id):
        own = await client.get("/soc_management/items/alert/1/sla", headers=as_user("ana"))
        foreign = await client.get(f"/soc_management/items/alert/{foreign_id}/sla", headers=as_user("ana"))
        missing = await client.get("/soc_management/items/case/999/sla", headers=as_user("admin"))
        return own, foreign, missing

    own, foreign, missing = call(scenario)
    assert own.status_code == 200 and own.json()["ack"]["target_minutes"] == 60
    assert foreign.status_code == 404 and missing.status_code == 404


def test_attention_rejects_states_that_need_no_attention():
    async def scenario(client, _):
        bad = await client.get("/soc_management/attention", params={"state": "met"}, headers=as_user("admin"))
        good = await client.get("/soc_management/attention", params={"state": "breached", "entity": "alert"}, headers=as_user("admin"))
        return bad, good

    bad, good = call(scenario)
    assert bad.status_code == 400
    assert good.status_code == 200 and set(good.json()) >= {"items", "total"}


def test_report_streams_a_pdf_named_after_the_period():
    async def fake_render(session, user, query):
        return b"%PDF-1.4 fake", "soc_report_20260831_20260907.pdf"

    async def scenario(client, _):
        with patch.object(report_service, "render_report", fake_render):
            return await client.get("/soc_management/report", params=PERIOD, headers=as_user("admin"))

    response = call(scenario)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="soc_report_20260831_20260907.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_report_failure_is_a_generic_500():
    async def broken(session, user, query):
        raise RuntimeError("wkhtmltopdf: SELECT secret FROM somewhere")

    async def scenario(client, _):
        with patch.object(report_service, "render_report", broken):
            return await client.get("/soc_management/report", params=PERIOD, headers=as_user("admin"))

    response = call(scenario)
    assert response.status_code == 500
    assert "secret" not in response.text
