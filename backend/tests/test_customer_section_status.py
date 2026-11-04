"""The status lights of a customer's page (#1325): ``GET /customers/{code}/sections/status``.

Real router, real in-memory database, real request parsing; only token decoding and user lookup
are replaced (as in test_customer_portal_activity).

Pinned here:
- a missing settings row reads as off, and an ``enabled = false`` row as off too;
- the lists count only this customer's entries;
- the languages are on only beyond English, and the portal chat only with the AI reports on and
  a customer limit (``talon_chat.chat_switched_on``);
- admin and analyst only, an analyst for their own customers only; an unknown customer is a 404;
- the whole answer is one SQL statement.

Run with: cd backend && python -m pytest tests/test_customer_section_status.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.dialects.mysql import LONGTEXT  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customers.services.section_status import get_section_status  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalAuditSettings  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import CustomerPortalChatSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalLanguageSettings  # noqa: E402
from app.db.universal_models import CustomerPortalSlaSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402
from app.db.universal_models import EventSources  # noqa: E402
from app.incidents.models import AIAnalystTriggerEnabled  # noqa: E402
from app.incidents.models import Notification  # noqa: E402
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    CustomerIntegrations,
)
from app.network_connectors.models.network_connectors import (  # noqa: E402
    CustomerNetworkConnectors,
)


@compiles(LONGTEXT, "sqlite")
def _longtext_on_sqlite(element, compiler, **kw):
    # The branding row's logo column is MySQL's LONGTEXT; SQLite stores any text as TEXT.
    return "TEXT"


USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"]}

TABLES = (
    "user",
    "role",
    "user_customer_access",
    "customers",
    "customer_portal_branding",
    "customer_portal_ai_report_settings",
    "customer_portal_sla_settings",
    "customer_portal_activity_settings",
    "customer_portal_notification_settings",
    "customer_portal_exposure_settings",
    "customer_portal_language_settings",
    "customer_portal_audit_settings",
    "customer_portal_soc_request_settings",
    "customer_portal_chat_settings",
    "customer_portal_ioc_enrichment_settings",
    "customer_waf_instances",
    "event_sources",
    "customer_notification_route",
    "customer_integrations",
    "customer_network_connectors",
    "incident_management_ai_analyst_trigger_enabled",
    "incident_management_notification",
)

STATUS = "/customers/{code}/sections/status"


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables[n] for n in TABLES]))
        return self


def _app(db: Db) -> FastAPI:
    from app.routers import customers

    api = FastAPI()
    api.include_router(customers.router)

    async def _session():
        async with db.factory() as session:
            yield session

    api.dependency_overrides[get_db] = _session
    return api


def _waf(code: str, name: str) -> CustomerWafInstance:
    return CustomerWafInstance(customer_code=code, name=name, api_url="https://waf", service_token_encrypted="x", token_prefix="wafst_")


def _route(code: str, name: str) -> CustomerNotificationRoute:
    return CustomerNotificationRoute(customer_code=code, name=name, trigger="alert_created", channel="webhook", destination="https://h")


def _integration(code: str, name: str) -> CustomerIntegrations:
    return CustomerIntegrations(customer_code=code, customer_name=code, integration_service_id=1, integration_service_name=name)


def _connector(code: str) -> CustomerNetworkConnectors:
    return CustomerNetworkConnectors(
        customer_code=code,
        customer_name=code,
        network_connector_service_id=1,
        network_connector_service_name="Fortinet",
    )


def _source(code: str, name: str) -> EventSources:
    return EventSources(customer_code=code, name=name, index_pattern=f"{name}-*", event_type="EDR")


async def _seed(db: Db, *, acme=True) -> None:
    async with db.factory() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
                Customers(customer_code="EMPTY", customer_name="Nothing set"),
            ],
        )
        await session.commit()
        session.add(UserCustomerAccess(user_id=2, customer_code="ACME"))
        if acme:
            session.add_all(
                [
                    # Switches: on, explicitly off, and (for every other one) no row at all.
                    AIAnalystTriggerEnabled(customer_code="ACME", enabled=True),
                    CustomerPortalSlaSettings(customer_code="ACME", enabled=True),
                    CustomerPortalAuditSettings(customer_code="ACME", enabled=False),
                    CustomerPortalIocEnrichmentSettings(customer_code="ACME", enabled=True),
                    CustomerPortalAiReportSettings(customer_code="ACME", enabled=True),
                    CustomerPortalChatSettings(customer_code="ACME", portal_chat_enabled=True, daily_message_limit=50),
                    CustomerPortalBranding(customer_code="ACME", enabled=True, title="Acme"),
                    CustomerPortalLanguageSettings(customer_code="ACME", languages=["en", "it", "de"]),
                    # Lists: ACME's entries, and GLOBEX's that must not count.
                    _integration("ACME", "Office365"),
                    _integration("ACME", "Huntress"),
                    _integration("GLOBEX", "Office365"),
                    _connector("ACME"),
                    _source("ACME", "wazuh"),
                    _source("ACME", "office365"),
                    _source("ACME", "crowdstrike"),
                    _source("GLOBEX", "wazuh"),
                    _waf("ACME", "prod"),
                    _route("ACME", "to the SOC"),
                    _route("ACME", "to the customer"),
                    _route("GLOBEX", "globex route"),
                    Notification(customer_code="ACME", shuffle_workflow_id="wf-1"),
                ],
            )
        # GLOBEX: its own switches, which must not light ACME's.
        session.add_all(
            [
                CustomerPortalBranding(customer_code="GLOBEX", enabled=False, title="Globex"),
                CustomerPortalAiReportSettings(customer_code="GLOBEX", enabled=False),
                CustomerPortalChatSettings(customer_code="GLOBEX", portal_chat_enabled=True, daily_message_limit=10),
                CustomerPortalLanguageSettings(customer_code="GLOBEX", languages=["en"]),
            ],
        )
        await session.commit()


def call(scenario, *, acme=True):
    async def _inner():
        db = await Db().create()
        try:
            await _seed(db, acme=acme)
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


def test_switches_lists_languages_and_chat():
    async def scenario(client, db):
        return (await client.get(STATUS.format(code="ACME"), headers=as_user("admin"))).json()

    body = call(scenario)
    assert body["success"] is True and body["customer_code"] == "ACME"
    sections = body["sections"]
    assert sections["ai_triggers"] == {"on": True}
    assert sections["portal_sla"] == {"on": True}
    assert sections["portal_audit"] == {"on": False}  # a row switched off
    assert sections["portal_activity"] == {"on": False}  # no row at all
    assert sections["portal_exposure"] == {"on": False}
    assert sections["portal_notifications"] == {"on": False}
    assert sections["portal_ask_soc"] == {"on": False}
    assert sections["portal_ioc_enrichment"] == {"on": True}
    assert sections["portal_branding"] == {"on": True}
    assert sections["portal_languages"] == {"on": True, "count": 3}
    assert sections["portal_ai_report"] == {"on": True}
    assert sections["portal_talon_chat"] == {"on": True}
    assert sections["integrations"] == {"count": 2}
    assert sections["network_connectors"] == {"count": 1}
    assert sections["event_sources"] == {"count": 3}
    assert sections["waf"] == {"count": 1}
    assert sections["notification_routes"] == {"count": 2}
    assert sections["notification_workflows"] == {"count": 1}


def test_a_customer_with_nothing_set_reads_all_off_and_english_only():
    async def scenario(client, db):
        return (await client.get(STATUS.format(code="EMPTY"), headers=as_user("admin"))).json()

    sections = call(scenario)["sections"]
    assert all(state["on"] is False for state in sections.values() if "on" in state)
    assert all(state["count"] == 0 for key, state in sections.items() if key != "portal_languages" and "count" in state)
    assert sections["portal_languages"] == {"on": False, "count": 1}
    assert sections["portal_ai_report"] == {"on": False}
    assert sections["portal_talon_chat"] == {"on": False}


def test_branding_switched_off_english_only_and_chat_without_ai_reports_read_off():
    async def scenario(client, db):
        return (await client.get(STATUS.format(code="GLOBEX"), headers=as_user("admin"))).json()

    sections = call(scenario)["sections"]
    assert sections["portal_branding"] == {"on": False}
    assert sections["portal_languages"] == {"on": False, "count": 1}
    # The chat row is on with a limit, but the AI reports are off: the chat is off.
    assert sections["portal_ai_report"] == {"on": False}
    assert sections["portal_talon_chat"] == {"on": False}
    assert sections["integrations"] == {"count": 1}


def test_the_chat_needs_a_customer_limit():
    async def scenario(client, db):
        async with db.factory() as session:
            row = (await session.execute(CustomerPortalChatSettings.__table__.select())).first()
            assert row is not None
            await session.execute(
                CustomerPortalChatSettings.__table__.update()
                .where(CustomerPortalChatSettings.customer_code == "ACME")
                .values(daily_message_limit=None),
            )
            await session.commit()
        return (await client.get(STATUS.format(code="ACME"), headers=as_user("admin"))).json()

    sections = call(scenario)["sections"]
    assert sections["portal_ai_report"] == {"on": True}
    assert sections["portal_talon_chat"] == {"on": False}


def test_who_may_read_it():
    async def scenario(client, db):
        return [
            (await client.get(STATUS.format(code="ACME"), headers=as_user("ana"))).status_code,
            (await client.get(STATUS.format(code="GLOBEX"), headers=as_user("ana"))).status_code,
            (await client.get(STATUS.format(code="ACME"), headers=as_user("portal"))).status_code,
            (await client.get(STATUS.format(code="ACME"))).status_code,
            (await client.get(STATUS.format(code="NOPE"), headers=as_user("admin"))).status_code,
        ]

    analyst_own, analyst_other, portal_user, anonymous, unknown = call(scenario)
    assert analyst_own == 200
    assert analyst_other == 403
    assert portal_user in (401, 403)
    assert anonymous in (401, 403)
    assert unknown == 404


def test_one_statement():
    async def scenario(client, db):
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        event.listen(db.engine.sync_engine, "before_cursor_execute", count)
        try:
            async with db.factory() as session:
                status = await get_section_status("ACME", session)
        finally:
            event.remove(db.engine.sync_engine, "before_cursor_execute", count)
        return status, statements

    status, statements = call(scenario)
    assert status.event_sources.count == 3
    assert len(statements) == 1
