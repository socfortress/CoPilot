"""E2E for #1282 (portal users' email and in-app notifications) — NOT collected by pytest (needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    PYTHONPATH=$PWD .venv/bin/python tests/e2e/customer_portal_notifications_e2e.py

Real routers, real MySQL, real JWTs, the real hooks in the incident and report routes,
the built-in templates seeded as at startup; only SMTP is replaced, by a recorder (what
would be sent is the point). Three portal users: two of customer A, one of customer B.

  A) the switch: off by default, an admin's to turn on, an analyst cannot;
  B) while it is off nothing is written, whatever happens;
  C) each user's choices: defaults, a save, refusals;
  D) the SOC waits on the customer: everyone of A who asked is told once, B never;
  E) whoever closes a case is not told; the others are, once per closing;
  F) a new alert reaches only the users whose threshold it meets — tags never hide a
     customer's own alerts from its portal users (tag RBAC's policy) — by email straight
     away when they chose so;
  G) reports: the requester's own, and one the SOC shares later;
  H) the bell: newest first, pages, unread count, marking read (never someone else's);
  I) the daily digest: not before the hour, one email with every item, once a day;
  J) a queued email that can no longer go out is skipped with the reason;
  K) a failed send is recorded, and without SMTP nothing pretends to send;
  L) an operator's template is used, and a broken one falls back to plain text;
  M) deleting a user or a customer takes their notifications along;
  N) the migration downgrades and upgrades again cleanly (it runs first: the tables come
     back empty).

Everything it creates is removed at the end. Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")
os.environ["SMTP_HOST"] = "smtp.e2e.invalid"
os.environ["CUSTOMER_PORTAL_URL"] = "https://portal.e2e.example"
os.environ["PORTAL_NOTIFICATION_DIGEST_HOUR"] = "7"

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.auth.services.security_admin as security_admin  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.models.users import UserTagAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import notification_events as events  # noqa: E402
from app.customer_portal.services import notifications as service  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalNotification  # noqa: E402
from app.db.universal_models import CustomerPortalNotificationPref  # noqa: E402
from app.db.universal_models import CustomerPortalNotificationSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402
from app.db.universal_models import NotificationTemplate  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler  # noqa: E402
from app.notifications.services.template_seeds import PORTAL_TEMPLATES  # noqa: E402
from app.notifications.services.template_seeds import (  # noqa: E402
    seed_builtin_templates,
)
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_PHISHING  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_VIP  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

PORTAL_A2 = "e2e_nt_portal_a2"
PORTAL_B = "e2e_nt_portal_b"
ANALYST = "e2e_nt_analyst"
EXTRA_USERS = (PORTAL_A2, PORTAL_B, ANALYST)
TEMPLATE_NAME = "e2e portal case closed"

results = []
outbox = []  # (to, subject, text, html) the SMTP recorder kept
smtp_failure = {"error": None}


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def fake_send_email(to_addr, subject, body, html_body=None):
    if smtp_failure["error"]:
        raise RuntimeError(smtp_failure["error"])
    outbox.append((to_addr, subject, body, html_body))


async def user_id(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User.id).where(User.username == username))).scalar()


async def rows(**where):
    async with AsyncSession(async_engine) as s:
        query = select(CustomerPortalNotification).order_by(CustomerPortalNotification.id)
        for key, value in where.items():
            query = query.where(getattr(CustomerPortalNotification, key) == value)
        return list((await s.execute(query)).scalars().all())


async def add_users():
    """A second portal user of A, a portal user of B, and an analyst of A.

    Tag RBAC is switched on with each portal user of A given one tag: it must change
    nothing for them, since customer users see every alert of their customer by policy.
    """
    hashed = AuthHandler().get_password_hash(PASSWORD)
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        await remove_users(s)
        for username, role, code in ((PORTAL_A2, 4, CUST_A), (PORTAL_B, 4, CUST_B), (ANALYST, 2, CUST_A)):
            user = User(username=username, password=hashed, email=f"{username}@e2e.example", role_id=role)
            s.add(user)
            await s.flush()
            s.add(UserCustomerAccess(user_id=user.id, customer_code=code))
        settings = (await s.execute(select(TagAccessSettings))).scalars().first()
        previous = (settings.enabled, settings.untagged_alert_behavior) if settings else None
        if not settings:
            settings = TagAccessSettings()
            s.add(settings)
        # Untagged alerts stay visible to everyone: only the tagged ones split the users.
        settings.enabled, settings.untagged_alert_behavior = True, "admin_only"
        tags = {t.tag: t.id for t in (await s.execute(select(AlertTag).where(AlertTag.tag.in_([TAG_PHISHING, TAG_VIP])))).scalars()}
        portal = (await s.execute(select(User).where(User.username == PORTAL_USER))).scalars().one()
        a2 = (await s.execute(select(User).where(User.username == PORTAL_A2))).scalars().one()
        s.add(UserTagAccess(user_id=portal.id, tag_id=tags[TAG_PHISHING]))
        s.add(UserTagAccess(user_id=a2.id, tag_id=tags[TAG_VIP]))
        await s.commit()
        return settings.id, previous, tags


async def remove_users(s):
    for username in EXTRA_USERS:
        user = (await s.execute(select(User).where(User.username == username))).scalars().first()
        if user:
            await s.execute(delete(UserTagAccess).where(UserTagAccess.user_id == user.id))
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
            await s.delete(user)
    portal = (await s.execute(select(User).where(User.username == PORTAL_USER))).scalars().first()
    if portal:
        await s.execute(delete(UserTagAccess).where(UserTagAccess.user_id == portal.id))
    await s.execute(delete(NotificationTemplate).where(NotificationTemplate.name == TEMPLATE_NAME))
    await s.commit()


async def restore_tag_settings(settings_id, previous):
    async with AsyncSession(async_engine) as s:
        settings = await s.get(TagAccessSettings, settings_id)
        if previous is None:
            await s.delete(settings)
        else:
            settings.enabled, settings.untagged_alert_behavior = previous
        await s.commit()


async def new_alert(name, severity, tags=(), status="OPEN") -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        alert = Alert(
            alert_name=name,
            alert_description=f"{name} description",
            status=status,
            alert_creation_time=datetime.utcnow(),
            customer_code=CUST_A,
            source="e2e_overview",
            severity=severity,
        )
        s.add(alert)
        await s.flush()
        for tag_id in tags:
            s.add(AlertToTag(alert_id=alert.id, tag_id=tag_id))
        await s.commit()
        return alert.id


async def new_report(generated_by, role, visible, status="completed") -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        report = IncidentManagementCustomerReport(
            report_name=f"e2e notify report {role}",
            customer_code=CUST_A,
            object_key=f"{CUST_A}/e2e-notify.pdf",
            file_name="e2e-notify.pdf",
            generated_by=generated_by,
            generated_by_role=role,
            visible_to_customer=visible,
            status=status,
            date_from=datetime(2026, 9, 1),
            date_to=datetime(2026, 9, 30),
        )
        s.add(report)
        await s.commit()
        return report.id


async def run(work):
    async with AsyncSession(async_engine) as s:
        return await work(s)


def migration_round_trip():
    """Down to the previous revision and back: every table goes, then comes back."""
    import sqlalchemy as sa

    from alembic import command
    from tests.e2e.talon_actions_e2e import URL
    from tests.e2e.talon_actions_e2e import alembic_cfg

    names = ("customer_portal_notification", "customer_portal_notification_pref", "customer_portal_notification_settings")
    engine = sa.create_engine(URL)

    def present():
        return sorted(t for t in sa.inspect(engine).get_table_names() if t in names)

    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "f1278a0b1c2d")
    gone = present()
    command.upgrade(cfg, "head")
    back = present()
    engine.dispose()
    check("N) the migration downgrades: its tables go", gone == [], str(gone))
    check("N) and upgrades again: they come back", back == sorted(names), str(back))


async def main():
    print("\n=== N) the migration, both ways ===")
    await asyncio.to_thread(migration_round_trip)
    security_admin.send_email = fake_send_email
    await seed()
    await seed_builtin_templates(async_engine)
    settings_id, previous_tags, tags = await add_users()
    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    analyst = {"Authorization": f"Bearer {await auth.encode_token(ANALYST)}"}
    p1 = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_USER)}"}
    p2 = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_A2)}"}
    pb = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_B)}"}
    id_p1, id_p2, id_pb = await user_id(PORTAL_USER), await user_id(PORTAL_A2), await user_id(PORTAL_B)

    app = build_app()
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    async with AsyncSession(async_engine) as s:
        a_alerts = list((await s.execute(select(Alert).where(Alert.customer_code == CUST_A).order_by(Alert.id))).scalars())
        a_cases = list((await s.execute(select(Case).where(Case.customer_code == CUST_A).order_by(Case.id))).scalars())
    open_alert = next(a for a in a_alerts if a.status == "OPEN")
    open_case = next(c for c in a_cases if c.case_status == "OPEN")

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://e2e") as client:

            async def put_alert_status(alert_id, status, headers=admin):
                response = await client.put(
                    "/incidents/db_operations/alert/status",
                    headers=headers,
                    json={"alert_id": alert_id, "status": status},
                )
                await events.drain()
                return response

            async def put_case_status(case_id, status, headers=admin):
                response = await client.put(
                    "/incidents/db_operations/case/status",
                    headers=headers,
                    json={"case_id": case_id, "status": status},
                )
                await events.drain()
                return response

            print("\n=== A) the switch ===")
            response = await client.get(f"/customer_portal/notifications/settings/{CUST_A}", headers=admin)
            body = response.json()
            check("off by default", response.status_code == 200 and body["settings"]["enabled"] is False, response.text[:200])
            check(
                "says whether email can go out, and the digest hour",
                (body["email_configured"], body["digest_hour_utc"]) == (True, 7),
                str(body)[:200],
            )
            response = await client.put(f"/customer_portal/notifications/settings/{CUST_A}", headers=analyst, json={"enabled": True})
            check("an analyst cannot turn it on", response.status_code in (401, 403), str(response.status_code))
            response = await client.put(f"/customer_portal/notifications/settings/{CUST_A}", headers=p1, json={"enabled": True})
            check("a portal user cannot turn it on", response.status_code in (401, 403), str(response.status_code))
            response = await client.get("/customer_portal/notifications/availability", headers=p1)
            check("the portal reads it off", response.json()["enabled"] is False, response.text[:200])

            print("\n=== B) off: nothing is written ===")
            await put_alert_status(open_alert.id, "PENDING_CUSTOMER")
            check("a wait while off notifies nobody", await rows() == [], str(len(await rows())))
            await put_alert_status(open_alert.id, "OPEN")

            response = await client.put(f"/customer_portal/notifications/settings/{CUST_A}", headers=admin, json={"enabled": True})
            check(
                "an admin turns it on",
                response.status_code == 200 and response.json()["settings"]["enabled"] is True,
                response.text[:200],
            )
            response = await client.put(
                f"/customer_portal/notifications/settings/{CUST_A}",
                headers=admin,
                json={"enabled": True, "extra": 1},
            )
            check("the switch refuses unknown fields", response.status_code == 422, str(response.status_code))
            availability = (await client.get("/customer_portal/notifications/availability", headers=p1)).json()
            check(
                "A's portal user sees it on, with email",
                (availability["enabled"], availability["email_available"], availability["digest_hour_utc"]) == (True, True, 7),
                str(availability),
            )
            check(
                "B's portal user does not",
                (await client.get("/customer_portal/notifications/availability", headers=pb)).json()["enabled"] is False,
            )

            print("\n=== C) each user's choices ===")
            prefs = (await client.get("/customer_portal/notifications/preferences", headers=p1)).json()["preferences"]
            check(
                "defaults: the bell for everything, email off, alerts from High",
                [(p["event"], p["in_app"], p["email"], p["min_severity"]) for p in prefs]
                == [
                    ("alert_created", True, "off", "High"),
                    ("waiting_on_you", True, "off", None),
                    ("case_closed", True, "off", None),
                    ("report_ready", True, "off", None),
                ],
                str(prefs),
            )
            for bad in (
                {"preferences": [{"event": "case_closed", "min_severity": "Low"}]},
                {"preferences": [{"event": "case_closed"}, {"event": "case_closed"}]},
                {"preferences": [{"event": "alert_created", "email": "weekly"}]},
                {"preferences": [{"event": "alert_created"}], "user_id": id_p2},
            ):
                response = await client.put("/customer_portal/notifications/preferences", headers=p1, json=bad)
                check(f"refused: {str(bad)[:70]}", response.status_code == 422, str(response.status_code))
            response = await client.put(
                "/customer_portal/notifications/preferences",
                headers=admin,
                json={"preferences": [{"event": "case_closed"}]},
            )
            check("an admin has no portal choices", response.status_code in (401, 403), str(response.status_code))
            response = await client.put(
                "/customer_portal/notifications/preferences",
                headers=p1,
                json={
                    "preferences": [
                        {"event": "alert_created", "in_app": True, "email": "immediate", "min_severity": "Medium"},
                        {"event": "waiting_on_you", "in_app": True, "email": "digest"},
                        {"event": "report_ready", "in_app": False, "email": "immediate"},
                    ],
                },
            )
            saved = {p["event"]: p for p in response.json()["preferences"]}
            check(
                "a save returns every event, the ones left out as they were",
                response.status_code == 200
                and saved["alert_created"]["min_severity"] == "Medium"
                and saved["waiting_on_you"]["email"] == "digest"
                and saved["case_closed"] == {"event": "case_closed", "in_app": True, "email": "off", "min_severity": None},
                str(saved),
            )

            print("\n=== D) the SOC waits on the customer ===")
            response = await put_alert_status(open_alert.id, "PENDING_CUSTOMER")
            waits = await rows(event="waiting_on_you")
            check("the change itself succeeded", response.status_code == 200, str(response.status_code))
            check(
                "both of A's portal users are told, B's never",
                sorted(r.user_id for r in waits) == sorted([id_p1, id_p2]),
                str([r.user_id for r in waits]),
            )
            mine = next(r for r in waits if r.user_id == id_p1)
            theirs = next(r for r in waits if r.user_id == id_p2)
            check(
                "the first by digest, queued",
                (mine.email_mode, mine.email_status) == ("digest", "pending"),
                f"{mine.email_mode}/{mine.email_status}",
            )
            check("the second in the bell only", (theirs.email_mode, theirs.email_status, theirs.in_app) == ("none", None, True))
            check("the title says what is asked", mine.title.startswith("The SOC is waiting on your reply:"), mine.title)
            await put_alert_status(open_alert.id, "PENDING_CUSTOMER")
            check("writing the same status again notifies nobody again", len(await rows(event="waiting_on_you")) == 2)
            await put_case_status(open_case.id, "PENDING_CUSTOMER")
            check("a waiting case notifies too", len(await rows(event="waiting_on_you", entity_type="case")) == 2)
            check("its alerts, moved by the cascade, do not", len(await rows(event="waiting_on_you", entity_type="alert")) == 2)

            print("\n=== E) closing a case ===")
            response = await put_case_status(open_case.id, "CLOSED", headers=p1)
            closed = await rows(event="case_closed")
            check("the customer may close it", response.status_code == 200, response.text[:200])
            check(
                "whoever closed it is not told; the other user is",
                [r.user_id for r in closed] == [id_p2],
                str([r.user_id for r in closed]),
            )
            await put_case_status(open_case.id, "IN_PROGRESS")
            await asyncio.sleep(1.1)  # a new closing time: DATETIME keeps whole seconds
            await put_case_status(open_case.id, "CLOSED")
            closed = await rows(event="case_closed")
            check(
                "closed again by the SOC: both are told, once more for the second user",
                sorted(r.user_id for r in closed) == sorted([id_p2, id_p1, id_p2]),
            )
            await put_case_status(open_case.id, "CLOSED")
            check("closing a closed case changes nothing", len(await rows(event="case_closed")) == 3)

            print("\n=== F) a new alert ===")
            outbox.clear()
            medium_phishing = await new_alert("e2e notify medium phishing", "Medium", [tags[TAG_PHISHING]])
            await run(lambda s: events.process_alert_created(medium_phishing, s))
            created = await rows(event="alert_created")
            check(
                "only the user whose threshold it meets (Medium, not High)",
                [r.user_id for r in created] == [id_p1],
                str([r.user_id for r in created]),
            )
            check(
                "emailed at once, recorded as sent",
                len(outbox) == 1 and outbox[0][0] == f"{PORTAL_USER}@e2e.example" and created[0].email_status == "sent",
                str([o[:2] for o in outbox]),
            )
            check(
                "the email links into the portal",
                outbox and f"https://portal.e2e.example/alerts/{medium_phishing}" in (outbox[0][3] or ""),
                (outbox[0][3] or "")[-400:] if outbox else "",
            )
            check("the built-in template is the one used", outbox and outbox[0][1] == created[0].title, outbox[0][1] if outbox else "")
            high_vip = await new_alert("e2e notify high vip", "High", [tags[TAG_VIP]])
            await run(lambda s: events.process_alert_created(high_vip, s))
            vip_rows = await rows(entity_id=high_vip)
            check(
                "tags never hide a customer's own alert from its portal users",
                sorted(r.user_id for r in vip_rows) == sorted([id_p1, id_p2]),
                str([(r.user_id, r.event) for r in vip_rows]),
            )
            low_untagged = await new_alert("e2e notify low", "Low")
            await run(lambda s: events.process_alert_created(low_untagged, s))
            check("below everyone's threshold: nobody", await rows(entity_id=low_untagged) == [])
            await run(lambda s: events.process_alert_created(medium_phishing, s))
            check("the same alert twice is notified once", len(await rows(event="alert_created", entity_id=medium_phishing)) == 1)
            response = await client.post(
                "/incidents/db_operations/alert",
                headers=admin,
                json={
                    "alert_name": "e2e notify manual",
                    "alert_description": "filed by the SOC",
                    "status": "OPEN",
                    "alert_creation_time": datetime.utcnow().isoformat(),
                    "customer_code": CUST_A,
                    "source": "e2e_overview",
                    "assigned_to": "",
                },
            )
            await events.drain()
            manual = response.json().get("id") if response.status_code == 200 else None
            check(
                "an alert filed by hand notifies through the route's hook",
                manual is not None
                and sorted(r.user_id for r in await rows(entity_id=manual, event="alert_created")) == sorted([id_p1, id_p2]),
                response.text[:200],
            )

            print("\n=== G) reports ===")
            outbox.clear()
            own = await new_report(id_p1, "customer_user", True)
            await run(lambda s: events.process_report_ready(own, s))
            own_rows = await rows(entity_id=own, event="report_ready")
            check("a requested report is the requester's alone", [r.user_id for r in own_rows] == [id_p1])
            check(
                "by email only, as chosen (not in the bell)",
                own_rows[0].in_app is False and len(outbox) == 1,
                f"{own_rows[0].in_app} {len(outbox)}",
            )
            hidden = await new_report(1, "analyst", False)
            await run(lambda s: events.process_report_ready(hidden, s))
            check("a SOC report not shared: nobody", await rows(entity_id=hidden, event="report_ready") == [])
            response = await client.patch(f"/incidents/customer_reports/{hidden}/visibility", headers=admin, json={"visible": True})
            await events.drain()
            check(
                "shared afterwards: every user of the customer",
                response.status_code == 200
                and sorted(r.user_id for r in await rows(entity_id=hidden, event="report_ready")) == sorted([id_p1, id_p2]),
                response.text[:200],
            )
            await client.patch(f"/incidents/customer_reports/{hidden}/visibility", headers=admin, json={"visible": False})
            await client.patch(f"/incidents/customer_reports/{hidden}/visibility", headers=admin, json={"visible": True})
            await events.drain()
            check("shared twice: told once", len(await rows(entity_id=hidden, event="report_ready")) == 2)

            print("\n=== H) the bell ===")
            feed = (await client.get("/customer_portal/notifications", headers=p2)).json()
            ids = [n["id"] for n in feed["notifications"]]
            check(
                "newest first, the user's own only",
                ids == sorted(ids, reverse=True) and all(r.user_id == id_p2 for r in await rows() if r.id in ids),
            )
            check("unread counted", feed["unread_count"] == len(ids) and not feed["has_more"], f"{feed['unread_count']} {len(ids)}")
            page = (await client.get("/customer_portal/notifications?limit=2", headers=p2)).json()
            rest = (
                await client.get(f"/customer_portal/notifications?limit=50&before={page['notifications'][-1]['id']}", headers=p2)
            ).json()
            check("pages by id", [n["id"] for n in page["notifications"] + rest["notifications"]] == ids and page["has_more"])
            p1_feed = (await client.get("/customer_portal/notifications", headers=p1)).json()["notifications"]
            check(
                "an email-only notification stays out of the bell",
                own not in [n["entity_id"] for n in p1_feed if n["event"] == "report_ready"],
            )
            foreign = p1_feed[0]["id"]
            response = await client.post("/customer_portal/notifications/read", headers=p2, json={"ids": [foreign, ids[0]]})
            check(
                "marking read: own ids only",
                response.json()["marked"] == 1 and (await rows(id=foreign))[0].read_at is None,
                response.text[:200],
            )
            check("the count follows", response.json()["unread_count"] == len(ids) - 1)
            response = await client.post("/customer_portal/notifications/read", headers=p2, json={"all": True})
            check(
                "mark all",
                response.json()["unread_count"] == 0
                and (await client.get("/customer_portal/notifications/unread-count", headers=p2)).json()["unread_count"] == 0,
            )
            check(
                "B's user sees nothing of A's",
                (await client.get("/customer_portal/notifications", headers=pb)).json()["notifications"] == [],
            )
            check("and was never written anything", await rows(user_id=id_pb) == [])
            response = await client.get("/customer_portal/notifications", headers=admin)
            check("the bell is a portal user's", response.status_code in (401, 403), str(response.status_code))

            print("\n=== I) the daily digest ===")
            outbox.clear()
            day = datetime.utcnow().replace(hour=6, minute=30, second=0, microsecond=0)
            check("nothing before the hour", await run(lambda s: service.send_digests(s, now=day)) == 0 and outbox == [])
            sent = await run(lambda s: service.send_digests(s, now=day.replace(hour=7, minute=5)))
            digest_rows = await rows(user_id=id_p1, email_mode="digest")
            check(
                "one email for the user who chose the digest",
                sent == 1 and len(outbox) == 1 and outbox[0][0] == f"{PORTAL_USER}@e2e.example",
            )
            check("holding every queued item", all(r.title in (outbox[0][2] or "") for r in digest_rows), outbox[0][1] if outbox else "")
            check("every item marked sent", {r.email_status for r in digest_rows} == {"sent"})
            check("the subject counts them", outbox and outbox[0][1].startswith(f"Your daily summary: {len(digest_rows)} notification"))
            check("a second run the same day sends nothing", await run(lambda s: service.send_digests(s, now=day.replace(hour=9))) == 0)
            await put_alert_status(a_alerts[1].id, "PENDING_CUSTOMER")
            check("a new item that day waits", await run(lambda s: service.send_digests(s, now=day.replace(hour=23))) == 0)
            check(
                "and goes out the next day",
                await run(lambda s: service.send_digests(s, now=day.replace(hour=7) + timedelta(days=1))) == 1,
            )

            print("\n=== J) queued emails that can no longer go out ===")
            await put_alert_status(a_alerts[2].id, "PENDING_CUSTOMER")
            await client.put(f"/customer_portal/notifications/settings/{CUST_A}", headers=admin, json={"enabled": False})
            await run(lambda s: service.send_digests(s, now=day.replace(hour=7) + timedelta(days=2)))
            skipped = [r for r in await rows(user_id=id_p1, email_mode="digest") if r.entity_id == a_alerts[2].id]
            check(
                "switched off meanwhile: skipped, with the reason",
                skipped
                and (skipped[0].email_status, skipped[0].email_error) == ("skipped", "Notifications are turned off for this customer"),
                str([(r.email_status, r.email_error) for r in skipped]),
            )
            check(
                "and the bell hides the customer's notifications",
                (await client.get("/customer_portal/notifications", headers=p1)).json()["notifications"] == [],
            )
            await client.put(f"/customer_portal/notifications/settings/{CUST_A}", headers=admin, json={"enabled": True})

            print("\n=== K) failures ===")
            smtp_failure["error"] = "mailbox unavailable"
            failing = await new_alert("e2e notify failing", "Critical", [tags[TAG_PHISHING]])
            await run(lambda s: events.process_alert_created(failing, s))
            failed = await rows(entity_id=failing, user_id=id_p1)
            check(
                "a failed send is recorded with its error, the bell row kept",
                failed and failed[0].email_status == "failed" and "mailbox unavailable" in failed[0].email_error and failed[0].in_app,
                str([(r.email_status, r.email_error) for r in failed]),
            )
            smtp_failure["error"] = None
            os.environ.pop("SMTP_HOST")
            outbox.clear()
            no_smtp = await new_alert("e2e notify no smtp", "Critical", [tags[TAG_PHISHING]])
            await run(lambda s: events.process_alert_created(no_smtp, s))
            row = (await rows(entity_id=no_smtp, user_id=id_p1))[0]
            check(
                "without SMTP: skipped as such, nothing sent",
                (row.email_status, row.email_error, outbox) == ("skipped", "SMTP is not configured", []),
            )
            availability = (await client.get("/customer_portal/notifications/availability", headers=p1)).json()
            check(
                "and the portal is told why",
                (availability["email_available"], availability["email_unavailable_reason"]) == (False, "SMTP is not configured"),
            )
            os.environ["SMTP_HOST"] = "smtp.e2e.invalid"

            print("\n=== L) templates ===")
            async with AsyncSession(async_engine) as s:
                s.add(
                    NotificationTemplate(
                        name=TEMPLATE_NAME,
                        trigger="portal_case_closed",
                        format="text",
                        subject_template="[{{ customer_name }}] {{ subject }}",
                        body_template="Hi {{ user_name }}: {{ subject }}",
                        customer_code=CUST_A,
                        is_default=False,
                        created_by="e2e",
                    ),
                )
                await s.commit()
                builtins = (
                    (await s.execute(select(NotificationTemplate.trigger).where(NotificationTemplate.is_default.is_(True)))).scalars().all()
                )
            check(
                "the built-ins are seeded",
                {t["trigger"] for t in PORTAL_TEMPLATES} <= set(builtins),
                str(sorted(t for t in set(builtins) if t))[:200],
            )
            await client.put(
                "/customer_portal/notifications/preferences",
                headers=p2,
                json={"preferences": [{"event": "case_closed", "in_app": True, "email": "immediate"}]},
            )
            outbox.clear()
            await put_case_status(open_case.id, "IN_PROGRESS")
            await asyncio.sleep(1.1)
            await put_case_status(open_case.id, "CLOSED")
            mail = [o for o in outbox if o[0] == f"{PORTAL_A2}@e2e.example"]
            check(
                "the customer's own template is used",
                mail and mail[0][1] == "[Acme Rome] Case closed: " + open_case.case_name,
                str([o[1] for o in mail]),
            )
            check("in its own format", mail and mail[0][2].startswith(f"Hi {PORTAL_A2}:") and mail[0][3] is None)
            async with AsyncSession(async_engine) as s:
                await s.execute(
                    update(NotificationTemplate).where(NotificationTemplate.name == TEMPLATE_NAME).values(body_template="{{ broken("),
                )
                await s.commit()
            outbox.clear()
            await put_case_status(open_case.id, "IN_PROGRESS")
            await asyncio.sleep(1.1)
            await put_case_status(open_case.id, "CLOSED")
            mail = [o for o in outbox if o[0] == f"{PORTAL_A2}@e2e.example"]
            check(
                "a broken template still sends: the plain text",
                mail and mail[0][1] == "Case closed: " + open_case.case_name and "Hello " in mail[0][2],
                str(mail)[:200],
            )

            print("\n=== M) cascades ===")
            async with AsyncSession(async_engine) as s:
                a2 = (await s.execute(select(User).where(User.username == PORTAL_A2))).scalars().one()
                await s.execute(delete(UserTagAccess).where(UserTagAccess.user_id == a2.id))
                await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == a2.id))
                await s.delete(a2)
                await s.commit()
                left = (
                    (await s.execute(select(CustomerPortalNotification).where(CustomerPortalNotification.user_id == id_p2))).scalars().all()
                )
                prefs_left = (
                    (await s.execute(select(CustomerPortalNotificationPref).where(CustomerPortalNotificationPref.user_id == id_p2)))
                    .scalars()
                    .all()
                )
            check("a deleted user's notifications and choices go with them", (left, prefs_left) == ([], []))
    finally:
        async with AsyncSession(async_engine) as s:
            await remove_users(s)
        await restore_tag_settings(settings_id, previous_tags)
        async with AsyncSession(async_engine) as s:
            await cleanup(s)
            gone = (
                (
                    await s.execute(
                        select(CustomerPortalNotificationSettings).where(
                            CustomerPortalNotificationSettings.customer_code.in_([CUST_A, CUST_B]),
                        ),
                    )
                )
                .scalars()
                .all()
            )
            orphans = (
                (await s.execute(select(CustomerPortalNotification).where(CustomerPortalNotification.customer_code.in_([CUST_A, CUST_B]))))
                .scalars()
                .all()
            )
            still = (await s.execute(select(Customers).where(Customers.customer_code == CUST_A))).scalars().first()
        check("a deleted customer's switch and notifications go with it", (gone, orphans, still) == ([], [], None))
        await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
