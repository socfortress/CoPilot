"""The Customer Portal SLA page (#1187): opt-in, tenant-scoped, read-only, anonymous.

Real router, real in-memory database, real request parsing; only token decoding and
user lookup are replaced (as in test_soc_management_routes).

Pinned here:
- a missing switch row reads as disabled, and a disabled customer is not read at all;
- only an admin flips the switch; an analyst may read it for customers they can see;
- a portal user sees their own customers' figures only, never another tenant's;
- nothing that names a person (analyst, assignee, resolver) crosses into the payload;
- the portal surface is GET-only apart from the operator's switch.

Run with: cd backend && python -m pytest tests/test_customer_portal_sla.py
"""

import asyncio
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
from app.customer_portal.schema import sla as portal_schema  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402
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
OVERVIEW = "/customer_portal/sla/overview"


def _app(db: Db) -> FastAPI:
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db) -> None:
    async with db.session() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                User(id=4, username="portal", password="x" * 8, email="portal@example.com", role_id=4),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add_all([UserCustomerAccess(user_id=4, customer_code="ACME"), UserCustomerAccess(user_id=2, customer_code="ACME")])
        await session.commit()
        await add_alert(session, customer="ACME", assigned_to="ana")
        await add_alert(session, customer="GLOBEX")
    clock = SimpleNamespace(now=T0)
    recorder = SlaLifecycleRecorder(db.factory, clock=lambda: clock.now)
    for alert_id in (1, 2):
        async with db.session() as session:
            await recorder.alert_opened(await session.get(Alert, alert_id))
    clock.now = T0 + timedelta(minutes=10)
    await recorder.alert_action(1, LifecycleAction.ASSIGNED, Actor(username="ana", is_soc=True))
    clock.now = T0 + timedelta(hours=2)
    await recorder.alert_action(1, LifecycleAction.STATUS_CHANGED, Actor(username="ana", is_soc=True), to_status="CLOSED")


def call(scenario):
    async def _inner():
        db = await Db().create()
        try:
            await _seed(db)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def test_the_page_is_off_until_an_admin_turns_it_on_for_the_customer():
    async def scenario(client):
        before = await client.get("/customer_portal/sla/availability", headers=as_user("portal"))
        hidden = await client.get(OVERVIEW, params=PERIOD, headers=as_user("portal"))
        denied = await client.put("/customer_portal/sla/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
        enabled = await client.put("/customer_portal/sla/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
        read_back = await client.get("/customer_portal/sla/settings/ACME", headers=as_user("ana"))
        after = await client.get("/customer_portal/sla/availability", headers=as_user("portal"))
        missing = await client.put("/customer_portal/sla/settings/NOPE", json={"enabled": True}, headers=as_user("admin"))
        return before, hidden, denied, enabled, read_back, after, missing

    before, hidden, denied, enabled, read_back, after, missing = call(scenario)
    assert before.json()["enabled"] is False
    assert hidden.status_code == 200 and hidden.json()["enabled"] is False and hidden.json()["alerts"] is None
    assert denied.status_code == 403
    assert enabled.status_code == 200 and enabled.json()["settings"]["enabled"] is True
    assert read_back.json()["settings"]["enabled"] is True
    assert after.json()["enabled"] is True
    assert missing.status_code == 404


def test_a_portal_user_sees_their_own_figures_and_never_a_name():
    async def scenario(client):
        for code in ("ACME", "GLOBEX"):
            await client.put(f"/customer_portal/sla/settings/{code}", json={"enabled": True}, headers=as_user("admin"))
        own = await client.get(OVERVIEW, params=PERIOD, headers=as_user("portal"))
        foreign = await client.get(OVERVIEW, params={**PERIOD, "customer_codes": ["GLOBEX"]}, headers=as_user("portal"))
        foreign_switch = await client.get(
            "/customer_portal/sla/availability",
            params={"customer_code": "GLOBEX"},
            headers=as_user("portal"),
        )
        admin = await client.get(OVERVIEW, params=PERIOD, headers=as_user("admin"))
        return own, foreign, foreign_switch, admin

    own, foreign, foreign_switch, admin = call(scenario)
    assert own.status_code == 200, own.text
    body = own.json()
    assert body["enabled"] is True and body["customer_codes"] == ["ACME"]
    assert body["alerts"]["opened"] == 1 and body["alerts"]["resolved"] == 1  # GLOBEX's alert is not counted
    assert body["alerts"]["acknowledge"] == {"met": 1, "breached": 0, "rate": 100.0}
    assert body["alerts"]["time_to_acknowledge"] == 600
    assert {t["severity"] for t in body["targets"] if t["entity"] == "alert"} >= {"Critical", "High"}
    assert "Informational" not in {t["severity"] for t in body["targets"]}  # no promise, not listed
    assert "ana" not in own.text  # neither the assignee nor the resolver
    assert foreign.json()["enabled"] is False  # asking for another tenant yields nothing, not their data
    assert foreign_switch.status_code == 403
    assert admin.json()["customer_codes"] == ["ACME", "GLOBEX"] and admin.json()["alerts"]["opened"] == 2


def test_an_invalid_period_is_a_400_with_a_fixed_reason():
    async def scenario(client):
        await client.put("/customer_portal/sla/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
        return await client.get(
            OVERVIEW,
            params={"date_from": PERIOD["date_to"], "date_to": PERIOD["date_from"]},
            headers=as_user("portal"),
        )

    response = call(scenario)
    assert response.status_code == 400 and "Invalid period" in response.text


def test_the_portal_sla_surface_is_read_only_and_the_switch_admin_only():
    from app.customer_portal.routes.sla import customer_portal_sla_router
    from tests.test_soc_management_routes import _scopes_of

    for route in customer_portal_sla_router.routes:
        assert isinstance(route, APIRoute)
        scopes = _scopes_of(route)
        if route.methods == {"PUT"}:
            assert route.path == "/sla/settings/{customer_code}" and scopes == {"admin"}
        else:
            assert route.methods == {"GET"}, f"{route.path} must be GET-only"
            portal_read = route.path in ("/sla/availability", "/sla/overview")
            assert ("customer_user" in scopes) is portal_read, f"{route.path}: {scopes}"


def test_no_portal_sla_model_has_a_field_that_could_name_a_person():
    forbidden = ("user", "analyst", "assign", "by", "actor", "resolver", "name")
    for model in (
        portal_schema.PortalSlaOverviewResponse,
        portal_schema.PortalSlaEntity,
        portal_schema.PortalSlaTarget,
        portal_schema.PortalSlaOpenNow,
    ):
        for field in model.model_fields:
            assert not any(part in field.split("_") for part in forbidden), f"{model.__name__}.{field}"
