"""E2E for #1187 (SOC Management & SLA) — NOT collected by pytest (needs a live MySQL); run by hand.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/soc_management_e2e.py

Points at a throwaway instance on port 13306: never at the MySQL in .env. Exits
non-zero when a check fails.

Real routers, real MySQL, real JWTs, real ingest service. The unit tests use SQLite and
a mocked request layer; this is where the whole loop runs as in production:

  A) policy: an admin saves a global policy and a customer override; an analyst cannot;
  B) ingest opens the clocks with the targets in force (override vs global);
  C) human actions through the incidents API stamp the milestones — the first SOC
     response is write-once; a portal user's comment is not a response, their closure
     is a resolution; close/reopen counts;
  D) cases: severity follows the linked alert, an explicit severity re-targets only the
     running clocks;
  E) the dashboard: seeded figures, an analyst scoped to one customer sees only it and
     only their own analyst row; per-item SLA is 404 across tenants;
  F) the PDF report renders (when wkhtmltopdf is installed);
  G) deleting an alert takes its tracking row with it (ON DELETE CASCADE);
  H) waiting on the customer: PENDING_CUSTOMER stops the clocks, a case takes its alerts
     with it, a portal reply hands both back and pushes the due times;
  I) business hours: a customer calendar and a business-hours cell open on it;
  J) SLA notifications: sent once per clock, never twice;
  K) the portal SLA page: off until an admin turns it on, then the customer's figures
     only, without a single analyst name.
"""

import asyncio
import datetime
import os
import shutil
import sys
from types import SimpleNamespace

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalSlaSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import CaseEvent  # noqa: E402
from app.incidents.models import CaseTask  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.incidents.services.incident_alert import create_alert_in_copilot  # noqa: E402
from app.soc_management.models.sla import AlertSlaTracking  # noqa: E402
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402
from app.soc_management.models.sla import SlaCalendar  # noqa: E402
from app.soc_management.models.sla import SlaPolicy  # noqa: E402
from app.soc_management.services.notifier import SlaNotifier  # noqa: E402

CUST_A, CUST_B = "E2E_SLA_A", "E2E_SLA_B"
ADMIN, ANALYST, PORTAL = "e2e_sla_admin", "e2e_sla_ana", "e2e_sla_portal"
PASSWORD = "E2ePassw0rd!x"
DB = "/incidents/db_operations"

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def build_app():
    """The real routers, without the startup hooks (MinIO, connectors, scheduler)."""
    from app.routers import auth
    from app.routers import customer_portal
    from app.routers import incidents
    from app.routers import soc_management

    app = FastAPI()
    for module in (auth, incidents, soc_management, customer_portal):
        app.include_router(module.router)
    return app


def session():
    return AsyncSession(async_engine, expire_on_commit=False)


async def cleanup():
    codes = [CUST_A, CUST_B]
    async with session() as s:
        alert_ids = select(Alert.id).where(Alert.customer_code.in_(codes))
        case_ids = select(Case.id).where(Case.customer_code.in_(codes))
        await s.execute(delete(CaseAlertLink).where(CaseAlertLink.case_id.in_(case_ids)))
        for child in (CaseEvent, CaseComment, CaseTask):
            await s.execute(delete(child).where(child.case_id.in_(case_ids)))
        await s.execute(delete(Case).where(Case.customer_code.in_(codes)))
        await s.execute(delete(Comment).where(Comment.alert_id.in_(alert_ids)))
        await s.execute(delete(Alert).where(Alert.customer_code.in_(codes)))
        await s.execute(delete(SlaPolicy).where(SlaPolicy.customer_code.in_(codes)))
        await s.execute(delete(SlaPolicy).where(SlaPolicy.updated_by == ADMIN))
        await s.execute(delete(SlaCalendar).where(SlaCalendar.customer_code.in_(codes)))
        await s.execute(delete(CustomerPortalSlaSettings).where(CustomerPortalSlaSettings.customer_code.in_(codes)))
        for username in (ADMIN, ANALYST, PORTAL):
            user = (await s.execute(select(User).where(User.username == username))).scalars().first()
            if user:
                await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
                await s.delete(user)
        await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code.in_(codes)))
        await s.execute(delete(Customers).where(Customers.customer_code.in_(codes)))
        await s.commit()


async def seed():
    async with session() as s:
        for role_id, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == role_id))).scalars().first():
                s.add(Role(id=role_id, name=name, description=name))
        await s.commit()
    await cleanup()
    async with session() as s:
        for code in (CUST_A, CUST_B):
            s.add(
                Customers(
                    customer_code=code,
                    customer_name=f"Customer {code}",
                    contact_first_name="E2E",
                    contact_last_name=code,
                    logo_file="",
                ),
            )
        password = AuthHandler().get_password_hash(PASSWORD)
        for username, role in ((ADMIN, 1), (ANALYST, 2), (PORTAL, 4)):
            s.add(User(username=username, password=password, email=f"{username}@e2e.example", role_id=role))
        await s.commit()
        ids = {u.username: u.id for u in (await s.execute(select(User).where(User.username.in_([ANALYST, PORTAL])))).scalars()}
        s.add(UserCustomerAccess(user_id=ids[ANALYST], customer_code=CUST_A))
        s.add(UserCustomerAccess(user_id=ids[PORTAL], customer_code=CUST_A))
        await s.commit()


async def ingest(code, title, severity="High"):
    """The real ingest service, as the Graylog/Wazuh pipeline calls it."""
    async with session() as s:
        payload = SimpleNamespace(alert_title_payload=title, source="wazuh", severity=severity)
        alert = await create_alert_in_copilot(payload, code, s)
        return alert.id


async def tracking(model, key):
    async with session() as s:
        return await s.get(model, key)


async def main():
    await seed()
    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    ana = {"Authorization": f"Bearer {await auth.encode_token(ANALYST)}"}
    portal = {"Authorization": f"Bearer {await auth.encode_token(PORTAL)}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        print("A) policy")
        high = {"entity": "alert", "severity": "High", "ack_minutes": 30, "resolve_minutes": 120}
        denied = await client.put("/soc_management/policies", json={"cells": [high]}, headers=ana)
        check("an analyst cannot save a policy", denied.status_code == 403, str(denied.status_code))
        saved_b = await client.put(
            "/soc_management/policies",
            json={"customer_code": CUST_B, "cells": [{**high, "ack_minutes": 5, "resolve_minutes": 60}]},
            headers=admin,
        )
        check("an admin saves a customer override", saved_b.status_code == 200, saved_b.text[:200])

        print("B) ingest opens the clocks")
        a1 = await ingest(CUST_A, "E2E brute force")
        a2 = await ingest(CUST_A, "E2E port scan")
        a3 = await ingest(CUST_A, "E2E phishing", severity="Medium")
        b1 = await ingest(CUST_B, "E2E ransomware")
        t_a1, t_b1 = await tracking(AlertSlaTracking, a1), await tracking(AlertSlaTracking, b1)
        check("ingest created tracked rows", bool(t_a1 and t_a1.tracked and t_b1 and t_b1.tracked))
        check(
            "global default targets apply to A (High: 1h/8h)",
            t_a1.ack_due_at - t_a1.opened_at == datetime.timedelta(hours=1)
            and t_a1.resolve_due_at - t_a1.opened_at == datetime.timedelta(hours=8),
        )
        check("B's override applies (5m/60m)", t_b1.ack_due_at - t_b1.opened_at == datetime.timedelta(minutes=5))
        check("nobody responded to an ingested alert yet", t_a1.first_ack_at is None)

        print("C) human actions")
        assign = await client.put(f"{DB}/alert/assigned-to", json={"alert_id": a1, "assigned_to": ANALYST}, headers=ana)
        check("analyst assigns herself", assign.status_code == 200, assign.text[:200])
        await client.post(f"{DB}/alert/comment", json={"alert_id": a1, "comment": "looking", "user_name": "x"}, headers=admin)
        t_a1 = await tracking(AlertSlaTracking, a1)
        check("first response is the assignment, by the analyst", (t_a1.first_ack_by, t_a1.first_ack_action) == (ANALYST, "assigned"))
        closed = await client.put(f"{DB}/alert/status", json={"alert_id": a1, "status": "CLOSED"}, headers=ana)
        check("analyst closes", closed.status_code == 200, closed.text[:200])
        t_a1 = await tracking(AlertSlaTracking, a1)
        check("resolution stamped", t_a1.resolved_at is not None and t_a1.resolved_by == ANALYST)

        commented = await client.post(
            f"{DB}/alert/comment",
            json={"alert_id": a2, "comment": "is this us?", "user_name": "x"},
            headers=portal,
        )
        t_a2 = await tracking(AlertSlaTracking, a2)
        check(
            "a portal comment is not a SOC response",
            commented.status_code == 200 and t_a2.first_ack_at is None,
            str(commented.status_code),
        )
        portal_close = await client.put(f"{DB}/alert/status", json={"alert_id": a2, "status": "CLOSED"}, headers=portal)
        reopen = await client.put(f"{DB}/alert/status", json={"alert_id": a2, "status": "IN_PROGRESS"}, headers=ana)
        check("portal close and analyst reopen accepted", (portal_close.status_code, reopen.status_code) == (200, 200))
        await client.put(f"{DB}/alert/status", json={"alert_id": a3, "status": "CLOSED"}, headers=portal)
        t_a3 = await tracking(AlertSlaTracking, a3)
        check("a portal closure resolves without acknowledging", t_a3.resolved_by == PORTAL and t_a3.first_ack_at is None)
        t_a2 = await tracking(AlertSlaTracking, a2)
        check(
            "reopen clears the resolution and counts",
            t_a2.resolved_at is None and t_a2.reopen_count == 1 and t_a2.first_resolved_at is not None,
        )
        check("the reopen by the analyst is her first response", t_a2.first_ack_by == ANALYST)

        print("D) cases")
        from_alert = await client.post(f"{DB}/case/from-alert", json={"alert_id": a2}, headers=ana)
        check("case from alert", from_alert.status_code == 200, from_alert.text[:200])
        case_id = from_alert.json()["case_alert_link"]["case_id"]
        t_case = await tracking(CaseSlaTracking, case_id)
        check(
            "case clock opened, acknowledged at creation by the analyst",
            bool(t_case and t_case.tracked and t_case.first_ack_by == ANALYST),
        )
        check("case severity follows its alert (High)", t_case.severity == "High", t_case.severity)
        ack_due_before = t_case.ack_due_at
        sev = await client.put(f"{DB}/case/severity", json={"case_id": case_id, "severity": "Critical"}, headers=ana)
        check("set case severity", sev.status_code == 200 and sev.json()["cases"][0]["severity"] == "Critical", sev.text[:200])
        t_case = await tracking(CaseSlaTracking, case_id)
        check(
            "severity re-targets the running resolve clock",
            t_case.severity == "Critical" and t_case.resolve_due_at - t_case.opened_at == datetime.timedelta(days=1),
        )
        check("the achieved acknowledgement keeps its due time", t_case.ack_due_at == ack_due_before)
        portal_sev = await client.put(f"{DB}/case/severity", json={"case_id": case_id, "severity": "Low"}, headers=portal)
        check("a portal user cannot set case severity", portal_sev.status_code == 403, str(portal_sev.status_code))

        print("E) dashboard")
        now = datetime.datetime.utcnow()
        period = {"date_from": (now - datetime.timedelta(days=1)).isoformat(), "date_to": (now + datetime.timedelta(hours=1)).isoformat()}
        dash_admin = (
            await client.get("/soc_management/dashboard", params={**period, "customer_codes": [CUST_A, CUST_B]}, headers=admin)
        ).json()
        check(
            "admin: 4 alerts opened across A and B",
            dash_admin["headline"]["alerts"]["opened"] == 4,
            str(dash_admin["headline"]["alerts"]["opened"]),
        )
        check("admin: 1 case opened", dash_admin["headline"]["cases"]["opened"] == 1)
        check("admin: a1 resolved within SLA", dash_admin["headline"]["alerts"]["sla"]["resolve"]["met"] >= 1)
        check(
            "admin: the portal closure is reported apart",
            dash_admin["headline"]["alerts"]["resolved_by_customer"] == 1,
            str(dash_admin["headline"]["alerts"]["resolved_by_customer"]),
        )
        analyst_names = {row["username"] for row in dash_admin["analysts"]}
        check("admin: sees the analyst row", ANALYST in analyst_names, str(analyst_names))

        dash_ana = (
            await client.get("/soc_management/dashboard", params={**period, "customer_codes": [CUST_A, CUST_B]}, headers=ana)
        ).json()
        check(
            "analyst: only A is counted",
            dash_ana["headline"]["alerts"]["opened"] == 3 and dash_ana["customer_codes"] == [CUST_A],
            str(dash_ana["customer_codes"]),
        )
        check("analyst: only her own analyst row", [row["username"] for row in dash_ana["analysts"]] == [ANALYST])
        own = await client.get(f"/soc_management/items/alert/{a1}/sla", headers=ana)
        foreign = await client.get(f"/soc_management/items/alert/{b1}/sla", headers=ana)
        check("per-item SLA: own alert visible, met", own.status_code == 200 and own.json()["resolve"]["state"] == "met", own.text[:200])
        check("per-item SLA: other tenant is 404", foreign.status_code == 404)
        portal_dash = await client.get("/soc_management/dashboard", params=period, headers=portal)
        check("a portal user cannot read the dashboard", portal_dash.status_code == 403)

        print("H) waiting on the customer")
        a4 = await ingest(CUST_A, "E2E suspicious login")
        resolve_due_before = (await tracking(AlertSlaTracking, a4)).resolve_due_at
        pending = await client.put(f"{DB}/alert/status", json={"alert_id": a4, "status": "PENDING_CUSTOMER"}, headers=ana)
        t_a4 = await tracking(AlertSlaTracking, a4)
        check("an alert can wait on the customer", pending.status_code == 200 and t_a4.paused_at is not None, pending.text[:200])
        counts = (await client.get(f"{DB}/alerts", params={"customer_codes": [CUST_A]}, headers=ana)).json()
        check("the alert list counts it apart", counts.get("pending_customer", 0) >= 1, str(counts.get("pending_customer")))
        item = (await client.get(f"/soc_management/items/alert/{a4}/sla", headers=ana)).json()
        check("its clocks read as paused", item["resolve"]["state"] == "paused" and item["paused_at"] is not None, str(item["resolve"]))
        await asyncio.sleep(1.1)
        reply = await client.post(
            f"{DB}/alert/comment",
            json={"alert_id": a4, "comment": "yes, that was me", "user_name": "x"},
            headers=portal,
        )
        t_a4 = await tracking(AlertSlaTracking, a4)
        status_a4 = (await client.get(f"{DB}/alert/{a4}", headers=ana)).json()["alerts"][0]["status"]
        check("a portal reply hands it back to the SOC", reply.status_code == 200 and status_a4 == "IN_PROGRESS", status_a4)
        check(
            "resuming banks the wait and pushes the resolve due",
            t_a4.paused_at is None and t_a4.paused_seconds >= 1 and t_a4.resolve_due_at > resolve_due_before,
            f"{t_a4.paused_seconds}s",
        )

        case_pending = await client.put(f"{DB}/case/status", json={"case_id": case_id, "status": "PENDING_CUSTOMER"}, headers=ana)
        a2_status = (await client.get(f"{DB}/alert/{a2}", headers=ana)).json()["alerts"][0]["status"]
        check(
            "a waiting case takes its active alerts with it",
            case_pending.status_code == 200 and a2_status == "PENDING_CUSTOMER",
            a2_status,
        )
        await client.post(f"{DB}/case/comment", json={"case_id": case_id, "comment": "attached the logs", "user_name": "x"}, headers=portal)
        case_status = (await client.get(f"{DB}/case/{case_id}", headers=ana)).json()["cases"][0]["case_status"]
        a2_status = (await client.get(f"{DB}/alert/{a2}", headers=ana)).json()["alerts"][0]["status"]
        t_case = await tracking(CaseSlaTracking, case_id)
        check(
            "a portal reply on the case resumes it and its alerts",
            (case_status, a2_status) == ("IN_PROGRESS", "IN_PROGRESS") and t_case.paused_at is None,
            f"{case_status}/{a2_status}",
        )

        print("I) business hours")
        week = {day: [["09:00", "17:00"]] for day in ("mon", "tue", "wed", "thu", "fri")}
        calendar = await client.put(
            "/soc_management/calendars",
            json={"customer_code": CUST_B, "timezone": "Europe/Rome", "week": week, "holidays": ["2026-12-25"]},
            headers=admin,
        )
        check(
            "an admin saves a customer calendar",
            calendar.status_code == 200 and calendar.json()["calendar"]["source"] == "customer",
            calendar.text[:200],
        )
        foreign_calendar = await client.get("/soc_management/calendars", params={"customer_code": CUST_B}, headers=ana)
        check("an analyst cannot read another tenant's calendar", foreign_calendar.status_code == 403)
        await client.put(
            "/soc_management/policies",
            json={"customer_code": CUST_B, "cells": [{**high, "ack_minutes": 60, "resolve_minutes": 240, "business_hours": True}]},
            headers=admin,
        )
        b2 = await ingest(CUST_B, "E2E data exfiltration")
        t_b2 = await tracking(AlertSlaTracking, b2)
        check("a business-hours cell opens on the customer calendar", t_b2.business_hours and t_b2.ack_due_at > t_b2.opened_at)
        b2_item = (await client.get(f"/soc_management/items/alert/{b2}/sla", headers=admin)).json()
        check(
            "the item says so, with its target in working minutes",
            b2_item["business_hours"] and b2_item["calendar_timezone"] == "Europe/Rome" and b2_item["ack"]["target_minutes"] == 60,
            str(b2_item["ack"]),
        )

        print("J) SLA notifications")
        sent = []
        later = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        notifier = SlaNotifier(send=sent.append, clock=lambda: later)
        await notifier.run()
        ours = [event for event in sent if event.customer_code in (CUST_A, CUST_B)]
        check(
            "breaches are notified",
            any(event.trigger.value == "sla_breached" for event in ours),
            str([(e.entity_id, e.trigger.value) for e in ours]),
        )
        check(
            "internal routes only, with the item's severity",
            all(event.trigger.value in ("sla_at_risk", "sla_breached") for event in ours),
        )
        sent.clear()
        await notifier.run()
        check("a second pass sends nothing new", not [event for event in sent if event.customer_code in (CUST_A, CUST_B)])

        print("K) portal SLA page")
        sla_period = {**period, "date_to": (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()}
        off = (await client.get("/customer_portal/sla/overview", params=sla_period, headers=portal)).json()
        check("off until an admin turns it on", off["enabled"] is False)
        denied_switch = await client.put(f"/customer_portal/sla/settings/{CUST_A}", json={"enabled": True}, headers=ana)
        check("an analyst cannot turn it on", denied_switch.status_code == 403)
        for code in (CUST_A, CUST_B):
            await client.put(f"/customer_portal/sla/settings/{code}", json={"enabled": True}, headers=admin)
        page = await client.get("/customer_portal/sla/overview", params=sla_period, headers=portal)
        body = page.json()
        check(
            "the customer sees only their own figures",
            body["enabled"] and body["customer_codes"] == [CUST_A],
            str(body["customer_codes"]),
        )
        check("their alerts are counted", body["alerts"]["opened"] == 4, str(body["alerts"]["opened"]))
        check("no analyst name reaches the customer", ANALYST not in page.text and ADMIN not in page.text)

        print("F) report")
        if shutil.which("wkhtmltopdf"):
            pdf = await client.get("/soc_management/report", params={**period, "customer_codes": [CUST_A, CUST_B]}, headers=admin)
            check("PDF report renders", pdf.status_code == 200 and pdf.content.startswith(b"%PDF"), pdf.headers.get("content-type", ""))
        else:
            print("  SKIP  wkhtmltopdf not installed")

        print("G) cascade")
        async with session() as s:
            await s.execute(delete(Comment).where(Comment.alert_id == b1))
            await s.execute(delete(Alert).where(Alert.id == b1))
            await s.commit()
        check("deleting an alert removes its tracking row", await tracking(AlertSlaTracking, b1) is None)

    await cleanup()
    await async_engine.dispose()
    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
