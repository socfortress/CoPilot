"""CoPilot's Talon v2 routes: the setting, its gate, and the thread and chat proxy (plan M5-5a).

Real routers (``app.routers.talon``), a real in-memory database, real request parsing; token
decoding and user lookup are replaced (as in test_talon_connector_tenant_checks), and talon-analyst
is an ``httpx.MockTransport`` that records every request it gets.

Pinned here:
- the setting off: every proxy route answers 404 ``{"detail": "Not Found"}`` and nothing reaches
  talon-analyst; the availability route says so; the scope check still comes first;
- the setting: GET/PUT admin only, the PUT audited, and refused unless talon-analyst's
  ``GET /v2/threads`` answers 2xx (its 404 means its own ``TALON_V2_API`` is off);
- identity: a client's forged ``X-Talon-*`` headers never reach talon-analyst; it gets the user's own
  values, each exactly once, and none of the browser's other headers;
- threads: a customer the user lacks is a 403 with no upstream call, a malformed or unknown one a
  400; thread ids are UUIDs; answers and refusals pass through with their status;
- a thread's earlier turns (talon-analyst M5-5t): only ``limit`` and ``before`` are forwarded, a bad
  query or id is refused before talon-analyst, both 403s keep their fixed texts, and a page larger
  than the thread routes' cap still comes through;
- chat: CoPilot builds the ``SubmitMessage``; each pre-stream refusal keeps its status with a fixed
  text (never a 200, never a 401); each golden v2 stream (talon-analyst ``tests/contract/golden``,
  copied at talon-analyst ``5a2103e``) comes through byte for byte, keepalives included, with the
  stream's headers; the upstream connection is closed however the response ends: finished,
  refused, or the browser leaving.

Run with: cd backend && python -m pytest tests/test_talon_v2_proxy.py
"""

import asyncio
import json
import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_v2 as service  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "talon_v2"
GOLDEN = sorted(FIXTURES.glob("v2_*.txt"))
KEEPALIVE = b": keepalive\n\n"

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "resp": SimpleNamespace(id=5, username="resp", role_id=5),
    # An admin since demoted to analyst: the token issued before still carries the admin scope.
    "demoted": SimpleNamespace(id=4, username="demoted", role_id=2),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "resp": ["responder", "analyst"], "demoted": ["admin"]}
MINE, THEIRS = "ACME", "GLOBEX"
API_KEY = "connector-key"
CONNECTOR = {"connector_url": "http://talon.invalid", "connector_api_key": API_KEY, "connector_verified": True}
THREAD = str(uuid.UUID("0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"))
THREAD_BODY = {
    "id": THREAD,
    "title": "t",
    "customer_code": None,
    "status": "active",
    "created_at": "2026-10-16T08:00:00+00:00",
    "updated_at": "2026-10-16T08:00:00+00:00",
    "archived_at": None,
    "accessible": True,
}
FORGED = {
    "X-Talon-User": "1",
    "X-Talon-Role": "admin",
    "X-Talon-Customers": "*",
    "X-Talon-Tags": "*",
    "X-Talon-Untagged": "true",
    "x-api-key": "forged-key",
    "Cookie": "session=browser",
}
IDENTITY = ("x-talon-user", "x-talon-role", "x-talon-customers", "x-talon-tags", "x-talon-untagged")


class _Db(Db):
    async def create(self) -> "_Db":
        await super().create()
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[TalonConnectorSettings.__table__]))
        return self


class Upstream:
    """talon-analyst: answers with ``respond(request)`` and records every request and client."""

    def __init__(self, respond=None):
        self.respond = respond or (lambda request: httpx.Response(200, json={"threads": [], "next": None}))
        self.requests = []
        self.clients = []
        self.events = []  # ("session closed",) and ("upstream", path), in order

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.events.append(("upstream", request.url.path))
        return self.respond(request)

    def new_client(self, timeout):
        client = httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=timeout)
        self.clients.append(client)
        return client


class Chunks(httpx.AsyncByteStream):
    """An upstream body sent in the given pieces; records whether it was closed."""

    def __init__(self, pieces, hang_after=None, then=None):
        self.pieces = list(pieces)
        self.hang_after = hang_after
        self.then = then
        self.closed = False

    async def __aiter__(self):
        for n, piece in enumerate(self.pieces):
            if self.hang_after is not None and n == self.hang_after:
                if self.then is not None:  # a quiet turn: one keepalive later, then nothing
                    await asyncio.sleep(0.05)
                    yield self.then
                await asyncio.Event().wait()
            yield piece

    async def aclose(self):
        self.closed = True


def _app(db, *, copilot_handler=False, events=None):
    from app.routers import talon

    app = FastAPI()
    app.include_router(talon.router)
    if copilot_handler:
        # CoPilot's own handler shape for FastAPI's HTTPException (it also logs to the database).
        async def handler(request, exc):
            return JSONResponse({"success": False, "message": exc.detail}, status_code=exc.status_code)

        app.add_exception_handler(HTTPException, handler)

    async def _session():
        async with db.session() as session:
            if events is not None:
                close = session.close

                async def recorded_close():
                    events.append(("session closed",))
                    await close()

                session.close = recorded_close
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db, enabled):
    async with db.session() as session:
        session.add_all(
            [
                User(id=u.id, username=u.username, password="x" * 8, email=f"{u.username}@example.com", role_id=u.role_id)
                for u in USERS.values()
            ]
            + [Customers(customer_code=MINE, customer_name="Acme"), Customers(customer_code=THEIRS, customer_name="Globex")],
        )
        await session.commit()
        session.add_all([UserCustomerAccess(user_id=2, customer_code=MINE), UserCustomerAccess(user_id=5, customer_code=MINE)])
        if enabled is not None:
            session.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=enabled))
        await session.commit()


def call(scenario, *, enabled=True, upstream=None, copilot_handler=False, connector=CONNECTOR):
    """Run ``scenario(client, ctx)`` against the app; ``ctx`` has the upstream, db and audit mock."""
    upstream = upstream or Upstream()

    async def _inner():
        db = await _Db().create()
        try:
            await _seed(db, enabled)
            app = _app(db, copilot_handler=copilot_handler, events=upstream.events)

            async def resolve_user(self, request, username):
                return USERS.get(username)

            audit = AsyncMock()
            ctx = SimpleNamespace(upstream=upstream, db=db, audit=audit, app=app)
            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ), patch.object(v2_client, "_new_client", upstream.new_client), patch.object(
                v2_client,
                "_connector",
                AsyncMock(return_value=connector),
            ), patch.object(
                service,
                "record_audit_event",
                audit,
            ):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    return await scenario(client, ctx)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name, **extra):
    return {"Authorization": f"Bearer {name}", **extra}


def chat_body(message="hello", **extra):
    return {"message": message, **extra}


PROXY_ROUTES = [
    ("GET", "/talon/v2/threads", None),
    ("POST", "/talon/v2/threads", {"title": "x"}),
    ("PATCH", f"/talon/v2/threads/{THREAD}", {"title": "y"}),
    ("DELETE", f"/talon/v2/threads/{THREAD}", None),
    ("GET", f"/talon/v2/threads/{THREAD}/messages", None),
    ("POST", f"/talon/v2/chat/{THREAD}", {"message": "hi"}),
]


# ── the setting off ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("enabled", [None, False], ids=["no row", "off"])
def test_with_the_setting_off_every_proxy_route_is_not_found(enabled):
    async def scenario(client, ctx):
        answers = []
        for method, path, body in PROXY_ROUTES:
            response = await client.request(method, path, json=body, headers=as_user("ana"))
            answers.append((method, path, response.status_code, response.json()))
        return answers, ctx.upstream.requests

    answers, upstream_requests = call(scenario, enabled=enabled, copilot_handler=True)
    for method, path, status, body in answers:
        # Exactly what an unknown path answers, not CoPilot's {"success": false, …} shape.
        assert (status, body) == (404, {"detail": "Not Found"}), (method, path)
    assert upstream_requests == []


def test_with_the_setting_off_the_scope_check_still_comes_first():
    async def scenario(client, ctx):
        return [(await client.request(m, p, json=b)).status_code for m, p, b in PROXY_ROUTES]

    assert call(scenario, enabled=False) == [401] * len(PROXY_ROUTES)


def test_availability_follows_the_setting():
    async def scenario(client, ctx):
        return (await client.get("/talon/v2/availability", headers=as_user("ana"))).json()

    assert call(scenario, enabled=None)["enabled"] is False
    assert call(scenario, enabled=False)["enabled"] is False
    assert call(scenario, enabled=True)["enabled"] is True


def test_with_the_setting_on_the_proxy_routes_answer():
    async def scenario(client, ctx):
        return (await client.get("/talon/v2/threads", headers=as_user("ana"))).status_code

    assert call(scenario) == 200


# ── the setting itself ────────────────────────────────────────────────────────


def test_the_settings_are_admin_only():
    async def scenario(client, ctx):
        return [
            (await client.get("/talon/v2/settings", headers=as_user("ana"))).status_code,
            (await client.put("/talon/v2/settings", json={"v2_enabled": True}, headers=as_user("ana"))).status_code,
            (await client.put("/talon/v2/settings", json={"v2_enabled": True}, headers=as_user("resp"))).status_code,
            ctx.upstream.requests,
            ctx.audit.await_count,
        ]

    assert call(scenario, enabled=False) == [403, 403, 403, [], 0]


def test_a_demoted_admins_old_token_can_neither_read_nor_change_the_setting():
    async def scenario(client, ctx):
        statuses = [
            (await client.get("/talon/v2/settings", headers=as_user("demoted"))).status_code,
            (await client.put("/talon/v2/settings", json={"v2_enabled": True}, headers=as_user("demoted"))).status_code,
            (await client.put("/talon/v2/settings", json={"v2_enabled": False}, headers=as_user("demoted"))).status_code,
        ]
        enabled = (await client.get("/talon/v2/availability", headers=as_user("admin"))).json()["enabled"]
        return statuses, enabled, ctx.upstream.requests, ctx.audit.await_count

    assert call(scenario, enabled=True) == ([403, 403, 403], True, [], 0)


def test_turning_v2_on_checks_talon_analyst_with_the_admins_headers_and_is_audited():
    async def scenario(client, ctx):
        put = await client.put("/talon/v2/settings", json={"v2_enabled": True}, headers=as_user("admin"))
        got = await client.get("/talon/v2/settings", headers=as_user("admin"))
        return put, got, ctx

    put, got, ctx = call(scenario, enabled=None)
    assert put.status_code == 200 and put.json()["v2_enabled"] is True
    assert got.json()["v2_enabled"] is True and got.json()["updated_by_user_id"] == 1
    (probe,) = ctx.upstream.requests
    assert (probe.method, probe.url.path, probe.url.params.get("limit")) == ("GET", "/v2/threads", "1")
    assert probe.headers["x-talon-customers"] == "*" and probe.headers["x-talon-role"] == "admin"
    assert probe.headers["x-api-key"] == API_KEY
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["action"].value == "connector.update"
    assert audited.kwargs["actor_user_id"] == 1 and audited.kwargs["entity_id"] == "Talon"
    assert (audited.kwargs["old_value"], audited.kwargs["new_value"]) == ({"v2_enabled": False}, {"v2_enabled": True})
    assert "result" not in audited.kwargs  # record_audit_event's default: success


@pytest.mark.parametrize(
    "respond, status",
    [
        (lambda r: httpx.Response(404, json={"detail": "Not Found"}), 409),  # TALON_V2_API off there
        (lambda r: httpx.Response(401, json={"error": "Unauthorized"}), 502),  # a wrong API key: never a 401 here
        (lambda r: httpx.Response(400, json={"detail": "X-Talon-Tags is not a list of tag ids or *"}), 502),
        (lambda r: httpx.Response(500, text="boom"), 502),
        (lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")), 502),
    ],
    ids=["v2 off", "bad key", "bad header", "5xx", "unreachable"],
)
def test_turning_v2_on_is_refused_unless_talon_analyst_answers(respond, status):
    async def scenario(client, ctx):
        put = await client.put("/talon/v2/settings", json={"v2_enabled": True}, headers=as_user("admin"))
        avail = await client.get("/talon/v2/availability", headers=as_user("admin"))
        return put, avail, ctx

    put, avail, ctx = call(scenario, enabled=None, upstream=Upstream(respond))
    assert put.status_code == status
    assert avail.json()["enabled"] is False
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["result"].value == "failure"
    if status == 409:
        assert "TALON_V2_API" in put.json()["detail"]


def test_turning_v2_off_never_asks_talon_analyst_and_is_audited():
    async def scenario(client, ctx):
        put = await client.put("/talon/v2/settings", json={"v2_enabled": False}, headers=as_user("admin"))
        threads = await client.get("/talon/v2/threads", headers=as_user("admin"))
        return put, threads, ctx

    put, threads, ctx = call(scenario, enabled=True)
    assert put.status_code == 200 and put.json()["v2_enabled"] is False
    assert threads.status_code == 404
    assert ctx.upstream.requests == []
    (audited,) = ctx.audit.await_args_list
    assert (audited.kwargs["old_value"], audited.kwargs["new_value"]) == ({"v2_enabled": True}, {"v2_enabled": False})


def test_the_settings_body_takes_only_the_switch():
    async def scenario(client, ctx):
        return (
            await client.put("/talon/v2/settings", json={"v2_enabled": True, "connector_name": "x"}, headers=as_user("admin"))
        ).status_code

    assert call(scenario) == 422


# ── identity ──────────────────────────────────────────────────────────────────


def _assert_own_identity(request, user_id, role, customers):
    for name in IDENTITY:
        assert len(request.headers.get_list(name)) == 1, name
    assert request.headers["x-talon-user"] == user_id
    assert request.headers["x-talon-role"] == role
    assert request.headers["x-talon-customers"] == customers
    assert request.headers["x-talon-tags"] == "*" and request.headers["x-talon-untagged"] == "true"
    assert request.headers.get_list("x-api-key") == [API_KEY]
    assert "authorization" not in request.headers and "cookie" not in request.headers
    assert {name for name in request.headers if name.startswith("x-talon-")} == set(IDENTITY)


def test_a_forged_identity_never_reaches_talon_analyst():
    def respond(request):
        if request.url.path.startswith("/v2/chat/"):
            return httpx.Response(200, content=(FIXTURES / "v2_text.txt").read_bytes(), headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json={"threads": [], "next": None})

    async def scenario(client, ctx):
        await client.get("/talon/v2/threads", headers=as_user("ana", **FORGED))
        await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body(), headers=as_user("ana", **FORGED))
        return ctx.upstream.requests

    listed, chatted = call(scenario, upstream=Upstream(respond))
    for request in (listed, chatted):
        _assert_own_identity(request, "2", "analyst", MINE)


def test_a_responder_is_sent_as_a_responder():
    async def scenario(client, ctx):
        await client.get("/talon/v2/threads", headers=as_user("resp"))
        return ctx.upstream.requests

    (request,) = call(scenario)
    _assert_own_identity(request, "5", "responder", MINE)


# ── threads ───────────────────────────────────────────────────────────────────


def test_listing_passes_the_query_and_the_answer_through():
    page = {"threads": [THREAD_BODY], "next": "abc"}

    async def scenario(client, ctx):
        response = await client.get("/talon/v2/threads?status=all&limit=5&cursor=abc&user_id=9", headers=as_user("ana"))
        return response, ctx.upstream.requests

    response, (request,) = call(scenario, upstream=Upstream(lambda r: httpx.Response(200, json=page)))
    assert (response.status_code, response.json()) == (200, page)
    assert dict(request.url.params) == {"status": "all", "limit": "5", "cursor": "abc"}


def test_listing_refuses_a_bad_query_before_talon_analyst():
    async def scenario(client, ctx):
        statuses = [
            (await client.get(f"/talon/v2/threads?{q}", headers=as_user("ana"))).status_code
            for q in ("status=mine", "limit=0", "limit=201")
        ]
        return statuses, ctx.upstream.requests

    assert call(scenario) == ([422, 422, 422], [])


def test_a_thread_for_a_customer_the_user_lacks_is_refused_before_talon_analyst():
    async def scenario(client, ctx):
        responses = [
            await client.post("/talon/v2/threads", json={"customer_code": code}, headers=as_user("ana")) for code in (THEIRS, "NOPE")
        ]
        return [r.status_code for r in responses], ctx.upstream.requests

    assert call(scenario) == ([403, 403], [])


def test_a_malformed_or_unknown_customer_is_refused_before_talon_analyst():
    async def scenario(client, ctx):
        codes = ["", "a,b", "has space", "*", "NOPE", "acme"]  # "acme": MySQL would match ACME; talon-analyst wouldn't
        statuses = [
            (await client.post("/talon/v2/threads", json={"customer_code": c}, headers=as_user("admin"))).status_code for c in codes
        ]
        return statuses, ctx.upstream.requests

    assert call(scenario) == ([400] * 6, [])


def test_a_thread_body_takes_no_other_field():
    async def scenario(client, ctx):
        bodies = [{"title": "x", "user_id": "1"}, {"customer_code": ["ACME"]}, {"title": "x" * 201}]
        statuses = [(await client.post("/talon/v2/threads", json=b, headers=as_user("ana"))).status_code for b in bodies]
        return statuses, ctx.upstream.requests

    assert call(scenario) == ([422, 422, 422], [])


def test_creating_a_scoped_and_a_general_thread():
    created = {**THREAD_BODY, "customer_code": MINE}

    async def scenario(client, ctx):
        scoped = await client.post("/talon/v2/threads", json={"title": "mine", "customer_code": MINE}, headers=as_user("ana"))
        general = await client.post("/talon/v2/threads", json={}, headers=as_user("ana"))
        return scoped, general, ctx.upstream.requests

    scoped, general, (first, second) = call(scenario, upstream=Upstream(lambda r: httpx.Response(201, json=created)))
    assert (scoped.status_code, scoped.json()) == (201, created)
    assert general.status_code == 201
    assert json.loads(first.content) == {"title": "mine", "customer_code": MINE}
    assert json.loads(second.content) == {"title": None, "customer_code": None}
    assert (first.method, first.url.path) == ("POST", "/v2/threads")


def test_rename_and_archive_forward_a_uuid_thread_id():
    async def scenario(client, ctx):
        renamed = await client.patch(f"/talon/v2/threads/{THREAD}", json={"title": None}, headers=as_user("ana"))
        archived = await client.delete(f"/talon/v2/threads/{THREAD}", headers=as_user("ana"))
        bad = [
            (await client.patch("/talon/v2/threads/not-a-uuid", json={"title": "x"}, headers=as_user("ana"))).status_code,
            (await client.delete("/talon/v2/threads/..%2Fv2%2Fbudgets", headers=as_user("ana"))).status_code,
            (await client.patch(f"/talon/v2/threads/{THREAD}", json={}, headers=as_user("ana"))).status_code,
        ]
        return renamed, archived, bad, ctx.upstream.requests

    renamed, archived, bad, requests = call(scenario, upstream=Upstream(lambda r: httpx.Response(200, json=THREAD_BODY)))
    assert renamed.status_code == archived.status_code == 200
    assert bad[0] == 422 and bad[2] == 422 and bad[1] in (404, 422)
    assert [(r.method, r.url.path) for r in requests] == [("PATCH", f"/v2/threads/{THREAD}"), ("DELETE", f"/v2/threads/{THREAD}")]
    assert json.loads(requests[0].content) == {"title": None}


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (404, {"detail": "thread not found"}, (404, "thread not found")),
        (409, {"detail": "thread limit reached: archive a thread first"}, (409, "thread limit reached: archive a thread first")),
        (403, {"detail": "customer_code is not in X-Talon-Customers"}, (403, "customer_code is not in X-Talon-Customers")),
        (422, {"detail": "invalid request"}, (422, "invalid request")),
        (500, {"detail": "Traceback at /srv/talon"}, (500, "Talon request failed")),
        (401, {"error": "Unauthorized"}, (502, "Talon request failed")),
        (200, None, (502, "Talon request failed")),  # a 2xx that isn't JSON
    ],
)
def test_thread_refusals_keep_their_status_with_a_fixed_text(status, body, expected):
    def respond(request):
        return httpx.Response(status, json=body) if body is not None else httpx.Response(status, text="<html>")

    async def scenario(client, ctx):
        response = await client.post("/talon/v2/threads", json={}, headers=as_user("ana"))
        return response.status_code, response.json()

    assert call(scenario, upstream=Upstream(respond)) == (expected[0], {"detail": expected[1]})


def test_no_connector_or_no_answer_is_a_502():
    async def scenario(client, ctx):
        return (await client.get("/talon/v2/threads", headers=as_user("ana"))).status_code

    assert call(scenario, connector=None) == 502

    def unreachable(request):
        raise httpx.ConnectError("connect to 10.0.0.7:8000 refused")

    async def scenario_body(client, ctx):
        response = await client.get("/talon/v2/threads", headers=as_user("ana"))
        return response.status_code, response.text

    status, text = call(scenario_body, upstream=Upstream(unreachable))
    assert status == 502 and "10.0.0.7" not in text


# ── a thread's earlier turns (talon-analyst M5-5t) ──────────────────────────────

MESSAGES = f"/talon/v2/threads/{THREAD}/messages"
PAGE = {
    "thread": {**THREAD_BODY, "context_tokens": 1055},
    "messages": [
        {"id": "r1-user", "role": "user", "parts": [{"type": "text", "text": "hi", "state": "done"}], "metadata": {}},
        {
            "id": "r1-assistant",
            "role": "assistant",
            "parts": [{"type": "text", "text": "hello", "state": "done"}],
            "metadata": {"created_at": "2026-10-16T08:00:00+00:00", "status": "completed"},
        },
    ],
    "next": "WzQyXQ",
}


def test_messages_forward_only_limit_and_before_and_pass_the_page_through():
    async def scenario(client, ctx):
        first = await client.get(MESSAGES, headers=as_user("ana", **FORGED))
        older = await client.get(f"{MESSAGES}?limit=5&before=WzQyXQ&user_id=9&status=all", headers=as_user("ana"))
        return first, older, ctx.upstream.requests

    first, older, (plain, paged) = call(scenario, upstream=Upstream(lambda r: httpx.Response(200, json=PAGE)))
    assert (first.status_code, first.json()) == (200, PAGE)
    assert older.status_code == 200
    assert (plain.method, plain.url.path, dict(plain.url.params)) == ("GET", f"/v2/threads/{THREAD}/messages", {})
    assert dict(paged.url.params) == {"limit": "5", "before": "WzQyXQ"}
    _assert_own_identity(plain, "2", "analyst", MINE)


def test_messages_refuse_a_bad_query_or_id_before_talon_analyst():
    async def scenario(client, ctx):
        paths = [
            f"{MESSAGES}?limit=0",
            f"{MESSAGES}?limit=101",
            f"{MESSAGES}?before=",
            f"{MESSAGES}?before={'x' * 65}",
            "/talon/v2/threads/not-a-uuid/messages",
        ]
        statuses = [(await client.get(path, headers=as_user("ana"))).status_code for path in paths]
        return statuses, ctx.upstream.requests

    assert call(scenario) == ([422] * 5, [])


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (403, {"detail": "access to this thread's customer was removed"}, (403, "access to this thread's customer was removed")),
        (
            403,
            {"detail": "your alert access changed since this thread began; start a new thread"},
            (403, "your alert access changed since this thread began; start a new thread"),
        ),
        (404, {"detail": "thread not found"}, (404, "thread not found")),
        (400, {"detail": "invalid cursor"}, (400, "invalid cursor")),
        (503, {"detail": "the thread's messages are busy; try again shortly"}, (503, "Talon request failed")),
        (401, {"error": "Unauthorized"}, (502, "Talon request failed")),
    ],
    ids=["customer removed", "tags narrowed", "not found", "bad cursor", "busy", "bad key"],
)
def test_messages_refusals_keep_their_status_with_a_fixed_text(status, body, expected):
    async def scenario(client, ctx):
        response = await client.get(MESSAGES, headers=as_user("ana"))
        return response.status_code, response.json()

    assert call(scenario, upstream=Upstream(lambda r: httpx.Response(status, json=body))) == (expected[0], {"detail": expected[1]})


def test_a_messages_page_over_the_thread_routes_cap_still_comes_through():
    big = {**PAGE, "messages": [{**PAGE["messages"][1], "parts": [{"type": "text", "text": "é" * 900_000, "state": "done"}]}]}

    async def scenario(client, ctx):
        response = await client.get(MESSAGES, headers=as_user("ana"))
        return response.status_code, response.json()

    assert len(json.dumps(big, ensure_ascii=False).encode()) > v2_client.MAX_JSON_BODY_BYTES
    assert call(scenario, upstream=Upstream(lambda r: httpx.Response(200, json=big))) == (200, big)

    huge = {**PAGE, "messages": [{**PAGE["messages"][1], "parts": [{"type": "text", "text": "x" * (5 * 1024 * 1024)}]}]}
    status, _ = call(scenario, upstream=Upstream(lambda r: httpx.Response(200, json=huge)))
    assert status == 502


# ── never cached ──────────────────────────────────────────────────────────────


def test_every_v2_json_answer_is_no_store_and_relayed_as_sent():
    # Upstream spacing and key order kept: the bytes are relayed, not re-encoded.
    raw = b'{ "threads" : [ ], "next" : null , "z": 1, "a": "\\u00e9" }'

    def respond(request):
        if request.url.path.endswith("/messages") and "before" in request.url.params:
            return httpx.Response(403, json={"detail": "access to this thread's customer was removed"})
        if request.method == "POST":
            return httpx.Response(201, json=THREAD_BODY)
        return httpx.Response(200, content=raw, headers={"content-type": "application/json"})

    async def scenario(client, ctx):
        return {
            "list": await client.get("/talon/v2/threads", headers=as_user("admin")),
            "create": await client.post("/talon/v2/threads", json={}, headers=as_user("admin")),
            "rename": await client.patch(f"/talon/v2/threads/{THREAD}", json={"title": "x"}, headers=as_user("admin")),
            "archive": await client.delete(f"/talon/v2/threads/{THREAD}", headers=as_user("admin")),
            "messages": await client.get(MESSAGES, headers=as_user("admin")),
            "messages 403": await client.get(f"{MESSAGES}?before=WzQyXQ", headers=as_user("admin")),
            "availability": await client.get("/talon/v2/availability", headers=as_user("admin")),
            "settings": await client.get("/talon/v2/settings", headers=as_user("admin")),
            "settings put": await client.put("/talon/v2/settings", json={"v2_enabled": False}, headers=as_user("admin")),
        }

    answers = call(scenario, upstream=Upstream(respond))
    for name, response in answers.items():
        assert response.status_code < 500, name
        assert response.headers["cache-control"] == "no-store", name
        assert response.headers["content-type"].startswith("application/json"), name
    assert answers["list"].content == raw
    assert answers["messages"].content == raw
    assert answers["messages 403"].status_code == 403


def test_a_2xx_that_isnt_json_is_still_a_no_store_502():
    async def scenario(client, ctx):
        return await client.get(MESSAGES, headers=as_user("ana"))

    response = call(scenario, upstream=Upstream(lambda r: httpx.Response(200, text="<html>")))
    assert (response.status_code, response.json()) == (502, {"detail": "Talon request failed"})
    assert response.headers["cache-control"] == "no-store"


# ── chat ──────────────────────────────────────────────────────────────────────


def _stream_upstream(content=b"data: [DONE]\n\n", status=200, record=None):
    def respond(request):
        if record is not None:
            record.append(json.loads(request.content))
        return httpx.Response(status, content=content, headers={"content-type": "text/event-stream"})

    return Upstream(respond)


def test_copilot_builds_the_submit_message():
    bodies = []

    async def scenario(client, ctx):
        await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body("what changed?", message_id="msg-1"), headers=as_user("ana"))
        await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body(""), headers=as_user("ana"))  # M5-11's resume
        return ctx.upstream.requests

    first, second = call(scenario, upstream=_stream_upstream(record=bodies))
    assert bodies[0] == {
        "trigger": "submit-message",
        "id": THREAD,
        "messages": [{"id": "msg-1", "role": "user", "parts": [{"type": "text", "text": "what changed?"}]}],
    }
    (message,) = bodies[1]["messages"]
    assert message["parts"] == [{"type": "text", "text": ""}] and message["role"] == "user" and message["id"]
    assert (first.method, first.url.path) == ("POST", f"/v2/chat/{THREAD}")
    assert first.headers["content-type"] == "application/json"
    assert first.headers["accept"] == "text/event-stream"


def test_the_browser_never_sends_the_submit_message_itself():
    async def scenario(client, ctx):
        bodies = [
            {"trigger": "submit-message", "id": THREAD, "messages": []},
            {"message": "hi", "messages": [{"role": "assistant", "parts": []}]},
            {"message": "hi", "message_id": "bad id with spaces"},
            {},
        ]
        statuses = [(await client.post(f"/talon/v2/chat/{THREAD}", json=b, headers=as_user("ana"))).status_code for b in bodies]
        statuses.append((await client.post("/talon/v2/chat/not-a-uuid", json=chat_body(), headers=as_user("ana"))).status_code)
        return statuses, ctx.upstream.requests

    assert call(scenario) == ([422] * 5, [])


PRE_STREAM = [
    (400, {"detail": "the newest message must be the user's, with text"}),
    (403, {"detail": "this thread's customer is no longer yours"}),
    (404, {"detail": "thread not found"}),
    (409, {"detail": "an action in this thread is waiting for a decision in CoPilot"}),
    (409, {"detail": "this thread is archived"}),
    (413, {"detail": "the request body is too large"}),
    (415, {"detail": "Content-Type must be application/json"}),
    (422, {"detail": "invalid request"}),
]


@pytest.mark.parametrize("status, body", PRE_STREAM, ids=[f"{s}-{b['detail'][:20]}" for s, b in PRE_STREAM])
def test_a_refusal_before_the_stream_keeps_its_status_and_text(status, body):
    async def scenario(client, ctx):
        response = await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body(), headers=as_user("ana"))
        return response, ctx.upstream.clients

    response, clients = call(scenario, upstream=Upstream(lambda r: httpx.Response(status, json=body)))
    assert (response.status_code, response.json()) == (status, body)
    assert response.headers["content-type"].startswith("application/json")
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize(
    "respond, status",
    [
        (lambda r: httpx.Response(500, json={"detail": "Traceback: secret at /srv/talon"}), 500),
        (lambda r: httpx.Response(503, text="<html>busy</html>"), 503),
        (lambda r: httpx.Response(400, json={"detail": "line one\nline two"}), 400),
        (lambda r: httpx.Response(422, json={"detail": [{"loc": ["body"], "msg": "x"}]}), 422),
        (lambda r: httpx.Response(401, json={"error": "Unauthorized"}), 502),
        (lambda r: httpx.Response(302, headers={"location": "http://elsewhere"}), 502),
        (lambda r: (_ for _ in ()).throw(httpx.ConnectError("connect to 10.0.0.7:8000 refused")), 502),
    ],
    ids=["500", "503", "multi-line", "structured", "401", "redirect", "unreachable"],
)
def test_any_other_failure_gets_the_fixed_text_never_a_200(respond, status):
    async def scenario(client, ctx):
        response = await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body(), headers=as_user("ana"))
        return response, ctx.upstream.clients

    response, clients = call(scenario, upstream=Upstream(respond))
    assert (response.status_code, response.json()) == (status, {"detail": "Talon request failed"})
    assert "secret" not in response.text and "10.0.0.7" not in response.text
    assert all(client.is_closed for client in clients)


def _with_keepalives(wire: bytes) -> bytes:
    """The stream with a keepalive comment between every two chunks, as a quiet turn sends."""
    blocks = wire.split(b"\n\n")
    assert blocks[-1] == b""
    return b"".join(block + b"\n\n" + KEEPALIVE for block in blocks[:-1])


@pytest.mark.parametrize("fixture", GOLDEN, ids=[path.stem for path in GOLDEN])
@pytest.mark.parametrize("keepalives", [False, True], ids=["plain", "keepalives"])
def test_each_golden_stream_comes_through_byte_for_byte(fixture, keepalives):
    wire = fixture.read_bytes()
    if keepalives:
        wire = _with_keepalives(wire)
    # Odd-sized pieces, so nothing on the way may rely on chunks lining up with events.
    pieces = [wire[i : i + 7] for i in range(0, len(wire), 7)]
    streams = []

    def respond(request):
        stream = Chunks(pieces)
        streams.append(stream)
        return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream; charset=utf-8"})

    async def scenario(client, ctx):
        response = await client.post(f"/talon/v2/chat/{THREAD}", json=chat_body(), headers=as_user("ana"))
        return response, ctx.upstream.clients

    response, clients = call(scenario, upstream=Upstream(respond))
    assert response.status_code == 200
    assert response.content == wire
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    # The stream ended: its upstream was closed.
    assert [s.closed for s in streams] == [True] and all(c.is_closed for c in clients)


def test_the_golden_fixtures_are_all_here():
    assert [p.name for p in GOLDEN] == ["v2_approval.txt", "v2_error.txt", "v2_text.txt", "v2_tool.txt"]
    for path in GOLDEN:
        assert path.read_bytes().endswith(b"data: [DONE]\n\n")


def test_every_proxy_route_closes_its_db_session_before_calling_talon_analyst():
    def respond(request):
        if request.url.path.startswith("/v2/chat/"):
            return httpx.Response(200, content=b"data: [DONE]\n\n", headers={"content-type": "text/event-stream"})
        status = 201 if request.method == "POST" else 200
        return httpx.Response(status, json=THREAD_BODY)

    routes = [
        ("GET", "/talon/v2/threads", None),
        ("POST", "/talon/v2/threads", {"title": "x", "customer_code": MINE}),
        ("PATCH", f"/talon/v2/threads/{THREAD}", {"title": "y"}),
        ("DELETE", f"/talon/v2/threads/{THREAD}", None),
        ("GET", f"/talon/v2/threads/{THREAD}/messages", None),
        ("POST", f"/talon/v2/chat/{THREAD}", {"message": "hi"}),
    ]

    async def scenario(client, ctx):
        found = []
        for method, path, body in routes:
            ctx.upstream.events.clear()
            response = await client.request(method, path, json=body, headers=as_user("ana"))
            assert response.status_code < 300, (method, path, response.status_code)
            upstream_at = next(n for n, event in enumerate(ctx.upstream.events) if event[0] == "upstream")
            found.append((method, path, ("session closed",) in ctx.upstream.events[:upstream_at]))
        return found

    for method, path, closed_first in call(scenario, upstream=Upstream(respond)):
        assert closed_first, (method, path)


# ── a browser that leaves ─────────────────────────────────────────────────────


def _asgi_chat(app, receive_disconnect, send_fails_after=None, spec_version="2.3"):
    """Drive one chat request at the ASGI level, so the client can leave mid-stream."""
    body = json.dumps(chat_body()).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": spec_version},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"/talon/v2/chat/{THREAD}",
        "raw_path": f"/talon/v2/chat/{THREAD}".encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"authorization", b"Bearer ana"), (b"content-type", b"application/json"), (b"host", b"copilot")],
        "client": ("127.0.0.1", 1),
        "server": ("copilot", 80),
    }
    sent = []
    first_body = asyncio.Event()
    state = {"requested": False}

    async def receive():
        if not state["requested"]:
            state["requested"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        if receive_disconnect:
            await first_body.wait()
            return {"type": "http.disconnect"}
        await asyncio.Event().wait()

    async def send(message):
        if message["type"] == "http.response.body" and message.get("body"):
            if send_fails_after is not None and len([m for m in sent if m.get("body")]) >= send_fails_after:
                raise OSError("the browser went away")
            first_body.set()
        sent.append(message)

    async def run():
        try:
            await asyncio.wait_for(app(scope, receive, send), timeout=5)
        except Exception as e:  # noqa: BLE001 - a ClientDisconnect is how spec 2.4 reports it
            return sent, e
        return sent, None

    return run()


@pytest.mark.parametrize("spec_version, how", [("2.3", "disconnect"), ("2.4", "send fails")])
def test_a_browser_that_leaves_closes_the_upstream(spec_version, how):
    first = b'data: {"type":"start"}\n\n'
    streams = []

    def respond(request):
        # One chunk, then a quiet turn (a keepalive later), then nothing: only the browser leaving ends it.
        stream = Chunks([first, b"never sent"], hang_after=1, then=KEEPALIVE)
        streams.append(stream)
        return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream"})

    async def scenario(client, ctx):
        sent, error = await _asgi_chat(
            ctx.app,
            receive_disconnect=how == "disconnect",
            send_fails_after=1 if how == "send fails" else None,
            spec_version=spec_version,
        )
        return sent, error, ctx.upstream.clients

    sent, error, clients = call(scenario, upstream=Upstream(respond))
    assert not isinstance(error, asyncio.TimeoutError), "the response never ended"
    assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 200
    assert [m["body"] for m in sent if m.get("body")] == [first]
    assert [s.closed for s in streams] == [True]
    assert all(client.is_closed for client in clients)


def test_v1_message_route_is_untouched_by_the_setting():
    """The v1 chat proxy answers as before whatever the setting (its own tests are unchanged)."""

    async def scenario(client, ctx):
        async def stream(*args, **kwargs):
            yield b'data: {"type":"done"}\n\n'

        with patch("app.connectors.talon.services.talon.send_post_request_sse", stream):
            response = await client.post("/talon/message", json={"message": "hi"}, headers=as_user("ana"))
        return response, ctx.upstream.requests

    for enabled in (None, False, True):
        response, upstream_requests = call(scenario, enabled=enabled)
        assert response.status_code == 200 and response.content == b'data: {"type":"done"}\n\n'
        assert upstream_requests == []
