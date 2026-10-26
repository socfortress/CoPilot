"""E2E for #1310 (the Customer Portal's languages) — NOT collected by pytest (needs a live MySQL).

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py (see its
docstring for the setup), then:

    .venv/bin/python tests/e2e/customer_portal_languages_e2e.py

Real routers, real MySQL, a real portal login:

  A) a customer has English only until an admin enables more; an analyst reads it; English can't
     be removed and an unknown code is refused; the change is in the audit log, old and new;
  B) the portal user picks a language enabled for their customer; it is stored on the account
     and /me shows it; a language enabled for none of their customers is refused;
  C) a user of two customers picks from the union of their languages;
  D) the language disabled, the portal shows English; enabled again, the pick is back;
  E) a deleted customer takes its languages with it (ON DELETE CASCADE);
  F) the migration downgrades (table and column gone) and upgrades again.

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
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalLanguageSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

TEMP_CUSTOMER = "E2E_LANG_TMP"
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def stored_locale(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User.locale).where(User.username == username))).scalar_one_or_none()


async def main():
    portal_user_id = (await seed())["portal_user_id"]
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
    settings_a = f"/customer_portal/languages/settings/{CUST_A}"
    settings_b = f"/customer_portal/languages/settings/{CUST_B}"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        portal = {"Authorization": f"Bearer {login.json()['access_token']}"}

        async def me():
            return (await client.get("/customer_portal/me", headers=portal)).json()

        print("\n=== A) a customer's languages ===")
        # Audit rows outlive the seed (other runs, the browser suite): count only this run's.
        async with AsyncSession(async_engine) as s:
            audit_floor = (await s.execute(select(func.coalesce(func.max(AuditLog.id), 0)))).scalar_one()
        body = (await client.get(settings_a, headers=admin)).json()
        check("English only at first", body["settings"]["languages"] == ["en"], str(body)[:200])
        check(
            "the editor gets every supported language",
            body["supported"] == ["en", "it", "de", "fr", "es", "nl", "cs"],
            str(body["supported"]),
        )
        saved = await client.put(settings_a, headers=admin, json={"languages": ["it", "en"]})
        check(
            "an admin enables Italian",
            saved.status_code == 200 and saved.json()["settings"]["languages"] == ["en", "it"],
            saved.text[:200],
        )
        no_english = await client.put(settings_a, headers=admin, json={"languages": ["it"]})
        check("English can't be removed (422)", no_english.status_code == 422, no_english.text[:200])
        unknown = await client.put(settings_a, headers=admin, json={"languages": ["en", "pt"]})
        check("an unknown language is refused (422)", unknown.status_code == 422, unknown.text[:200])
        by_portal = await client.put(settings_a, headers=portal, json={"languages": ["en", "it"]})
        check("a portal user can't set it (403)", by_portal.status_code == 403)
        async with AsyncSession(async_engine) as s:
            rows = (
                (
                    await s.execute(
                        select(AuditLog)
                        .where(
                            AuditLog.id > audit_floor,
                            AuditLog.action == "portal_languages.settings_update",
                            AuditLog.customer_code == CUST_A,
                        )
                        .order_by(AuditLog.id.desc()),
                    )
                )
                .scalars()
                .all()
            )
        check(
            "the change is audited once, old and new",
            len(rows) == 1 and rows[0].old_value == {"languages": ["en"]} and rows[0].new_value == {"languages": ["en", "it"]},
            str([(r.old_value, r.new_value) for r in rows]),
        )

        print("\n=== B) the portal user's pick ===")
        body = await me()
        check(
            "/me: English, and the two to pick from",
            (body["locale"], body["available_locales"]) == ("en", ["en", "it"]),
            str(body)[:200],
        )
        picked = await client.put("/customer_portal/languages/me", headers=portal, json={"locale": "it"})
        check("the user picks Italian", picked.status_code == 200 and picked.json()["locale"] == "it", picked.text[:200])
        check("stored on the account", await stored_locale(PORTAL_USER) == "it")
        check("/me shows it", (await me())["locale"] == "it")
        refused = await client.put("/customer_portal/languages/me", headers=portal, json={"locale": "de"})
        check("German, enabled for none of their customers, is refused (400)", refused.status_code == 400, refused.text[:200])
        check("the stored pick is untouched", await stored_locale(PORTAL_USER) == "it")

        print("\n=== C) two customers: the union ===")
        await client.put(settings_b, headers=admin, json={"languages": ["en", "de", "nl"]})
        await client.post(f"/auth/users/{portal_user_id}/customers", headers=admin, json=[CUST_A, CUST_B])
        body = await me()
        check(
            "the union of both customers' languages",
            body["available_locales"] == ["en", "it", "de", "nl"],
            str(body["available_locales"]),
        )
        german = await client.put("/customer_portal/languages/me", headers=portal, json={"locale": "de"})
        check("German is now allowed", german.status_code == 200)
        await client.post(f"/auth/users/{portal_user_id}/customers", headers=admin, json=[CUST_A])
        body = await me()
        check("the second customer removed: German no longer shown, English instead", body["locale"] == "en", str(body)[:200])
        await client.put("/customer_portal/languages/me", headers=portal, json={"locale": "it"})

        print("\n=== D) a language disabled, then enabled again ===")
        await client.put(settings_a, headers=admin, json={"languages": ["en"]})
        body = await me()
        check(
            "disabled: English, with English only to pick",
            (body["locale"], body["available_locales"]) == ("en", ["en"]),
            str(body)[:200],
        )
        check("the stored pick is kept", await stored_locale(PORTAL_USER) == "it")
        await client.put(settings_a, headers=admin, json={"languages": ["en", "it"]})
        check("enabled again: the pick is back", (await me())["locale"] == "it")

        print("\n=== E) a deleted customer takes its languages ===")
        async with AsyncSession(async_engine) as s:
            s.add(Customers(customer_code=TEMP_CUSTOMER, customer_name="Temporary", contact_last_name="x", contact_first_name="x"))
            await s.commit()
        await client.put(f"/customer_portal/languages/settings/{TEMP_CUSTOMER}", headers=admin, json={"languages": ["en", "fr"]})
        async with AsyncSession(async_engine) as s:
            await s.execute(text("DELETE FROM customers WHERE customer_code = :code"), {"code": TEMP_CUSTOMER})
            await s.commit()
            left = (
                await s.execute(select(CustomerPortalLanguageSettings).where(CustomerPortalLanguageSettings.customer_code == TEMP_CUSTOMER))
            ).first()
        check("its row is gone with it", left is None)

    async with AsyncSession(async_engine) as s:
        await cleanup(s)

    print("\n=== F) the migration round trip ===")
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def schema():
        async with AsyncSession(async_engine) as s:
            table = bool((await s.execute(text("SHOW TABLES LIKE 'customer_portal_language_settings'"))).first())
            column = bool((await s.execute(text("SHOW COLUMNS FROM `user` LIKE 'locale'"))).first())
        return table, column

    await asyncio.to_thread(command.downgrade, config, "d0b7e1a2c3f4")
    check("downgrade drops the table and the column", await schema() == (False, False))
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings both back", await schema() == (True, True))
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
