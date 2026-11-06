"""E2E for #1325 (the status lights of a customer's page) — NOT collected by pytest (needs a live
MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_section_status_e2e.py

Real routers, real JWTs, real SQL: ``GET /customers/{code}/sections/status`` for a customer of its
own (``E2E_SS``), created here with a row in every table it reads and removed afterwards.

  A) every section as stored: switches on, off and missing, the languages, the portal chat, lists
     counted for this customer only;
  B) the AI reports switched off take the chat with them; a branding row switched off is off;
  C) who may read it: an admin, an analyst for their own customers only (403 otherwise); an
     unknown customer is a 404;
  D) one SQL statement for the whole answer, on MySQL (JSON included).

Exits non-zero when a check fails.
"""

import asyncio
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customers.services.section_status import get_section_status  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalAuditSettings  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import CustomerPortalChatSettings  # noqa: E402
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
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.customer_portal_audit_e2e import upgrade_head  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
CODE = "E2E_SS"
ANALYST = "e2e_ss_analyst"
PASSWORD = "Section-Status-2026!x"
STATUS = "/customers/{code}/sections/status"

#: Every table the status reads, holding rows for CODE (removed before and after the run).
OWNED = (
    CustomerNotificationRoute,
    CustomerPortalAiReportSettings,
    CustomerPortalAuditSettings,
    CustomerPortalBranding,
    CustomerPortalChatSettings,
    CustomerPortalLanguageSettings,
    CustomerPortalSlaSettings,
    CustomerWafInstance,
    EventSources,
    AIAnalystTriggerEnabled,
    Notification,
    CustomerIntegrations,
)


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def build_app() -> FastAPI:
    from app.routers import auth
    from app.routers import customers

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(customers.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


async def clean():
    async with AsyncSession(async_engine) as s:
        for model in OWNED:
            await s.execute(delete(model).where(model.customer_code == CODE))
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username == ANALYST))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(delete(Customers).where(Customers.customer_code == CODE))
        await s.commit()


async def seed_customer():
    async with AsyncSession(async_engine) as s:
        s.add(Customers(customer_code=CODE, customer_name="E2E section status"))
        await s.commit()
        s.add_all(
            [
                AIAnalystTriggerEnabled(customer_code=CODE, enabled=True),
                CustomerPortalSlaSettings(customer_code=CODE, enabled=True),
                CustomerPortalAuditSettings(customer_code=CODE, enabled=False),
                CustomerPortalAiReportSettings(customer_code=CODE, enabled=True),
                CustomerPortalChatSettings(customer_code=CODE, portal_chat_enabled=True, daily_message_limit=40),
                # A large logo: the status reads only `enabled`.
                CustomerPortalBranding(customer_code=CODE, enabled=True, title="E2E", logo_base64="A" * 200_000),
                CustomerPortalLanguageSettings(customer_code=CODE, languages=["en", "it", "fr"]),
                CustomerIntegrations(
                    customer_code=CODE,
                    customer_name=CODE,
                    integration_service_id=1,
                    integration_service_name="Office365",
                ),
                CustomerIntegrations(customer_code=CODE, customer_name=CODE, integration_service_id=2, integration_service_name="Huntress"),
                EventSources(customer_code=CODE, name="e2e-ss-wazuh", index_pattern="e2e-ss-*", event_type="EDR"),
                CustomerWafInstance(
                    customer_code=CODE,
                    name="prod",
                    api_url="https://waf",
                    service_token_encrypted="x",
                    token_prefix="wafst_",
                ),
                CustomerNotificationRoute(
                    customer_code=CODE,
                    name="e2e",
                    trigger="alert_created",
                    channel="webhook",
                    destination="https://h",
                ),
                Notification(customer_code=CODE, shuffle_workflow_id="wf-e2e"),
            ],
        )
        await s.commit()


async def main():
    await upgrade_head()
    await seed(quiet=True)
    await clean()
    await seed_customer()
    admin = bearer(await AuthHandler().encode_token(ADMIN))

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
            created = await client.post(
                "/auth/register",
                json={
                    "username": ANALYST,
                    "password": PASSWORD,
                    "email": f"{ANALYST}@e2e.example",
                    "role_id": 2,
                    "customer_codes": [CUST_A],
                },
                headers=admin,
            )
            if created.status_code != 201:
                print(f"could not create {ANALYST}: {created.status_code} {created.text[:200]}")
                return 1
            async with AsyncSession(async_engine) as s:
                await s.execute(update(User).where(User.username == ANALYST).values(must_change_password=False))
                await s.commit()
            analyst = bearer(await AuthHandler().encode_token(ANALYST))

            print("\n=== A) every section as stored ===")
            answer = await client.get(STATUS.format(code=CODE), headers=admin)
            body = answer.json()
            sections = body.get("sections") or {}
            check("an admin reads it", answer.status_code == 200 and body.get("customer_code") == CODE, str(answer.status_code))
            check("a switch on", sections.get("portal_sla") == {"on": True} and sections.get("ai_triggers") == {"on": True})
            check("a switch row turned off", sections.get("portal_audit") == {"on": False})
            check(
                "no row reads as off",
                all(
                    sections.get(key) == {"on": False}
                    for key in ("portal_activity", "portal_exposure", "portal_ask_soc", "portal_notifications")
                ),
            )
            check("the branding switched on", sections.get("portal_branding") == {"on": True})
            check(
                "the languages, from MySQL's JSON",
                sections.get("portal_languages") == {"on": True, "count": 3},
                str(sections.get("portal_languages")),
            )
            check(
                "the AI reports and their chat",
                sections.get("portal_ai_report") == {"on": True} and sections.get("portal_talon_chat") == {"on": True},
            )
            check(
                "the lists, this customer's only",
                [
                    sections.get(key)
                    for key in (
                        "integrations",
                        "event_sources",
                        "waf",
                        "notification_routes",
                        "notification_workflows",
                        "network_connectors",
                        "knowledge",
                    )
                ]
                == [{"count": 2}, {"count": 1}, {"count": 1}, {"count": 1}, {"count": 1}, {"count": 0}, {"count": 0}],
                str(sections),
            )

            print("\n=== B) the chat goes with the AI reports; branding off ===")
            async with AsyncSession(async_engine) as s:
                await s.execute(
                    update(CustomerPortalAiReportSettings)
                    .where(CustomerPortalAiReportSettings.customer_code == CODE)
                    .values(enabled=False),
                )
                await s.execute(update(CustomerPortalBranding).where(CustomerPortalBranding.customer_code == CODE).values(enabled=False))
                await s.commit()
            sections = (await client.get(STATUS.format(code=CODE), headers=admin)).json()["sections"]
            check(
                "AI reports off: the chat off",
                sections["portal_ai_report"] == {"on": False} and sections["portal_talon_chat"] == {"on": False},
                str((sections["portal_ai_report"], sections["portal_talon_chat"])),
            )
            check("a branding row switched off", sections["portal_branding"] == {"on": False})

            print("\n=== C) who may read it ===")
            own = await client.get(STATUS.format(code=CUST_A), headers=analyst)
            other = await client.get(STATUS.format(code=CODE), headers=analyst)
            unknown = await client.get(STATUS.format(code="E2E_NOPE"), headers=admin)
            anonymous = await client.get(STATUS.format(code=CODE))
            check("an analyst, their own customer", own.status_code == 200, str(own.status_code))
            check("an analyst, another customer: 403", other.status_code == 403, str(other.status_code))
            check("an unknown customer: 404", unknown.status_code == 404, str(unknown.status_code))
            check("no token: refused", anonymous.status_code in (401, 403), str(anonymous.status_code))

            print("\n=== D) one statement ===")
            counter = StatementCounter()
            async with AsyncSession(async_engine) as s:
                counter.reset()
                await get_section_status(CODE, s)
            check("the whole answer is one SQL statement", len(counter.statements) == 1, str(len(counter.statements)))
    finally:
        await clean()

    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
