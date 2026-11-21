"""Who may change an event source, and which source a dashboard may read.

An event source's ``index_pattern`` is the tenant boundary for Event Search and the SIEM dashboards,
the Customer Portal's included: CoPilot adds no customer filter to those queries. Before this, an
analyst could edit any customer's source by id, add sources for any customer, point their own
customer's source at another customer's indices, and enable a dashboard for their customer on
another customer's source. Pinned here:

- only an admin adds a source or changes a pattern, judged by the database role (a demoted admin's
  token still says "admin"); the edit form resending the unchanged pattern is no change;
- an analyst (a responder too) edits the other fields of their own customers' sources only;
- a dashboard is enabled only for a customer the caller may see, and only on that customer's source;
- panel-data refuses a dashboard bound to another customer's source before the indexer is asked.

Real routers, real in-memory database, real request parsing; only token decoding and user lookup are
replaced (as in test_customer_knowledge).

Run with: cd backend && python -m pytest tests/test_event_source_tenant_checks.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
from sqlmodel import select  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import EnabledDashboards  # noqa: E402
from app.db.universal_models import EventSources  # noqa: E402
from app.siem.schema.event_sources import EventSourceUpdate  # noqa: E402
from app.siem.services import dashboards as dashboards_service  # noqa: E402
from app.siem.services import event_sources as event_sources_service  # noqa: E402

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    # Demoted to analyst after signing in: the token still carries the admin scope.
    "demoted": SimpleNamespace(id=3, username="demoted", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
    "rex": SimpleNamespace(id=5, username="rex", role_id=5),
}
SCOPES = {
    "admin": ["admin"],
    "ana": ["analyst"],
    "demoted": ["admin"],
    "portal": ["customer_user"],
    "rex": ["responder", "analyst"],
}
TABLES = ("user", "role", "user_customer_access", "customers", "event_sources", "enabled_dashboards")

ACME_SOURCE = 1
GLOBEX_SOURCE = 2
ACME_PATTERN = "wazuh-acme_*"
GLOBEX_PATTERN = "wazuh-globex_*"


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables[n] for n in TABLES]))
        return self


async def _seed(db: Db) -> None:
    async with db.factory() as session:
        session.add_all(
            [
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add_all(
            [
                EventSources(id=ACME_SOURCE, customer_code="ACME", name="EDR", index_pattern=ACME_PATTERN, event_type="EDR"),
                EventSources(id=GLOBEX_SOURCE, customer_code="GLOBEX", name="EDR", index_pattern=GLOBEX_PATTERN, event_type="EDR"),
                # Everyone but the admin is assigned ACME only.
                *(UserCustomerAccess(user_id=USERS[name].id, customer_code="ACME") for name in ("ana", "demoted", "portal", "rex")),
            ],
        )
        await session.commit()


def _app(db: Db) -> FastAPI:
    from app.routers import siem

    api = FastAPI()
    api.include_router(siem.router)

    async def _session():
        async with db.factory() as session:
            yield session

    api.dependency_overrides[get_db] = _session
    return api


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
                    return await scenario(client, db)
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


async def source(db, source_id):
    async with db.factory() as session:
        return await session.get(EventSources, source_id)


async def sources(db):
    async with db.factory() as session:
        return list((await session.execute(select(EventSources).order_by(EventSources.id))).scalars().all())


async def dashboards(db):
    async with db.factory() as session:
        return list((await session.execute(select(EnabledDashboards))).scalars().all())


def new_source(code="ACME", pattern="fortigate-acme*"):
    return {"customer_code": code, "name": "Firewall", "index_pattern": pattern, "event_type": "Network Security"}


def edr_dashboard(code="ACME", source_id=ACME_SOURCE):
    return {
        "customer_code": code,
        "event_source_id": source_id,
        "library_card": "wazuh_edr",
        "template_id": "EDR_OVERVIEW",
        "display_name": "EDR overview",
    }


def detail(response) -> str:
    """The refusal's text, whichever error shape the app's handlers gave it."""
    body = response.json()
    return body.get("detail") or body.get("message") or ""


# --- what counts as changing the pattern --------------------------------------------------------


@pytest.mark.parametrize(
    ("update", "changes"),
    [
        ({"name": "renamed"}, False),
        ({"index_pattern": ACME_PATTERN, "name": "renamed"}, False),
        ({"index_pattern": "*"}, True),
        ({"index_pattern": None}, True),
    ],
)
def test_only_a_different_pattern_is_a_pattern_change(update, changes):
    stored = EventSources(id=ACME_SOURCE, customer_code="ACME", name="EDR", index_pattern=ACME_PATTERN, event_type="EDR")
    assert event_sources_service.changes_index_pattern(stored, EventSourceUpdate(**update)) is changes


# --- editing a source ---------------------------------------------------------------------------


def test_an_analyst_cannot_edit_another_customers_source():
    async def scenario(client, db):
        response = await client.put(
            f"/siem/event_sources/{GLOBEX_SOURCE}",
            json={"name": "mine now", "enabled": False},
            headers=as_user("ana"),
        )
        assert response.status_code == 403
        stored = await source(db, GLOBEX_SOURCE)
        assert (stored.name, stored.enabled, stored.index_pattern) == ("EDR", True, GLOBEX_PATTERN)

    call(scenario)


@pytest.mark.parametrize("who", ["ana", "rex"])
def test_an_analyst_edits_the_rest_of_their_own_customers_source(who):
    columns = [{"key": "agent_name", "label": "Agent"}]

    async def scenario(client, db):
        response = await client.put(
            f"/siem/event_sources/{ACME_SOURCE}",
            json={"name": "EDR alerts", "time_field": "@timestamp", "enabled": False, "displayed_columns": columns},
            headers=as_user(who),
        )
        assert response.status_code == 200, response.text
        stored = await source(db, ACME_SOURCE)
        assert (stored.name, stored.time_field, stored.enabled, stored.displayed_columns) == ("EDR alerts", "@timestamp", False, columns)
        assert stored.index_pattern == ACME_PATTERN

    call(scenario)


def test_the_edit_form_resending_the_unchanged_pattern_is_allowed():
    # CustomerEventSourceForm.vue sends every field with each save.
    form = {"name": "EDR alerts", "index_pattern": ACME_PATTERN, "event_type": "EDR", "time_field": "timestamp", "enabled": True}

    async def scenario(client, db):
        response = await client.put(f"/siem/event_sources/{ACME_SOURCE}", json=form, headers=as_user("ana"))
        assert response.status_code == 200, response.text
        assert (await source(db, ACME_SOURCE)).name == "EDR alerts"

    call(scenario)


@pytest.mark.parametrize("who", ["ana", "rex", "demoted"])
def test_only_an_admin_changes_a_pattern(who):
    async def scenario(client, db):
        response = await client.put(
            f"/siem/event_sources/{ACME_SOURCE}",
            json={"name": "renamed", "index_pattern": "*"},
            headers=as_user(who),
        )
        assert response.status_code == 403
        assert detail(response) == event_sources_service.ADMIN_ONLY_PATTERN
        # Refused whole: the rest of the update isn't applied either.
        stored = await source(db, ACME_SOURCE)
        assert (stored.name, stored.index_pattern) == ("EDR", ACME_PATTERN)

    call(scenario)


def test_an_admin_changes_any_customers_pattern():
    async def scenario(client, db):
        response = await client.put(
            f"/siem/event_sources/{GLOBEX_SOURCE}",
            json={"index_pattern": "wazuh-globex-v2_*"},
            headers=as_user("admin"),
        )
        assert response.status_code == 200, response.text
        assert (await source(db, GLOBEX_SOURCE)).index_pattern == "wazuh-globex-v2_*"

    call(scenario)


def test_a_portal_user_never_edits_a_source():
    async def scenario(client, db):
        response = await client.put(f"/siem/event_sources/{ACME_SOURCE}", json={"name": "renamed"}, headers=as_user("portal"))
        assert response.status_code == 403
        assert (await source(db, ACME_SOURCE)).name == "EDR"

    call(scenario)


@pytest.mark.parametrize("who", ["ana", "admin"])
def test_an_unknown_source_is_a_404(who):
    async def scenario(client, db):
        response = await client.put("/siem/event_sources/999", json={"name": "x"}, headers=as_user(who))
        assert response.status_code == 404

    call(scenario)


# --- adding a source ----------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["ana", "rex", "demoted", "portal"])
@pytest.mark.parametrize("code", ["ACME", "GLOBEX"])
def test_only_an_admin_adds_a_source(who, code):
    async def scenario(client, db):
        response = await client.post("/siem/event_sources", json=new_source(code=code, pattern="*"), headers=as_user(who))
        assert response.status_code == 403
        assert [s.id for s in await sources(db)] == [ACME_SOURCE, GLOBEX_SOURCE]

    call(scenario)


def test_an_admin_adds_a_source():
    async def scenario(client, db):
        response = await client.post("/siem/event_sources", json=new_source(), headers=as_user("admin"))
        assert response.status_code == 200, response.text
        added = (await sources(db))[-1]
        assert (added.customer_code, added.name, added.index_pattern) == ("ACME", "Firewall", "fortigate-acme*")

    call(scenario)


# --- which source a dashboard reads -------------------------------------------------------------


def test_an_analyst_cannot_enable_a_dashboard_for_another_customer():
    async def scenario(client, db):
        response = await client.post(
            "/siem/dashboards/enable",
            json=edr_dashboard(code="GLOBEX", source_id=GLOBEX_SOURCE),
            headers=as_user("ana"),
        )
        assert response.status_code == 403
        assert await dashboards(db) == []

    call(scenario)


@pytest.mark.parametrize("who", ["ana", "admin"])
def test_a_dashboard_never_reads_another_customers_source(who):
    async def scenario(client, db):
        response = await client.post(
            "/siem/dashboards/enable",
            json=edr_dashboard(code="ACME", source_id=GLOBEX_SOURCE),
            headers=as_user(who),
        )
        # The same answer as a source that doesn't exist: nothing about Globex's.
        assert response.status_code == 404
        assert detail(response) == f"Event source {GLOBEX_SOURCE} not found for customer ACME"
        assert await dashboards(db) == []

    call(scenario)


def test_a_dashboard_on_the_customers_own_source_is_enabled():
    async def scenario(client, db):
        response = await client.post("/siem/dashboards/enable", json=edr_dashboard(), headers=as_user("ana"))
        assert response.status_code == 200, response.text
        (row,) = await dashboards(db)
        assert (row.customer_code, row.event_source_id) == ("ACME", ACME_SOURCE)

    call(scenario)


async def _bind(db, source_id):
    async with db.factory() as session:
        session.add(
            EnabledDashboards(
                id=7,
                customer_code="ACME",
                event_source_id=source_id,
                library_card="wazuh_edr",
                template_id="EDR_OVERVIEW",
                display_name="EDR overview",
            ),
        )
        await session.commit()


@pytest.mark.parametrize("who", ["portal", "ana", "admin"])
def test_panel_data_refuses_a_dashboard_bound_to_another_customers_source(who):
    # A row written before enabling checked the binding.
    indexer = AsyncMock(return_value={})

    async def scenario(client, db):
        await _bind(db, GLOBEX_SOURCE)
        with patch.object(dashboards_service, "execute_panels", indexer):
            response = await client.post("/siem/dashboards/panel-data", json={"dashboard_id": 7}, headers=as_user(who))
        assert response.status_code == 409
        assert detail(response) == dashboards_service.MISMATCHED_SOURCE
        assert "GLOBEX" not in response.text and GLOBEX_PATTERN not in response.text

    call(scenario)
    indexer.assert_not_awaited()


def test_panel_data_reads_the_dashboards_own_source():
    indexer = AsyncMock(return_value={})

    async def scenario(client, db):
        await _bind(db, ACME_SOURCE)
        with patch.object(dashboards_service, "execute_panels", indexer):
            response = await client.post("/siem/dashboards/panel-data", json={"dashboard_id": 7}, headers=as_user("portal"))
        assert response.status_code == 200, response.text
        assert response.json()["customer_code"] == "ACME"

    call(scenario)
    assert indexer.await_args.kwargs["index_pattern"] == ACME_PATTERN
