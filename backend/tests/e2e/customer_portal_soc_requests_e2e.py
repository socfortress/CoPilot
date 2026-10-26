"""E2E for #1305 ('Ask the SOC' from the Customer Portal) — NOT collected by pytest (needs a live
MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_portal_soc_requests_e2e.py

Real routers, real JWTs, real SQL, the real SLA recorder and the real notification dispatch to
a webhook on localhost (no other network). It checks, on the routes a browser calls:

  A) the migration: both tables, their unique key and their cascades;
  B) the switch: off by default (403), admin only to change (audited), an analyst reads it;
  C) a question on an alert without a case opens a case from it (linked, an SLA clock, a
     case event) with the question as the user's comment; on an alert with an open case it goes
     there; kept on the alert it is the alert's comment;
  D) a question on a waiting case hands it back to the SOC;
  E) the cooldown and the daily limit, and two users racing for the last slot: exactly one wins;
  F) another customer's alert or case, and a SOC user asking: refused;
  G) the SOC is told through an internal webhook route with the built-in template (the dispatch
     log says sent), never through the customer's own route;
  H) answering: a portal user's comment leaves it open, the SOC's comment answers it, an analyst
     marks one by hand; the SOC's list is scoped to its customers; the portal never sees who;
  I) a deleted case takes its questions with it;
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

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import or_  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequest  # noqa: E402
from app.db.universal_models import NotificationDispatchLog  # noqa: E402
from app.db.universal_models import NotificationTemplate  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import CaseEvent  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.notifications.services.template_seeds import (  # noqa: E402
    seed_builtin_templates,
)
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_sr_"
JANE = f"{PREFIX}jane"
BOB = f"{PREFIX}bob"
BETA = f"{PREFIX}beta"
ANALYST_A = f"{PREFIX}ana"
ANALYST_B = f"{PREFIX}gina"
PASSWORD = "Ask-The-Soc-2026!x"
WEBHOOK_ROUTE = "E2E customer question webhook"
CUSTOMER_ROUTE = "E2E customer question on the customer's channel"
PREVIOUS = "b1296a0c1d2e"
BASE = "/customer_portal/soc_requests"
QUESTION = "We see this sign-in from Lisbon every Monday: is it our VPN?"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def session():
    return AsyncSession(async_engine)


def build_app():
    from app.routers import auth
    from app.routers import customer_portal
    from app.routers import incidents
    from app.routers import notifications

    app = FastAPI()
    for module in (auth, incidents, customer_portal, notifications):
        app.include_router(module.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


class Receiver:
    """A bare HTTP endpoint on localhost that records every request body it is sent."""

    def __init__(self):
        self.bodies = []
        self.server = None

    async def start(self) -> str:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return f"http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}/hook"

    async def _handle(self, reader, writer):
        head = await reader.readuntil(b"\r\n\r\n")
        length = next((int(line.split(b":")[1]) for line in head.split(b"\r\n") if line.lower().startswith(b"content-length:")), 0)
        self.bodies.append((await reader.readexactly(length)).decode())
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: application/json\r\n\r\n{}")
        await writer.drain()
        writer.close()

    async def wait_for(self, count: int, seconds: float = 10.0) -> None:
        for _ in range(int(seconds * 10)):
            if len(self.bodies) >= count:
                return
            await asyncio.sleep(0.1)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()


async def remove_users():
    async with session() as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.like(f"{PREFIX}%")))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(delete(AuditLog).where(or_(AuditLog.actor_username.like(f"{PREFIX}%"), AuditLog.entity_id == CUST_A)))
        await s.execute(delete(CustomerNotificationRoute).where(CustomerNotificationRoute.name.in_([WEBHOOK_ROUTE, CUSTOMER_ROUTE])))
        await s.commit()


async def alembic(target: str) -> None:
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade if target != "head" else command.upgrade, config, target)


async def tables_exist() -> tuple:
    async with session() as s:
        names = {row[0] for row in (await s.execute(text("SHOW TABLES LIKE 'customer_portal_soc_request%'"))).all()}
    return "customer_portal_soc_request" in names, "customer_portal_soc_request_settings" in names


async def main():
    await alembic("head")
    await seed(quiet=True)
    await remove_users()
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
    receiver = Receiver()
    hook = await receiver.start()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:

        def bearer(token):
            return {"Authorization": f"Bearer {token}"}

        async def portal(username):
            response = await client.post("/auth/token/customer-portal", data={"username": username, "password": PASSWORD})
            return bearer(response.json()["access_token"])

        for username, role, codes in (
            (JANE, 4, [CUST_A]),
            (BOB, 4, [CUST_A]),
            (BETA, 4, [CUST_B]),
            (ANALYST_A, 2, [CUST_A]),
            (ANALYST_B, 2, [CUST_B]),
        ):
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
        async with session() as s:
            await s.execute(update(User).where(User.username.like(f"{PREFIX}%")).values(must_change_password=False))
            await s.commit()
        jane, bob, beta = await portal(JANE), await portal(BOB), await portal(BETA)
        ana = bearer(await AuthHandler().encode_token(ANALYST_A))
        gina = bearer(await AuthHandler().encode_token(ANALYST_B))

        async with session() as s:
            a_alerts = [row[0] for row in (await s.execute(select(Alert.id).where(Alert.customer_code == CUST_A).order_by(Alert.id))).all()]
            linked = set((await s.execute(select(CaseAlertLink.alert_id))).scalars().all())
            a_cases = {
                row.case_status: row.id
                for row in (await s.execute(select(Case).where(Case.customer_code == CUST_A).order_by(Case.id))).scalars().all()
            }
            b_alert = (await s.execute(select(Alert.id).where(Alert.customer_code == CUST_B))).scalars().first()
            b_case = (await s.execute(select(Case.id).where(Case.customer_code == CUST_B))).scalars().first()
            open_case = a_cases["OPEN"]
            on_open_case = (await s.execute(select(CaseAlertLink.alert_id).where(CaseAlertLink.case_id == open_case))).scalars().first()
        free = [alert for alert in a_alerts if alert not in linked]

        def ask(kind, target_id, headers=jane, **body):
            return client.post(f"{BASE}/{kind}/{target_id}", json={"question": QUESTION, **body}, headers=headers)

        print("\n=== A) the migration ===")
        check("both tables exist", await tables_exist() == (True, True))
        async with session() as s:
            rules = dict(
                (
                    await s.execute(
                        text(
                            "SELECT k.COLUMN_NAME, r.DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS r "
                            "JOIN information_schema.KEY_COLUMN_USAGE k ON k.CONSTRAINT_NAME = r.CONSTRAINT_NAME AND k.CONSTRAINT_SCHEMA = r.CONSTRAINT_SCHEMA "
                            "WHERE r.CONSTRAINT_SCHEMA = DATABASE() AND r.TABLE_NAME = 'customer_portal_soc_request'",
                        ),
                    )
                ).all(),
            )
            unique = (
                await s.execute(text("SHOW INDEX FROM customer_portal_soc_request_settings WHERE Column_name = 'customer_code'"))
            ).all()
        check(
            "a question goes with its customer, case and alert (CASCADE)",
            rules == {"customer_code": "CASCADE", "case_id": "CASCADE", "alert_id": "CASCADE"},
            str(rules),
        )
        check("one switch per customer", any(row[1] == 0 for row in unique))

        print("\n=== B) the switch ===")
        off = await ask("alert", free[0], target="alert")
        check("off: refused (403)", off.status_code == 403, str(off.status_code))
        check("off: not available", (await client.get(f"{BASE}/availability", headers=jane)).json()["enabled"] is False)
        check(
            "an analyst can't turn it on",
            (await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True}, headers=ana)).status_code == 403,
        )
        on = await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True, "daily_request_limit": 5}, headers=admin)
        check(
            "an admin turns it on with a daily limit",
            on.status_code == 200 and on.json()["settings"]["daily_request_limit"] == 5,
            on.text[:200],
        )
        check(
            "an analyst of the customer reads it",
            (await client.get(f"{BASE}/settings/{CUST_A}", headers=ana)).json()["settings"]["enabled"] is True,
        )
        async with session() as s:
            audited = (
                (
                    await s.execute(
                        select(AuditLog.new_value).where(
                            AuditLog.action == "soc_request.settings_update",
                            AuditLog.customer_code == CUST_A,
                        ),
                    )
                )
                .scalars()
                .all()
            )
        check("audited", audited == [{"enabled": True, "daily_request_limit": 5}], str(audited))
        check("on: available", (await client.get(f"{BASE}/availability", headers=jane)).json()["enabled"] is True)

        # The SOC's internal route, and the customer's own route on the same trigger, which must stay silent.
        await seed_builtin_templates(async_engine)
        async with session() as s:
            template_id = (
                await s.execute(
                    select(NotificationTemplate.id).where(
                        NotificationTemplate.name == "Customer question",
                        NotificationTemplate.is_default.is_(True),
                    ),
                )
            ).scalar_one()
        route = await client.post(
            "/internal_notification_routes",
            json={
                "name": WEBHOOK_ROUTE,
                "trigger": "customer_question",
                "channel": "webhook",
                "scope": "internal",
                "min_severity": "Informational",
                "template_id": template_id,
                "config": {"url": hook},
            },
            headers=admin,
        )
        check("an admin creates an internal route for customer questions", route.status_code == 200, route.text[:200])
        route_id = route.json()["route"]["id"]

        print("\n=== C) asking about an alert ===")
        new = await ask("alert", free[0], urgency="high", target="case")
        check("on a case, for an alert without one: accepted", new.status_code == 200, new.text[:200])
        asked = new.json()["request"]
        new_case = asked["case_id"]
        async with session() as s:
            link = (await s.execute(select(CaseAlertLink).where(CaseAlertLink.case_id == new_case))).scalars().all()
            comments = (await s.execute(select(CaseComment).where(CaseComment.case_id == new_case))).scalars().all()
            clock = (await s.execute(select(CaseSlaTracking).where(CaseSlaTracking.case_id == new_case))).scalars().first()
            created_event = (
                (await s.execute(select(CaseEvent).where(CaseEvent.case_id == new_case, CaseEvent.event_type == "case_created")))
                .scalars()
                .first()
            )
        check(
            "a case was made from the alert and linked to it",
            [row.alert_id for row in link] == [free[0]] and asked["origin_alert_id"] == free[0],
        )
        check(
            "the question is the user's comment on it",
            [(c.user_name, c.comment.startswith("Question for the SOC (urgency: High)") and QUESTION in c.comment) for c in comments]
            == [(JANE, True)],
            str([(c.user_name, c.comment[:40]) for c in comments]),
        )
        check("the new case has an SLA clock", clock is not None)
        check(
            "and its creation event names where it came from",
            created_event is not None and (created_event.payload or {}).get("source") == "from_alert",
        )

        await receiver.wait_for(1)
        body = receiver.bodies[0] if receiver.bodies else ""
        check("G) the SOC's webhook got it", len(receiver.bodies) == 1, str(len(receiver.bodies)))
        check(
            "with the built-in template: urgency, the case, the customer, who and the question",
            "*Customer question* — urgency *high*" in body
            and f"#{new_case}" in body
            and CUST_A in body
            and JANE in body
            and "Lisbon" in body,
            body[:200].replace("\n", " | "),
        )
        logged = []
        for _ in range(50):  # the log row is written once the webhook has answered
            async with session() as s:
                logged = (
                    (await s.execute(select(NotificationDispatchLog.status).where(NotificationDispatchLog.route_id == route_id)))
                    .scalars()
                    .all()
                )
            if logged:
                break
            await asyncio.sleep(0.1)
        check("the dispatch log says sent", logged == ["sent"], str(logged))

        existing = await ask("alert", on_open_case, headers=bob, target="case")
        check(
            "on a case, for an alert with an open case: that case",
            existing.status_code == 200 and existing.json()["request"]["case_id"] == open_case,
            existing.text[:200],
        )
        kept = await ask("alert", free[1], urgency="low", target="alert")
        async with session() as s:
            alert_comments = (await s.execute(select(Comment.user_name, Comment.comment).where(Comment.alert_id == free[1]))).all()
        check(
            "kept on the alert: the alert's comment",
            kept.status_code == 200
            and kept.json()["request"]["alert_id"] == free[1]
            and any(name == JANE and "urgency: Low" in text_ for name, text_ in alert_comments),
            kept.text[:200],
        )
        listed = (await client.get(f"{BASE}/alert/{free[0]}", headers=jane)).json()
        check(
            "the alert lists its question and its case",
            [r["id"] for r in listed["requests"]] == [asked["id"]] and listed["open_case_id"] == new_case,
        )
        check("the portal never sees who answers", all("answered_by" not in r for r in listed["requests"]))

        print("\n=== D) a waiting case ===")
        waiting = a_cases["PENDING_CUSTOMER"]
        on_waiting = await ask("case", waiting, headers=bob)
        async with session() as s:
            status = (await s.execute(select(Case.case_status).where(Case.id == waiting))).scalar_one()
        check(
            "a question on a waiting case hands it back to the SOC",
            on_waiting.status_code == 200 and status == "IN_PROGRESS",
            f"{on_waiting.status_code} {status}",
        )

        print("\n=== E) cooldown, daily limit, the last slot ===")
        again = await ask("alert", free[0], headers=bob, target="alert")
        check("the same alert again within minutes: 429", again.status_code == 429, str(again.status_code))
        # Four sent so far, limit 5: one slot left, two users race for it.
        race = await asyncio.gather(ask("alert", free[2], target="alert"), ask("alert", free[3], headers=bob, target="alert"))
        codes = sorted(r.status_code for r in race)
        check("two users racing for the last slot: exactly one wins", codes == [200, 429], str(codes))
        over = await ask("case", a_cases["CLOSED"])
        check(
            "over the daily limit: 429",
            over.status_code == 429 and "daily limit" in over.json().get("message", over.text),
            over.text[:200],
        )

        print("\n=== F) refusals ===")
        await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True, "daily_request_limit": None}, headers=admin)
        check("another customer's alert: 403", (await ask("alert", b_alert, target="alert")).status_code == 403)
        check("another customer's case: 403", (await ask("case", b_case)).status_code == 403)
        check("a SOC user can't ask: 403", (await ask("case", open_case, headers=ana)).status_code == 403)
        check("B's portal user, B's switch off: 403", (await ask("case", b_case, headers=beta)).status_code == 403)
        check(
            "an empty question: 422",
            (await client.post(f"{BASE}/case/{open_case}", json={"question": " "}, headers=jane)).status_code == 422,
        )

        print("\n=== H) answering ===")
        await client.post(
            "/incidents/db_operations/case/comment",
            json={"case_id": new_case, "comment": "Any news?", "user_name": "x"},
            headers=bob,
        )
        state = (await client.get(f"{BASE}/case/{new_case}", headers=jane)).json()["requests"]
        check("a portal user's comment leaves it open", [r["status"] for r in state] == ["open"], str(state))
        await client.post(
            "/incidents/db_operations/case/comment",
            json={"case_id": new_case, "comment": "Yes, that is your VPN.", "user_name": "x"},
            headers=ana,
        )
        state = (await client.get(f"{BASE}/case/{new_case}", headers=jane)).json()["requests"]
        check("the SOC's comment answers it", [r["status"] for r in state] == ["answered"] and state[0]["answered_at"], str(state))
        soc = (await client.get(BASE, headers=ana)).json()
        mine = {r["id"]: r for r in soc["requests"]}
        check(
            "the SOC's list names who answered and how",
            (mine[asked["id"]]["answered_by"], mine[asked["id"]]["answered_via"]) == (ANALYST_A, "comment"),
        )
        check("and counts the open ones", soc["open"] == soc["total"] - 1, f"{soc['open']}/{soc['total']}")
        check("another customer's analyst sees none of them", (await client.get(BASE, headers=gina)).json()["total"] == 0)
        kept_id = kept.json()["request"]["id"]
        check("nor can mark one (404)", (await client.post(f"{BASE}/{kept_id}/answered", headers=gina)).status_code == 404)
        marked = await client.post(f"{BASE}/{kept_id}/answered", headers=ana)
        check("an analyst marks one answered by hand", marked.status_code == 200 and marked.json()["request"]["answered_via"] == "manual")
        async with session() as s:
            answers = (await s.execute(select(AuditLog.entity_id).where(AuditLog.action == "soc_request.answer"))).scalars().all()
        check("audited", str(kept_id) in answers, str(answers))

        print("\n=== I) cascade ===")
        deleted = await client.delete(f"/incidents/db_operations/case/{new_case}", headers=admin)
        async with session() as s:
            left = (
                (await s.execute(select(CustomerPortalSocRequest.id).where(CustomerPortalSocRequest.case_id == new_case))).scalars().all()
            )
        check("a deleted case takes its questions with it", deleted.status_code == 200 and left == [], f"{deleted.status_code} {left}")

        await client.delete(f"/internal_notification_routes/{route_id}", headers=admin)

    await receiver.stop()
    print("\n=== J) the migration round trip ===")
    await remove_users()
    await seed(quiet=True)  # nothing of A or B left that the downgrade would trip on
    await alembic(PREVIOUS)
    check("downgrade drops both tables", await tables_exist() == (False, False))
    await alembic("head")
    check("upgrade brings them back", await tables_exist() == (True, True))

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
