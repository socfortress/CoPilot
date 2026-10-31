"""E2E for Talon portal chat, CoPilot's side (talon-analyst D97, PC-3) — NOT collected by pytest
(needs a live MySQL); run by hand.

The disposable MySQL on 13306 of customer_portal_overview_e2e.py (see its docstring; never the
MySQL in .env), then:

    .venv/bin/python tests/e2e/customer_portal_talon_chat_e2e.py

Real routers, real JWTs, real SQL. The unit tests run on SQLite, which ignores ``FOR UPDATE``;
this is where the migration and the locks are exercised:

  A) the migration: ``customer_portal_chat_settings`` and its unique customer key and cascade,
     ``customer_portal_soc_request.talon_draft_id`` (unique), ``customer_portal_ioc_lookup.reserved_by``;
  B) two admins saving the settings at once: both saved, versions 1 and 2, never a lost bump;
  C) the cascade: AI reports off turns the chat off in the same transaction, version bumped;
  D) the lookup meter under the customer's settings lock: two reservations racing for the last
     lookup of the day (one 201, one 429); the same value twice at once (one 201, one 409); two
     completions of one lookup at once (one 204, one 404);
  E) two filings of one draft at once (``soc_requests._reserve``): one row, the other refused by
     the unique ``talon_draft_id`` (``DraftAlreadyFiled``);
  F) the migration downgrades and upgrades again.

Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
from types import SimpleNamespace

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
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.customer_portal.services import soc_requests  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalChatSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocLookup  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequest  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequestSettings  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_pc_"
JANE = f"{PREFIX}jane"
SERVICE = "talon-analyst"  # the Talon service account's default name
PREVIOUS = "a1318a0b1c2d"
DRAFT = "6f1c0b55-7a39-4e57-9d6e-3f1a2b3c4d5e"
SETTINGS = f"/customer_portal/talon_chat/settings/{CUST_A}"
METER = "/talon/v2/portal/ioc_lookups"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def session():
    return AsyncSession(async_engine, expire_on_commit=False)


def build_app():
    from app.routers import customer_portal
    from app.routers import talon

    app = FastAPI()
    for module in (customer_portal, talon):
        app.include_router(module.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


async def alembic(target: str) -> None:
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade if target != "head" else command.upgrade, config, target)


async def schema() -> dict:
    async with session() as s:
        tables = {row[0] for row in (await s.execute(text("SHOW TABLES LIKE 'customer_portal_%'"))).all()}
        columns = {}
        for table in ("customer_portal_soc_request", "customer_portal_ioc_lookup"):
            columns[table] = {row[0] for row in (await s.execute(text(f"SHOW COLUMNS FROM {table}"))).all()}
        unique = {}
        for table, column in (("customer_portal_chat_settings", "customer_code"), ("customer_portal_soc_request", "talon_draft_id")):
            if table in tables:
                rows = (await s.execute(text(f"SHOW INDEX FROM {table} WHERE Column_name = :c"), {"c": column})).all()
                unique[table] = any(row[1] == 0 for row in rows)  # Non_unique
    return {"tables": tables, "columns": columns, "unique": unique}


async def cleanup() -> None:
    async with session() as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.in_([JANE, SERVICE])))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        for model in (
            CustomerPortalChatSettings,
            CustomerPortalIocLookup,
            CustomerPortalIocEnrichmentSettings,
            CustomerPortalSocRequestSettings,
            CustomerPortalAiReportSettings,
        ):
            await s.execute(delete(model).where(model.customer_code == CUST_A))
        await s.execute(delete(CustomerPortalSocRequest).where(CustomerPortalSocRequest.talon_draft_id == DRAFT))
        await s.execute(delete(AuditLog).where(AuditLog.action == "talon_portal_chat.update"))
        await s.commit()


async def setup() -> None:
    async with session() as s:
        for name, role in ((JANE, 4), (SERVICE, 2)):
            user = User(username=name, password="x" * 60, email=f"{name}@e2e.example", role_id=role)
            s.add(user)
            await s.flush()
            s.add(UserCustomerAccess(user_id=user.id, customer_code=CUST_A))
        s.add(CustomerPortalAiReportSettings(customer_code=CUST_A, enabled=True))
        s.add(CustomerPortalIocEnrichmentSettings(customer_code=CUST_A, enabled=True, daily_lookup_limit=1))
        s.add(CustomerPortalSocRequestSettings(customer_code=CUST_A, enabled=True))
        row = (await s.execute(select(TalonConnectorSettings).where(TalonConnectorSettings.connector_name == "Talon"))).scalars().first()
        if row is None:
            s.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=True))
        else:
            row.v2_enabled = True
        await s.commit()


async def main() -> int:
    await alembic("head")
    await seed(quiet=True)
    await cleanup()

    print("\n=== A) the migration ===")
    found = await schema()
    check("customer_portal_chat_settings exists", "customer_portal_chat_settings" in found["tables"])
    check("its customer_code is unique", found["unique"].get("customer_portal_chat_settings") is True)
    check("talon_draft_id is a unique column", "talon_draft_id" in found["columns"]["customer_portal_soc_request"])
    check("talon_draft_id's index is unique", found["unique"].get("customer_portal_soc_request") is True)
    check("customer_portal_ioc_lookup.reserved_by exists", "reserved_by" in found["columns"]["customer_portal_ioc_lookup"])

    await setup()
    try:
        await run()
    finally:
        await cleanup()

    print("\n=== F) the migration round trip ===")
    await alembic(PREVIOUS)
    found = await schema()
    check(
        "downgrade drops the table and the two columns",
        "customer_portal_chat_settings" not in found["tables"]
        and "talon_draft_id" not in found["columns"]["customer_portal_soc_request"]
        and "reserved_by" not in found["columns"]["customer_portal_ioc_lookup"],
    )
    await alembic("head")
    found = await schema()
    check(
        "upgrade brings them back",
        "customer_portal_chat_settings" in found["tables"] and found["unique"].get("customer_portal_soc_request") is True,
    )

    failed = [name for name, passed, _ in results if not passed]
    print("\n" + "=" * 60)
    print(f"RESULT: {len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    await async_engine.dispose()
    return 1 if failed else 0


async def run() -> None:
    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    service = {"Authorization": f"Bearer {await auth.encode_token(SERVICE)}"}
    async with session() as s:
        jane_id = (await s.execute(select(User.id).where(User.username == JANE))).scalar_one()
    on = {"portal_chat_enabled": True, "log_search_enabled": False, "daily_message_limit": 200, "user_daily_message_limit": 50}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        print("\n=== B) two admins saving at once ===")
        first, second = await asyncio.gather(
            client.put(SETTINGS, json=on, headers=admin),
            client.put(SETTINGS, json={**on, "log_search_enabled": True}, headers=admin),
        )
        versions = sorted(r.json()["settings"]["version"] for r in (first, second) if r.status_code == 200)
        check("both saved", (first.status_code, second.status_code) == (200, 200), f"{first.status_code} {second.status_code}")
        check("versions 1 and 2, never a lost bump", versions == [1, 2], str(versions))
        async with session() as s:
            rows = (
                (await s.execute(select(CustomerPortalChatSettings).where(CustomerPortalChatSettings.customer_code == CUST_A)))
                .scalars()
                .all()
            )
        check("one row for the customer", len(rows) == 1 and rows[0].version == 2)

        print("\n=== C) the cascade ===")
        off = await client.put(f"/customer_portal/ai_reports/settings/{CUST_A}", json={"enabled": False}, headers=admin)
        async with session() as s:
            row = (
                (await s.execute(select(CustomerPortalChatSettings).where(CustomerPortalChatSettings.customer_code == CUST_A)))
                .scalars()
                .one()
            )
        check(
            "AI reports off turns the chat off, version bumped",
            off.status_code == 200 and not row.portal_chat_enabled and row.version == 3,
        )
        await client.put(f"/customer_portal/ai_reports/settings/{CUST_A}", json={"enabled": True}, headers=admin)

        print("\n=== D) the lookup meter under the lock ===")

        def reserve(value):
            return client.post(METER, json={"customer_code": CUST_A, "user_id": jane_id, "value": value}, headers=service)

        same = await asyncio.gather(reserve("93.184.216.34"), reserve("93.184.216.34"))
        check(
            "the same value twice at once: one 201, one 409",
            sorted(r.status_code for r in same) == [201, 409],
            str([r.text for r in same]),
        )
        lookup_id = next(r.json()["lookup_id"] for r in same if r.status_code == 201)
        completions = await asyncio.gather(
            client.post(f"{METER}/{lookup_id}/complete", json={"answered": False}, headers=service),
            client.post(f"{METER}/{lookup_id}/complete", json={"answered": True}, headers=service),
        )
        check(
            "two completions at once: one 204, one 404",
            sorted(r.status_code for r in completions) == [204, 404],
            str([r.status_code for r in completions]),
        )
        async with session() as s:
            await s.execute(delete(CustomerPortalIocLookup).where(CustomerPortalIocLookup.customer_code == CUST_A))
            await s.commit()
        last = await asyncio.gather(reserve("151.101.1.69"), reserve("151.101.65.69"))
        check(
            "two values racing for the last lookup: one 201, one 429",
            sorted(r.status_code for r in last) == [201, 429],
            str([r.text for r in last]),
        )
        async with session() as s:
            rows = (await s.execute(select(CustomerPortalIocLookup).where(CustomerPortalIocLookup.customer_code == CUST_A))).scalars().all()
        check("one lookup row, the meter's", len(rows) == 1 and rows[0].reserved_by == "talon" and rows[0].requested_by_user_id == jane_id)

    print("\n=== E) two filings of one draft at once ===")
    user = SimpleNamespace(id=jane_id, username=JANE, role_id=4)

    async def reserve_request(cooldown_case):
        # Distinct cooldown keys, so CoPilot's own rules pass for both and only the unique key decides.
        async with session() as s:
            try:
                row = await soc_requests._reserve(
                    user,
                    CUST_A,
                    s,
                    question="q",
                    urgency="normal",
                    cooldown_case=cooldown_case,
                    talon_draft_id=DRAFT,
                )
                return row.id
            except soc_requests.DraftAlreadyFiled:
                return "already filed"
            except soc_requests.SocRequestRefused as e:
                return f"refused: {e.code}"

    outcomes = await asyncio.gather(reserve_request(2_000_000_001), reserve_request(2_000_000_002))
    async with session() as s:
        rows = (await s.execute(select(CustomerPortalSocRequest).where(CustomerPortalSocRequest.talon_draft_id == DRAFT))).scalars().all()
    check("one request row", len(rows) == 1, str(outcomes))
    check("the other refused by the unique draft id", sorted(map(str, outcomes))[-1] == "already filed", str(outcomes))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
