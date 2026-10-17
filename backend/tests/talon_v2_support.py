"""Shared fixtures for the Talon v2 usage, budgets and run view tests (plan M5-9a). Not collected by pytest.

Real routers (``app.routers.talon``), a real in-memory database, real request parsing; token decoding
and user lookup are replaced (as in ``test_talon_v2_proxy``). talon-analyst and Phoenix are each an
``httpx.MockTransport`` that records every request it gets. Phoenix's transport is plugged in under
the real Phoenix client (``phoenix_client._transport``), so the client's own settings (its GET-only
hook, no redirects, no proxy) are the ones under test.
"""

import asyncio
import functools
import gzip
import json
import os
from contextlib import ExitStack
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_usage  # noqa: E402
from app.connectors.talon.utils import phoenix_client  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402

ACME, GLOBEX, DOTTED, CHAT = "ACME", "GLOBEX", "acme.io", "chat"
#: name -> (user id, role id, token scopes, customers)
USERS = {
    "admin": (1, 1, ["admin"], []),
    "ana": (2, 2, ["analyst"], [ACME, DOTTED, CHAT]),
    "resp": (5, 5, ["responder", "analyst"], [ACME]),
    # An admin since demoted to analyst: the token issued before still carries the admin scope.
    "demoted": (4, 2, ["admin"], [ACME]),
    "gus": (6, 2, ["analyst"], [GLOBEX]),
    "portal": (7, 4, ["customer_user"], [ACME]),
    "sched": (8, 3, ["scheduler"], []),
}
TALON_KEY = "talon-connector-key"
TALON_CONNECTOR = {"connector_url": "http://talon.invalid", "connector_api_key": TALON_KEY, "connector_verified": True}
PHOENIX_URL = "http://phoenix-secret-host.invalid:6006"
PHOENIX_KEY = "phx-viewer-key-SECRET-0123456789"
UPDATED = datetime(2026, 10, 16, 7, 0, 0)
CREATED = datetime(2026, 10, 16, 8, 0, 0)
COMPLETED = datetime(2026, 10, 16, 8, 5, 30)

JOB_ACME = "copilot-inv-1-1760601600000"
JOB_GLOBEX = "copilot-inv-2-1760601600001"
JOB_DOTTED = "copilot-inv-3-1760601600002"
JOB_CHAT = "copilot-inv-4-1760601600003"
JOB_MISMATCH = "copilot-inv-2-1760601600004"  # says ACME, its alert is GLOBEX's
JOB_RUNNING = "copilot-inv-1-1760601600005"  # not completed yet


def phoenix_connector(**overrides):
    attributes = {
        "connector_name": "Talon Phoenix",
        "connector_url": PHOENIX_URL,
        "connector_api_key": PHOENIX_KEY,
        "connector_last_updated": UPDATED,
        "connector_verified": True,
    }
    attributes.update(overrides)
    return attributes


class _Db(Db):
    async def create(self) -> "_Db":
        await super().create()
        tables = [TalonConnectorSettings.__table__, AiAnalystJob.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self


class Upstream:
    """talon-analyst: answers with ``respond(request)`` and records every request."""

    def __init__(self, respond=None):
        self.respond = respond or (lambda request: httpx.Response(200, json={"ok": True}))
        self.requests = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.respond(request)

    def new_client(self, timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=timeout)


def span(job_id=JOB_ACME, customer=ACME, *, n=0, **extra):
    """One Phoenix 20.20 ``getSpans`` span (``routers/v1/spans.py:Span``), attributes flattened."""
    attributes = {
        "job_id": job_id,
        "customer_code": customer,
        "stage": "S5",
        "role": "analyst",
        "llm.model_name": "claude-sonnet-5-5",
        "llm.token_count.prompt": 1200 + n,
        "llm.token_count.completion": 300,
        "llm.token_count.total": 1500 + n,
    }
    attributes.update(extra.pop("attributes", {}))
    body = {
        "id": f"U3BhbjE{n}",
        "name": "chat claude-sonnet-5-5",
        "context": {"trace_id": f"{n:032x}", "span_id": f"{n + 1:016x}"},
        "span_kind": "LLM",
        "parent_id": None,
        "start_time": f"2026-10-16T08:00:{n % 60:02d}.000000+00:00",
        "end_time": f"2026-10-16T08:01:{n % 60:02d}.500000+00:00",
        "status_code": "OK",
        "status_message": "",
        "attributes": attributes,
        "events": [],
    }
    body.update(extra)
    return body


class Phoenix:
    """Phoenix 20.20's REST API as far as CoPilot reads it. Every request it sees must be a GET."""

    def __init__(self, *, role="VIEWER", pages=None, projects=(f"talon-{ACME}", f"talon-{GLOBEX}")):
        self.role = role
        self.pages = pages if pages is not None else [[span()]]
        self.projects = set(projects)
        self.requests = []
        self.user_answer = None  # an httpx.Response to give /v1/user instead
        self.spans_answer = None  # a callable(request, page_index) -> httpx.Response, instead
        self.gate = None  # an asyncio.Event a spans request waits for

    async def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET", f"Phoenix got a {request.method}"
        self.requests.append(request)
        path = request.url.path
        if path == "/v1/user":
            if self.user_answer is not None:
                return self.user_answer
            data = (
                {"auth_method": "ANONYMOUS"}
                if self.role is None
                else {"id": "VXNlcjo3", "username": "copilot-viewer", "role": self.role, "auth_method": "LOCAL"}
            )
            return httpx.Response(200, json={"data": data})
        if path.startswith("/v1/projects/") and path.endswith("/spans"):
            project = path[len("/v1/projects/") : -len("/spans")]
            if self.gate is not None:
                await self.gate.wait()
            if project not in self.projects:
                return httpx.Response(404, json={"detail": f"Project with name {project} not found"})
            cursor = request.url.params.get("cursor")
            index = 0 if cursor is None else int(cursor.removeprefix("c"))
            if self.spans_answer is not None:
                return self.spans_answer(request, index)
            data = self.pages[index] if index < len(self.pages) else []
            next_cursor = f"c{index + 1}" if index + 1 < len(self.pages) else None
            return httpx.Response(200, json={"data": data, "next_cursor": next_cursor})
        return httpx.Response(404, json={"detail": "Not Found"})

    def span_requests(self):
        return [r for r in self.requests if r.url.path.endswith("/spans")]

    def user_requests(self):
        return [r for r in self.requests if r.url.path == "/v1/user"]


async def _seed(db, enabled):
    async with db.session() as session:
        session.add_all([Customers(customer_code=code, customer_name=code) for code in (ACME, GLOBEX, DOTTED, CHAT)])
        session.add_all(
            [
                User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role)
                for name, (uid, role, _, _) in USERS.items()
            ],
        )
        await session.commit()
        for name, (uid, _, _, customers) in USERS.items():
            session.add_all([UserCustomerAccess(user_id=uid, customer_code=code) for code in customers])
        if enabled is not None:
            session.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=enabled))
        acme = await add_alert(session, customer=ACME, name="ACME alert")
        globex = await add_alert(session, customer=GLOBEX, name="GLOBEX alert")
        dotted = await add_alert(session, customer=DOTTED, name="dotted alert")
        chat = await add_alert(session, customer=CHAT, name="chat alert")
        jobs = [
            (JOB_ACME, acme.id, ACME, COMPLETED),
            (JOB_GLOBEX, globex.id, GLOBEX, COMPLETED),
            (JOB_DOTTED, dotted.id, DOTTED, COMPLETED),
            (JOB_CHAT, chat.id, CHAT, COMPLETED),
            (JOB_MISMATCH, globex.id, ACME, COMPLETED),
            (JOB_RUNNING, acme.id, ACME, None),
        ]
        session.add_all(
            [
                AiAnalystJob(
                    id=jid,
                    alert_id=alert_id,
                    customer_code=code,
                    status="completed",
                    triggered_by="manual",
                    created_at=CREATED,
                    completed_at=done,
                )
                for jid, alert_id, code, done in jobs
            ],
        )
        await session.commit()
        return SimpleNamespace(acme_alert=acme.id, globex_alert=globex.id)


async def restrict_tags(ctx, alert_id):
    """Tag RBAC on, and the alert given a tag nobody is granted."""
    async with ctx.db.session() as session:
        tag = AlertTag(tag="restricted")
        session.add_all([tag, TagAccessSettings(enabled=True, untagged_alert_behavior="visible_to_all")])
        await session.commit()
        session.add(AlertToTag(alert_id=alert_id, tag_id=tag.id))
        await session.commit()


def _app(db):
    from app.routers import talon

    app = FastAPI()
    app.include_router(talon.router)

    async def handler(request, exc):  # CoPilot's own shape for FastAPI's HTTPException
        return JSONResponse({"success": False, "message": exc.detail}, status_code=exc.status_code)

    app.add_exception_handler(HTTPException, handler)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


def call(scenario, *, enabled=True, upstream=None, phoenix=None, connector="default"):
    """Run ``scenario(client, ctx)``. ``ctx``: upstream, phoenix, db, audit, the seeded ids."""
    upstream = upstream or Upstream()
    phoenix = phoenix or Phoenix()
    attributes = phoenix_connector() if connector == "default" else connector

    async def _inner():
        db = await _Db().create()
        try:
            ctx = await _seed(db, enabled)
            ctx.upstream, ctx.phoenix, ctx.db = upstream, phoenix, db
            ctx.audit = AsyncMock()
            ctx.phoenix_attributes = AsyncMock(return_value=attributes)
            app = _app(db)

            async def resolve_user(self, request, username):
                if username not in USERS:
                    return None
                uid, role, _, _ = USERS[username]
                return SimpleNamespace(id=uid, username=username, role_id=role)

            @asynccontextmanager
            async def own_session():
                async with db.session() as session:
                    yield session

            phoenix_client.clear_role_cache()
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(AuthHandler, "decode_token", lambda self, token: (token, USERS.get(token, (0, 0, [], []))[2])),
                )
                stack.enter_context(patch.object(AuthHandler, "_resolve_user", resolve_user))
                stack.enter_context(patch.object(v2_client, "_new_client", upstream.new_client))
                stack.enter_context(patch.object(v2_client, "_connector", AsyncMock(return_value=TALON_CONNECTOR)))
                stack.enter_context(patch.object(phoenix_client, "_transport", lambda: httpx.MockTransport(phoenix.handler)))
                stack.enter_context(patch.object(phoenix_client, "_connector_attributes", ctx.phoenix_attributes))
                stack.enter_context(patch.object(talon_usage, "record_audit_event", ctx.audit))
                stack.enter_context(patch.object(talon_usage, "get_db_session", own_session))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    return await scenario(client, ctx)
        finally:
            phoenix_client.clear_role_cache()
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name, **extra):
    return {"Authorization": f"Bearer {name}", **extra}


def body_of(response):
    return json.loads(response.content)


#: Every route M5-9a adds, with a request that would otherwise be accepted.
NEW_ROUTES = [
    ("GET", "/talon/v2/usage?from=2026-10-01&to=2026-10-16", None),
    ("GET", f"/talon/v2/usage/investigations/{JOB_ACME}", None),
    ("GET", "/talon/v2/usage/threads/0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e", None),
    ("GET", "/talon/v2/budgets", None),
    ("PUT", f"/talon/v2/budgets/{ACME}", {"daily_usd": "25", "monthly_usd": None}),
    ("GET", f"/talon/v2/runs/{JOB_ACME}/timeline", None),
]


class RawStream(httpx.AsyncByteStream):
    """A body as a network transport hands it over: raw bytes, never pre-read by httpx (so its
    ``Content-Encoding`` would be decoded as it is read). ``forever`` dribbles ``data`` for ever,
    one chunk each ``delay`` seconds."""

    def __init__(self, data: bytes, *, chunk: int = 65536, delay: float = 0.0, forever: bool = False):
        self.data, self.chunk, self.delay, self.forever = data, chunk, delay, forever
        self.sent = 0

    async def __aiter__(self):
        while True:
            for start in range(0, len(self.data), self.chunk):
                if self.delay:
                    await asyncio.sleep(self.delay)
                piece = self.data[start : start + self.chunk]
                self.sent += len(piece)
                yield piece
            if not self.forever:
                return

    async def aclose(self):
        pass


@functools.lru_cache(maxsize=1)
def stacked_gzip(size: int = 64 * 1024 * 1024) -> bytes:
    """``size`` bytes of zeros, gzipped twice: a few hundred bytes on the wire. Made once."""
    return gzip.compress(gzip.compress(b"0" * size, compresslevel=9), compresslevel=9)


def bomb_response(status: int = 200, encoding: str = "gzip, gzip") -> httpx.Response:
    return httpx.Response(
        status,
        headers={"content-encoding": encoding, "content-type": "application/json"},
        stream=RawStream(stacked_gzip()),
    )


def deeply_nested(depth: int = 100_000) -> bytes:
    """JSON that ``json.loads`` can't parse without passing the recursion limit."""
    return b'{"data": ' + b"[" * depth + b"]" * depth + b', "next_cursor": null}'
