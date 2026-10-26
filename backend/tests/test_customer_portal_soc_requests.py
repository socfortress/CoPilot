"""'Ask the SOC' from the Customer Portal (#1305): a portal user's question about an alert or a case.

Real routers, real in-memory database, real request parsing; only token decoding, user lookup,
the SLA recorder (its own sessions), the audit writer and the notification emitter are replaced.

Pinned here:
- off until an admin turns it on (audited), with an optional daily limit; an analyst reads it;
- on an alert the user chooses: the alert's open case, a new case from the alert, or the alert
  itself; the question is a comment signed by the user, the request row says where it went;
- a question on a case; a waiting case is handed back to the SOC by it;
- the cooldown per alert or case and the customer's daily limit; refusals audited;
- only the user's own customers' alerts and cases; the SOC can't ask; the question is checked;
- the SOC hears it through the internal ``customer_question`` trigger, severity from the urgency;
- a SOC comment on the target answers the open questions, a portal user's does not; an analyst
  marks one answered by hand; the SOC's list is scoped to their customers; the portal never
  learns who answered;
- the pure rules, the event, the default body and the built-in template.

Run with: cd backend && python -m pytest tests/test_customer_portal_soc_requests.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
from sqlmodel import select  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.schema.soc_requests import clean_question  # noqa: E402
from app.customer_portal.services import soc_requests as service  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequest  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequestSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    customer_question_event,
)
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

PEOPLE = [(1, "admin", 1), (2, "ana", 2), (3, "gina", 2), (10, "jane", 4), (11, "bob", 4)]
USERS = {name: SimpleNamespace(id=uid, username=name, role_id=role) for uid, name, role in PEOPLE}
SCOPES = {name: ["customer_user"] if role == 4 else (["admin"] if role == 1 else ["analyst"]) for _, name, role in PEOPLE}
TABLES = {"customer_portal_soc_request", "customer_portal_soc_request_settings"}
BASE = "/customer_portal/soc_requests"
QUESTION = "We see this sign-in from Lisbon every Monday: is it our VPN?"


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        tables = _tables() + [SQLModel.metadata.tables[name] for name in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    def session(self) -> AsyncSession:
        return self.factory()


def _app(db: Db) -> FastAPI:
    from app.routers import customer_portal
    from app.routers import incidents

    app = FastAPI()
    app.include_router(customer_portal.router)
    app.include_router(incidents.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db, *, enabled=("ACME",), limit=None) -> dict:
    async with db.session() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all([Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")])
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=10, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="ACME"),
                UserCustomerAccess(user_id=2, customer_code="ACME"),
                UserCustomerAccess(user_id=3, customer_code="GLOBEX"),
            ],
        )
        s.add_all(CustomerPortalSocRequestSettings(customer_code=code, enabled=True, daily_request_limit=limit) for code in enabled)
        await s.commit()
        lonely = await add_alert(s, name="Odd login")
        linked = await add_alert(s, name="Brute force")
        open_case = await add_case(s, name="Brute force investigation", status="IN_PROGRESS")
        s.add(CaseAlertLink(case_id=open_case.id, alert_id=linked.id))
        waiting = await add_case(s, name="Waiting on Acme", status="PENDING_CUSTOMER")
        globex_alert = await add_alert(s, name="Globex alert", customer="GLOBEX")
        globex_case = await add_case(s, name="Globex case", customer="GLOBEX")
        await s.commit()
        return {
            "lonely": lonely.id,
            "linked": linked.id,
            "open_case": open_case.id,
            "waiting": waiting.id,
            "globex_alert": globex_alert.id,
            "globex_case": globex_case.id,
        }


class Recorded(SimpleNamespace):
    pass


def call(scenario, *, enabled=("ACME",), limit=None):
    async def _inner():
        db = await Db().create()
        ids = await _seed(db, enabled=enabled, limit=limit)
        rec = Recorded(events=[], audit=AsyncMock(), db=db, ids=ids)

        async def resolve_user(self, request, username):
            return USERS.get(username)

        recorder = {
            name: AsyncMock()
            for name in ("alert_opened", "case_opened", "alert_action", "alerts_action", "case_action", "case_links_changed")
        }
        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ), patch.multiple(SlaLifecycleRecorder, **recorder), patch(
            "app.customer_portal.services.soc_requests.emit",
            lambda event: rec.events.append(event),
        ), patch(
            "app.customer_portal.services.soc_requests.record_audit_event",
            rec.audit,
        ), patch(
            "app.customer_portal.routes.soc_requests.record_audit_event",
            rec.audit,
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(db)), base_url="http://test") as client:
                return await scenario(client, rec)

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


async def rows(db: Db, model, *where):
    async with db.session() as s:
        return (await s.execute(select(model).where(*where))).scalars().all()


def ask(client, kind, target_id, user="jane", **body):
    return client.post(f"{BASE}/{kind}/{target_id}", json={"question": QUESTION, **body}, headers=as_user(user))


# ── the switch ────────────────────────────────────────────────────────────────


def test_off_until_an_admin_turns_it_on():
    async def scenario(client, rec):
        available = (await client.get(f"{BASE}/availability", headers=as_user("jane"))).json()
        refused = await ask(client, "alert", rec.ids["lonely"])
        by_analyst = await client.put(f"{BASE}/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
        turned_on = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_request_limit": 20}, headers=as_user("admin"))
        again = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_request_limit": 20}, headers=as_user("admin"))
        read = (await client.get(f"{BASE}/settings/ACME", headers=as_user("ana"))).json()
        now_available = (await client.get(f"{BASE}/availability", params={"customer_code": "ACME"}, headers=as_user("jane"))).json()
        return available, refused, by_analyst, turned_on, again, read, now_available

    rec_holder = {}

    def capture(scenario):
        async def wrapped(client, rec):
            rec_holder["rec"] = rec
            return await scenario(client, rec)

        return wrapped

    available, refused, by_analyst, turned_on, again, read, now_available = call(capture(scenario), enabled=())
    rec = rec_holder["rec"]
    assert available["enabled"] is False
    assert refused.status_code == 403 and refused.json()["detail"] == service.NOT_ENABLED
    assert by_analyst.status_code == 403
    assert turned_on.status_code == 200 and again.status_code == 200
    assert read["settings"]["enabled"] is True and read["settings"]["daily_request_limit"] == 20
    assert now_available["enabled"] is True
    actions = [c.kwargs["action"] for c in rec.audit.await_args_list]
    # The refused question, then the switch once: saving the same values again changes nothing.
    assert [a.value for a in actions] == ["soc_request.create", "soc_request.settings_update"]
    assert rec.audit.await_args_list[0].kwargs["result"].value == "failure"
    assert rec.audit.await_args_list[1].kwargs["new_value"] == {"enabled": True, "daily_request_limit": 20}


def test_the_limit_must_be_a_sensible_number_and_an_unknown_customer_is_a_404():
    async def scenario(client, rec):
        zero = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_request_limit": 0}, headers=as_user("admin"))
        missing = await client.put(f"{BASE}/settings/NOPE", json={"enabled": True}, headers=as_user("admin"))
        other = await client.get(f"{BASE}/settings/GLOBEX", headers=as_user("ana"))
        return zero, missing, other

    zero, missing, other = call(scenario)
    assert zero.status_code == 422
    assert missing.status_code == 404
    assert other.status_code == 403


# ── asking about an alert ─────────────────────────────────────────────────────


def test_a_question_on_an_alert_without_a_case_opens_one_from_it():
    async def scenario(client, rec):
        response = await ask(client, "alert", rec.ids["lonely"], urgency="high", target="case")
        listed = (await client.get(f"{BASE}/alert/{rec.ids['lonely']}", headers=as_user("jane"))).json()
        links = await rows(rec.db, CaseAlertLink, CaseAlertLink.alert_id == rec.ids["lonely"])
        case_id = links[0].case_id if links else None
        comments = await rows(rec.db, CaseComment, CaseComment.case_id == case_id)
        requests = await rows(rec.db, CustomerPortalSocRequest)
        return rec, response, listed, case_id, comments, requests

    rec, response, listed, case_id, comments, requests = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()["request"]
    assert case_id is not None
    assert (body["case_id"], body["alert_id"], body["origin_alert_id"]) == (case_id, None, rec.ids["lonely"])
    assert (body["status"], body["urgency"], body["requested_by"]) == ("open", "high", "jane")
    assert "answered_by" not in body
    # The question is a comment on the new case, signed by the user.
    assert [(c.user_name, c.comment) for c in comments] == [("jane", f"Question for the SOC (urgency: High):\n\n{QUESTION}")]
    assert requests[0].comment_id == comments[0].id
    # The alert's list shows it, and the case it now has.
    assert [r["id"] for r in listed["requests"]] == [body["id"]] and listed["open_case_id"] == case_id
    # The SOC hears about it on the case.
    (event,) = rec.events
    assert event.trigger == NotificationTrigger.CUSTOMER_QUESTION
    assert (event.entity_type, event.entity_id, event.customer_code) == ("case", case_id, "ACME")
    assert event.severity == NotificationSeverity.HIGH and event.actor_username == "jane"
    assert event.context["question"] == QUESTION
    success = rec.audit.await_args_list[-1].kwargs
    assert (success["action"].value, success["result"].value, success["entity_type"], success["entity_id"]) == (
        "soc_request.create",
        "success",
        "case",
        case_id,
    )


def test_a_question_on_an_alert_with_an_open_case_goes_on_that_case():
    async def scenario(client, rec):
        response = await ask(client, "alert", rec.ids["linked"], target="case")
        cases = await rows(rec.db, Case)
        comments = await rows(rec.db, CaseComment, CaseComment.case_id == rec.ids["open_case"])
        return rec, response, cases, comments

    rec, response, cases, comments = call(scenario)
    assert response.status_code == 200
    assert response.json()["request"]["case_id"] == rec.ids["open_case"]
    assert len(cases) == 3  # no new case
    assert [c.user_name for c in comments] == ["jane"]


def test_a_question_kept_on_the_alert_is_a_comment_on_it():
    async def scenario(client, rec):
        response = await ask(client, "alert", rec.ids["linked"], target="alert", urgency="low")
        comments = await rows(rec.db, Comment, Comment.alert_id == rec.ids["linked"])
        case_comments = await rows(rec.db, CaseComment)
        return rec, response, comments, case_comments

    rec, response, comments, case_comments = call(scenario)
    body = response.json()["request"]
    assert (body["alert_id"], body["case_id"], body["origin_alert_id"]) == (rec.ids["linked"], None, None)
    assert [(c.user_name, c.comment.startswith("Question for the SOC (urgency: Low)")) for c in comments] == [("jane", True)]
    assert case_comments == []
    (event,) = rec.events
    assert (event.entity_type, event.entity_id, event.severity) == ("alert", rec.ids["linked"], NotificationSeverity.LOW)


# ── asking about a case ───────────────────────────────────────────────────────


def test_a_question_on_a_waiting_case_hands_it_back_to_the_soc():
    async def scenario(client, rec):
        response = await ask(client, "case", rec.ids["waiting"])
        case = (await rows(rec.db, Case, Case.id == rec.ids["waiting"]))[0]
        listed = (await client.get(f"{BASE}/case/{rec.ids['waiting']}", headers=as_user("jane"))).json()
        return rec, response, case, listed

    rec, response, case, listed = call(scenario)
    assert response.status_code == 200
    assert response.json()["request"]["case_id"] == rec.ids["waiting"]
    assert case.case_status == "IN_PROGRESS"
    assert [r["status"] for r in listed["requests"]] == ["open"]
    assert rec.events[0].severity == NotificationSeverity.MEDIUM


# ── limits and refusals ───────────────────────────────────────────────────────


def test_one_question_per_alert_or_case_every_few_minutes():
    async def scenario(client, rec):
        first = await ask(client, "alert", rec.ids["lonely"], target="alert")
        second = await ask(client, "alert", rec.ids["lonely"], user="bob", target="case")
        other = await ask(client, "alert", rec.ids["linked"], target="alert")
        case_first = await ask(client, "case", rec.ids["open_case"])
        case_again = await ask(client, "case", rec.ids["open_case"])
        return first, second, other, case_first, case_again

    first, second, other, case_first, case_again = call(scenario)
    assert first.status_code == 200 and other.status_code == 200 and case_first.status_code == 200
    assert second.status_code == 429 and "ask again in 10 minutes" in second.json()["detail"]
    assert case_again.status_code == 429


def test_the_customer_daily_limit():
    async def scenario(client, rec):
        return [
            (await ask(client, "alert", rec.ids["lonely"], target="alert")).status_code,
            (await ask(client, "alert", rec.ids["linked"], target="alert")).status_code,
            (await ask(client, "case", rec.ids["waiting"], user="bob")).status_code,
        ]

    assert call(scenario, limit=2) == [200, 200, 429]


def test_only_the_users_own_alerts_and_cases_and_only_portal_users():
    async def scenario(client, rec):
        return [
            (await ask(client, "alert", rec.ids["globex_alert"])).status_code,
            (await ask(client, "case", rec.ids["globex_case"])).status_code,
            (await ask(client, "alert", 99999)).status_code,
            (await ask(client, "case", rec.ids["open_case"], user="ana")).status_code,
            (await client.get(f"{BASE}/case/{rec.ids['globex_case']}", headers=as_user("jane"))).status_code,
        ]

    assert call(scenario, enabled=("ACME", "GLOBEX")) == [403, 403, 404, 403, 403]


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001, "pay ‮to this", "a\x00b"])
def test_the_question_is_checked(question):
    async def scenario(client, rec):
        return await client.post(f"{BASE}/case/{rec.ids['open_case']}", json={"question": question}, headers=as_user("jane"))

    assert call(scenario).status_code == 422


def test_a_bad_urgency_or_target_is_refused():
    async def scenario(client, rec):
        return [
            (await ask(client, "case", rec.ids["open_case"], urgency="urgent")).status_code,
            (await ask(client, "alert", rec.ids["lonely"], target="email")).status_code,
        ]

    assert call(scenario) == [422, 422]


def test_a_failure_while_filing_costs_the_customer_nothing():
    async def scenario(client, rec):
        with patch("app.customer_portal.services.soc_requests._comment_on_case", AsyncMock(side_effect=RuntimeError("db gone"))):
            failed = await ask(client, "case", rec.ids["open_case"])
        left = await rows(rec.db, CustomerPortalSocRequest)
        retried = await ask(client, "case", rec.ids["open_case"])
        return rec, failed, left, retried

    rec, failed, left, retried = call(scenario)
    assert failed.status_code == 502 and failed.json()["detail"] == service.FAILED
    assert "db gone" not in failed.text
    assert left == []
    # No cooldown spent on the failure.
    assert retried.status_code == 200
    assert len(rec.events) == 1


# ── answering ─────────────────────────────────────────────────────────────────


def test_the_socs_comment_answers_the_open_questions_and_a_portal_users_does_not():
    async def scenario(client, rec):
        await ask(client, "case", rec.ids["open_case"])
        await client.post(
            "/incidents/db_operations/case/comment",
            json={"case_id": rec.ids["open_case"], "comment": "One more detail", "user_name": "x"},
            headers=as_user("bob"),
        )
        still_open = (await client.get(f"{BASE}/case/{rec.ids['open_case']}", headers=as_user("jane"))).json()["requests"]
        await client.post(
            "/incidents/db_operations/case/comment",
            json={"case_id": rec.ids["open_case"], "comment": "That is our VPN, nothing to do.", "user_name": "x"},
            headers=as_user("ana"),
        )
        answered = (await client.get(f"{BASE}/case/{rec.ids['open_case']}", headers=as_user("jane"))).json()["requests"]
        soc = (await client.get(BASE, headers=as_user("ana"))).json()
        return still_open, answered, soc

    still_open, answered, soc = call(scenario)
    assert [r["status"] for r in still_open] == ["open"]
    assert [r["status"] for r in answered] == ["answered"] and answered[0]["answered_at"]
    assert "answered_by" not in answered[0]
    assert (soc["requests"][0]["answered_by"], soc["requests"][0]["answered_via"]) == ("ana", "comment")


def test_an_alert_question_is_answered_by_a_comment_on_the_alert():
    async def scenario(client, rec):
        await ask(client, "alert", rec.ids["lonely"], target="alert")
        await client.post(
            "/incidents/db_operations/alert/comment",
            json={"alert_id": rec.ids["lonely"], "comment": "Looking into it", "user_name": "x"},
            headers=as_user("admin"),
        )
        return (await client.get(f"{BASE}/alert/{rec.ids['lonely']}", headers=as_user("jane"))).json()["requests"]

    assert [r["status"] for r in call(scenario)] == ["answered"]


def test_the_soc_lists_its_customers_questions_and_marks_one_answered_by_hand():
    async def scenario(client, rec):
        await ask(client, "case", rec.ids["open_case"], urgency="high")
        await ask(client, "alert", rec.ids["lonely"], target="alert")
        listed = (await client.get(BASE, params={"status": "open"}, headers=as_user("ana"))).json()
        other_analyst = (await client.get(BASE, headers=as_user("gina"))).json()
        target = listed["requests"][-1]["id"]
        foreign = await client.post(f"{BASE}/{target}/answered", headers=as_user("gina"))
        by_portal = await client.post(f"{BASE}/{target}/answered", headers=as_user("jane"))
        marked = await client.post(f"{BASE}/{target}/answered", headers=as_user("ana"))
        again = await client.post(f"{BASE}/{target}/answered", headers=as_user("ana"))
        after = (await client.get(BASE, headers=as_user("ana"))).json()
        by_case = (await client.get(BASE, params={"case_id": rec.ids["open_case"]}, headers=as_user("ana"))).json()
        return rec, listed, other_analyst, foreign, by_portal, marked, again, after, by_case

    rec, listed, other_analyst, foreign, by_portal, marked, again, after, by_case = call(scenario)
    assert (listed["total"], listed["open"]) == (2, 2)
    assert [r["title"] for r in listed["requests"]] == ["Odd login", "Brute force investigation"]
    assert all(r["customer_code"] == "ACME" for r in listed["requests"])
    assert other_analyst["requests"] == [] and other_analyst["total"] == 0
    assert foreign.status_code == 404 and by_portal.status_code == 403
    assert marked.status_code == 200
    assert (marked.json()["request"]["status"], marked.json()["request"]["answered_via"]) == ("answered", "manual")
    assert again.json()["request"]["answered_at"] == marked.json()["request"]["answered_at"]
    assert (after["total"], after["open"]) == (2, 1)
    assert [r["case_id"] for r in by_case["requests"]] == [rec.ids["open_case"]]
    answers = [c.kwargs for c in rec.audit.await_args_list if c.kwargs["action"].value == "soc_request.answer"]
    assert len(answers) == 1 and answers[0]["new_value"] == {"status": "answered", "via": "manual"}


# ── the pure parts ────────────────────────────────────────────────────────────


NOW = datetime(2026, 10, 1, 12, 0, 0)


def settings(enabled=True, limit=None):
    return CustomerPortalSocRequestSettings(customer_code="ACME", enabled=enabled, daily_request_limit=limit)


def test_refusal_rules():
    assert service.refusal(None, None, 0, NOW).status_code == 403
    assert service.refusal(settings(enabled=False), None, 0, NOW).status_code == 403
    assert service.refusal(settings(), None, 0, NOW) is None
    recent = service.refusal(settings(), NOW - timedelta(minutes=9, seconds=30), 0, NOW)
    assert recent.status_code == 429 and "in 1 minute." in recent.detail
    assert service.refusal(settings(), NOW - timedelta(minutes=10), 0, NOW) is None
    assert service.refusal(settings(limit=3), None, 3, NOW).status_code == 429
    assert service.refusal(settings(limit=3), None, 2, NOW) is None
    # Unlimited ignores the count.
    assert service.refusal(settings(limit=None), None, 999, NOW) is None


def test_clean_question():
    assert clean_question("  line one\r\nline two\t ") == "line one\nline two"
    for bad in ("", "\n\n", "x" * 2001, "a​b", "a\x07b"):
        with pytest.raises(ValueError):
            clean_question(bad)


def test_the_comment_names_the_urgency():
    assert service.comment_text("Why?", "low") == "Question for the SOC (urgency: Low):\n\nWhy?"
    assert service.comment_text("Why?", "bogus").startswith("Question for the SOC (urgency: Normal)")


def test_the_event_is_internal_one_per_question_and_carries_an_excerpt():
    event = customer_question_event(
        request_id=7,
        entity_type="alert",
        entity_id=3,
        title="Odd login",
        customer_code="ACME",
        urgency="low",
        asked_by="jane",
        question="x" * 900,
    )
    assert "customer_question" in INTERNAL_TRIGGERS and NotificationTrigger.CUSTOMER_QUESTION in DISPATCH_TRIGGERS
    assert event.dedupe_key == "customer_question:7"
    assert event.severity == NotificationSeverity.LOW
    assert len(event.context["question"]) == 500 and event.context["question"].endswith("…")
    assert event.subject == "Customer question on alert #3 — Odd login"
    assert event.link_url is None or event.link_url.endswith("/incident-management/alerts/3")


def test_the_default_body_and_the_builtin_template():
    from app.notifications.services.notifications import _format_default_body_core
    from app.notifications.services.rendering import render
    from app.notifications.services.template_seeds import BUILTIN_TEMPLATES
    from app.notifications.services.templates import sample_event

    event = customer_question_event(
        request_id=1,
        entity_type="case",
        entity_id=12,
        title="Brute force",
        customer_code="ACME",
        urgency="high",
        asked_by="jane",
        question="Is it our VPN?",
    )
    body = _format_default_body_core(event)
    assert "*Customer question* — urgency *high*" in body and "Case: #12 — Brute force" in body and "> Is it our VPN?" in body
    assert "Asked by: jane" in body

    (template,) = [t for t in BUILTIN_TEMPLATES if t["trigger"] == "customer_question"]
    text = render(template["body_template"], sample_event("customer_question", "ACME"))
    assert "*Customer question* — urgency *high*" in text and "Asked by: jane.doe" in text


def test_the_portal_projection_never_names_who_answered():
    request = CustomerPortalSocRequest(
        id=1,
        customer_code="ACME",
        case_id=2,
        question="Q",
        urgency="normal",
        status="answered",
        requested_by="jane",
        requested_at=NOW,
        answered_at=NOW,
        answered_by="ana",
        answered_via="comment",
    )
    portal = service.to_portal(request).model_dump()
    assert "answered_by" not in portal and "answered_via" not in portal
    assert portal["answered_at"] == "2026-10-01T12:00:00Z"
    assert service.to_soc(request, {2: "Case"}, {}).answered_by == "ana"


def test_a_socs_role_is_what_answers():
    from app.customer_portal.services.soc_request_answers import is_soc_user

    assert [is_soc_user(SimpleNamespace(role_id=r)) for r in (1, 2, 3, 4, 5, 99)] == [True, True, False, False, True, False]
