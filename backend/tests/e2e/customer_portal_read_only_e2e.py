"""E2E for #1312 (read-only portal users) — NOT collected by pytest (needs a live MySQL).

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py (see its
docstring for the setup), then:

    .venv/bin/python tests/e2e/customer_portal_read_only_e2e.py

Real routers, real JWTs, real SQL; only SMTP is switched off, in process (no email can leave):

  A) the SOC makes the seeded portal user read-only on customer A: audited once, listed on the
     Security tab, said by /me;
  B) every write the portal makes on A's data answers 403 with the fixed text, and nothing is
     written: alert status (single and bulk), alert and case comments (create, edit, delete),
     cases (create, from an alert, status, assignee, link, unlink, file upload), reports
     (generate, delete), asset criticality, an AI analysis, a question to the SOC;
  C) what is theirs stays theirs: language, notification preferences, saved searches;
  D) on customer B, where they are not read-only, the same user writes; turned off on A, they
     write there again;
  E) never with the customer admin role; a customer admin invites a read-only user and changes
     their access, audited with the actor; the customer's audit log names it;
  F) the migration downgrades (the column is gone) and upgrades again.

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

from unittest.mock import patch  # noqa: E402

import httpx  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.services import security_admin  # noqa: E402
from app.auth.services.read_only import READ_ONLY  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import CustomerPortalAiRequest  # noqa: E402
from app.db.universal_models import CustomerPortalAuditSettings  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequest  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequestSettings  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

PREFIX = "e2e_ro_"
INVITED = f"{PREFIX}auditor"
MIGRATION_PARENT = "e1310a0b1c2d"
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def refused(response) -> bool:
    return response.status_code == 403 and response.json().get("detail") == READ_ONLY


async def scalar(query):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(query)).scalar()


async def count(model, *where):
    return await scalar(select(func.count()).select_from(model).where(*where))


async def read_only_audits(username):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(
            select(AuditLog.actor_username, AuditLog.customer_code, AuditLog.old_value, AuditLog.new_value)
            .where(AuditLog.action == "customer_user.read_only_update", AuditLog.entity_id == username)
            .order_by(AuditLog.id),
        )
        return [tuple(row) for row in rows.all()]


async def cleanup():
    async with AsyncSession(async_engine) as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.like(f"{PREFIX}%")))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(delete(AuditLog).where(AuditLog.entity_id.like(f"{PREFIX}%")))
        await s.execute(delete(AuditLog).where(AuditLog.action == "customer_user.read_only_update", AuditLog.entity_id == PORTAL_USER))
        await s.commit()


async def main():
    await cleanup()
    fixture = await seed()
    portal_user_id = fixture["portal_user_id"]
    alert_id = fixture["cased_alert_id"]
    fresh_alert_id = fixture["fresh_alert_id"]
    agent = fixture["agent_a0"]
    case_id = agent["case_id"]
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
    soc = f"/auth/security/customers/{CUST_A}/users/{portal_user_id}"

    async with AsyncSession(async_engine) as s:
        # Seeded rows used as is: not held on a password change, and the questions to the SOC on.
        await s.execute(update(User).where(User.id == portal_user_id).values(must_change_password=False))
        s.add(CustomerPortalSocRequestSettings(customer_code=CUST_A, enabled=True))
        s.add(Comment(alert_id=alert_id, comment="mine", user_name=PORTAL_USER))
        s.add(CaseComment(case_id=case_id, comment="mine", user_name=PORTAL_USER))
        await s.commit()
        comment_id = (await s.execute(select(func.max(Comment.id)).where(Comment.alert_id == alert_id))).scalar()
        case_comment_id = (await s.execute(select(func.max(CaseComment.id)).where(CaseComment.case_id == case_id))).scalar()
        report_id = (
            await s.execute(
                select(func.min(IncidentManagementCustomerReport.id)).where(
                    IncidentManagementCustomerReport.customer_code == CUST_A,
                    IncidentManagementCustomerReport.generated_by == portal_user_id,
                ),
            )
        ).scalar()

    smtp_off = patch.object(security_admin, "smtp_configured", return_value=False)
    with smtp_off:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
            login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
            portal = {"Authorization": f"Bearer {login.json()['access_token']}"}

            print("\n=== A) the SOC makes the portal user read-only on A ===")
            made = await client.put(f"{soc}/read-only", json={"read_only": True}, headers=admin)
            again = await client.put(f"{soc}/read-only", json={"read_only": True}, headers=admin)
            check("the SOC sets it", made.status_code == 200 and again.status_code == 200, made.text[:200])
            check(
                "audited once, old and new",
                await read_only_audits(PORTAL_USER) == [(ADMIN, CUST_A, {"read_only": False}, {"read_only": True})],
                str(await read_only_audits(PORTAL_USER)),
            )
            listed = (await client.get(f"/auth/security/customers/{CUST_A}/users", headers=admin)).json()["users"]
            check("the Security tab lists it", any(u["id"] == portal_user_id and u["read_only"] for u in listed))
            me = (await client.get("/customer_portal/me", headers=portal)).json()
            check(
                "/me says it for A",
                [(c["customer_code"], c["read_only"]) for c in me["customers"]] == [(CUST_A, True)],
                str(me["customers"]),
            )

            print("\n=== B) every write on A's data is refused, and nothing is written ===")
            before = {
                "alert": await scalar(select(Alert.status).where(Alert.id == alert_id)),
                "case": await scalar(select(Case.case_status).where(Case.id == case_id)),
                "comments": await count(Comment, Comment.alert_id == alert_id),
                "case_comments": await count(CaseComment, CaseComment.case_id == case_id),
                "cases": await count(Case, Case.customer_code == CUST_A),
                "links": await count(CaseAlertLink, CaseAlertLink.case_id == case_id),
                "reports": await count(IncidentManagementCustomerReport, IncidentManagementCustomerReport.customer_code == CUST_A),
                "critical": await scalar(select(Agents.critical_asset).where(Agents.agent_id == agent["agent_id"])),
                "questions": await count(CustomerPortalSocRequest, CustomerPortalSocRequest.customer_code == CUST_A),
                "ai": await count(CustomerPortalAiRequest, CustomerPortalAiRequest.customer_code == CUST_A),
            }
            # Audit rows outlive a run: count only this one's.
            audit_floor = await scalar(select(func.coalesce(func.max(AuditLog.id), 0)))
            db = "/incidents/db_operations"
            attempts = {
                "alert status": client.put(f"{db}/alert/status", json={"alert_id": alert_id, "status": "CLOSED"}, headers=portal),
                "alert comment": client.post(
                    f"{db}/alert/comment",
                    json={"alert_id": alert_id, "comment": "x", "user_name": "x"},
                    headers=portal,
                ),
                "alert comment edit": client.put(
                    f"{db}/alert/comment",
                    json={
                        "alert_id": alert_id,
                        "comment_id": comment_id,
                        "comment": "e",
                        "user_name": "x",
                        "created_at": "2026-10-27T08:00:00",
                    },
                    headers=portal,
                ),
                "alert comment delete": client.delete(f"{db}/alert/comment/{comment_id}", headers=portal),
                "case create": client.post(
                    f"{db}/case/create",
                    json={
                        "case_name": "x",
                        "case_description": "x",
                        "case_creation_time": "2026-10-27T08:00:00",
                        "case_status": "OPEN",
                        "customer_code": CUST_A,
                    },
                    headers=portal,
                ),
                "case from alert": client.post(f"{db}/case/from-alert", json={"alert_id": fresh_alert_id}, headers=portal),
                "case status": client.put(f"{db}/case/status", json={"case_id": case_id, "status": "CLOSED"}, headers=portal),
                "case assignee": client.put(
                    f"{db}/case/assigned-to",
                    json={"case_id": case_id, "assigned_to": PORTAL_USER},
                    headers=portal,
                ),
                "case link": client.post(f"{db}/case/alert-link", json={"case_id": case_id, "alert_id": fresh_alert_id}, headers=portal),
                "case unlink": client.post(f"{db}/case/alert-unlink", json={"case_id": case_id, "alert_id": alert_id}, headers=portal),
                "case comment": client.post(
                    f"{db}/case/comment",
                    json={"case_id": case_id, "comment": "x", "user_name": "x"},
                    headers=portal,
                ),
                "case comment edit": client.put(
                    f"{db}/case/comment",
                    json={
                        "case_id": case_id,
                        "comment_id": case_comment_id,
                        "comment": "e",
                        "user_name": "x",
                        "created_at": "2026-10-27T08:00:00",
                    },
                    headers=portal,
                ),
                "case comment delete": client.delete(f"{db}/case/comment/{case_comment_id}", headers=portal),
                "case file upload": client.post(
                    f"{db}/case/data-store/upload",
                    params={"case_id": case_id},
                    files={"file": ("note.txt", b"hello", "text/plain")},
                    headers=portal,
                ),
                "report generate": client.post(
                    "/incidents/customer_reports/generate/background",
                    json={"customer_code": CUST_A, "date_from": "2026-09-01T00:00:00", "date_to": "2026-10-01T00:00:00"},
                    headers=portal,
                ),
                "report delete": client.delete(f"/incidents/customer_reports/{report_id}", headers=portal),
                "agent critical": client.post(f"/agents/{agent['agent_id']}/critical", headers=portal),
                "agent noncritical": client.post(f"/agents/{agent['agent_id']}/noncritical", headers=portal),
                "AI analysis": client.post(f"/customer_portal/ai_reports/alert/{fresh_alert_id}/investigate", headers=portal),
                "question on an alert": client.post(
                    f"/customer_portal/soc_requests/alert/{fresh_alert_id}",
                    json={"question": "Ours?"},
                    headers=portal,
                ),
                "question on a case": client.post(
                    f"/customer_portal/soc_requests/case/{case_id}",
                    json={"question": "Ours?"},
                    headers=portal,
                ),
            }
            for name, attempt in attempts.items():
                response = await attempt
                check(f"refused: {name}", refused(response), f"{response.status_code} {response.text[:160]}")
            bulk = await client.put(f"{db}/alerts/status", json={"alert_ids": [alert_id], "status": "CLOSED"}, headers=portal)
            check(
                "bulk status skips A's alert",
                bulk.status_code == 200 and bulk.json()["not_updated_alert_ids"] == [alert_id],
                bulk.text[:200],
            )
            after = {
                "alert": await scalar(select(Alert.status).where(Alert.id == alert_id)),
                "case": await scalar(select(Case.case_status).where(Case.id == case_id)),
                "comments": await count(Comment, Comment.alert_id == alert_id),
                "case_comments": await count(CaseComment, CaseComment.case_id == case_id),
                "cases": await count(Case, Case.customer_code == CUST_A),
                "links": await count(CaseAlertLink, CaseAlertLink.case_id == case_id),
                "reports": await count(IncidentManagementCustomerReport, IncidentManagementCustomerReport.customer_code == CUST_A),
                "critical": await scalar(select(Agents.critical_asset).where(Agents.agent_id == agent["agent_id"])),
                "questions": await count(CustomerPortalSocRequest, CustomerPortalSocRequest.customer_code == CUST_A),
                "ai": await count(CustomerPortalAiRequest, CustomerPortalAiRequest.customer_code == CUST_A),
            }
            check("nothing of A's was written", after == before, f"{before} -> {after}")
            refusals = await count(
                AuditLog,
                AuditLog.id > audit_floor,
                AuditLog.actor_username == PORTAL_USER,
                AuditLog.details == READ_ONLY,
            )
            check("the refused question and AI request are audited as failures", refusals == 3, str(refusals))

            print("\n=== C) what is theirs stays theirs ===")
            language = await client.put("/customer_portal/languages/me", json={"locale": "en"}, headers=portal)
            prefs = await client.put(
                "/customer_portal/notifications/preferences",
                json={"preferences": [{"event": "case_closed", "in_app": True}]},
                headers=portal,
            )
            search = await client.post(f"/siem/event_search/{CUST_A}/recent", json={"source": "wazuh", "query": "*"}, headers=portal)
            check("their language", language.status_code == 200, language.text[:160])
            check("their notification choices", prefs.status_code != 403, prefs.text[:160])
            check("their searches", search.status_code != 403, search.text[:160])

            print("\n=== D) a customer they work on, and the flag turned off ===")
            async with AsyncSession(async_engine) as s:
                s.add(UserCustomerAccess(user_id=portal_user_id, customer_code=CUST_B))
                await s.commit()
                b_alert = (await s.execute(select(func.min(Alert.id)).where(Alert.customer_code == CUST_B))).scalar()
            on_b = await client.put(f"{db}/alert/status", json={"alert_id": b_alert, "status": "IN_PROGRESS"}, headers=portal)
            check("on B they still write", on_b.status_code == 200, on_b.text[:160])
            me = (await client.get("/customer_portal/me", headers=portal)).json()
            check(
                "/me: read-only on A only",
                sorted((c["customer_code"], c["read_only"]) for c in me["customers"]) == [(CUST_A, True), (CUST_B, False)],
                str(me["customers"]),
            )
            async with AsyncSession(async_engine) as s:
                await s.execute(
                    delete(UserCustomerAccess).where(
                        UserCustomerAccess.user_id == portal_user_id,
                        UserCustomerAccess.customer_code == CUST_B,
                    ),
                )
                await s.commit()
            off = await client.put(f"{soc}/read-only", json={"read_only": False}, headers=admin)
            writes = await client.put(f"{db}/alert/status", json={"alert_id": alert_id, "status": "IN_PROGRESS"}, headers=portal)
            check("turned off, they write on A again", off.status_code == 200 and writes.status_code == 200, writes.text[:160])

            print("\n=== E) the customer admin side ===")
            await client.put(f"{soc}/read-only", json={"read_only": True}, headers=admin)
            no_admin = await client.put(f"{soc}/customer-admin", json={"is_customer_admin": True}, headers=admin)
            check("a read-only user can't be made a customer admin (409)", no_admin.status_code == 409, no_admin.text[:160])
            await client.put(f"{soc}/read-only", json={"read_only": False}, headers=admin)
            await client.put(f"{soc}/customer-admin", json={"is_customer_admin": True}, headers=admin)
            not_both = await client.put(f"{soc}/read-only", json={"read_only": True}, headers=admin)
            check("a customer admin can't be made read-only (409)", not_both.status_code == 409, not_both.text[:160])

            invited = await client.post(
                "/customer_portal/users",
                json={"username": INVITED, "email": f"{INVITED}@e2e.example", "customer_codes": [CUST_A], "read_only": True},
                headers=portal,
            )
            check(
                "a customer admin invites a read-only user",
                invited.status_code == 201 and invited.json()["user"]["read_only"] is True,
                invited.text[:200],
            )
            invited_id = invited.json()["user"]["id"] if invited.status_code == 201 else None
            stored = await scalar(select(UserCustomerAccess.read_only).where(UserCustomerAccess.user_id == invited_id))
            check("stored on their access row", stored is True)
            lifted = await client.put(f"/customer_portal/users/{invited_id}/read-only", json={"read_only": False}, headers=portal)
            check(
                "the customer admin lets them change data",
                lifted.status_code == 200 and lifted.json()["user"]["read_only"] is False,
                lifted.text[:200],
            )
            check(
                "audited with the customer admin as actor",
                await read_only_audits(INVITED) == [(PORTAL_USER, CUST_A, {"read_only": True}, {"read_only": False})],
                str(await read_only_audits(INVITED)),
            )
            async with AsyncSession(async_engine) as s:
                s.add(CustomerPortalAuditSettings(customer_code=CUST_A, enabled=True))
                await s.commit()
            log = (await client.get("/customer_portal/audit", headers=portal)).json()
            labels = [e["label"] for e in log.get("entries", [])]
            check("the customer's audit log names it", "Can change data again" in labels, str(labels[:10]))
            await client.put(f"{soc}/customer-admin", json={"is_customer_admin": False}, headers=admin)

    print("\n=== F) the migration round trip ===")
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def column():
        async with AsyncSession(async_engine) as s:
            return bool((await s.execute(text("SHOW COLUMNS FROM `user_customer_access` LIKE 'read_only'"))).first())

    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade, config, MIGRATION_PARENT)
    check("downgrade drops the column", await column() is False)
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings it back", await column() is True)

    await cleanup()
    async with AsyncSession(async_engine) as s:
        await s.execute(delete(CustomerPortalAuditSettings).where(CustomerPortalAuditSettings.customer_code == CUST_A))
        await s.commit()
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
