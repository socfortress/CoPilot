"""Talon v2 action proposals in CoPilot: the mirror, approve and deny, the run, and the result
(talon-analyst plan M5-11a; SPEC §5.3 M5-11, §8 "v2 API" Actions, §9.5, D46, D47, INV-ACT-1).

Real routers (``app.routers.talon``), a real in-memory database, CoPilot's real alert route
handlers; token decoding and user lookup are replaced (as in test_talon_v2_proxy), and
talon-analyst is ``FakeTalon``, an ``httpx.MockTransport`` that keeps its records by the rules of
talon-analyst's ``talon.api.actions`` (who may read and decide, the claim's ``claimed``, the
result's ``recorded``, the fixed 409 texts, the 24 h result window). Velociraptor is never called:
the quarantine service is a recorder.

Pinned here:
- the setting off: every action route answers 404 ``{"detail": "Not Found"}`` after the scope check,
  nothing reaches talon-analyst, and the job does nothing;
- the mirror is filled from ``GET /v2/actions/{id}`` only: its target comes from the GET even when
  the stream's ``tool-input-available`` says otherwise; the chat tap mirrors after the stream ends,
  a disconnect included, as the requester, and never changes the forwarded bytes; a record that
  changes is refused; the card's GET syncs on demand and shows only the requester or a decider;
- D47 in CoPilot: an analyst, a demoted admin (admin scope in the token, analyst ``role_id``) and a
  portal user can't approve a quarantine; a responder can't approve for a customer they lack; an
  alert outside the approver's tags or of another customer is refused; nothing is claimed;
- one run per proposal: two concurrent approvals run once and claim once;
- the claim: ``claimed: false``, an expired or withdrawn claim and a transport error run nothing; a
  lost answer posts ``failed`` (decision f);
- each re-check failure runs nothing: a shared host name, a changed client id, another customer's
  client, another agent claiming the client, an unknown assignee, one without access, a portal user;
- the executor passes the approver (and the request) to each handler, whose signatures are pinned;
  the alert routes' own effects happen (status, SLA recorder, a comment as written); quarantine
  audits both events;
- the result: posted inline up to 3 times, then by the job, with the same body each time; the job
  backs off and stops on success, at talon-analyst's window 409 and 24 h after the approval; stale
  rows of a request that died are settled without running anything;
- deny, withdraw, the archive re-sync, the lists, the audit events.

Run with: cd backend && python -m pytest tests/test_talon_actions.py
"""

import asyncio
import inspect
import json
import os
import uuid
from contextlib import ExitStack
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.audit.models.audit import AuditAction  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonActionRequest  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_action_execution as execution  # noqa: E402
from app.connectors.talon.services import talon_action_sync as sync  # noqa: E402
from app.connectors.talon.services import talon_actions as actions  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.connectors.talon.utils.approval_tap import ApprovalScanner  # noqa: E402
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes  # noqa: E402
from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    QuarantineResponse,
)
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from app.incidents.routes import db_operations as incident_routes  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.test_talon_v2_proxy import Chunks  # noqa: E402
from tests.test_talon_v2_proxy import _asgi_chat  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "talon_v2"
ACME, GLOBEX = "ACME", "GLOBEX"
THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
GOLDEN_APPROVAL_ID = "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b"
HOST = "WIN-ACME-01"
VID = "C.0123456789abcdef"
CONNECTOR = {"connector_url": "http://talon.invalid", "connector_api_key": "connector-key", "connector_verified": True}
UTC = timezone.utc

# name: (id, role_id, customers). Tokens carry SCOPES; the database role is role_id.
USERS = {
    "admin": (1, 1, []),
    "ana": (2, 2, [ACME]),
    "demoted": (4, 2, [ACME]),  # an admin since demoted to analyst: the old token still says admin
    "resp": (5, 5, [ACME]),
    "globex_resp": (6, 5, [GLOBEX]),
    "globex_ana": (7, 2, [GLOBEX]),
    "portal": (10, 4, [ACME]),
}
SCOPES = {
    "admin": ["admin"],
    "ana": ["analyst"],
    "demoted": ["admin"],
    "resp": ["responder", "analyst"],
    "globex_resp": ["responder", "analyst"],
    "globex_ana": ["analyst"],
    "portal": ["customer_user"],
}
ROLE_NAMES = {1: "admin", 2: "analyst", 4: "customer_user", 5: "responder"}
APPROVERS = {"endpoint-action": {"admin", "responder"}, "external-action": {"admin", "analyst", "responder"}}
CLASSES = dict(sync.ACTION_CLASSES)


def user_ns(name):
    uid, role_id, _ = USERS[name]
    return SimpleNamespace(id=uid, username=name, role_id=role_id)


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def iso(moment):
    return moment.astimezone(UTC).isoformat() if moment is not None else None


def now():
    return datetime.now(UTC)


# ── talon-analyst, as a fake that keeps its records by its own rules ─────────


class FakeTalon:
    """talon-analyst's v2 action API (``talon.api.actions``, ``talon.actions``), kept in memory."""

    def __init__(self):
        self.records = {}
        self.requests = []
        self.lenient = False  # answer every GET (as a talon-analyst bug would): CoPilot must still check
        self.intercept = None  # async (request) -> Response | None, consulted first; may raise
        self.chat_pieces = None
        self.claim_gate = None  # an asyncio.Event a claim waits on

    # records ------------------------------------------------------------------

    def add(
        self,
        action="set_alert_status",
        *,
        alert_id=1,
        customer=ACME,
        user="2",
        thread=THREAD,
        status="pending",
        ttl=timedelta(hours=4),
        **over,
    ):
        rid = over.pop("id", str(uuid.uuid4()))
        if action in sync.ALERT_ACTIONS:
            target = {"alert_id": alert_id}
            args = {
                "set_alert_status": {"alert_id": alert_id, "status": "CLOSED"},
                "assign_alert": {"alert_id": alert_id, "assigned_to": "ana"},
                "comment_on_alert": {"alert_id": alert_id, "comment": "a comment"},
            }[action]
        else:
            target = {"customer_code": customer, "agent_id": "021", "velociraptor_id": VID, "hostname": HOST}
            args = {
                "hostname": HOST,
                "velociraptor_id": VID,
                "action": "quarantine" if action == "quarantine_host" else "remove_quarantine",
                "artifact_name": "Windows.Remediation.Quarantine",
            }
        rec = {
            "id": rid,
            "thread_id": thread,
            "tool_call_id": f"call_{rid[:8]}",
            "customer_code": customer,
            "user_id": user,
            "action": action,
            "target": over.pop("target", target),
            "args": over.pop("args", args),
            "reason": over.pop("reason", "a known scanner"),
            "links": over.pop("links", False),
            "provenance": {"untrusted_seen": False, "injection_detected": False, "web_used": False},
            "status": status,
            "decided_by": None,
            "decided_at": None,
            "result": None,
            "reported_at": None,
            "copilot_ref": None,
            "created_at": now(),
            "expires_at": now() + ttl,
        }
        rec.update(over)
        self.records[rid] = rec
        return rid

    def body(self, rec):
        due = iso(rec["decided_at"] + timedelta(hours=24)) if rec["status"] == "approved" and rec["decided_at"] else None
        out = dict(rec)
        out.update(
            side_effect=CLASSES.get(rec["action"]),
            executes_through="(route)",
            decided_at=iso(rec["decided_at"]),
            reported_at=iso(rec["reported_at"]),
            created_at=iso(rec["created_at"]),
            expires_at=iso(rec["expires_at"]),
            result_due_by=due,
        )
        return out

    def _expire(self, rec):
        if rec["status"] == "pending" and rec["expires_at"] <= now():
            rec["status"] = "expired"

    # the transport ------------------------------------------------------------

    def outcome_posts(self, action_id=None):
        return [
            json.loads(r.content)
            for r in self.requests
            if r.method == "POST" and r.url.path.endswith("/outcome") and (action_id is None or f"/v2/actions/{action_id}/" in r.url.path)
        ]

    async def handler(self, request):
        self.requests.append(request)
        if self.intercept is not None:
            answer = await self.intercept(request)
            if answer is not None:
                return answer
        return await self.default(request)

    async def default(self, request):
        path, method, h = request.url.path, request.method, request.headers
        who = SimpleNamespace(user=h["x-talon-user"], role=h["x-talon-role"], customers=h["x-talon-customers"])

        def allows(code):
            return who.customers == "*" or code in who.customers.split(",")

        def may_decide(rec):
            return who.role in APPROVERS[CLASSES[rec["action"]]]

        if path.startswith("/v2/actions/"):
            rid = path.split("/")[3]
            rec = self.records.get(rid)
            if rec is None:
                return httpx.Response(404, json={"detail": "action not found"})
            self._expire(rec)
            if method == "GET":
                if not self.lenient and (not allows(rec["customer_code"]) or (rec["user_id"] != who.user and not may_decide(rec))):
                    return httpx.Response(404, json={"detail": "action not found"})
                return httpx.Response(200, json=self.body(rec))
            if path.endswith("/withdraw"):
                if rec["user_id"] != who.user:
                    return httpx.Response(404, json={"detail": "action not found"})
                if rec["status"] == "pending":
                    rec["status"], rec["decided_at"] = "withdrawn", now()
                if rec["status"] != "withdrawn":
                    return httpx.Response(409, json={"detail": "this action was already decided"})
                return httpx.Response(200, json={"id": rid, "status": rec["status"]})
            return await self._outcome(request, rec, who, allows, may_decide)
        if method == "DELETE" and path.startswith("/v2/threads/"):
            thread = path.split("/")[3]
            for rec in self.records.values():
                if rec["thread_id"] == thread and rec["status"] == "pending":
                    rec["status"], rec["decided_at"] = "withdrawn", now()
            return httpx.Response(200, json={"id": thread, "status": "archived"})
        if method == "POST" and path.startswith("/v2/chat/"):
            return httpx.Response(
                200,
                stream=Chunks(self.chat_pieces or [b"data: [DONE]\n\n"]),
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(404, json={"detail": "Not Found"})

    async def _outcome(self, request, rec, who, allows, may_decide):
        body = json.loads(request.content)
        approver = rec["decided_by"] is not None and rec["decided_by"] == who.user
        if not approver and not allows(rec["customer_code"]):
            return httpx.Response(404, json={"detail": "action not found"})
        if body["decided_by"] != who.user:
            return httpx.Response(400, json={"detail": "decided_by must be the caller (X-Talon-User)"})
        if body["thread_id"] != rec["thread_id"]:
            return httpx.Response(409, json={"detail": "the action is not of that thread"})

        def refusal():
            text = {"expired": "this action expired before a decision", "withdrawn": "this action was withdrawn"}.get(
                rec["status"],
                "this action was already decided",
            )
            return httpx.Response(409, json={"detail": text})

        if body["outcome"] in ("approved", "denied"):
            if not allows(rec["customer_code"]):
                return httpx.Response(404, json={"detail": "action not found"})
            if not may_decide(rec):
                return httpx.Response(403, json={"detail": "this role may not decide this action"})
            if self.claim_gate is not None:
                await self.claim_gate.wait()
            self._expire(rec)
            if rec["status"] == "pending":
                rec.update(status=body["outcome"], decided_by=body["decided_by"], decided_at=now(), copilot_ref=body.get("copilot_ref"))
                return httpx.Response(200, json={**self.body(rec), "claimed": True})
            if (
                rec["status"] == body["outcome"]
                and rec["decided_by"] == body["decided_by"]
                and rec["copilot_ref"] == body.get("copilot_ref")
            ):
                return httpx.Response(200, json={**self.body(rec), "claimed": False})
            return refusal()
        if rec["status"] == "approved":
            if rec["decided_by"] != body["decided_by"]:
                return httpx.Response(409, json={"detail": "only the approver reports the result"})
            if now() >= rec["decided_at"] + timedelta(hours=24):
                return httpx.Response(409, json={"detail": "the result came after its window"})
            rec.update(status=body["outcome"], result=body.get("result"), reported_at=now())
            return httpx.Response(200, json={**self.body(rec), "recorded": True})
        if rec["status"] == body["outcome"] and rec["decided_by"] == body["decided_by"] and rec["result"] == body.get("result"):
            return httpx.Response(200, json={**self.body(rec), "recorded": False})
        if rec["status"] == "pending":
            return httpx.Response(409, json={"detail": "this action isn't approved"})
        return refusal()


# ── the app and its database ──────────────────────────────────────────────────


class _Db(Db):
    async def create(self) -> "_Db":
        await super().create()
        tables = [TalonConnectorSettings.__table__, TalonActionRequest.__table__, Agents.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self


class FakeRecorder:
    """The SLA lifecycle recorder the alert routes call (``SlaLifecycleRecorder``)."""

    calls = []

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        async def record(*args, **kwargs):
            FakeRecorder.calls.append((name, args, kwargs))

        return record


def agent_row(hostname=HOST, vid=VID, customer=ACME, agent_id="021"):
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.0.1",
        os="Windows 11",
        hostname=hostname,
        label="",
        critical_asset=False,
        wazuh_last_seen=datetime(2026, 10, 16, 8, 0),
        velociraptor_id=vid,
        velociraptor_last_seen=datetime(2026, 10, 16, 8, 0),
        wazuh_agent_version="4.9",
        wazuh_agent_status="active",
        velociraptor_agent_version="0.75",
        customer_code=customer,
        quarantined=False,
        velociraptor_org="root",
    )


async def _seed(db, enabled):
    async with db.session() as session:
        session.add_all([Customers(customer_code=ACME, customer_name="Acme"), Customers(customer_code=GLOBEX, customer_name="Globex")])
        session.add_all(
            [
                User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role)
                for name, (uid, role, _) in USERS.items()
            ],
        )
        await session.commit()
        for name, (uid, _, customers) in USERS.items():
            session.add_all([UserCustomerAccess(user_id=uid, customer_code=code) for code in customers])
        if enabled is not None:
            session.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=enabled))
        acme_alert = await add_alert(session, customer=ACME, name="ACME alert")
        globex_alert = await add_alert(session, customer=GLOBEX, name="GLOBEX alert")
        session.add(agent_row())
        await session.commit()
        return SimpleNamespace(alert_id=acme_alert.id, globex_alert_id=globex_alert.id)


def _app(db):
    from app.routers import talon

    app = FastAPI()
    app.include_router(talon.router)

    # CoPilot's own handler shape for FastAPI's HTTPException.
    async def handler(request, exc):
        return JSONResponse({"success": False, "message": exc.detail}, status_code=exc.status_code)

    app.add_exception_handler(HTTPException, handler)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


def call(scenario, *, enabled=True, talon=None):
    """Run ``scenario(client, ctx)``; ``ctx`` has the fake talon-analyst, the db and the recorders."""
    talon = talon or FakeTalon()
    FakeRecorder.calls = []

    async def _inner():
        db = await _Db().create()
        try:
            ctx = await _seed(db, enabled)
            ctx.talon, ctx.db = talon, db
            ctx.audit = AsyncMock()
            ctx.quarantine_audit = AsyncMock()
            ctx.velociraptor = AsyncMock(return_value=QuarantineResponse(success=True, message="Quarantine scheduled", results=None))
            ctx.emit = MagicMock()
            app = _app(db)
            ctx.app = app

            async def resolve_user(self, request, username):
                return user_ns(username) if username in USERS else None

            def new_client(timeout):
                return httpx.AsyncClient(transport=httpx.MockTransport(talon.handler), timeout=timeout)

            async def all_users(*args, **kwargs):
                async with db.session() as session:
                    return (await session.execute(select(User))).scalars().all()

            artifacts = SimpleNamespace(
                artifacts=[SimpleNamespace(name="Windows.Remediation.Quarantine"), SimpleNamespace(name="Linux.Remediation.Quarantine")],
            )
            with ExitStack() as stack:
                stack.enter_context(patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))))
                stack.enter_context(patch.object(AuthHandler, "_resolve_user", resolve_user))
                stack.enter_context(patch.object(v2_client, "_new_client", new_client))
                stack.enter_context(patch.object(v2_client, "_connector", AsyncMock(return_value=CONNECTOR)))
                stack.enter_context(patch.object(sync, "new_session", db.session))
                stack.enter_context(patch.object(actions, "record_audit_event", ctx.audit))
                stack.enter_context(patch.object(actions, "INLINE_PAUSES", (0, 0)))
                stack.enter_context(patch.object(velociraptor_routes, "record_audit_event", ctx.quarantine_audit))
                stack.enter_context(patch.object(velociraptor_routes, "quarantine_host", ctx.velociraptor))
                stack.enter_context(patch.object(velociraptor_routes, "get_all_artifacts_for_hostname", AsyncMock(return_value=artifacts)))
                stack.enter_context(patch.object(incident_routes, "SlaLifecycleRecorder", FakeRecorder))
                stack.enter_context(patch.object(incident_routes, "emit", ctx.emit))
                stack.enter_context(patch.object(incident_routes, "select_all_users", all_users))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    try:
                        return await scenario(client, ctx)
                    finally:
                        await sync.wait_for_background()
        finally:
            await db.dispose()

    return asyncio.run(_inner())


async def row_of(ctx, action_id):
    async with ctx.db.session() as session:
        return await session.get(TalonActionRequest, action_id)


async def set_row(ctx, action_id, **values):
    async with ctx.db.session() as session:
        await session.execute(update(TalonActionRequest).where(TalonActionRequest.id == action_id).values(**values))
        await session.commit()


async def approve(client, name, action_id):
    return await client.post(f"/talon/actions/{action_id}/approve", headers=as_user(name))


async def deny(client, name, action_id):
    return await client.post(f"/talon/actions/{action_id}/deny", headers=as_user(name))


def claims(talon, action_id=None):
    return [b for b in talon.outcome_posts(action_id) if b["outcome"] in ("approved", "denied")]


def results(talon, action_id=None):
    return [b for b in talon.outcome_posts(action_id) if b["outcome"] in ("executed", "failed")]


def audit_actions(ctx):
    return [(c.kwargs["action"], c.kwargs["result"].value) for c in ctx.audit.await_args_list]


# ── the setting ───────────────────────────────────────────────────────────────

ANY_ID = "6a0f8c55-1a39-4e57-9d6e-3f1a2b3c4d5e"
ROUTES = [
    ("GET", "/talon/actions"),
    ("GET", "/talon/actions?scope=mine"),
    ("GET", f"/talon/actions/{ANY_ID}"),
    ("POST", f"/talon/actions/{ANY_ID}/approve"),
    ("POST", f"/talon/actions/{ANY_ID}/deny"),
    ("POST", f"/talon/actions/{ANY_ID}/withdraw"),
]


@pytest.mark.parametrize("enabled", [None, False], ids=["no row", "off"])
def test_with_the_setting_off_every_action_route_is_not_found(enabled):
    async def scenario(client, ctx):
        out = []
        for method, path in ROUTES:
            for name in ("admin", "resp"):
                response = await client.request(method, path, headers=as_user(name))
                out.append((method, path, response.status_code, response.json()))
        unauthenticated = [(await client.request(m, p)).status_code for m, p in ROUTES]
        return out, unauthenticated, ctx.talon.requests

    out, unauthenticated, requests = call(scenario, enabled=enabled)
    for method, path, status, body in out:
        assert (status, body) == (404, {"detail": "Not Found"}), (method, path)
    assert unauthenticated == [401] * len(ROUTES)  # the scope check comes first
    assert requests == []


def test_with_the_setting_off_the_job_does_nothing():
    async def scenario(client, ctx):
        rid = ctx.talon.add()
        async with ctx.db.session() as session:
            session.add(
                TalonActionRequest(
                    id=rid,
                    thread_id=THREAD,
                    tool_call_id="c",
                    customer_code=ACME,
                    requester_user_id="2",
                    action="set_alert_status",
                    side_effect="external-action",
                    talon_status="approved",
                    expires_at=sync.utcnow(),
                    state="executed",
                    approver_user_id=2,
                    copilot_ref="copilot-x",
                    execution_result={"success": True, "message": "ok", "status_code": 200},
                    next_attempt_at=sync.utcnow() - timedelta(minutes=5),
                ),
            )
            await session.commit()
        counts = await actions.run_outcome_job()
        return counts, ctx.talon.requests

    counts, requests = call(scenario, enabled=False)
    assert counts == {"posted": 0, "retry": 0, "stopped": 0, "done": 0} and requests == []


# ── the mirror ────────────────────────────────────────────────────────────────


def test_the_mirror_takes_its_target_from_the_get_even_when_the_stream_says_otherwise():
    wire = (FIXTURES / "v2_approval.txt").read_bytes()
    assert b'"input":{"alert_id":840,"status":"CLOSED"' in wire  # what the stream claims

    async def scenario(client, ctx):
        # The record says another alert and another status: the record is what counts.
        ctx.talon.add(id=GOLDEN_APPROVAL_ID, args={"alert_id": ctx.alert_id, "status": "IN_PROGRESS"}, alert_id=ctx.alert_id)
        ctx.talon.chat_pieces = [wire[i : i + 5] for i in range(0, len(wire), 5)]
        response = await client.post(f"/talon/v2/chat/{THREAD}", json={"message": "close it"}, headers=as_user("ana"))
        await sync.wait_for_background()
        gets = [r for r in ctx.talon.requests if r.method == "GET"]
        return response, await row_of(ctx, GOLDEN_APPROVAL_ID), gets, ctx.alert_id

    response, row, gets, alert_id = call(scenario)
    assert response.status_code == 200 and response.content == wire  # forwarded byte for byte
    assert row is not None and row.state == "pending"
    assert row.target == {"alert_id": alert_id} and row.args == {"alert_id": alert_id, "status": "IN_PROGRESS"}
    assert alert_id != 840
    # Read back as the requester, with their own identity.
    (get,) = gets
    assert (
        get.url.path == f"/v2/actions/{GOLDEN_APPROVAL_ID}"
        and get.headers["x-talon-user"] == "2"
        and get.headers["x-talon-role"] == "analyst"
    )


def test_the_tap_mirrors_after_the_browser_leaves():
    card = f'data: {{"type":"tool-approval-request","approvalId":"{GOLDEN_APPROVAL_ID}","toolCallId":"call_q"}}\n\n'.encode()

    async def scenario(client, ctx):
        ctx.talon.add(id=GOLDEN_APPROVAL_ID, alert_id=ctx.alert_id)
        streams = []

        async def intercept(request):
            if request.url.path.startswith("/v2/chat/"):
                # The card, then a quiet turn: only the browser leaving ends it.
                stream = Chunks([b'data: {"type":"start"}\n\n', card, b"never"], hang_after=2)
                streams.append(stream)
                return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream"})
            return None

        ctx.talon.intercept = intercept
        sent, error = await _asgi_chat(ctx.app, receive_disconnect=True)
        await sync.wait_for_background()
        return sent, streams, await row_of(ctx, GOLDEN_APPROVAL_ID)

    sent, streams, row = call(scenario)
    assert b"".join(m["body"] for m in sent if m.get("body")).endswith(card)
    assert [s.closed for s in streams] == [True]
    assert row is not None and row.requester_user_id == "2" and row.state == "pending"


def test_the_golden_stream_is_unchanged_through_the_tap_with_keepalives():
    wire = (FIXTURES / "v2_approval.txt").read_bytes()
    blocks = wire.split(b"\n\n")[:-1]
    noisy = b"".join(block + b"\n\n: keepalive\n\n" for block in blocks)

    async def scenario(client, ctx):
        ctx.talon.add(id=GOLDEN_APPROVAL_ID, alert_id=ctx.alert_id)
        ctx.talon.chat_pieces = [noisy[i : i + 3] for i in range(0, len(noisy), 3)]
        response = await client.post(f"/talon/v2/chat/{THREAD}", json={"message": "x"}, headers=as_user("ana"))
        await sync.wait_for_background()
        return response.content, await row_of(ctx, GOLDEN_APPROVAL_ID)

    content, row = call(scenario)
    assert content == noisy and row is not None


def _scan(pieces):
    scanner = ApprovalScanner()
    for piece in pieces:
        scanner.feed(piece)
    scanner.close()
    return scanner.approval_ids


def test_the_scanner_finds_the_card_at_every_split_point():
    wire = (FIXTURES / "v2_approval.txt").read_bytes()
    for at in range(len(wire) + 1):
        assert _scan([wire[:at], wire[at:]]) == [GOLDEN_APPROVAL_ID], at
    crlf = wire.replace(b"\n", b"\r\n")
    cr = wire.replace(b"\n", b"\r")
    for variant in (crlf, cr):
        for at in range(0, len(variant) + 1, 3):
            assert _scan([variant[:at], variant[at:]]) == [GOLDEN_APPROVAL_ID], at


def test_the_scanner_reads_only_real_cards():
    other = "5b0c1d2e-3f40-4a5b-8c6d-7e8f90a1b2c3"
    lines = [
        # A text delta that mentions the type is no card; neither is a malformed id.
        b'data: {"type":"text-delta","delta":"tool-approval-request 5b0c1d2e-3f40-4a5b-8c6d-7e8f90a1b2c3","id":"text-1"}\n\n',
        b'data: {"type":"tool-approval-request","approvalId":"not-a-uuid"}\n\n',
        b'data: {"type":"tool-approval-request","approvalId":"' + GOLDEN_APPROVAL_ID.upper().encode() + b'"}\n\n',
        # A line longer than the scanner reads is skipped, the event with it dropped.
        b'data: {"type":"tool-approval-request","approvalId":"' + GOLDEN_APPROVAL_ID.encode() + b'","pad":"' + b"x" * 70000 + b'"}\n\n',
        b": keepalive\n\n",
        # A card split over two data lines is one event; the last event lacks its blank line.
        b'data: {"type":"tool-approval-request",\ndata: "approvalId":"' + other.encode() + b'"}\n\n',
        b'data: {"type":"tool-approval-request","approvalId":"' + GOLDEN_APPROVAL_ID.encode() + b'"}',
    ]
    assert _scan(lines) == [other, GOLDEN_APPROVAL_ID]
    # The same id twice is one sync.
    twice = b'data: {"type":"tool-approval-request","approvalId":"' + other.encode() + b'"}\n\n'
    assert _scan([twice, twice]) == [other]


def test_the_cards_get_syncs_on_demand_and_shows_only_the_requester_or_a_decider():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)  # proposed by ana (user 2)
        out = {}
        for name in ("ana", "resp", "admin", "globex_ana", "globex_resp"):
            response = await client.get(f"/talon/actions/{rid}", headers=as_user(name))
            out[name] = (response.status_code, response.json().get("action"))
        host = ctx.talon.add("quarantine_host", user="5")
        for name in ("ana", "resp"):
            response = await client.get(f"/talon/actions/{host}", headers=as_user(name))
            out[f"host:{name}"] = (response.status_code, response.json().get("action"))
        return out, await row_of(ctx, rid)

    out, row = call(scenario)
    assert out["ana"][0] == 200 and out["ana"][1]["is_requester"] is True and out["ana"][1]["can_decide"] is True
    assert out["resp"][0] == 200 and out["resp"][1]["is_requester"] is False and out["resp"][1]["can_decide"] is True
    assert out["admin"][0] == 200
    assert out["globex_ana"][0] == 404 and out["globex_resp"][0] == 404  # talon-analyst's 404, as our own
    assert out["host:resp"][0] == 200 and out["host:resp"][1]["can_decide"] is True
    assert out["host:ana"][0] == 404  # an analyst neither proposed nor may decide a quarantine
    assert row is not None and row.reason == "a known scanner"


def test_the_reason_args_and_comment_are_kept_as_sent():
    raw = "<a href='https://evil.example'>click</a> **bold** [x](https://y.example) | # h"

    async def scenario(client, ctx):
        rid = ctx.talon.add(
            "comment_on_alert",
            alert_id=ctx.alert_id,
            reason=raw,
            args={"alert_id": ctx.alert_id, "comment": raw},
            links=True,
        )
        response = await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        return response.json()["action"]

    action = call(scenario)
    assert action["reason"] == raw and action["args"]["comment"] == raw and action["links"] is True


def test_a_record_that_changes_after_it_was_mirrored_is_refused():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        ctx.talon.records[rid]["args"] = {"alert_id": ctx.alert_id, "status": "OPEN"}
        second = await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        response = await approve(client, "ana", rid)
        return second.json()["action"], response, claims(ctx.talon)

    action, response, claimed = call(scenario)
    assert action["state"] == "refused" and action["args"]["status"] == "CLOSED"  # the stored proposal stays
    assert response.status_code == 409 and claimed == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: {**b, "action": "run_shell"},
        lambda b: {**b, "side_effect": "read"},
        lambda b: {**b, "id": str(uuid.uuid4())},
        lambda b: {**b, "customer_code": "bad code!"},
        lambda b: {k: v for k, v in b.items() if k != "status"},
    ],
    ids=["unknown action", "wrong class", "another id", "bad customer", "no status"],
)
def test_an_answer_that_isnt_a_proposal_is_not_mirrored(mutate):
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)

        async def intercept(request):
            if request.method == "GET":
                return httpx.Response(200, json=mutate(ctx.talon.body(ctx.talon.records[rid])))
            return None

        ctx.talon.intercept = intercept
        response = await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        return response.status_code, await row_of(ctx, rid)

    status, row = call(scenario)
    assert status == 502 and row is None


# ── D47 in CoPilot ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["ana", "demoted"])
def test_an_analyst_or_a_demoted_admin_cannot_approve_a_quarantine(name):
    async def scenario(client, ctx):
        ctx.talon.lenient = True  # even if talon-analyst answered them, CoPilot refuses
        rid = ctx.talon.add("quarantine_host", user="5")
        response = await approve(client, name, rid)
        return response, claims(ctx.talon), ctx.velociraptor.await_count, await row_of(ctx, rid)

    response, claimed, ran, row = call(scenario)
    assert response.status_code == 403 and response.json()["message"] == "this role may not decide this action"
    assert claimed == [] and ran == 0 and row.state == "pending"


def test_a_portal_user_cannot_reach_the_decision_routes():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        statuses = [(await approve(client, "portal", rid)).status_code, (await deny(client, "portal", rid)).status_code]
        return statuses, ctx.talon.requests

    statuses, requests = call(scenario)
    assert all(status in (401, 403) for status in statuses) and requests == []


@pytest.mark.parametrize("lenient", [False, True], ids=["talon refuses", "copilot refuses"])
def test_a_responder_cannot_approve_for_a_customer_they_lack(lenient):
    async def scenario(client, ctx):
        ctx.talon.lenient = lenient
        rid = ctx.talon.add("quarantine_host", user="5")
        response = await approve(client, "globex_resp", rid)
        return response.status_code, claims(ctx.talon), ctx.velociraptor.await_count

    status, claimed, ran = call(scenario)
    assert status == (403 if lenient else 404) and claimed == [] and ran == 0


def test_an_alert_outside_the_approvers_tags_is_refused():
    async def scenario(client, ctx):
        ctx.talon.lenient = True
        async with ctx.db.session() as session:
            tag = AlertTag(tag="restricted")
            session.add_all([tag, TagAccessSettings(enabled=True, untagged_alert_behavior="visible_to_all")])
            await session.commit()
            session.add(AlertToTag(alert_id=ctx.alert_id, tag_id=tag.id))
            await session.commit()
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        response = await approve(client, "ana", rid)
        return response, claims(ctx.talon), await row_of(ctx, rid)

    response, claimed, row = call(scenario)
    assert response.status_code == 403 and "tag" in response.json()["message"]
    assert claimed == [] and row.state == "pending"


def test_an_alert_of_another_customer_is_refused():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.globex_alert_id)  # the record says ACME; the alert is GLOBEX's
        response = await approve(client, "admin", rid)
        return response, claims(ctx.talon)

    response, claimed = call(scenario)
    assert response.status_code == 403 and response.json()["message"] == "the alert is not this proposal's customer's"
    assert claimed == []


def test_a_host_of_another_customer_is_refused_before_the_claim():
    async def scenario(client, ctx):
        async with ctx.db.session() as session:
            session.add(agent_row(hostname="WIN-GLOBEX-01", vid="C.fedcba9876543210", customer=GLOBEX, agent_id="099"))
            await session.commit()
        target = {"customer_code": ACME, "agent_id": "099", "velociraptor_id": "C.fedcba9876543210", "hostname": "WIN-GLOBEX-01"}
        args = {
            "hostname": "WIN-GLOBEX-01",
            "velociraptor_id": "C.fedcba9876543210",
            "action": "quarantine",
            "artifact_name": "Windows.Remediation.Quarantine",
        }
        rid = ctx.talon.add("quarantine_host", user="5", target=target, args=args)
        response = await approve(client, "resp", rid)
        return response, claims(ctx.talon), ctx.velociraptor.await_count

    response, claimed, ran = call(scenario)
    assert response.status_code == 403 and claimed == [] and ran == 0


# ── one run per proposal, and the claim ───────────────────────────────────────


def test_two_concurrent_approvals_run_once():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        ctx.talon.claim_gate = asyncio.Event()
        first = asyncio.create_task(approve(client, "resp", rid))
        while not claims(ctx.talon):  # the first is holding its claim at talon-analyst
            await asyncio.sleep(0.01)
        second = await approve(client, "admin", rid)
        ctx.talon.claim_gate.set()
        return await first, second, claims(ctx.talon), ctx.velociraptor.await_count, await row_of(ctx, rid)

    first, second, claimed, ran, row = call(scenario)
    assert first.status_code == 200 and first.json()["action"]["state"] == "executed"
    assert second.status_code == 409 and second.json()["message"] == "this action is being decided"
    assert len(claimed) == 1 and ran == 1 and row.state == "executed"


def test_an_approval_after_another_ran_is_refused():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        first = await approve(client, "ana", rid)
        second = await approve(client, "resp", rid)
        return first.status_code, second, claims(ctx.talon)

    first, second, claimed = call(scenario)
    assert first == 200 and second.status_code == 409 and len(claimed) == 1


def _claim_answer(make):
    async def intercept(request):
        if request.url.path.endswith("/outcome") and json.loads(request.content)["outcome"] == "approved":
            return await make(request)
        return None

    return intercept


@pytest.mark.parametrize(
    "case",
    ["claimed false", "expired", "withdrawn", "transport error", "answer lost after landing", "5xx", "claimed missing"],
)
def test_a_claim_without_claimed_true_runs_nothing(case):
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        talon = ctx.talon

        async def make(request):
            rec = talon.records[rid]
            if case == "claimed false":
                answer = await talon.default(request)
                return httpx.Response(200, json={**json.loads(answer.content), "claimed": False})
            if case == "claimed missing":
                answer = await talon.default(request)
                payload = json.loads(answer.content)
                payload.pop("claimed")
                return httpx.Response(200, json=payload)
            if case == "expired":
                rec["expires_at"] = now() - timedelta(seconds=1)
                return None
            if case == "withdrawn":
                rec["status"] = "withdrawn"
                return None
            if case == "transport error":
                raise httpx.ConnectError("refused")
            if case == "answer lost after landing":
                await talon.default(request)
                raise httpx.ReadTimeout("lost")
            return httpx.Response(500, json={"detail": "boom"})

        talon.intercept = _claim_answer(make)
        response = await approve(client, "resp", rid)
        return response, ctx.velociraptor.await_count, await row_of(ctx, rid), results(talon, rid), talon.records[rid]

    response, ran, row, posted, rec = call(scenario)
    assert ran == 0
    if case == "expired":
        assert response.status_code == 409 and row.state == "expired" and posted == []
    elif case == "withdrawn":
        assert response.status_code == 409 and row.state == "withdrawn" and posted == []
    else:
        # Decision f: never run, and "failed" is posted so the thread isn't left waiting.
        assert response.status_code == 502
        assert posted and all(p["outcome"] == "failed" and p["result"]["success"] is False for p in posted)
        assert all(p["result"]["message"].startswith("not run:") for p in posted)
        if case in ("claimed false", "answer lost after landing", "claimed missing"):
            assert row.state == "failed" and rec["status"] == "failed" and row.outcome_posted_at is not None
        else:  # the claim never landed: talon-analyst's record is still pending; the job settles it
            assert row.state == "claim_lost" and rec["status"] == "pending" and row.next_attempt_at is not None


def test_a_lost_claim_that_never_landed_is_settled_when_the_record_expires():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")

        async def make(request):
            raise httpx.ConnectError("refused")

        ctx.talon.intercept = _claim_answer(make)
        await approve(client, "resp", rid)
        ctx.talon.intercept = None
        ctx.talon.records[rid]["expires_at"] = now() - timedelta(seconds=1)
        await actions.run_outcome_job(now=sync.utcnow() + timedelta(hours=2))
        return await row_of(ctx, rid), ctx.velociraptor.await_count, claims(ctx.talon, rid)

    row, ran, claimed = call(scenario)
    assert row.state == "expired" and ran == 0 and len(claimed) == 1  # never claimed again


# ── re-checks just before the run ─────────────────────────────────────────────


async def _host_scenario(client, ctx, change):
    async with ctx.db.session() as session:
        await change(session)
        await session.commit()
    rid = ctx.talon.add("quarantine_host", user="5")
    response = await approve(client, "resp", rid)
    return response, ctx.velociraptor.await_count, await row_of(ctx, rid), results(ctx.talon, rid)


async def _shared_name(session):
    session.add(agent_row(hostname=HOST.lower(), vid="C.1111111111111111", agent_id="022"))


async def _changed_client(session):
    await session.execute(update(Agents).where(Agents.agent_id == "021").values(velociraptor_id="C.2222222222222222"))


async def _other_customer(session):
    await session.execute(update(Agents).where(Agents.agent_id == "021").values(customer_code=GLOBEX))


async def _client_claimed_elsewhere(session):
    session.add(agent_row(hostname="OTHER", vid=VID.upper().replace("C.", "c.") + "-O123", agent_id="023"))


async def _org_suffixed(session):
    await session.execute(update(Agents).where(Agents.agent_id == "021").values(velociraptor_id=VID + "-O123"))


@pytest.mark.parametrize(
    "change, why",
    [
        (_shared_name, "the host name is not on exactly one agent"),
        (_changed_client, "the host's Velociraptor client changed"),
        (_other_customer, "the host belongs to another customer"),
        (_client_claimed_elsewhere, "another agent carries the host's Velociraptor client"),
        (_org_suffixed, "the host's Velociraptor client changed"),
    ],
    ids=["shared host name", "changed client id", "another customer's client", "client claimed by another agent", "org-suffixed client"],
)
def test_each_host_recheck_failure_runs_nothing(change, why):
    async def scenario(client, ctx):
        # D47's enforce_hostname_access passes (the host is still ACME's, or found first); the
        # re-check under the lock catches what changed.
        with patch.object(execution, "enforce_hostname_access", AsyncMock()):
            return await _host_scenario(client, ctx, change)

    response, ran, row, posted = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "failed"
    assert ran == 0 and row.state == "failed"
    assert row.execution_result == {"success": False, "message": f"not run: {why}", "status_code": None}
    assert [p["outcome"] for p in posted] == ["failed"]


@pytest.mark.parametrize(
    "assignee, why",
    [
        ("nobody", "the assignee is not one CoPilot user"),
        ("globex_ana", "the assignee has no access to this customer"),
        ("portal", "the assignee is not a SOC user"),
        ("ANA", "the assignee is not one CoPilot user"),
    ],
    ids=["unknown", "no access", "portal user", "case differs"],
)
def test_each_assignee_recheck_failure_runs_nothing(assignee, why):
    async def scenario(client, ctx):
        rid = ctx.talon.add("assign_alert", alert_id=ctx.alert_id, args={"alert_id": ctx.alert_id, "assigned_to": assignee})
        response = await approve(client, "ana", rid)
        async with ctx.db.session() as session:
            alert = await session.get(Alert, ctx.alert_id)
        return response, await row_of(ctx, rid), alert.assigned_to, ctx.emit.call_count

    response, row, assigned, emitted = call(scenario)
    assert response.status_code == 200 and row.state == "failed"
    assert row.execution_result["message"] == f"not run: {why}"
    assert assigned is None and emitted == 0


def test_an_assignee_with_access_is_assigned_through_the_route():
    async def scenario(client, ctx):
        rid = ctx.talon.add("assign_alert", alert_id=ctx.alert_id, args={"alert_id": ctx.alert_id, "assigned_to": "resp"})
        response = await approve(client, "ana", rid)
        async with ctx.db.session() as session:
            alert = await session.get(Alert, ctx.alert_id)
        return response, alert.assigned_to, ctx.emit.call_count, FakeRecorder.calls

    response, assigned, emitted, recorded = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "executed"
    assert assigned == "resp" and emitted == 1  # the route's assignment notification
    assert recorded[0][0] == "alert_action" and recorded[0][2]["assignee"] == "resp"


# ── the run: CoPilot's own route handlers, under the approver ────────────────


def test_the_handler_signatures_are_pinned():
    expected = {
        incident_routes.update_alert_status_endpoint: ["alert_status", "current_user", "db"],
        incident_routes.update_assigned_to_endpoint: ["assigned_to", "current_user", "db"],
        incident_routes.create_comment_endpoint: ["comment", "current_user", "db"],
        velociraptor_routes.quarantine: ["quarantine_body", "request", "current_user", "session"],
    }
    for handler, names in expected.items():
        assert list(inspect.signature(handler).parameters) == names, handler.__name__


@pytest.mark.parametrize("action", ["set_alert_status", "assign_alert", "comment_on_alert", "quarantine_host", "release_host"])
def test_the_executor_passes_the_approver_to_each_handler(action):
    handler_name = {
        "set_alert_status": (incident_routes, "update_alert_status_endpoint"),
        "assign_alert": (incident_routes, "update_assigned_to_endpoint"),
        "comment_on_alert": (incident_routes, "create_comment_endpoint"),
        "quarantine_host": (velociraptor_routes, "quarantine"),
        "release_host": (velociraptor_routes, "quarantine"),
    }[action]

    async def scenario(client, ctx):
        mock = AsyncMock(return_value=SimpleNamespace(success=True, message="done by the route"))
        approver = "resp" if action in sync.HOST_ACTIONS else "ana"
        rid = ctx.talon.add(action, alert_id=ctx.alert_id, user="1")  # proposed by someone else
        with patch.object(*handler_name, mock):
            response = await approve(client, approver, rid)
        return response, mock, approver

    response, mock, approver = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "executed"
    (call_,) = mock.await_args_list
    user = call_.kwargs["current_user"]
    assert (user.id, user.username) == (USERS[approver][0], approver)
    if action in sync.HOST_ACTIONS:
        body = call_.kwargs["quarantine_body"]
        assert body.hostname == HOST and body.action.value == ("quarantine" if action == "quarantine_host" else "remove_quarantine")
        assert call_.kwargs["request"] is not None  # the audit's source IP
    elif action == "comment_on_alert":
        assert call_.kwargs["comment"].comment == "a comment"
    assert response.json()["action"]["execution_result"] == {"success": True, "message": "done by the route", "status_code": 200}


def test_a_status_change_runs_through_the_alert_route_and_its_result_is_reported():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        response = await approve(client, "ana", rid)
        async with ctx.db.session() as session:
            alert = await session.get(Alert, ctx.alert_id)
        return response, alert.status, FakeRecorder.calls, results(ctx.talon, rid), ctx.talon.records[rid], await row_of(ctx, rid)

    response, status, recorded, posted, rec, row = call(scenario)
    assert response.status_code == 200 and status == "CLOSED"
    (name, args, kwargs) = recorded[0]
    assert name == "alert_action" and args[2].username == "ana" and kwargs["to_status"] == "CLOSED"
    assert posted == [
        {
            "thread_id": THREAD,
            "outcome": "executed",
            "decided_by": "2",
            "result": {"success": True, "message": "Alert status updated successfully", "status_code": 200},
            "copilot_ref": row.copilot_ref,
        },
    ]
    assert rec["status"] == "executed" and row.state == "executed" and row.outcome_posted_at is not None


def test_the_claim_is_posted_as_the_approver_with_copilots_ref():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id, user="1")  # admin proposed, ana approves
        await approve(client, "ana", rid)
        posts = [r for r in ctx.talon.requests if r.url.path.endswith("/outcome")]
        return posts, await row_of(ctx, rid)

    posts, row = call(scenario)
    claim = json.loads(posts[0].content)
    assert claim == {"thread_id": THREAD, "outcome": "approved", "decided_by": "2", "copilot_ref": row.copilot_ref}
    assert posts[0].headers["x-talon-user"] == "2" and posts[0].headers["x-talon-role"] == "analyst"
    assert posts[0].headers["x-talon-customers"] == ACME
    assert row.approver_user_id == 2 and row.copilot_ref.startswith("copilot-")


def test_a_comment_is_posted_as_written_and_signed_by_the_approver():
    raw = "<script>x</script> **not bold** [link](https://example.com)"

    async def scenario(client, ctx):
        rid = ctx.talon.add("comment_on_alert", alert_id=ctx.alert_id, args={"alert_id": ctx.alert_id, "comment": raw})
        response = await approve(client, "resp", rid)
        async with ctx.db.session() as session:
            comments = (await session.execute(select(Comment).where(Comment.alert_id == ctx.alert_id))).scalars().all()
        return response, [(c.comment, c.user_name) for c in comments]

    response, comments = call(scenario)
    assert response.status_code == 200 and comments == [(raw, "resp")]


def test_a_handler_refusal_is_reported_as_failed_with_its_status():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        with patch.object(
            incident_routes,
            "update_alert_status_endpoint",
            AsyncMock(side_effect=HTTPException(status_code=404, detail="Alert not found")),
        ):
            response = await approve(client, "ana", rid)
        return response, results(ctx.talon, rid)

    response, posted = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "failed"
    assert posted[0]["outcome"] == "failed" and posted[0]["result"] == {"success": False, "message": "Alert not found", "status_code": 404}


def test_an_unexpected_handler_error_is_a_fixed_text():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        with patch.object(incident_routes, "update_alert_status_endpoint", AsyncMock(side_effect=RuntimeError("SELECT secret FROM x"))):
            response = await approve(client, "ana", rid)
        return response, results(ctx.talon, rid)

    response, posted = call(scenario)
    assert posted[0]["result"] == {"success": False, "message": "the action failed in CoPilot", "status_code": 500}
    assert "secret" not in response.text


def test_quarantine_runs_through_its_route_and_audits_both_events():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="2")  # an analyst proposed it; a responder approves
        response = await approve(client, "resp", rid)
        async with ctx.db.session() as session:
            agent = (await session.execute(select(Agents).where(Agents.agent_id == "021"))).scalars().one()
        return response, ctx, agent.quarantined, rid

    response, ctx, quarantined, rid = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "executed"
    (sent,) = ctx.velociraptor.await_args_list
    body = sent.args[0]
    assert (body.hostname, body.velociraptor_id) == (HOST, VID) and quarantined is True
    (route_audit,) = ctx.quarantine_audit.await_args_list
    assert route_audit.kwargs["action"] == AuditAction.RESPONSE_QUARANTINE and route_audit.kwargs["actor_username"] == "resp"
    assert audit_actions(ctx) == [(AuditAction.TALON_ACTION_APPROVE, "success"), (AuditAction.TALON_ACTION_EXECUTE, "success")]
    for event in ctx.audit.await_args_list:
        kwargs = event.kwargs
        assert kwargs["customer_code"] == ACME and kwargs["entity_type"] == "talon_action" and kwargs["entity_id"] == rid
        assert kwargs["actor_user_id"] == 5
        value = kwargs["new_value"]
        assert value["action"] == "quarantine_host" and value["target"]["hostname"] == HOST
        assert value["requester_user_id"] == "2" and value["copilot_ref"].startswith("copilot-")


# ── the result: inline, then the job ──────────────────────────────────────────


def _failing_results(times, status=500):
    state = {"left": times}

    async def intercept(request):
        if request.url.path.endswith("/outcome") and json.loads(request.content)["outcome"] in ("executed", "failed") and state["left"] > 0:
            state["left"] -= 1
            if status is None:
                raise httpx.ConnectError("down")
            return httpx.Response(status, json={"detail": "busy"})
        return None

    return intercept


def test_the_result_is_tried_inline_three_times_then_by_the_job_with_the_same_body():
    async def scenario(client, ctx):
        ctx.talon.intercept = _failing_results(4, status=None)
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        response = await approve(client, "ana", rid)
        after_inline = await row_of(ctx, rid)
        early = await actions.run_outcome_job(now=sync.utcnow())  # not due yet
        first = await actions.run_outcome_job(now=sync.utcnow() + timedelta(minutes=2))  # fails once more
        mid = await row_of(ctx, rid)
        second = await actions.run_outcome_job(now=sync.utcnow() + timedelta(hours=1))
        again = await actions.run_outcome_job(now=sync.utcnow() + timedelta(hours=3))
        return (
            response,
            after_inline,
            early,
            first,
            mid,
            second,
            again,
            results(ctx.talon, rid),
            await row_of(ctx, rid),
            ctx.talon.records[rid],
        )

    response, after_inline, early, first, mid, second, again, posted, row, rec = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["outcome_reported"] is False
    assert after_inline.outcome_attempts == 3 and after_inline.next_attempt_at is not None and after_inline.state == "executed"
    assert early["retry"] == 0 and early["posted"] == 0
    assert first["retry"] == 1 and mid.outcome_attempts == 4
    assert mid.next_attempt_at - after_inline.next_attempt_at >= timedelta(minutes=1)  # backed off
    assert second["posted"] == 1 and again == {"posted": 0, "retry": 0, "stopped": 0, "done": 0}
    assert len(posted) == 5 and all(p == posted[0] for p in posted)  # the same result, the same ref
    assert row.outcome_posted_at is not None and row.next_attempt_at is None and rec["status"] == "executed"


def test_a_retried_result_talon_already_has_is_idempotent():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await approve(client, "ana", rid)
        # The answer to the first result was lost: CoPilot posts it again, talon-analyst says "recorded: false".
        await set_row(ctx, rid, outcome_posted_at=None, next_attempt_at=sync.utcnow())
        counts = await actions.run_outcome_job(now=sync.utcnow() + timedelta(minutes=1))
        return counts, results(ctx.talon, rid), await row_of(ctx, rid), ctx.talon.records[rid]

    counts, posted, row, rec = call(scenario)
    assert counts["posted"] == 1 and len(posted) == 2 and posted[0] == posted[1]
    assert row.outcome_posted_at is not None and rec["status"] == "executed"


def test_the_backoff_goes_from_a_minute_to_an_hour():
    assert [actions.backoff(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 20)] == [
        timedelta(minutes=1),
        timedelta(minutes=2),
        timedelta(minutes=4),
        timedelta(minutes=8),
        timedelta(minutes=16),
        timedelta(minutes=32),
        timedelta(hours=1),
        timedelta(hours=1),
        timedelta(hours=1),
    ]


def test_the_job_retries_a_minute_after_the_inline_tries_then_backs_off():
    minutes = [actions.retry_delay(n) / timedelta(minutes=1) for n in range(1, 12)]
    assert minutes == [1, 1, 1, 2, 4, 8, 16, 32, 60, 60, 60]


def test_a_recheck_that_cannot_be_made_runs_nothing():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        with patch.object(execution, "lock_and_recheck_host", AsyncMock(side_effect=RuntimeError("lock wait timeout"))):
            response = await approve(client, "resp", rid)
        return response, ctx.velociraptor.await_count, await row_of(ctx, rid), results(ctx.talon, rid)

    response, ran, row, posted = call(scenario)
    assert response.status_code == 200 and ran == 0 and row.state == "failed"
    assert posted[0]["result"]["message"] == "not run: the checks before the run could not be made"


def test_the_job_stops_at_talon_analysts_window():
    async def scenario(client, ctx):
        ctx.talon.intercept = _failing_results(3)
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await approve(client, "ana", rid)
        ctx.talon.intercept = None
        ctx.talon.records[rid]["decided_at"] = now() - timedelta(hours=25)  # talon-analyst's window has passed
        counts = await actions.run_outcome_job(now=sync.utcnow() + timedelta(minutes=5))
        later = await actions.run_outcome_job(now=sync.utcnow() + timedelta(hours=2))
        return counts, later, await row_of(ctx, rid), len(results(ctx.talon, rid))

    counts, later, row, posts = call(scenario)
    assert counts["stopped"] == 1 and row.state == "unreported" and row.next_attempt_at is None
    assert row.execution_result["success"] is True  # what happened stays on the record
    assert later["posted"] + later["retry"] + later["stopped"] == 0 and posts == 4


def test_the_job_stops_24_hours_after_the_approval():
    async def scenario(client, ctx):
        ctx.talon.intercept = _failing_results(100)
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await approve(client, "ana", rid)
        row = await row_of(ctx, rid)
        counts = await actions.run_outcome_job(now=row.talon_decided_at + timedelta(hours=24, minutes=1))
        return counts, await row_of(ctx, rid)

    counts, row = call(scenario)
    assert counts["stopped"] == 1 and row.state == "unreported" and row.last_outcome_error


@pytest.mark.parametrize("stale_state", ["claiming", "claimed", "executing"])
def test_rows_a_dead_request_left_are_settled_without_running_anything(stale_state):
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))
        if stale_state != "claiming":  # the claim landed
            rec = ctx.talon.records[rid]
            rec.update(status="approved", decided_by="5", decided_at=now(), copilot_ref="copilot-dead")
        await set_row(
            ctx,
            rid,
            state=stale_state,
            decision="approve",
            approver_user_id=5,
            approver_username="resp",
            decided_at=sync.utcnow() - timedelta(minutes=30),
            copilot_ref="copilot-dead",
            state_changed_at=sync.utcnow() - timedelta(minutes=30),
        )
        # The card keeps reading the record (as an open card polls): that doesn't keep it alive.
        await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))
        await actions.run_outcome_job()
        return await row_of(ctx, rid), ctx.velociraptor.await_count, results(ctx.talon, rid), ctx.talon.records[rid]

    row, ran, posted, rec = call(scenario)
    assert ran == 0
    if stale_state == "executing":
        # It may have run: nothing is claimed about it; talon-analyst tells the model "not reported".
        assert row.state == "unreported" and posted == []
    elif stale_state == "claimed":
        assert row.state == "failed" and posted[0]["result"]["message"] == "not run: CoPilot stopped before running it"
        assert rec["status"] == "failed"
    else:  # the claim's answer was lost with the request: never run, "failed" posted
        assert row.state == "claim_lost" and posted and posted[0]["outcome"] == "failed"


def test_a_row_whose_state_just_changed_is_not_stale_and_a_sync_does_not_touch_it():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))
        await set_row(ctx, rid, state="claimed", decision="approve", approver_user_id=5, updated_at=sync.utcnow() - timedelta(hours=2))
        before = (await row_of(ctx, rid)).state_changed_at
        await set_row(ctx, rid, state_changed_at=before)
        await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))  # a sync
        after_sync = (await row_of(ctx, rid)).state_changed_at
        await actions.run_outcome_job()
        return before, after_sync, await row_of(ctx, rid)

    before, after_sync, row = call(scenario)
    assert after_sync == before and row.state == "claimed"


def test_a_run_inside_velociraptors_flow_timeout_is_not_called_dead():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        await client.get(f"/talon/actions/{rid}", headers=as_user("resp"))
        await set_row(
            ctx,
            rid,
            state="executing",
            decision="approve",
            approver_user_id=5,
            state_changed_at=sync.utcnow() - timedelta(minutes=40),
        )
        with patch.object(actions, "FLOW_TIMEOUT_SECONDS", 3600):
            await actions.run_outcome_job()
            during = (await row_of(ctx, rid)).state
            await actions.run_outcome_job(now=sync.utcnow() + timedelta(hours=1))
        return during, (await row_of(ctx, rid)).state, actions.executing_stale_after()

    during, after, window = call(scenario)
    assert during == "executing" and after == "unreported"
    assert window == timedelta(minutes=15)  # the default flow timeout (300 s) + 5 min is shorter


def test_a_run_the_job_settled_meanwhile_keeps_its_outcome():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)

        async def slow_route(**kwargs):
            await set_row(ctx, rid, state="unreported")  # the job, while the route ran
            return SimpleNamespace(success=True, message="done late")

        with patch.object(incident_routes, "update_alert_status_endpoint", slow_route):
            await approve(client, "ana", rid)
        return await row_of(ctx, rid), results(ctx.talon, rid)

    row, posted = call(scenario)
    assert row.state == "unreported" and row.execution_result["message"] == "done late" and row.executed_at is not None
    assert posted == []


def test_a_claim_answer_for_another_proposal_runs_nothing():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")

        async def make(request):
            answer = await ctx.talon.default(request)
            payload = json.loads(answer.content)
            payload["args"] = {**payload["args"], "hostname": "SOMEONE-ELSE"}
            return httpx.Response(200, json=payload)

        ctx.talon.intercept = _claim_answer(make)
        response = await approve(client, "resp", rid)
        return response.status_code, ctx.velociraptor.await_count, await row_of(ctx, rid), results(ctx.talon, rid), audit_actions(ctx)

    status, ran, row, posted, audited = call(scenario)
    assert status == 502 and ran == 0 and row.state == "failed" and row.args["hostname"] == HOST
    assert posted[0]["result"]["message"] == "not run: talon-analyst's answer to the claim is not this proposal"
    assert audited == [(AuditAction.TALON_ACTION_APPROVE, "failure")]


@pytest.mark.parametrize("status, retried", [(404, True), (408, True), (429, True), (503, True), (401, True), (400, False), (422, False)])
def test_which_result_answers_are_retried(status, retried):
    async def scenario(client, ctx):
        ctx.talon.intercept = _failing_results(1, status=status)
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await approve(client, "ana", rid)
        return await row_of(ctx, rid)

    row = call(scenario)
    if retried:  # the inline retry got through
        assert row.state == "executed" and row.outcome_posted_at is not None
    else:
        assert row.state == "unreported" and row.outcome_posted_at is None


def test_the_job_audits_what_it_settles():
    async def scenario(client, ctx):
        ids = {}
        for decision in ("approve", "deny"):
            rid = ctx.talon.add(alert_id=ctx.alert_id)
            await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
            await set_row(
                ctx,
                rid,
                state="claiming",
                decision=decision,
                approver_user_id=2,
                approver_username="ana",
                copilot_ref=f"copilot-{decision}",
                state_changed_at=sync.utcnow() - timedelta(hours=1),
            )
            ids[decision] = rid
        await actions.run_outcome_job()
        events = {
            (c.kwargs["entity_id"], c.kwargs["action"], c.kwargs["result"].value, c.kwargs["actor_username"])
            for c in ctx.audit.await_args_list
        }
        return ids, events, await row_of(ctx, ids["deny"])

    ids, events, denied = call(scenario)
    assert (ids["approve"], AuditAction.TALON_ACTION_APPROVE, "failure", "ana") in events
    assert (ids["deny"], AuditAction.TALON_ACTION_DENY, "failure", "ana") in events
    assert denied.state == "pending"


def test_the_requesters_list_and_card_follow_their_current_tags():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id, user="2")  # ana's own proposal
        await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        async with ctx.db.session() as session:
            tag = AlertTag(tag="restricted")
            session.add_all([tag, TagAccessSettings(enabled=True, untagged_alert_behavior="visible_to_all")])
            await session.commit()
            session.add(AlertToTag(alert_id=ctx.alert_id, tag_id=tag.id))
            await session.commit()
        ctx.talon.lenient = True  # even if talon-analyst still showed it
        lists = [
            (await client.get(f"/talon/actions?scope={scope}", headers=as_user("ana"))).json()["actions"] for scope in ("pending", "mine")
        ]
        card = await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        return lists, card.status_code

    lists, card = call(scenario)
    assert lists == [[], []] and card == 404


# ── deny ──────────────────────────────────────────────────────────────────────


def test_deny_runs_nothing_and_is_audited():
    async def scenario(client, ctx):
        rid = ctx.talon.add("quarantine_host", user="5")
        response = await deny(client, "resp", rid)
        again = await approve(client, "admin", rid)
        return response, again.status_code, ctx.velociraptor.await_count, ctx.talon.records[rid], audit_actions(ctx), claims(ctx.talon, rid)

    response, again, ran, rec, audited, claimed = call(scenario)
    assert response.status_code == 200 and response.json()["action"]["state"] == "denied"
    assert again == 409 and ran == 0 and rec["status"] == "denied" and rec["decided_by"] == "5"
    assert audited == [(AuditAction.TALON_ACTION_DENY, "success")]
    assert [c["outcome"] for c in claimed] == ["denied"]


def test_deny_is_guarded_by_d47_too():
    async def scenario(client, ctx):
        ctx.talon.lenient = True
        rid = ctx.talon.add("quarantine_host", user="2")
        return (await deny(client, "ana", rid)).status_code, claims(ctx.talon)

    assert call(scenario) == (403, [])


def test_a_lost_denial_is_replayed_then_left_pending():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        seen = {"n": 0}

        async def intercept(request):
            if request.url.path.endswith("/outcome"):
                seen["n"] += 1
                if seen["n"] == 1:  # the first lands, its answer is lost; the replay says claimed: false
                    await ctx.talon.default(request)
                    raise httpx.ReadTimeout("lost")
            return None

        ctx.talon.intercept = intercept
        first = await deny(client, "ana", rid)
        rid2 = ctx.talon.add(alert_id=ctx.alert_id)

        async def down(request):
            if request.url.path.endswith("/outcome"):
                raise httpx.ConnectError("down")
            return None

        ctx.talon.intercept = down
        second = await deny(client, "ana", rid2)
        return first, second, await row_of(ctx, rid), await row_of(ctx, rid2), len(claims(ctx.talon, rid2))

    first, second, row, row2, tries = call(scenario)
    assert first.status_code == 200 and row.state == "denied"
    assert second.status_code == 502 and row2.state == "pending" and row2.copilot_ref is None and tries == 3


# ── withdraw and archive ──────────────────────────────────────────────────────


def test_only_the_requester_withdraws():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        other = await client.post(f"/talon/actions/{rid}/withdraw", headers=as_user("resp"))
        mine = await client.post(f"/talon/actions/{rid}/withdraw", headers=as_user("ana"))
        late = await approve(client, "resp", rid)
        return other.status_code, mine, late.status_code, ctx.talon.records[rid]["status"]

    other, mine, late, status = call(scenario)
    assert other == 404 and mine.status_code == 200 and mine.json()["action"]["state"] == "withdrawn"
    assert late == 409 and status == "withdrawn"


def test_archiving_a_thread_resyncs_its_pending_rows():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        response = await client.delete(f"/talon/v2/threads/{THREAD}", headers=as_user("ana"))
        await sync.wait_for_background()
        return response.status_code, await row_of(ctx, rid)

    status, row = call(scenario)
    assert status == 200 and row.state == "withdrawn" and row.talon_status == "withdrawn"


# ── the lists ─────────────────────────────────────────────────────────────────


def test_the_pending_list_shows_what_the_caller_may_decide_and_their_own():
    async def scenario(client, ctx):
        alert = ctx.talon.add(alert_id=ctx.alert_id, user="2")  # ana's
        host = ctx.talon.add("quarantine_host", user="5")  # resp's
        globex = ctx.talon.add(alert_id=ctx.globex_alert_id, customer=GLOBEX, user="7")
        for rid, name in ((alert, "ana"), (host, "resp"), (globex, "globex_ana")):
            await client.get(f"/talon/actions/{rid}", headers=as_user(name))
        lists = {}
        for name in ("ana", "resp", "admin", "globex_ana"):
            for scope in ("pending", "mine"):
                response = await client.get(f"/talon/actions?scope={scope}", headers=as_user(name))
                lists[(name, scope)] = {a["id"]: (a["can_decide"], a["is_requester"]) for a in response.json()["actions"]}
        return lists, alert, host, globex

    lists, alert, host, globex = call(scenario)
    assert lists[("ana", "pending")] == {alert: (True, True)}  # an analyst can't decide the quarantine
    assert lists[("resp", "pending")] == {alert: (True, False), host: (True, True)}
    assert lists[("admin", "pending")] == {alert: (True, False), host: (True, False), globex: (True, False)}
    assert lists[("globex_ana", "pending")] == {globex: (True, True)}
    assert lists[("ana", "mine")] == {alert: (True, True)} and lists[("resp", "mine")] == {host: (True, True)}
    assert lists[("admin", "mine")] == {}


def test_an_expired_proposal_is_shown_expired_and_cannot_be_approved():
    async def scenario(client, ctx):
        rid = ctx.talon.add(alert_id=ctx.alert_id)
        await client.get(f"/talon/actions/{rid}", headers=as_user("ana"))
        ctx.talon.records[rid]["expires_at"] = now() - timedelta(seconds=1)
        await set_row(ctx, rid, expires_at=sync.utcnow() - timedelta(seconds=1))
        listed = (await client.get("/talon/actions", headers=as_user("ana"))).json()["actions"]
        response = await approve(client, "ana", rid)
        return listed, response, claims(ctx.talon)

    listed, response, claimed = call(scenario)
    assert listed == [] and response.status_code == 409 and claimed == []
