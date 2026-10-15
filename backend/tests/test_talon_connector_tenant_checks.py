"""Tenant checks on the Talon connector and the AI analyst write-back routes (§5.3 P1 of talon-analyst's SPEC).

Real routers, real in-memory database, real request parsing; only token decoding and
user lookup are replaced (as in test_customer_portal_sla).

Pinned here, each for a scoped analyst (assigned ACME), an admin, and where it matters an
unassigned analyst:
- ``GET /talon/jobs/{alert_id}``: another customer's alert is a 403, an unknown alert too
  (fail closed); the analyst's own alert and any alert for an admin are allowed;
- ``GET /talon/status``: an analyst sees only their own conversation lane and no scheduled
  tasks; an admin sees every lane;
- ``PUT /incidents/db_operations/ai_trigger`` and ``/notification``: the body's customer is
  checked, and must be the ``?customer_code=`` the route checked exists;
- ``POST /notifications/dispatch``: admin only, `investigation_complete` only, and the alert must be the
  body's customer's (real dispatch service: nothing sent or logged when refused);
- ``POST /ai_analyst/jobs``, ``/reports``, ``/iocs``, ``/palace_lessons``: the alert, job,
  report or review named must be the body's customer's; a second report for a job is a 409;
- ``GET /ai_analyst/alerts_with_reports``: narrowed to the caller's customers.

Run with: cd backend && python -m pytest tests/test_talon_connector_tenant_checks.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.dialects.mysql import LONGTEXT  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import AiAnalystReport  # noqa: E402
from app.db.universal_models import AiAnalystReview  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402


@compiles(LONGTEXT, "sqlite")
def _longtext_on_sqlite(type_, compiler, **kw):
    """`ai_analyst_report.report_markdown` is MySQL's LONGTEXT; SQLite stores it as TEXT."""
    return "TEXT"


USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "lonely": SimpleNamespace(id=3, username="lonely", role_id=2),
    "resp": SimpleNamespace(id=5, username="resp", role_id=5),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "lonely": ["analyst"], "resp": ["responder", "analyst"]}

MINE, THEIRS = "ACME", "GLOBEX"
MY_ALERT, THEIR_ALERT = 1, 2
MY_JOB = "copilot-inv-1-1000"  # no report yet
MY_REPORTED_JOB = "copilot-inv-1-900"
THEIR_JOB = "copilot-inv-2-1000"
THEIR_REPORT = 1
THEIR_REVIEW = 1
T0 = datetime(2026, 10, 1, 8, 0, 0)


class _Db(Db):
    """soc_management_support's database plus the AI analyst tables."""

    async def create(self) -> "_Db":
        extra = ("ai_analyst", "customer_notification_route", "notification_", "customer_shuffle_integration", "customer_portal_ai_report")
        names = {t.name for t in _tables()} | {name for name in SQLModel.metadata.tables if name.startswith(extra)}
        tables = [SQLModel.metadata.tables[name] for name in names]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self


def _app(db: Db) -> FastAPI:
    from app.routers import ai_analyst
    from app.routers import incidents
    from app.routers import notifications
    from app.routers import talon

    app = FastAPI()
    for module in (talon, ai_analyst, incidents, notifications):
        app.include_router(module.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db) -> None:
    async with db.session() as session:
        session.add_all(
            [
                User(id=u.id, username=u.username, password="x" * 8, email=f"{u.username}@example.com", role_id=u.role_id)
                for u in USERS.values()
            ]
            + [Customers(customer_code=MINE, customer_name="Acme Corp"), Customers(customer_code=THEIRS, customer_name="Globex")],
        )
        await session.commit()
        session.add_all([UserCustomerAccess(user_id=2, customer_code=MINE), UserCustomerAccess(user_id=5, customer_code=MINE)])
        await session.commit()
        await add_alert(session, customer=MINE)  # id 1
        await add_alert(session, customer=THEIRS)  # id 2
        session.add_all(
            [
                AiAnalystJob(id=MY_JOB, alert_id=MY_ALERT, customer_code=MINE, triggered_by="webhook", created_at=T0),
                AiAnalystJob(id=MY_REPORTED_JOB, alert_id=MY_ALERT, customer_code=MINE, triggered_by="webhook", created_at=T0),
                AiAnalystJob(id=THEIR_JOB, alert_id=THEIR_ALERT, customer_code=THEIRS, triggered_by="webhook", created_at=T0),
            ],
        )
        await session.commit()
        session.add_all(
            [
                AiAnalystReport(
                    id=THEIR_REPORT,
                    job_id=THEIR_JOB,
                    alert_id=THEIR_ALERT,
                    customer_code=THEIRS,
                    summary="theirs",
                    created_at=T0,
                ),
                AiAnalystReport(id=2, job_id=MY_REPORTED_JOB, alert_id=MY_ALERT, customer_code=MINE, summary="mine", created_at=T0),
            ],
        )
        await session.commit()
        session.add(
            AiAnalystReview(
                id=THEIR_REVIEW,
                report_id=THEIR_REPORT,
                alert_id=THEIR_ALERT,
                customer_code=THEIRS,
                reviewer_user_id=1,
                created_at=T0,
            ),
        )
        await session.commit()


def call(scenario, with_db=False):
    async def _inner():
        db = await _Db().create()
        try:
            await _seed(db)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ), patch("app.ai_analyst.services.ai_analyst.emit"):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await (scenario(client, db) if with_db else scenario(client))
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


# ── GET /talon/jobs/{alert_id} ────────────────────────────────────────────────


def test_talon_job_for_another_customers_alert_is_refused():
    async def scenario(client):
        return [(await client.get(f"/talon/jobs/{THEIR_ALERT}", headers=as_user(who))).status_code for who in ("ana", "resp", "lonely")]

    assert call(scenario) == [403, 403, 403]


def test_talon_job_for_own_alert_is_allowed():
    async def scenario(client):
        return await client.get(f"/talon/jobs/{MY_ALERT}", headers=as_user("ana"))

    response = call(scenario)
    assert response.status_code == 200
    assert response.json()["data"]["customer_code"] == MINE


def test_admin_reads_any_talon_job():
    async def scenario(client):
        return await client.get(f"/talon/jobs/{THEIR_ALERT}", headers=as_user("admin"))

    response = call(scenario)
    assert response.status_code == 200
    assert [r["summary"] for r in response.json()["data"]["reports"]] == ["theirs"]


def test_talon_job_for_an_unknown_alert_fails_closed_for_a_scoped_analyst():
    async def scenario(client):
        return [(await client.get("/talon/jobs/999", headers=as_user(who))).status_code for who in ("ana", "admin")]

    # The analyst can't be shown the alert is theirs; the admin learns there is no job.
    assert call(scenario) == [403, 404]


# ── GET /talon/status ─────────────────────────────────────────────────────────

TALON_STATUS = {
    "status": "ok",
    "uptime_seconds": 12,
    "active_investigations": 1,
    "pending_queue_depth": 0,
    "sessions": [
        {"lane": "copilot-u-1", "user_id": "1", "session_id": "s1", "input_tokens": 100, "updated_at": "2026-10-15T08:00:00Z"},
        {"lane": "copilot-u-2", "user_id": "2", "session_id": "s2", "input_tokens": 200, "updated_at": "2026-10-15T08:00:00Z"},
        {"lane": "copilot-u-9", "user_id": "9", "session_id": "s9", "input_tokens": 900, "updated_at": "2026-10-15T08:00:00Z"},
    ],
    "scheduled_tasks": [{"id": "nightly", "prompt": "a deployment-wide task"}],
}


def _status_as(who):
    async def scenario(client):
        upstream = AsyncMock(return_value={"success": True, "data": TALON_STATUS})
        with patch("app.connectors.talon.services.talon.send_get_request", upstream):
            return await client.get("/talon/status", headers=as_user(who))

    response = call(scenario)
    assert response.status_code == 200
    return response.json()["data"]


def test_status_shows_an_analyst_only_their_own_lane():
    data = _status_as("ana")
    assert [s["user_id"] for s in data["sessions"]] == ["2"]
    assert data["scheduled_tasks"] == []
    # Service-level figures describe Talon, not a tenant, and are kept.
    assert data["status"] == "ok" and data["active_investigations"] == 1


def test_status_shows_an_analyst_with_no_lane_nothing():
    data = _status_as("lonely")
    assert data["sessions"] == []


def test_status_shows_an_admin_every_lane():
    data = _status_as("admin")
    assert [s["user_id"] for s in data["sessions"]] == ["1", "2", "9"]
    assert data["scheduled_tasks"] == TALON_STATUS["scheduled_tasks"]


# ── PUT /incidents/db_operations/ai_trigger and /notification ─────────────────


def _put(path, who, body_code, query_code, **extra):
    async def scenario(client):
        return await client.put(
            f"/incidents/db_operations/{path}",
            params={"customer_code": query_code},
            json={"customer_code": body_code, "enabled": True, **extra},
            headers=as_user(who),
        )

    return call(scenario)


def test_ai_trigger_for_another_customer_is_refused():
    assert _put("ai_trigger", "ana", THEIRS, THEIRS).status_code == 403
    assert _put("ai_trigger", "resp", THEIRS, THEIRS).status_code == 403


def test_unknown_and_foreign_customers_read_the_same_to_a_scoped_analyst():
    # `check_customer_exists` would say 404 for an unknown code; the access check runs first.
    assert _put("ai_trigger", "ana", "NO_SUCH_CUSTOMER", "NO_SUCH_CUSTOMER").status_code == 403
    assert _put("notification", "ana", "NO_SUCH_CUSTOMER", "NO_SUCH_CUSTOMER", shuffle_workflow_id="wf").status_code == 403
    assert _put("ai_trigger", "admin", "NO_SUCH_CUSTOMER", "NO_SUCH_CUSTOMER").status_code == 404


def test_ai_trigger_cannot_be_smuggled_past_the_existence_check():
    # The query parameter is what `check_customer_exists` reads; the body is what gets written.
    assert _put("ai_trigger", "ana", THEIRS, MINE).status_code == 403


def test_ai_trigger_for_own_customer_is_allowed():
    response = _put("ai_trigger", "ana", MINE, MINE)
    assert response.status_code == 200
    assert [t["customer_code"] for t in response.json()["ai_triggers"]] == [MINE]


def test_admin_sets_any_ai_trigger_but_the_two_codes_must_agree():
    assert _put("ai_trigger", "admin", THEIRS, THEIRS).status_code == 200
    assert _put("ai_trigger", "admin", THEIRS, MINE).status_code == 400


def test_notification_setting_follows_the_same_rules():
    extra = {"shuffle_workflow_id": "wf-1"}
    assert _put("notification", "ana", THEIRS, THEIRS, **extra).status_code == 403
    assert _put("notification", "ana", THEIRS, MINE, **extra).status_code == 403
    assert _put("notification", "ana", MINE, MINE, **extra).status_code == 200
    assert _put("notification", "admin", THEIRS, THEIRS, **extra).status_code == 200


# ── POST /notifications/dispatch ──────────────────────────────────────────────
#
# The real dispatch service runs here; only the webhook's network call is replaced. ACME has
# an enabled webhook route that includes the full report, so a dispatch that got through
# would both call the webhook and write a dispatch-log row (with its dedupe key).


async def _add_webhook_route(session):
    from app.db.universal_models import CustomerNotificationRoute
    from app.db.universal_models import CustomerPortalAiReportSettings

    # A customer-facing route only carries AI output once the customer's AI report switch is on.
    session.add(CustomerPortalAiReportSettings(customer_code=MINE, enabled=True))
    session.add(
        CustomerNotificationRoute(
            customer_code=MINE,
            scope="customer",
            name="ACME webhook",
            trigger="investigation_complete",
            channel="webhook",
            destination="https://hooks.invalid/acme",
            min_severity="Low",
            config='{"url": "https://hooks.invalid/acme", "method": "POST", "include_full_report": true}',
        ),
    )
    await session.commit()


def _dispatch(who, code, alert_id, trigger="investigation_complete"):
    """(status, webhook calls, dispatch-log rows) for one dispatch."""
    from sqlalchemy import func
    from sqlalchemy import select

    from app.db.universal_models import NotificationDispatchLog
    from app.notifications.channels.base import SendResult
    from app.notifications.channels.webhook import WebhookChannel

    async def scenario(client, db):
        async with db.session() as session:
            await _add_webhook_route(session)
        send = AsyncMock(return_value=SendResult(status="sent", latency_ms=1))
        with patch.object(WebhookChannel, "send", send):
            response = await client.post(
                "/notifications/dispatch",
                json={"customer_code": code, "alert_id": alert_id, "trigger": trigger, "severity_assessment": "High", "summary": "s"},
                headers=as_user(who),
            )
        async with db.session() as session:
            rows = (await session.execute(select(func.count()).select_from(NotificationDispatchLog))).scalar()
        return response.status_code, send.await_count, rows

    return call(scenario, with_db=True)


def test_dispatch_with_another_customers_alert_is_refused_and_nothing_is_sent_or_logged():
    # The proof of concept: ACME's route, GLOBEX's alert, whose report the webhook would carry.
    assert _dispatch("admin", MINE, THEIR_ALERT) == (400, 0, 0)
    assert _dispatch("ana", MINE, THEIR_ALERT) == (403, 0, 0)


def test_dispatch_of_any_other_trigger_is_refused_and_takes_no_dedupe_key():
    for trigger in ("ai_report_reviewed", "alert_created", "alert_assigned", "sla_breached"):
        assert _dispatch("admin", MINE, MY_ALERT, trigger=trigger) == (400, 0, 0), trigger


def test_dispatch_is_admin_only():
    # talon-analyst never calls it, and CoPilot emits investigation_complete itself on write-back.
    for who in ("ana", "resp", "lonely"):
        assert _dispatch(who, MINE, MY_ALERT)[0] == 403, who


def test_dispatch_for_an_unknown_alert_is_a_404_for_an_admin():
    assert _dispatch("admin", MINE, 999) == (404, 0, 0)


def test_dispatch_for_the_alerts_own_customer_still_works():
    assert _dispatch("admin", MINE, MY_ALERT) == (200, 1, 1)


# ── POST /ai_analyst/jobs ─────────────────────────────────────────────────────


def _post(path, who, body):
    async def scenario(client):
        return await client.post(f"/ai_analyst/{path}", json=body, headers=as_user(who))

    return call(scenario)


def _job(job_id, alert_id, code):
    return {"id": job_id, "alert_id": alert_id, "customer_code": code, "triggered_by": "webhook"}


def test_job_for_another_customers_alert_is_refused():
    # Body names the analyst's own customer, so the route's check passes; the alert is not theirs.
    assert _post("jobs", "ana", _job("copilot-inv-2-2000", THEIR_ALERT, MINE)).status_code == 400
    assert _post("jobs", "admin", _job("copilot-inv-2-2000", THEIR_ALERT, MINE)).status_code == 400
    assert _post("jobs", "ana", _job("copilot-inv-2-2000", THEIR_ALERT, THEIRS)).status_code == 403


def test_another_customers_job_cannot_be_rewritten_by_naming_its_id():
    assert _post("jobs", "ana", _job(THEIR_JOB, MY_ALERT, MINE)).status_code == 409


def test_job_for_own_alert_is_created_and_an_unknown_alert_is_not():
    response = _post("jobs", "ana", _job("copilot-inv-1-2000", MY_ALERT, MINE))
    assert response.status_code == 200
    assert response.json()["job"]["customer_code"] == MINE
    assert _post("jobs", "ana", _job("copilot-inv-999-2000", 999, MINE)).status_code == 404
    # Re-sending the same job (FR-WB-1 is an idempotent upsert) still works.
    assert _post("jobs", "ana", _job(MY_JOB, MY_ALERT, MINE)).status_code == 200


# ── POST /ai_analyst/reports and /iocs ────────────────────────────────────────


def _report(job_id, alert_id, code):
    return {
        "job_id": job_id,
        "alert_id": alert_id,
        "customer_code": code,
        "severity_assessment": "High",
        "summary": "s",
        "report_markdown": "r",
        "recommended_actions": "a",
    }


def test_report_under_another_customers_job_is_refused():
    assert _post("reports", "ana", _report(THEIR_JOB, MY_ALERT, MINE)).status_code == 400
    assert _post("reports", "ana", _report(THEIR_JOB, THEIR_ALERT, MINE)).status_code == 400
    assert _post("reports", "ana", _report(THEIR_JOB, THEIR_ALERT, THEIRS)).status_code == 403
    # An admin can't file one under a mismatched job either: it's integrity, not access.
    assert _post("reports", "admin", _report(THEIR_JOB, MY_ALERT, MINE)).status_code == 400


def test_a_second_report_for_one_job_is_refused():
    async def scenario(client):
        first = await client.post("/ai_analyst/reports", json=_report(MY_JOB, MY_ALERT, MINE), headers=as_user("ana"))
        second = await client.post("/ai_analyst/reports", json=_report(MY_JOB, MY_ALERT, MINE), headers=as_user("ana"))
        by_admin = await client.post("/ai_analyst/reports", json=_report(MY_JOB, MY_ALERT, MINE), headers=as_user("admin"))
        return first, second, by_admin

    first, second, by_admin = call(scenario)
    assert first.status_code == 200
    assert second.status_code == 409 and by_admin.status_code == 409
    assert second.json()["detail"] == f"A report already exists for job {MY_JOB}"


def test_iocs_on_another_customers_report_are_refused():
    body = {"report_id": THEIR_REPORT, "alert_id": THEIR_ALERT, "customer_code": MINE, "iocs": [{"ioc_value": "1.2.3.4", "ioc_type": "ip"}]}
    assert _post("iocs", "ana", body).status_code == 400
    assert _post("iocs", "ana", {**body, "customer_code": THEIRS}).status_code == 403


def test_iocs_on_own_report_are_allowed():
    body = {"report_id": 2, "alert_id": MY_ALERT, "customer_code": MINE, "iocs": [{"ioc_value": "1.2.3.4", "ioc_type": "ip"}]}
    response = _post("iocs", "ana", body)
    assert response.status_code == 200
    assert response.json()["iocs_created"] == 1


# ── POST /ai_analyst/palace_lessons ───────────────────────────────────────────


def test_lesson_citing_another_customers_review_is_refused():
    body = {"customer_code": MINE, "lesson_type": "environment", "lesson_text": "t", "review_id": THEIR_REVIEW}
    assert _post("palace_lessons", "ana", body).status_code == 400
    assert _post("palace_lessons", "ana", {**body, "review_id": None}).status_code == 200


# ── GET /ai_analyst/alerts_with_reports ───────────────────────────────────────


def _alerts_with_reports(who, **params):
    async def scenario(client):
        return await client.get("/ai_analyst/alerts_with_reports", params=params, headers=as_user(who))

    response = call(scenario)
    assert response.status_code == 200
    return sorted(a["customer_code"] for a in response.json()["alerts"])


def test_alerts_with_reports_are_narrowed_to_the_callers_customers():
    assert _alerts_with_reports("ana") == [MINE]
    assert _alerts_with_reports("ana", customer_codes=THEIRS) == []
    assert _alerts_with_reports("lonely") == []
    assert _alerts_with_reports("admin") == [MINE, THEIRS]
    assert _alerts_with_reports("admin", customer_codes=THEIRS) == [THEIRS]


# ── the unique index as the last word on a race ───────────────────────────────


def _racing_submit(orig_message):
    """``submit_report`` where the pre-check finds nothing but the commit hits an IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    from app.ai_analyst.schema.ai_analyst import SubmitReportRequest
    from app.ai_analyst.services import ai_analyst as svc

    session = AsyncMock()
    session.add = lambda obj: None
    session.get = AsyncMock(return_value=SimpleNamespace(customer_code=MINE, alert_id=MY_ALERT))
    no_report = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None))
    session.execute = AsyncMock(return_value=no_report)
    session.commit = AsyncMock(side_effect=IntegrityError("INSERT …", {}, Exception(orig_message)))
    request = SubmitReportRequest(**_report(MY_JOB, MY_ALERT, MINE))
    try:
        asyncio.run(svc.submit_report(request, session))
    finally:
        session.rollback.assert_awaited()


def test_a_report_that_loses_the_race_is_a_409():
    from fastapi import HTTPException

    try:
        _racing_submit("(1062, \"Duplicate entry 'x' for key 'ai_analyst_report.uq_ai_analyst_report_job_id'\")")
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("expected a 409")


def test_any_other_integrity_error_is_not_dressed_up_as_a_duplicate():
    from sqlalchemy.exc import IntegrityError

    try:
        _racing_submit("(1452, 'Cannot add or update a child row: a foreign key constraint fails')")
    except IntegrityError:
        pass
    else:
        raise AssertionError("expected the IntegrityError itself")
