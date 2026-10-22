"""E2E for #1296 (a customer admin manages their customers' portal users) — NOT collected by
pytest (needs a live MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_portal_tenant_users_e2e.py

Real routers, real JWTs, real SQL; only SMTP is replaced, in process, by a recorder (whatever the
environment says: no real email can leave). It checks, on the routes a browser calls:

  A) the migration: both columns, their defaults, and an existing account neither admin nor disabled;
  B) the SOC appoints a customer admin (audited), only a portal user with access, admins only;
     the Security tab and /customer_portal/me show it;
  C) the list: the administered customer's portal users only (no SOC user, no other tenant's user),
     another customer never named, who may be managed and why not;
  D) invitations: password shown without SMTP (no-store), emailed with it (never in the response),
     shown when the email fails; the new user signs in held on the change; duplicates and other
     customers refused; audited;
  E) disabling: the user's session ends at its next request (401, X-Account-Disabled), sign-in
     refused (also between the password and the second factor), enabling restores it; audited;
  F) what a customer admin may not do: themself, another admin, a shared account (403 with the
     reason), another tenant's or a SOC user (404), a plain portal user (403 on everything);
  G) 2FA reset and a temporary password, audited; the old password stops working;
  H) the SOC disables and enables a portal user too, never a SOC user;
  I) a disabled account is sent no portal notification;
  J) the migration downgrades and upgrades again.

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

from unittest.mock import AsyncMock  # noqa: E402
from unittest.mock import patch  # noqa: E402

import httpx  # noqa: E402
import pyotp  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.totp import UserTOTP  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.services import security_admin  # noqa: E402
from app.auth.services import totp as totp_service  # noqa: E402
from app.auth.services.account_status import ACCOUNT_DISABLED  # noqa: E402
from app.auth.services.account_status import ACCOUNT_DISABLED_HEADER  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services.notifications import portal_users_of  # noqa: E402
from app.customer_portal.services.tenant_users import REASON_ADMIN  # noqa: E402
from app.customer_portal.services.tenant_users import (  # noqa: E402
    REASON_OTHER_CUSTOMER,
)
from app.customer_portal.services.tenant_users import REASON_SELF  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_tu_"
CADMIN = f"{PREFIX}cadmin"
COLLEAGUE = f"{PREFIX}colleague"
SHARED = f"{PREFIX}shared"
OTHER_ADMIN = f"{PREFIX}otheradmin"
BETA_USER = f"{PREFIX}beta"
ANALYST = f"{PREFIX}analyst"
INVITED = f"{PREFIX}invited"
MAILED = f"{PREFIX}mailed"
UNLUCKY = f"{PREFIX}unlucky"
PASSWORD = "Tenant-Users-2026!"
MIGRATION = "b1296a0c1d2e"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


async def user_row(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User).where(User.username == username))).scalars().first()


async def user_id(username):
    return (await user_row(username)).id


async def audit_actions(username):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(
            select(AuditLog.action, AuditLog.actor_username, AuditLog.customer_code)
            .where(AuditLog.entity_id == username)
            .order_by(AuditLog.id),
        )
        return [tuple(row) for row in rows.all()]


async def remove_users():
    async with AsyncSession(async_engine) as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.like(f"{PREFIX}%")))).all()]
        if ids:
            await s.execute(delete(UserTOTP).where(UserTOTP.user_id.in_(ids)))
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(delete(AuditLog).where(AuditLog.entity_id.like(f"{PREFIX}%")))
        await s.commit()


async def release(username):
    """A seeded account is used as is: not held on the password change (#1277)."""
    async with AsyncSession(async_engine) as s:
        await s.execute(update(User).where(User.username == username).values(must_change_password=False))
        await s.commit()


async def migration_round_trip():
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def columns():
        async with AsyncSession(async_engine) as s:
            disabled = (await s.execute(text("SHOW COLUMNS FROM user LIKE 'disabled_at'"))).all()
            admin = (await s.execute(text("SHOW COLUMNS FROM user_customer_access LIKE 'is_customer_admin'"))).all()
            return bool(disabled), bool(admin)

    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade, config, "a1289e0b1c2d")
    check("downgrade drops both columns", await columns() == (False, False))
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings them back", await columns() == (True, True))


async def main():
    await seed()
    await remove_users()
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

    app = build_app()
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    sent = []

    async def record_email(to_addr, subject, body, html_body=None):
        sent.append({"to": to_addr, "subject": subject, "body": body})

    # No real email may leave, whatever SMTP_* says in this environment.
    smtp_off = (
        patch.object(security_admin, "smtp_configured", return_value=False),
        patch.object(security_admin, "send_email", AsyncMock()),
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:

        def bearer(token):
            return {"Authorization": f"Bearer {token}"}

        async def portal_login(username, password=PASSWORD):
            return await client.post("/auth/token/customer-portal", data={"username": username, "password": password})

        async def token_of(username, password=PASSWORD):
            response = await portal_login(username, password)
            return response.json().get("access_token")

        async def register(username, role_id, codes):
            response = await client.post(
                "/auth/register",
                json={
                    "username": username,
                    "password": PASSWORD,
                    "email": f"{username}@e2e.example",
                    "role_id": role_id,
                    "customer_codes": codes,
                },
                headers=admin,
            )
            await release(username)
            return response

        for username, role, codes in (
            (CADMIN, 4, [CUST_A]),
            (COLLEAGUE, 4, [CUST_A]),
            (SHARED, 4, [CUST_A, CUST_B]),
            (OTHER_ADMIN, 4, [CUST_A]),
            (BETA_USER, 4, [CUST_B]),
            (ANALYST, 2, [CUST_A]),
        ):
            created = await register(username, role, codes)
            if created.status_code != 201:
                print(f"could not create {username}: {created.status_code} {created.text[:200]}")
                return 1

        print("\n=== A) the migration ===")
        async with AsyncSession(async_engine) as s:
            disabled = (await s.execute(text("SHOW COLUMNS FROM user LIKE 'disabled_at'"))).all()
            admin_col = (await s.execute(text("SHOW COLUMNS FROM user_customer_access LIKE 'is_customer_admin'"))).all()
        check("user.disabled_at exists, nullable", disabled and disabled[0][2] == "YES", str(disabled))
        check(
            "user_customer_access.is_customer_admin exists, not null, default 0",
            admin_col and admin_col[0][2] == "NO" and str(admin_col[0][4]) == "0",
        )
        seeded = await user_row(PORTAL_USER)
        check("an existing account is not disabled", seeded.disabled_at is None)

        print("\n=== B) the SOC appoints a customer admin ===")
        cadmin_id = await user_id(CADMIN)
        url = f"/auth/security/customers/{CUST_A}/users/{{}}/customer-admin"
        appointed = await client.put(url.format(cadmin_id), json={"is_customer_admin": True}, headers=admin)
        check("appointed", appointed.status_code == 200, appointed.text[:200])
        await client.put(url.format(await user_id(OTHER_ADMIN)), json={"is_customer_admin": True}, headers=admin)
        check(
            "audited with old and new values",
            ("customer_admin.update", ADMIN, CUST_A) in await audit_actions(CADMIN),
            str(await audit_actions(CADMIN)),
        )
        not_portal = await client.put(url.format(await user_id(ANALYST)), json={"is_customer_admin": True}, headers=admin)
        check("a SOC user can't be one (400)", not_portal.status_code == 400, not_portal.text[:120])
        wrong_customer = await client.put(
            f"/auth/security/customers/{CUST_B}/users/{cadmin_id}/customer-admin",
            json={"is_customer_admin": True},
            headers=admin,
        )
        check("nor for a customer they can't see (400)", wrong_customer.status_code == 400)
        analyst_token = {"Authorization": f"Bearer {await AuthHandler().encode_token(ANALYST)}"}
        by_analyst = await client.put(url.format(await user_id(COLLEAGUE)), json={"is_customer_admin": True}, headers=analyst_token)
        check("an analyst can't appoint (403)", by_analyst.status_code == 403)
        listed = (await client.get(f"/auth/security/customers/{CUST_A}/users", headers=admin)).json()["users"]
        flags = {u["username"]: u["is_customer_admin"] for u in listed}
        check("the Security tab shows it", flags.get(CADMIN) is True and flags.get(COLLEAGUE) is False, str(flags))

        cadmin = bearer(await token_of(CADMIN))
        me = (await client.get("/customer_portal/me", headers=cadmin)).json()
        check(
            "/customer_portal/me says which customer they administer",
            [(c["customer_code"], c["is_customer_admin"]) for c in me["customers"]] == [(CUST_A, True)],
            str(me["customers"]),
        )

        print("\n=== C) the list ===")
        listing = await client.get("/customer_portal/users", headers=cadmin)
        body = listing.json()
        users = {u["username"]: u for u in body.get("users", [])}
        check("200", listing.status_code == 200, listing.text[:200])
        check("the administered customer only", [c["customer_code"] for c in body["customers"]] == [CUST_A])
        check("its portal users", {CADMIN, COLLEAGUE, SHARED, OTHER_ADMIN, PORTAL_USER} <= set(users), str(sorted(users)))
        check("no SOC user, no other tenant's user", ANALYST not in users and BETA_USER not in users)
        check("the caller first", body["users"][0]["username"] == CADMIN)
        check("another customer is never named", CUST_B not in listing.text)
        check(
            "the caller can't manage themself",
            (users[CADMIN]["can_manage"], users[CADMIN]["managed_by_soc_reason"]) == (False, REASON_SELF),
        )
        check("nor another admin", users[OTHER_ADMIN]["managed_by_soc_reason"] == REASON_ADMIN)
        check("nor a shared account", users[SHARED]["managed_by_soc_reason"] == REASON_OTHER_CUSTOMER)
        check("a plain colleague can be managed", users[COLLEAGUE]["can_manage"] is True)
        plain = bearer(await token_of(COLLEAGUE))
        refused = await client.get("/customer_portal/users", headers=plain)
        check("a portal user who administers nothing gets a 403", refused.status_code == 403)

        print("\n=== D) invitations ===")
        with smtp_off[0], smtp_off[1]:
            invite = await client.post(
                "/customer_portal/users",
                json={"username": INVITED, "email": f"{INVITED}@e2e.example", "customer_codes": [CUST_A]},
                headers=cadmin,
            )
        body = invite.json()
        temporary = body.get("temporary_password")
        check("201", invite.status_code == 201, invite.text[:200])
        check("without SMTP the password is shown once", body.get("delivery") == "shown" and bool(temporary))
        check("and not stored by the browser", invite.headers.get("cache-control") == "no-store")
        invited = await user_row(INVITED)
        async with AsyncSession(async_engine) as s:
            rows = (
                await s.execute(
                    select(UserCustomerAccess.customer_code, UserCustomerAccess.is_customer_admin).where(
                        UserCustomerAccess.user_id == invited.id,
                    ),
                )
            ).all()
        check(
            "a portal user of that customer, never an admin",
            invited.role_id == 4 and [tuple(r) for r in rows] == [(CUST_A, False)],
            str(rows),
        )
        login = await portal_login(INVITED, temporary)
        check("who signs in held on the password change", login.status_code == 200 and login.json().get("must_change_password") is True)
        actions = [a for a, *_ in await audit_actions(INVITED)]
        check("audited", "customer_user.invite" in actions and "user.password_change_required" in actions, str(actions))

        duplicate = await client.post(
            "/customer_portal/users",
            json={"username": INVITED.upper(), "email": "x@e2e.example", "customer_codes": [CUST_A]},
            headers=cadmin,
        )
        check("a taken username is a 409 (any case)", duplicate.status_code == 409)
        same_email = await client.post(
            "/customer_portal/users",
            json={"username": f"{PREFIX}other", "email": f"{INVITED}@e2e.example", "customer_codes": [CUST_A]},
            headers=cadmin,
        )
        check("a registered email is a 409", same_email.status_code == 409)
        elsewhere = await client.post(
            "/customer_portal/users",
            json={"username": PREFIX + "else", "email": "else@e2e.example", "customer_codes": [CUST_B]},
            headers=cadmin,
        )
        check("another customer is a 403", elsewhere.status_code == 403)
        bad_name = await client.post(
            "/customer_portal/users",
            json={"username": "a b", "email": "ab@e2e.example", "customer_codes": [CUST_A]},
            headers=cadmin,
        )
        check("a bad username is a 422", bad_name.status_code == 422)
        by_plain = await client.post(
            "/customer_portal/users",
            json={"username": f"{PREFIX}nope", "email": "nope@e2e.example", "customer_codes": [CUST_A]},
            headers=plain,
        )
        check("a plain portal user can't invite (403)", by_plain.status_code == 403)
        check("nothing was created by the refusals", await user_row(PREFIX + "else") is None and await user_row(f"{PREFIX}nope") is None)

        generated = []
        real_generate = security_admin.generate_temporary_password

        def capture():
            password = real_generate()
            generated.append(password.plain)
            return password

        with (
            patch.object(security_admin, "smtp_configured", return_value=True),
            patch.object(security_admin, "send_email", side_effect=record_email),
            patch.object(security_admin, "generate_temporary_password", side_effect=capture),
        ):
            mailed = await client.post(
                "/customer_portal/users",
                json={"username": MAILED, "email": f"{MAILED}@e2e.example", "customer_codes": [CUST_A]},
                headers=cadmin,
            )
        body = mailed.json()
        check("with SMTP the password is emailed", mailed.status_code == 201 and body.get("delivery") == "email")
        check("and never in the response", body.get("temporary_password") is None and 'temporary_password": "' not in mailed.text)
        check("to the invited address", [m["to"] for m in sent] == [f"{MAILED}@e2e.example"], str(sent))
        emailed = generated[0] if generated else None
        check("the email carries the generated password", bool(sent) and emailed and emailed in sent[0]["body"])
        check("which signs in", emailed and (await portal_login(MAILED, emailed)).status_code == 200)

        with patch.object(security_admin, "smtp_configured", return_value=True), patch.object(
            security_admin,
            "send_email",
            AsyncMock(side_effect=OSError("relay down")),
        ):
            unlucky = await client.post(
                "/customer_portal/users",
                json={"username": UNLUCKY, "email": f"{UNLUCKY}@e2e.example", "customer_codes": [CUST_A]},
                headers=cadmin,
            )
        body = unlucky.json()
        check(
            "a failed email shows the password instead, and says why",
            unlucky.status_code == 201 and body.get("delivery") == "shown" and body.get("temporary_password") and body.get("email_problem"),
        )

        print("\n=== E) disabling ===")
        colleague_id = await user_id(COLLEAGUE)
        disabled = await client.post(f"/customer_portal/users/{colleague_id}/disable", headers=cadmin)
        check("disabled", disabled.status_code == 200 and disabled.json()["user"]["disabled"] is True, disabled.text[:200])
        ended = await client.get("/customer_portal/me", headers=plain)
        check(
            "their session ends at its next request (401, header)",
            ended.status_code == 401 and ended.headers.get(ACCOUNT_DISABLED_HEADER) == "true",
            f"{ended.status_code} {dict(ended.headers)}",
        )
        refresh = await client.get("/auth/refresh", headers=plain)
        check("no refreshed token", refresh.status_code == 401)
        relogin = await portal_login(COLLEAGUE)
        check("sign-in refused, saying why", relogin.status_code == 401 and ACCOUNT_DISABLED in relogin.text, relogin.text[:200])
        again = await client.post(f"/customer_portal/users/{colleague_id}/disable", headers=cadmin)
        check("disabling again changes nothing", again.status_code == 200)
        enabled = await client.post(f"/customer_portal/users/{colleague_id}/enable", headers=cadmin)
        check("enabled", enabled.status_code == 200 and enabled.json()["user"]["disabled"] is False)
        check("they sign in again", (await portal_login(COLLEAGUE)).status_code == 200)
        actions = [(a, actor) for a, actor, _ in await audit_actions(COLLEAGUE)]
        check(
            "audited once each, by the customer admin",
            actions.count(("user.disable", CADMIN)) == 1 and actions.count(("user.enable", CADMIN)) == 1,
            str(actions),
        )
        failures = [a for a, *_ in await audit_actions(COLLEAGUE) if a == "auth.login_failed"]
        check("the refused sign-in is audited", len(failures) == 1, str(failures))

        print("\n=== F) what a customer admin may not do ===")
        for target, status, reason in (
            (CADMIN, 403, REASON_SELF),
            (OTHER_ADMIN, 403, REASON_ADMIN),
            (SHARED, 403, REASON_OTHER_CUSTOMER),
            (BETA_USER, 404, None),
            (ANALYST, 404, None),
        ):
            tid = await user_id(target)
            for method, path in (("POST", "disable"), ("POST", "temporary-password"), ("DELETE", "totp")):
                response = await client.request(method, f"/customer_portal/users/{tid}/{path}", headers=cadmin)
                ok = response.status_code == status and (reason is None or reason in response.text)
                check(f"{target.removeprefix(PREFIX)}: {path} is a {status}", ok, f"{response.status_code} {response.text[:120]}")
        unknown = await client.post("/customer_portal/users/999999999/disable", headers=cadmin)
        check("an unknown id is a 404", unknown.status_code == 404)
        untouched = [(await user_row(n)).disabled_at is None for n in (CADMIN, OTHER_ADMIN, SHARED, BETA_USER, ANALYST)]
        check("nobody was disabled by the refusals", all(untouched))
        by_plain = await client.post(f"/customer_portal/users/{await user_id(INVITED)}/disable", headers=bearer(await token_of(COLLEAGUE)))
        check("a plain portal user can't disable anyone (403)", by_plain.status_code == 403)
        by_soc = await client.get("/customer_portal/users", headers=analyst_token)
        check("nor can a SOC user reach the portal's list (403)", by_soc.status_code == 403)

        print("\n=== G) 2FA reset and a temporary password ===")
        setup = await totp_service.setup_totp(colleague_id, COLLEAGUE)
        await totp_service.verify_setup(colleague_id, pyotp.TOTP(setup["secret"]).now())
        listed = {u["username"]: u for u in (await client.get("/customer_portal/users", headers=cadmin)).json()["users"]}
        check("the list shows 2FA on", listed[COLLEAGUE]["totp_enabled"] is True)
        reset = await client.delete(f"/customer_portal/users/{colleague_id}/totp", headers=cadmin)
        check("2FA reset", reset.status_code == 200 and reset.json()["user"]["totp_enabled"] is False, reset.text[:200])
        with smtp_off[0], smtp_off[1]:
            issued = await client.post(f"/customer_portal/users/{colleague_id}/temporary-password", headers=cadmin)
        fresh = issued.json().get("temporary_password")
        check("a temporary password, shown once", issued.status_code == 200 and fresh and issued.headers.get("cache-control") == "no-store")
        check("the old password stops working", (await portal_login(COLLEAGUE)).status_code == 401)
        login = await portal_login(COLLEAGUE, fresh)
        check("the new one signs in, held on the change", login.status_code == 200 and login.json().get("must_change_password") is True)
        actions = [a for a, *_ in await audit_actions(COLLEAGUE)]
        check("audited", "customer_user.totp_reset" in actions and "customer_user.password_reset" in actions, str(actions))

        print("\n=== E bis) disabled between the password and the second factor ===")
        other_id = await user_id(MAILED)
        await release(MAILED)
        async with AsyncSession(async_engine) as s:
            await s.execute(update(User).where(User.id == other_id).values(password=AuthHandler().get_password_hash(PASSWORD)))
            await s.commit()
        setup = await totp_service.setup_totp(other_id, MAILED)
        await totp_service.verify_setup(other_id, pyotp.TOTP(setup["secret"]).now())
        first = (await portal_login(MAILED)).json()
        check("the password asks for the second factor", first.get("requires_2fa") is True, str(first)[:120])
        await client.post(f"/customer_portal/users/{other_id}/disable", headers=cadmin)
        second = await client.post(
            "/auth/2fa/validate",
            json={"temp_token": first["access_token"], "code": pyotp.TOTP(setup["secret"]).now()},
        )
        check(
            "the second factor is refused once disabled",
            second.status_code == 401 and ACCOUNT_DISABLED in second.text,
            second.text[:200],
        )
        check("and so is the password", (await portal_login(MAILED)).status_code == 401)

        print("\n=== H) the SOC disables and enables a portal user ===")
        beta_id = await user_id(BETA_USER)
        soc_disable = await client.post(f"/auth/security/users/{beta_id}/disable", headers=admin)
        check("disabled by the SOC", soc_disable.status_code == 200 and (await user_row(BETA_USER)).disabled_at is not None)
        shown = {u["username"]: u for u in (await client.get(f"/auth/security/customers/{CUST_B}/users", headers=admin)).json()["users"]}
        check("the Security tab shows it", shown[BETA_USER]["disabled_at"] is not None)
        check("they can't sign in", (await portal_login(BETA_USER)).status_code == 401)
        soc_enable = await client.post(f"/auth/security/users/{beta_id}/enable", headers=admin)
        check("enabled by the SOC", soc_enable.status_code == 200 and (await portal_login(BETA_USER)).status_code == 200)
        not_portal = await client.post(f"/auth/security/users/{await user_id(ANALYST)}/disable", headers=admin)
        check("a SOC user is not disabled here (400)", not_portal.status_code == 400)
        by_analyst = await client.post(f"/auth/security/users/{beta_id}/disable", headers=analyst_token)
        check("an analyst can't (403)", by_analyst.status_code == 403)
        actions = [(a, actor) for a, actor, _ in await audit_actions(BETA_USER)]
        check("audited as the SOC admin", ("user.disable", ADMIN) in actions and ("user.enable", ADMIN) in actions, str(actions))

        print("\n=== I) no notification for a disabled account ===")
        await client.post(f"/customer_portal/users/{colleague_id}/disable", headers=cadmin)
        async with AsyncSession(async_engine) as s:
            recipients = [u.username for u in await portal_users_of(CUST_A, s)]
        check("not a recipient", COLLEAGUE not in recipients and INVITED in recipients, str(recipients))

        print("\n=== J) the migration round trip ===")
        await remove_users()
        await migration_round_trip()

    await remove_users()
    failed = [name for name, passed, _ in results if not passed]
    print("\n" + "=" * 60)
    print(f"RESULT: {len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    await async_engine.dispose()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
