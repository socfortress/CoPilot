"""Shared fixtures for the Talon portal chat tests (talon-analyst D97, plan PC-3). Not collected by pytest.

Real routers (``app.routers.customer_portal`` and ``app.routers.talon``), a real in-memory database,
real request parsing; token decoding and user lookup are replaced, as in the other portal and Talon
tests. talon-analyst is ``FakeTalon``: an ``httpx.MockTransport`` holding a few portal threads and
drafts, answering its portal, review and health routes the way the SPEC writes them, and recording
every request it gets (its path and its headers).
"""

import asyncio
import json
import os
import re
import uuid
from contextlib import ExitStack
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
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
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.utils import health_client  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.customer_portal.services import talon_chat  # noqa: E402
from app.customer_portal.services import talon_chat_drafts  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerPortalChatSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequestSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

ACME, GLOBEX = "ACME", "GLOBEX"
#: name -> (user id, role id, token scopes, customers, read-only customers)
USERS = {
    "admin": (1, 1, ["admin"], [], []),
    "ana": (2, 2, ["analyst"], [ACME], []),
    "gus": (3, 2, ["analyst"], [GLOBEX], []),
    # An admin since demoted to analyst: the token issued before still carries the admin scope.
    "demoted": (4, 2, ["admin"], [ACME], []),
    "resp": (5, 5, ["responder", "analyst"], [ACME], []),
    "jane": (10, 4, ["customer_user"], [ACME], []),
    "rory": (11, 4, ["customer_user"], [ACME], [ACME]),
    "multi": (12, 4, ["customer_user"], [ACME, GLOBEX], [GLOBEX]),
    "gina": (13, 4, ["customer_user"], [GLOBEX], []),
    "talon-analyst": (20, 2, ["analyst"], [ACME, GLOBEX], []),
}
TALON = {
    "connector_name": "Talon",
    "connector_url": "http://talon.invalid",
    "connector_api_key": "dummy-talon-key",
    "connector_verified": True,
}
TABLES = {
    "customer_portal_soc_request",
    "customer_portal_soc_request_settings",
    "customer_portal_chat_settings",
    "customer_portal_ai_report_settings",
    "customer_portal_ai_request",
    "customer_portal_ioc_lookup",
    "customer_portal_ioc_enrichment_settings",
    "customer_portal_language_settings",
    "talon_connector_settings",
}
QUESTION = "Is the sign-in from Lisbon on Monday our VPN?"
_ID_PATH = re.compile(r"^/v2/portal/(threads|drafts|chat)/([0-9a-f-]{36})(/[a-z]+)?$")


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


def _json(status, body):
    return httpx.Response(status, json=body)


def refusal(code, status):
    texts = {
        "thread_not_found": "thread not found",
        "draft_not_found": "draft not found",
        "draft_expired": "this draft expired",
        "draft_conflict": "this draft was already decided",
        "portal_off": "portal chat is turned off for this customer",
        "read_only": "this account can view this customer's data but not change it",
    }
    return _json(status, {"detail": texts.get(code, code), "code": code})


class FakeTalon:
    """talon-analyst's portal, review and health routes, as far as CoPilot uses them."""

    def __init__(self):
        self.requests = []
        self.threads = {}  # id -> {"customer_code", "owner"}
        self.drafts = {}  # id -> draft dict (plus "owner")
        self.portal_chat = True
        self.claim_override = None  # callable(draft) -> httpx.Response
        self.messages_override = None  # an httpx.Response for every thread read-back (a busy transcript pool)
        self.outcomes = []
        self.claims = 0
        self.switched_off = set()  # customers talon-analyst reads as off (FR-API-45 still answers)
        self.stream = (
            b'data: {"type":"start"}\n\n'
            b'data: {"type":"error","errorText":"portal chat is turned off for this customer","code":"portal_off"}\n\n'
            b'data: {"type":"finish","finishReason":"error"}\n\ndata: [DONE]\n\n'
        )

    # ── state ──
    def add_thread(self, customer_code=ACME, owner="10"):
        thread_id = str(uuid.uuid4())
        self.threads[thread_id] = {"customer_code": customer_code, "owner": owner}
        return thread_id

    def add_draft(self, kind, target_id, customer_code=ACME, owner="10", status="pending"):
        draft_id = str(uuid.uuid4())
        self.drafts[draft_id] = {
            "id": draft_id,
            "thread_id": str(uuid.uuid4()),
            "customer_code": customer_code,
            "target": {"kind": kind, "id": target_id},
            "question": "drafted by Talon",
            "urgency": None,
            "file_on": None,
            "status": status,
            "copilot_ref": None,
            "claimed_at": None,
            "owner": owner,
        }
        return draft_id

    def thread_body(self, thread_id):
        """FR-API-45's (and the list's) thread: never refused for the switch, ``accessible`` instead."""
        thread = self.threads[thread_id]
        accessible = thread["customer_code"] not in self.switched_off
        return {"id": thread_id, "title": None, "customer_code": thread["customer_code"], "status": "active", "accessible": accessible}

    def portal_requests(self):
        """Every request to talon-analyst's portal chat or review routes (its health route apart)."""
        return [r for r in self.requests if r.url.path.startswith("/v2/") and r.url.path != "/v2/health"]

    # ── the transport ──
    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path, method = request.url.path, request.method
        user = request.headers.get("X-Talon-User")
        if path == "/v2/health":
            return _json(200, {"status": "ok", "config": {"portal_chat": self.portal_chat}})
        if path == "/v2/portal/threads":
            if method == "GET":
                return _json(200, {"threads": [self.thread_body(t) for t, v in self.threads.items() if v["owner"] == user], "next": None})
            body = json.loads(request.content)
            thread_id = self.add_thread(body["customer_code"], owner=user)
            return _json(201, {**self.thread_body(thread_id), "language": body.get("language")})
        if path.startswith("/v2/portal-review/"):
            if path == "/v2/portal-review/threads":
                return _json(200, {"threads": [], "next": None})
            return _json(200, {"thread": {"id": path.split("/")[3]}, "messages": [], "next": None})
        match = _ID_PATH.match(path)
        if match is None:
            return _json(404, {"detail": "Not Found"})
        kind, object_id, rest = match.group(1), match.group(2), match.group(3)
        if kind in ("threads", "chat"):
            thread = self.threads.get(object_id)
            if thread is None or thread["owner"] != user:
                return refusal("thread_not_found", 404)
            if kind == "chat":
                return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=self.stream)
            if rest == "/messages":
                if self.messages_override is not None:
                    return self.messages_override
                return _json(200, {"thread": self.thread_body(object_id), "messages": [], "next": None})
            # GET /v2/portal/threads/{id}: the thread itself, as one item of the list (PATCH and
            # DELETE answer the thread too).
            if rest == "/feedback":
                return httpx.Response(204)
            return _json(200, self.thread_body(object_id))
        draft = self.drafts.get(object_id)
        if draft is None or draft["owner"] != user:
            return refusal("draft_not_found", 404)
        public = {k: v for k, v in draft.items() if k != "owner"}
        if rest is None:
            return _json(200, public)
        body = json.loads(request.content)
        if rest == "/claim":
            if self.claim_override is not None:
                return self.claim_override(draft)
            if draft["status"] == "pending":
                self.claims += 1
                draft.update(
                    status="submitting",
                    urgency=body["urgency"],
                    file_on=body.get("file_on"),
                    claimed_at=f"2026-10-31T12:00:{self.claims:02d}Z",
                )
                public = {k: v for k, v in draft.items() if k != "owner"}
                return _json(200, {"draft": public, "claimed": True})
            if draft["status"] == "submitting":
                return _json(200, {"draft": public, "claimed": False})
            return refusal("draft_conflict", 409)
        if rest == "/outcome":
            self.outcomes.append((object_id, body))
            outcome = body["outcome"]
            if outcome == "submitted":
                # From submitting, and from pending or expired as a late ref (talon-analyst PR #197).
                if draft["status"] == "submitted" and draft["copilot_ref"] != body["copilot_ref"]:
                    return refusal("draft_conflict", 409)
                late = draft["status"] in ("pending", "expired")
                draft.update(status="submitted", copilot_ref=body["copilot_ref"], late_ref=late)
            elif outcome == "failed":
                # Only for the draft's current claim (talon-analyst PR #197): a stale one is a conflict.
                if draft["status"] != "submitting" or body.get("claimed_at") != draft.get("claimed_at"):
                    return refusal("draft_conflict", 409)
                draft.update(status="pending")
            elif outcome == "discarded":
                if draft["status"] != "pending":
                    return refusal("draft_conflict", 409)
                draft.update(status="discarded")
            return _json(200, {k: v for k, v in draft.items() if k != "owner"})
        return _json(404, {"detail": "Not Found"})

    def new_client(self, timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=timeout)


async def seed(db, *, chat=True, ai_reports=True, soc_requests=True, ioc=True, ioc_limit=None, v2=True, daily=200, per_user=50):
    async with db.session() as s:
        s.add_all([Customers(customer_code=code, customer_name=code) for code in (ACME, GLOBEX)])
        s.add_all(
            User(id=uid, username=name, password="x" * 8, email=f"{uid}@example.com", role_id=role)
            for name, (uid, role, *_) in USERS.items()
        )
        await s.commit()
        for name, (uid, _, _, customers, read_only) in USERS.items():
            s.add_all(UserCustomerAccess(user_id=uid, customer_code=code, read_only=code in read_only) for code in customers)
        for code in (ACME, GLOBEX):
            if ai_reports:
                s.add(CustomerPortalAiReportSettings(customer_code=code, enabled=True, allow_customer_requests=True))
            if chat:
                s.add(
                    CustomerPortalChatSettings(
                        customer_code=code,
                        portal_chat_enabled=True,
                        daily_message_limit=daily,
                        user_daily_message_limit=per_user,
                        version=3,
                    ),
                )
            if soc_requests:
                s.add(CustomerPortalSocRequestSettings(customer_code=code, enabled=True))
            if ioc:
                s.add(CustomerPortalIocEnrichmentSettings(customer_code=code, enabled=True, daily_lookup_limit=ioc_limit))
        s.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=v2))
        await s.commit()
        lonely = await add_alert(s, name="Odd login")
        linked = await add_alert(s, name="Brute force")
        open_case = await add_case(s, name="Brute force investigation", status="IN_PROGRESS")
        s.add(CaseAlertLink(case_id=open_case.id, alert_id=linked.id))
        globex_alert = await add_alert(s, name="Globex alert", customer=GLOBEX)
        await s.commit()
        return SimpleNamespace(lonely=lonely.id, linked=linked.id, open_case=open_case.id, globex_alert=globex_alert.id)


def _app(db):
    from app.routers import customer_portal
    from app.routers import talon

    app = FastAPI()
    app.include_router(customer_portal.router)
    app.include_router(talon.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


def call(scenario, *, talon=None, **seeded):
    """Run ``scenario(client, ctx)``: ``ctx`` has the db, the fake Talon, the seeded ids and the events."""
    talon = talon or FakeTalon()

    async def _inner():
        db = await Db().create()
        ids = await seed(db, **seeded)
        ctx = SimpleNamespace(db=db, talon=talon, ids=ids, events=[])

        async def resolve_user(self, request, username):
            if username not in USERS:
                return None
            uid, role, *_ = USERS[username]
            return SimpleNamespace(id=uid, username=username, role_id=role)

        recorder = {
            name: AsyncMock()
            for name in ("alert_opened", "case_opened", "alert_action", "alerts_action", "case_action", "case_links_changed")
        }
        talon_chat.clear_health_cache()
        with ExitStack() as stack:
            stack.enter_context(patch.object(AuthHandler, "decode_token", lambda self, token: (token, USERS.get(token, (0, 0, []))[2])))
            stack.enter_context(patch.object(AuthHandler, "_resolve_user", resolve_user))
            stack.enter_context(patch.object(v2_client, "_new_client", talon.new_client))
            stack.enter_context(patch.object(v2_client, "_connector", AsyncMock(return_value=TALON)))
            stack.enter_context(patch.object(health_client, "_new_client", talon.new_client))
            stack.enter_context(patch.object(talon_chat, "_connector_attributes", AsyncMock(return_value=TALON)))
            stack.enter_context(patch.object(talon_chat_drafts, "OUTCOME_PAUSE_SECONDS", 0))
            stack.enter_context(patch.multiple(SlaLifecycleRecorder, **recorder))
            stack.enter_context(patch("app.customer_portal.services.soc_requests.emit", lambda event: ctx.events.append(event)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(db)), base_url="http://copilot") as client:
                try:
                    return await scenario(client, ctx)
                finally:
                    talon_chat.clear_health_cache()
                    await db.engine.dispose()

    return asyncio.run(_inner())


def as_user(name, **extra):
    return {"Authorization": f"Bearer {name}", **extra}


async def rows(db, model, *where):
    async with db.session() as s:
        return (await s.execute(select(model).where(*where))).scalars().all()


async def set_chat(db, customer_code=ACME, **values):
    async with db.session() as s:
        row = (
            (await s.execute(select(CustomerPortalChatSettings).where(CustomerPortalChatSettings.customer_code == customer_code)))
            .scalars()
            .one()
        )
        for name, value in values.items():
            setattr(row, name, value)
        await s.commit()


def a_while_ago(minutes):
    return datetime.utcnow() - timedelta(minutes=minutes)
