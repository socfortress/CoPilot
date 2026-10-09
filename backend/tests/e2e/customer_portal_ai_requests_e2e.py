"""E2E for #1215 (portal users requesting an AI analysis) — NOT collected by pytest (needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    PYTHONPATH=$PWD .venv/bin/python tests/e2e/customer_portal_ai_requests_e2e.py

Real routers, real MySQL, real JWTs; only Talon is replaced, by a recorder (there is no
Talon here, and what CoPilot sends it is the point):

  A) requests are off until an admin allows them, and the analysis says so (can_request);
  B) the admin's settings round-trip, partial writes keep what was not sent, usage is reported;
  C) an allowed request reaches Talon for the alert's customer, is stored, noted on the
     alert and audited;
  D) the same alert again inside 30 minutes is refused with the time left;
  E) an analysis still running is not started twice;
  F) the daily limit refuses without naming the number, and counts only real requests;
  G) when Talon fails the customer gets a generic 502 and keeps the request;
  H) a portal user cannot request for another customer's alert;
  I) the analyst route checks the alert's customer too.

Everything it creates is removed at the end. Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
from datetime import datetime

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.connectors.talon.services.talon as talon_service  # noqa: E402
import app.customer_portal.services.ai_requests as requests_service  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.schema.talon import TalonInvestigateResponse  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import CustomerPortalAiRequest  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
sent_to_talon = []
talon_fails = False


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def fake_talon(request):
    if talon_fails:
        raise HTTPException(status_code=500, detail="Talon stack trace: secret internals")
    sent_to_talon.append(request)
    return TalonInvestigateResponse(success=True, message="Investigation triggered successfully")


async def alert_ids(customer_code):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(select(Alert.id).where(Alert.customer_code == customer_code).order_by(Alert.id))
        return [row[0] for row in rows]


async def stored_requests(customer_code=CUST_A):
    async with AsyncSession(async_engine) as s:
        return (
            await s.execute(
                select(func.count()).select_from(CustomerPortalAiRequest).where(CustomerPortalAiRequest.customer_code == customer_code),
            )
        ).scalar_one()


def build():
    from app.routers import talon

    app = build_app()
    app.include_router(talon.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


async def main():
    await seed(quiet=True)
    try:
        await run_checks()
    finally:
        async with AsyncSession(async_engine) as s:
            await s.execute(delete(AiAnalystJob).where(AiAnalystJob.id == "e2e-1215-running"))
            await s.execute(delete(AuditLog).where(AuditLog.customer_code.in_([CUST_A, CUST_B]), AuditLog.action.like("ai_%")))
            await s.commit()
            await cleanup(s)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


async def run_checks():
    global talon_fails
    requests_service.investigate_alert = fake_talon
    talon_service.investigate_alert = fake_talon

    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    portal = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_USER)}"}
    a_alerts, b_alerts = await alert_ids(CUST_A), await alert_ids(CUST_B)
    with_job, fresh, running, third, fourth = a_alerts[0], a_alerts[2], a_alerts[3], a_alerts[4], a_alerts[5]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build()), base_url="http://e2e") as client:

        def ask(alert_id, headers=portal):
            return client.post(f"/customer_portal/ai_reports/alert/{alert_id}/investigate", headers=headers)

        async def settings(**body):
            return await client.put(f"/customer_portal/ai_reports/settings/{CUST_A}", headers=admin, json={"enabled": True, **body})

        print("\n=== A) off until an admin allows it ===")
        analysis = (await client.get(f"/customer_portal/ai_reports/alert/{fresh}", headers=portal)).json()
        check(
            "the analysis does not offer a request",
            analysis["enabled"] is True and analysis["can_request"] is False,
            str(analysis)[:160],
        )
        response = await ask(fresh)
        check("a request is refused with 403", response.status_code == 403, response.text[:160])
        check("and never reaches Talon", sent_to_talon == [])

        print("\n=== B) operator settings ===")
        response = await settings(allow_customer_requests=True, daily_request_limit=2)
        stored = response.json()["settings"]
        check(
            "an admin allows requests with a limit",
            response.status_code == 200 and (stored["allow_customer_requests"], stored["daily_request_limit"]) == (True, 2),
            response.text[:200],
        )
        stored = (await settings()).json()["settings"]
        check(
            "a write without the request settings keeps them",
            (stored["allow_customer_requests"], stored["daily_request_limit"]) == (True, 2),
        )
        response = await client.put(
            f"/customer_portal/ai_reports/settings/{CUST_A}",
            headers=portal,
            json={"enabled": True, "allow_customer_requests": True},
        )
        check("a portal user cannot change them", response.status_code in (401, 403), str(response.status_code))
        analysis = (await client.get(f"/customer_portal/ai_reports/alert/{fresh}", headers=portal)).json()
        check("the analysis now offers a request", analysis["can_request"] is True)

        print("\n=== C) an allowed request ===")
        response = await ask(fresh)
        check("is accepted", response.status_code == 200, response.text[:200])
        sent = sent_to_talon[-1] if sent_to_talon else None
        check(
            "reaches Talon for the alert's customer, as the portal",
            sent is not None and (sent.alert_id, sent.customer_code, sent.sender) == (fresh, CUST_A, "customer-portal"),
            str(sent),
        )
        check("is stored", await stored_requests() == 1)
        async with AsyncSession(async_engine) as s:
            notes = (await s.execute(select(Comment).where(Comment.alert_id == fresh))).scalars().all()
            audited = (
                (await s.execute(select(AuditLog).where(AuditLog.action == "ai_analysis.request", AuditLog.customer_code == CUST_A)))
                .scalars()
                .all()
            )
        check(
            "is noted on the alert, signed by the user",
            any("Customer Portal" in n.comment and n.user_name == PORTAL_USER for n in notes),
            str([(n.user_name, n.comment) for n in notes]),
        )
        check("is audited", any(a.result == "success" and a.entity_id == str(fresh) for a in audited))
        used = (await client.get(f"/customer_portal/ai_reports/settings/{CUST_A}", headers=admin)).json()["settings"]["requests_last_24h"]
        check("the operator sees it counted", used == 1, str(used))

        print("\n=== D) cooldown ===")
        response = await ask(fresh)
        check("the same alert again is refused with 429", response.status_code == 429, response.text[:160])
        check("saying how long to wait", "30 minutes" in response.text or "29 minutes" in response.text, response.text[:160])

        print("\n=== E) an analysis in progress ===")
        async with AsyncSession(async_engine) as s:
            s.add(
                AiAnalystJob(
                    id="e2e-1215-running",
                    alert_id=running,
                    customer_code=CUST_A,
                    status="running",
                    triggered_by="manual",
                    created_at=datetime.utcnow(),
                ),
            )
            await s.commit()
        response = await ask(running)
        check("is not started twice (409)", response.status_code == 409, response.text[:160])

        print("\n=== F) daily limit ===")
        response = await ask(third)
        check("the second request of the day is accepted", response.status_code == 200, response.text[:160])
        response = await ask(fourth)
        check("the third is refused (429)", response.status_code == 429 and "daily limit" in response.text, response.text[:160])
        check("without naming the limit", "2" not in response.json().get("message", response.text), response.text[:160])
        check("refused requests are not counted", await stored_requests() == 2)
        stored = (await settings(daily_request_limit=None)).json()["settings"]
        check("an explicit null makes it unlimited", stored["daily_request_limit"] is None)

        print("\n=== G) Talon fails ===")
        talon_fails = True
        response = await ask(fourth)
        talon_fails = False
        check("the customer gets a generic 502", response.status_code == 502 and "internals" not in response.text, response.text[:160])
        check("and keeps the request (nothing stored)", await stored_requests() == 2)
        response = await ask(fourth)
        check("so trying again right away works", response.status_code == 200, response.text[:160])

        print("\n=== H) another customer's alert ===")
        response = await ask(b_alerts[1])
        check("is refused (403)", response.status_code == 403, response.text[:160])

        print("\n=== I) the analyst route ===")
        response = await client.post("/talon/investigate", headers=admin, json={"alert_id": with_job, "customer_code": CUST_B})
        check("refuses a customer code that is not the alert's (400)", response.status_code == 400, response.text[:160])
        response = await client.post("/talon/investigate", headers=admin, json={"alert_id": with_job, "customer_code": CUST_A})
        check("accepts the alert's own", response.status_code == 200, response.text[:160])


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
