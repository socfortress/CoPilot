"""E2E for #1298 (the Customer Portal Audit Log page) — NOT collected by pytest (needs a live
MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_portal_audit_e2e.py

Real routers, real JWTs, real SQL. The actions are taken through the routes a browser calls
(sign-ins, status changes, comments, a case from an alert, report downloads, 2FA), so the audit
rows are the ones CoPilot really writes; only the report's bytes are served without MinIO.

  A) the migration: the table, its unique customer key; off by default (403, not available);
  B) the SOC appoints a customer admin and turns the switch on (audited); a plain portal user,
     an analyst and the admin of a customer whose switch is off read nothing;
  C) the log shows exactly the customer's actions and its users' account events: what a member
     did by name (with the address), what the SOC did as "SOC" (no name, no address), never the
     SOC's verdicts or settings, another customer's actions or a hidden SOC report;
  D) filters (category, user, period), paging and the total; a user who is not theirs is a 404;
  E) the CSV is the filtered log, the same rows, no-store;
  F) light: a handful of statements per page;
  G) the migration downgrades and upgrades again.

Exits non-zero when a check fails.
"""

import asyncio
import csv
import datetime
import io
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
from sqlalchemy import or_  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.totp import UserTOTP  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services.audit import CSV_HEADER  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_au_"
CADMIN = f"{PREFIX}cadmin"
MEMBER = f"{PREFIX}member"
BETA_ADMIN = f"{PREFIX}betaadmin"
ANALYST = f"{PREFIX}analyst"
PASSWORD = "Audit-Log-2026!x"
PREVIOUS = "b1296a0c1d2e"
AUDIT = "/customer_portal/audit"
SHOWN_REPORT = "E2E audit: shared monthly review"
HIDDEN_REPORT = "E2E audit: internal weak spots"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def user_id(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User.id).where(User.username == username))).scalar_one()


async def remove_users():
    async with AsyncSession(async_engine) as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.like(f"{PREFIX}%")))).all()]
        if ids:
            await s.execute(delete(UserTOTP).where(UserTOTP.user_id.in_(ids)))
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(
            delete(AuditLog).where(or_(AuditLog.actor_username.like(f"{PREFIX}%"), AuditLog.entity_id.like(f"{PREFIX}%"))),
        )
        await s.execute(delete(IncidentManagementCustomerReport).where(IncidentManagementCustomerReport.report_name.like("E2E audit:%")))
        await s.commit()


async def migration_round_trip():
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def exists():
        async with AsyncSession(async_engine) as s:
            return bool((await s.execute(text("SHOW TABLES LIKE 'customer_portal_audit_settings'"))).all())

    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade, config, PREVIOUS)
    check("downgrade drops the table", await exists() is False)
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings it back", await exists() is True)


async def upgrade_head():
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    await asyncio.to_thread(command.upgrade, config, "head")


async def main():
    await upgrade_head()
    await seed(quiet=True)
    await remove_users()
    admin = bearer(await AuthHandler().encode_token(ADMIN))

    app = build_app()
    app.add_exception_handler(HTTPException, custom_http_exception_handler)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:

        async def portal_login(username, password=PASSWORD):
            return await client.post("/auth/token/customer-portal", data={"username": username, "password": password})

        async def token_of(username):
            return (await portal_login(username)).json().get("access_token")

        for username, role, codes in ((CADMIN, 4, [CUST_A]), (MEMBER, 4, [CUST_A]), (BETA_ADMIN, 4, [CUST_B]), (ANALYST, 2, [CUST_A])):
            created = await client.post(
                "/auth/register",
                json={
                    "username": username,
                    "password": PASSWORD,
                    "email": f"{username}@e2e.example",
                    "role_id": role,
                    "customer_codes": codes,
                },
                headers=admin,
            )
            if created.status_code != 201:
                print(f"could not create {username}: {created.status_code} {created.text[:200]}")
                return 1
        async with AsyncSession(async_engine) as s:
            await s.execute(update(User).where(User.username.like(f"{PREFIX}%")).values(must_change_password=False))
            await s.commit()
        analyst = bearer(await AuthHandler().encode_token(ANALYST))

        print("\n=== A) the migration, off by default ===")
        async with AsyncSession(async_engine) as s:
            index = (await s.execute(text("SHOW INDEX FROM customer_portal_audit_settings WHERE Column_name = 'customer_code'"))).all()
            fks = (
                await s.execute(
                    text(
                        "SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'customer_portal_audit_settings'",
                    ),
                )
            ).all()
        check("a unique key per customer", any(row[1] == 0 for row in index), str(index))
        check("goes with its customer (ON DELETE CASCADE)", [row[0] for row in fks] == ["CASCADE"], str(fks))
        cadmin_id = await user_id(CADMIN)
        appoint = await client.put(
            f"/auth/security/customers/{CUST_A}/users/{cadmin_id}/customer-admin",
            json={"is_customer_admin": True},
            headers=admin,
        )
        check("the SOC appoints a customer admin", appoint.status_code == 200, appoint.text[:200])
        beta_admin_id = await user_id(BETA_ADMIN)
        await client.put(
            f"/auth/security/customers/{CUST_B}/users/{beta_admin_id}/customer-admin",
            json={"is_customer_admin": True},
            headers=admin,
        )
        cadmin = bearer(await token_of(CADMIN))
        off = await client.get(AUDIT, headers=cadmin)
        check("off: the log is refused (403)", off.status_code == 403, str(off.status_code))
        available = (await client.get(f"{AUDIT}/availability", headers=cadmin)).json()
        check("off: not available", available["available"] is False and available["customers"] == [])

        print("\n=== B) the switch ===")
        refused = await client.put(f"{AUDIT}/settings/{CUST_A}", json={"enabled": True}, headers=analyst)
        check("an analyst can't turn it on (403)", refused.status_code == 403)
        turned_on = await client.put(f"{AUDIT}/settings/{CUST_A}", json={"enabled": True}, headers=admin)
        check("an admin turns it on", turned_on.status_code == 200 and turned_on.json()["settings"]["enabled"] is True)
        read = (await client.get(f"{AUDIT}/settings/{CUST_A}", headers=analyst)).json()
        check("an analyst of the customer reads it", read["settings"]["enabled"] is True)
        async with AsyncSession(async_engine) as s:
            audited = (
                await s.execute(
                    select(AuditLog.new_value)
                    .where(AuditLog.action == "audit.settings_update", AuditLog.customer_code == CUST_A)
                    .order_by(AuditLog.id.desc()),
                )
            ).first()
        check("audited", audited is not None and audited[0] == {"enabled": True}, str(audited))
        available = (await client.get(f"{AUDIT}/availability", headers=cadmin)).json()
        check(
            "on: available for the customer admin, by name",
            available["available"] is True and [c["customer_code"] for c in available["customers"]] == [CUST_A],
        )

        member = bearer(await token_of(MEMBER))
        beta_admin = bearer(await token_of(BETA_ADMIN))
        for who, headers in (
            ("a plain portal user", member),
            ("an analyst", analyst),
            ("the admin of a customer whose switch is off", beta_admin),
        ):
            status = (await client.get(AUDIT, headers=headers)).status_code
            check(f"{who} reads nothing (403)", status == 403, str(status))
        other = await client.get(AUDIT, params={"customer_codes": CUST_B}, headers=cadmin)
        check("asking for a customer they don't administer: 403", other.status_code == 403)

        print("\n=== C) what the log shows ===")
        # DATETIME rounds to whole seconds: the setup above lands before `start`, the actions below after it.
        await asyncio.sleep(1.1)
        now = to_naive_utc(now_utc())
        start = now.replace(microsecond=0) + datetime.timedelta(seconds=1)
        async with AsyncSession(async_engine) as s:
            a_alert = (await s.execute(select(Alert).where(Alert.customer_code == CUST_A).order_by(Alert.id))).scalars().first()
            b_alert = (await s.execute(select(Alert).where(Alert.customer_code == CUST_B).order_by(Alert.id))).scalars().first()
            a_case = (await s.execute(select(Case).where(Case.customer_code == CUST_A).order_by(Case.id))).scalars().first()
            await s.execute(update(Alert).where(Alert.id.in_([a_alert.id, b_alert.id])).values(status="OPEN"))
            await s.execute(update(Case).where(Case.id == a_case.id).values(case_status="OPEN"))
            shown_report = IncidentManagementCustomerReport(
                report_name=SHOWN_REPORT,
                customer_code=CUST_A,
                object_key=f"{CUST_A}/e2e-audit-shown.pdf",
                file_name="e2e-audit-shown.pdf",
                generated_by=1,
                generated_by_role="admin",
                date_from=start - datetime.timedelta(days=30),
                date_to=start,
                visible_to_customer=True,
                status="completed",
            )
            hidden_report = IncidentManagementCustomerReport(
                report_name=HIDDEN_REPORT,
                customer_code=CUST_A,
                object_key=f"{CUST_A}/e2e-audit-hidden.pdf",
                file_name="e2e-audit-hidden.pdf",
                generated_by=1,
                generated_by_role="admin",
                date_from=start - datetime.timedelta(days=30),
                date_to=start,
                visible_to_customer=False,
                status="completed",
            )
            s.add_all([shown_report, hidden_report])
            await s.flush()
            shown_id, hidden_id = shown_report.id, hidden_report.id
            a_alert_id, b_alert_id, a_case_id = a_alert.id, b_alert.id, a_case.id
            await s.commit()
        await asyncio.sleep((start - now).total_seconds() + 0.6)

        # The member: a failed sign-in, a sign-in, a status change, a comment, a download, 2FA on and off.
        await portal_login(MEMBER, "not-the-password")
        member = bearer(await token_of(MEMBER))
        moved = await client.put(
            "/incidents/db_operations/alert/status",
            json={"alert_id": a_alert_id, "status": "IN_PROGRESS"},
            headers=member,
        )
        check("the member moves an alert", moved.status_code == 200, moved.text[:200])
        commented = await client.post(
            "/incidents/db_operations/alert/comment",
            json={"alert_id": a_alert_id, "comment": "E2E secret comment text", "user_name": "ignored"},
            headers=member,
        )
        check("the member comments", commented.status_code == 200, commented.text[:200])
        pdf = AsyncMock(return_value={"file_content": b"%PDF-1.4 e2e", "content_type": "application/pdf", "file_name": "e2e.pdf"})
        with patch("app.incidents.routes.customer_report.get_customer_report_download", pdf):
            downloaded = await client.get(f"/incidents/customer_reports/{shown_id}/download", headers=member)
            check("the member downloads the shared report", downloaded.status_code == 200, downloaded.text[:200])
            soc_shown = await client.get(f"/incidents/customer_reports/{shown_id}/download", headers=analyst)
            soc_hidden = await client.get(f"/incidents/customer_reports/{hidden_id}/download", headers=analyst)
            check("the SOC downloads both reports", soc_shown.status_code == 200 and soc_hidden.status_code == 200)
        setup = (await client.post("/auth/2fa/setup", headers=member)).json()
        enabled = await client.post("/auth/2fa/verify-setup", json={"code": pyotp.TOTP(setup["secret"]).now()}, headers=member)
        disabled = await client.request("DELETE", "/auth/2fa/disable", json={"backup_code": setup["backup_codes"][0]}, headers=member)
        check(
            "the member turns 2FA on and off",
            enabled.status_code == 200 and disabled.status_code == 200,
            f"{enabled.text[:100]} {disabled.text[:100]}",
        )

        # The SOC: a case status, a case from the alert, a verdict (internal, never shown).
        case_moved = await client.put(
            "/incidents/db_operations/case/status",
            json={"case_id": a_case_id, "status": "IN_PROGRESS"},
            headers=analyst,
        )
        check("the SOC moves a case", case_moved.status_code == 200, case_moved.text[:200])
        from_alert = await client.post("/incidents/db_operations/case/from-alert", json={"alert_id": a_alert_id}, headers=analyst)
        check("the SOC opens a case from the alert", from_alert.status_code == 200, from_alert.text[:200])
        verdict = await client.put(
            "/incidents/db_operations/alert/verdict",
            json={"alert_id": a_alert_id, "verdict": "TRUE_POSITIVE"},
            headers=analyst,
        )
        check("the SOC sets a verdict", verdict.status_code == 200, verdict.text[:200])

        # Another customer's admin acts on their own alert.
        beta_moved = await client.put(
            "/incidents/db_operations/alert/status",
            json={"alert_id": b_alert_id, "status": "IN_PROGRESS"},
            headers=beta_admin,
        )
        check("another customer's admin moves their alert", beta_moved.status_code == 200, beta_moved.text[:200])

        since = {"since": start.isoformat() + "Z"}
        response = await client.get(AUDIT, params={**since, "page_size": 100}, headers=cadmin)
        check("the customer admin reads the log", response.status_code == 200, response.text[:200])
        check("never cached", response.headers.get("cache-control") == "no-store")
        body = response.json()
        member_id = await user_id(MEMBER)
        seen = [(e["action"], e["actor"]["kind"], e["actor"]["username"]) for e in body["entries"]]
        expected = sorted(
            [
                ("auth.login_failed", "unknown", None),  # nobody signed in: who tried is unknown
                ("auth.login", "member", MEMBER),
                ("alert.status_change", "member", MEMBER),
                ("alert.comment_create", "member", MEMBER),
                ("report.download", "member", MEMBER),
                ("report.download", "soc", None),
                ("user.totp_enable", "member", MEMBER),
                ("user.totp_disable", "member", MEMBER),
                ("case.status_change", "soc", None),
                ("case.create", "soc", None),
            ],
            key=str,
        )
        check("exactly the customer's actions and its users' account events", sorted(seen, key=str) == expected, str(seen))
        check("the total counts them", body["total"] == len(expected), str(body["total"]))
        members = {m["username"] for m in body["members"]}
        check(
            "the members are the customer's portal users",
            {CADMIN, MEMBER} <= members and not members & {BETA_ADMIN, ANALYST, ADMIN},
            str(members),
        )
        by_action = {}
        for entry in body["entries"]:
            by_action.setdefault(entry["action"], []).append(entry)
        status_entry = by_action["alert.status_change"][0]
        check(
            "a status change says from and to",
            (status_entry["from_value"], status_entry["to_value"]) == ("OPEN", "IN_PROGRESS"),
            str(status_entry),
        )
        check("…and names the alert", status_entry["target"] == {"type": "alert", "id": str(a_alert_id), "label": None})
        login = by_action["auth.login"][0]
        check("a member's sign-in carries its address", bool(login["source_ip"]), str(login))
        soc_rows = [e for e in body["entries"] if e["actor"]["kind"] == "soc"]
        check("the SOC carries no name and no address", all(e["actor"]["username"] is None and e["source_ip"] is None for e in soc_rows))
        check(
            "the case opened from the alert is named",
            by_action["case.create"][0]["target"]["label"] not in (None, ""),
            str(by_action["case.create"]),
        )
        check("the SOC's download names the shared report", by_action["report.download"][0]["target"]["label"] == SHOWN_REPORT)
        check("…and never the hidden one", HIDDEN_REPORT not in response.text)
        for secret, what in (
            (ANALYST, "the analyst's name"),
            ("E2E secret comment text", "the comment text"),
            ("TRUE_POSITIVE", "the verdict"),
        ):
            check(f"{what} never reaches the portal", secret not in response.text)

        print("\n=== D) filters and paging ===")
        cases = (await client.get(AUDIT, params={**since, "category": "cases"}, headers=cadmin)).json()["entries"]
        check("category: cases only", sorted(e["action"] for e in cases) == ["case.create", "case.status_change"], str(cases))
        account = (await client.get(AUDIT, params={**since, "category": "account"}, headers=cadmin)).json()["entries"]
        check(
            "category: account events",
            {e["action"] for e in account} == {"auth.login", "auth.login_failed", "user.totp_enable", "user.totp_disable"},
        )
        mine = (await client.get(AUDIT, params={**since, "user_id": member_id, "page_size": 100}, headers=cadmin)).json()
        about_member = all(e["actor"]["username"] == MEMBER or (e["target"] or {}).get("label") == MEMBER for e in mine["entries"])
        check("user: what the member did, and what was done to their account", mine["total"] == 7 and about_member, str(mine["total"]))
        foreign = await client.get(AUDIT, params={"user_id": beta_admin_id}, headers=cadmin)
        check("a user who isn't theirs: 404", foreign.status_code == 404)
        soc_user = await client.get(AUDIT, params={"user_id": await user_id(ANALYST)}, headers=cadmin)
        check("a SOC user: 404", soc_user.status_code == 404)
        future = (await client.get(AUDIT, params={"since": (start + datetime.timedelta(days=1)).isoformat() + "Z"}, headers=cadmin)).json()
        check("a period with nothing in it", future["total"] == 0 and future["entries"] == [])
        reversed_ = await client.get(
            AUDIT,
            params={"since": start.isoformat() + "Z", "until": (start - datetime.timedelta(days=1)).isoformat() + "Z"},
            headers=cadmin,
        )
        check("a reversed period: 422", reversed_.status_code == 422)
        page1 = (await client.get(AUDIT, params={**since, "page_size": 4}, headers=cadmin)).json()
        page3 = (await client.get(AUDIT, params={**since, "page_size": 4, "page": 3}, headers=cadmin)).json()
        ids = [e["id"] for e in body["entries"]]
        check(
            "pages are slices of the same order",
            [e["id"] for e in page1["entries"]] == ids[:4] and [e["id"] for e in page3["entries"]] == ids[8:],
        )
        stamps = [e["timestamp"] for e in body["entries"]]
        check("newest first", stamps == sorted(stamps, reverse=True))

        print("\n=== E) the CSV ===")
        export = await client.get(f"{AUDIT}/export", params=since, headers=cadmin)
        rows = list(csv.reader(io.StringIO(export.text)))
        check(
            "a CSV, no-store, not truncated",
            export.status_code == 200
            and export.headers.get("cache-control") == "no-store"
            and export.headers.get("x-export-truncated") == "false",
        )
        check("its header", rows[0] == CSV_HEADER)
        check("the same rows as the log", [row[3] for row in rows[1:]] == [e["label"] for e in body["entries"]], str(len(rows)))
        check("the SOC is 'SOC' there too", {row[4] for row in rows[1:]} == {MEMBER, "SOC", "Unknown"} and ANALYST not in export.text)
        check("refused like the log", (await client.get(f"{AUDIT}/export", headers=member)).status_code == 403)

        print("\n=== F) light ===")
        counter = StatementCounter()
        counter.reset()
        await client.get(AUDIT, params=since, headers=cadmin)
        statements = [
            s for s in counter.statements if "audit_log" in s or "customer_portal_audit_settings" in s or "user_customer_access" in s
        ]
        check("a handful of statements per page", len(counter.statements) <= 12, f"{len(counter.statements)}: {statements}")

        print("\n=== switched off again ===")
        await client.put(f"{AUDIT}/settings/{CUST_A}", json={"enabled": False}, headers=admin)
        check("off again: 403", (await client.get(AUDIT, headers=cadmin)).status_code == 403)

        print("\n=== G) the migration round trip ===")
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
