"""E2E for #1277 (a password an admin chose must be replaced) — NOT collected by pytest
(needs a live MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/password_change_e2e.py

Real routers, real JWTs, real SQL; only SMTP is replaced, in process, by a recorder. It
checks, on the routes a browser calls:

  A) the migration: the column exists and an account already in use is not held;
  B) an account an admin creates is held: the portal login says so, the portal reaches only
     the change, its profile, a token refresh and its branding (403 with the header, never
     401, everywhere else), and the audit records who set it;
  C) the change: the password received is required, the same password is refused, a wrong
     one keeps the hold, the right one lifts it for the very token in use;
  D) an admin reset holds the user again mid-session; an admin resetting their own does not;
  E) an emailed temporary password holds the user, also when the email fails;
  F) a 2FA login says so too, and an analyst carries the flag without being held (and changes
     their own as the analyst frontend does, without the current password);
  G) the customer's Security tab shows who still has to change.

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
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.totp import UserTOTP  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.services import security_admin  # noqa: E402
from app.auth.services import totp as totp_service  # noqa: E402
from app.auth.services.password_change import PASSWORD_CHANGE_HEADER  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_pwc_"
CUSTOMER = f"{PREFIX}customer"
ANALYST = f"{PREFIX}analyst"
FIRST = "Given-By-Admin-2026!"
CHOSEN = "My-Own-Choice-2026!"
RESET = "Reset-By-Admin-2026!"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


async def flag(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User.must_change_password).where(User.username == username))).scalar_one()


async def audit_actions(username):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(select(AuditLog.action, AuditLog.actor_username).where(AuditLog.entity_id == username).order_by(AuditLog.id))
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


async def main():
    await seed()
    await remove_users()
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

    # The app's own exception handler, as in production: it is what turns the refusal into
    # the response the portal reads, and it used to drop the exception's headers.
    app = build_app()
    app.add_exception_handler(HTTPException, custom_http_exception_handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:

        async def portal_login(username, password):
            return await client.post("/auth/token/customer-portal", data={"username": username, "password": password})

        def bearer(token):
            return {"Authorization": f"Bearer {token}"}

        print("\n=== A) the migration ===")
        async with AsyncSession(async_engine) as s:
            columns = (await s.execute(text("SHOW COLUMNS FROM user LIKE 'must_change_password'"))).all()
        check("the column exists, not null, default 0", columns and columns[0][2] == "NO" and str(columns[0][4]) == "0", str(columns))
        check("an account already in use is not held", await flag(PORTAL_USER) is False)

        print("\n=== B) an account an admin creates ===")
        created = await client.post(
            "/auth/register",
            json={"username": CUSTOMER, "password": FIRST, "email": f"{CUSTOMER}@e2e.example", "role_id": 4, "customer_codes": [CUST_A]},
            headers=admin,
        )
        check("created", created.status_code == 201, created.text[:200])
        check("held", await flag(CUSTOMER) is True)
        login = await portal_login(CUSTOMER, FIRST)
        body = login.json()
        check("the portal login says so", login.status_code == 200 and body.get("must_change_password") is True, str(body)[:200])
        token = body["access_token"]

        refused = await client.get("/customer_portal/overview", headers=bearer(token))
        check("the overview: 403, never 401", refused.status_code == 403, str(refused.status_code))
        check(
            "in the app's own error shape",
            refused.json().get("success") is False and "new password" in refused.json().get("message", ""),
            refused.text[:200],
        )
        check("with the header the portal reads", refused.headers.get(PASSWORD_CHANGE_HEADER) == "true", str(dict(refused.headers)))
        for path in ("/incidents/db_operations/alerts", "/agents", "/customer_portal/ai_reports/availability"):
            response = await client.get(path, headers=bearer(token))
            check(
                f"{path}: refused the same way",
                response.status_code == 403 and response.headers.get(PASSWORD_CHANGE_HEADER) == "true",
                str(response.status_code),
            )
        me = await client.get("/customer_portal/me", headers=bearer(token))
        check("its profile answers, and says so", me.status_code == 200 and me.json()["must_change_password"] is True, me.text[:200])
        check("a token refresh answers", (await client.get("/auth/refresh", headers=bearer(token))).status_code == 200)
        check("its branding answers", (await client.get("/customer_portal/settings/effective", headers=bearer(token))).status_code == 200)
        actions = await audit_actions(CUSTOMER)
        check(
            "audited: created, and required by the admin",
            ("user.create", ADMIN) in actions and ("user.password_change_required", ADMIN) in actions,
            str(actions),
        )

        print("\n=== C) the change ===")

        async def change(current, new, headers):
            payload = {"username": CUSTOMER, "new_password": new}
            if current is not None:
                payload["current_password"] = current
            return await client.post("/auth/reset-password/me", json=payload, headers=headers)

        response = await change(None, CHOSEN, bearer(token))
        check("without the password received: 400", response.status_code == 400, response.text[:200])
        response = await change(FIRST, FIRST, bearer(token))
        check("the same password: 400", response.status_code == 400, response.text[:200])
        response = await change("Wrong-Guess-2026!", CHOSEN, bearer(token))
        check("a wrong one: 400, still held", response.status_code == 400 and await flag(CUSTOMER) is True, response.text[:200])
        response = await change(FIRST, CHOSEN, bearer(token))
        check("the right one: 200, released", response.status_code == 200 and await flag(CUSTOMER) is False, response.text[:200])
        overview = await client.get("/customer_portal/overview", headers=bearer(token))
        check("the same token now reaches the overview", overview.status_code == 200, str(overview.status_code))
        check("audited: the user replaced it", ("user.password_change", CUSTOMER) in await audit_actions(CUSTOMER))
        login = await portal_login(CUSTOMER, CHOSEN)
        check("the next login is not held", login.json().get("must_change_password") is False)

        print("\n=== D) an admin reset ===")
        response = await client.post("/auth/reset-password", json={"username": CUSTOMER, "new_password": RESET}, headers=admin)
        check("reset", response.status_code == 200, response.text[:200])
        held = await client.get("/customer_portal/overview", headers=bearer(token))
        check(
            "held again mid-session, on the token already in use",
            held.status_code == 403 and held.headers.get(PASSWORD_CHANGE_HEADER) == "true",
        )
        async with AsyncSession(async_engine) as s:
            admin_hash = (await s.execute(select(User.password).where(User.username == ADMIN))).scalar_one()
        response = await client.post("/auth/reset-password", json={"username": ADMIN, "new_password": RESET}, headers=admin)
        check("an admin resetting their own is not held", response.status_code == 200 and await flag(ADMIN) is False)
        async with AsyncSession(async_engine) as s:
            await s.execute(text("UPDATE user SET password = :p WHERE username = :u").bindparams(p=admin_hash, u=ADMIN))
            await s.commit()
        await change(RESET, CHOSEN, bearer(token))

        print("\n=== E) an emailed temporary password ===")
        async with AsyncSession(async_engine) as s:
            user_id = (await s.execute(select(User.id).where(User.username == CUSTOMER))).scalar_one()
        sent, issued = {}, []
        generate = security_admin.generate_temporary_password

        async def record_email(**kwargs):
            sent.update(kwargs)

        def remember(*args, **kwargs):
            issued.append(generate(*args, **kwargs))
            return issued[-1]

        with (
            patch.object(security_admin, "smtp_configured", return_value=True),
            patch.object(security_admin, "send_email", side_effect=record_email),
            patch.object(security_admin, "generate_temporary_password", side_effect=remember),
        ):
            response = await client.post(f"/auth/security/users/{user_id}/send-temp-password", json={}, headers=admin)
        check("sent", response.status_code == 200 and sent.get("to_addr") == f"{CUSTOMER}@e2e.example", response.text[:200])
        check("held", await flag(CUSTOMER) is True)
        temporary = issued[0].plain if issued else ""
        check("the email carries it", temporary and temporary in (sent.get("body") or ""))
        login = await portal_login(CUSTOMER, temporary)
        check(
            "the emailed password logs in, held",
            login.status_code == 200 and login.json().get("must_change_password") is True,
            login.text[:160],
        )
        await change(temporary, CHOSEN, bearer(login.json().get("access_token", "")))
        check("and is replaced", await flag(CUSTOMER) is False)

        with (
            patch.object(security_admin, "smtp_configured", return_value=True),
            patch.object(security_admin, "send_email", AsyncMock(side_effect=OSError("mail relay down"))),
        ):
            response = await client.post(f"/auth/security/users/{user_id}/send-temp-password", json={}, headers=admin)
        check(
            "an email that fails still leaves the password rotated and held",
            response.status_code == 502 and await flag(CUSTOMER) is True,
            response.text[:160],
        )

        print("\n=== F) 2FA and other roles ===")
        async with AsyncSession(async_engine) as s:
            await s.execute(text("UPDATE user SET must_change_password = 1 WHERE username = :u").bindparams(u=CUSTOMER))
            await s.execute(
                text("UPDATE user SET password = :p WHERE username = :u").bindparams(p=AuthHandler().get_password_hash(CHOSEN), u=CUSTOMER),
            )
            await s.commit()
        setup = await totp_service.setup_totp(user_id, CUSTOMER)
        await totp_service.verify_setup(user_id, pyotp.TOTP(setup["secret"]).now())
        first = (await portal_login(CUSTOMER, CHOSEN)).json()
        check(
            "2FA first: no session, no flag yet",
            first.get("requires_2fa") is True and "must_change_password" not in first,
            str(first)[:160],
        )
        validated = await client.post(
            "/auth/2fa/validate",
            json={"temp_token": first["access_token"], "backup_code": setup["backup_codes"][0]},
        )
        check(
            "the 2FA login says so",
            validated.status_code == 200 and validated.json().get("must_change_password") is True,
            validated.text[:200],
        )

        created = await client.post(
            "/auth/register",
            json={"username": ANALYST, "password": FIRST, "email": f"{ANALYST}@e2e.example", "role_id": 2, "customer_codes": [CUST_A]},
            headers=admin,
        )
        analyst_login = await client.post("/auth/token", data={"username": ANALYST, "password": FIRST})
        check("an analyst carries the flag", created.status_code == 201 and analyst_login.json().get("must_change_password") is True)
        reach = await client.get("/incidents/db_operations/alerts", headers=bearer(analyst_login.json()["access_token"]))
        check("but is not held (the analyst frontend has no forced change yet)", reach.status_code == 200, str(reach.status_code))
        own = await client.post(
            "/auth/reset-password/me",
            json={"username": ANALYST, "new_password": CHOSEN},
            headers=bearer(analyst_login.json()["access_token"]),
        )
        check(
            "and changes it as before, without the current one; that clears it",
            own.status_code == 200 and await flag(ANALYST) is False,
            own.text[:160],
        )

        print("\n=== G) the customer's Security tab ===")
        listed = await client.get(f"/auth/security/customers/{CUST_A}/users", headers=admin)
        flags = {u["username"]: u["must_change_password"] for u in listed.json().get("users", [])}
        check("shows who still has to change", flags.get(CUSTOMER) is True and flags.get(PORTAL_USER) is False, str(flags))

    await remove_users()
    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
