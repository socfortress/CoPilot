"""The Talon Memory tab's backend, ``/api/talon/memory/...`` (``services/talon_memory.py``).

Real routers, a real in-memory database (``talon_v2_support``), talon-analyst's ``/v2/memory`` API as
an ``httpx.MockTransport`` plugged in under the real memory client (its 8 s deadline, capped reads,
no redirects, no proxy). No network.
"""
import asyncio
import gzip
import hashlib
import json
import re
import ssl
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch
from urllib.parse import quote

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.auth.utils import AuthHandler
from app.connectors.talon.services import talon_memory
from app.connectors.talon.utils import memory_client
from tests.talon_v2_support import ACME
from tests.talon_v2_support import CHAT
from tests.talon_v2_support import DOTTED
from tests.talon_v2_support import GLOBEX
from tests.talon_v2_support import TALON_KEY
from tests.talon_v2_support import USERS
from tests.talon_v2_support import _app
from tests.talon_v2_support import _Db
from tests.talon_v2_support import _seed
from tests.talon_v2_support import as_user
from tests.talon_v2_support import body_of

PASSWORD = "talon-connector-password"
URL = "http://talon-user:talon-pass@talon.invalid:3100/?token=abc#frag"
ONE_OFF = "drawer_ACME_false_positives_0123456789abcdef01234567"
DURABLE = "drawer_ACME_alerts_aaaaaaaaaaaaaaaaaaaaaaaa"
HASH = "0123456789abcdef01234567"


def customer_drawer(code, room="false_positives", digest=HASH):
    """A MemPalace drawer id in ``code``'s wing (talon-analyst ``mempalace.drawer_id_for``)."""
    return f"drawer_{code}_{room}_{digest}"


def chat_drawer(uid, digest="b" * 24):
    """A drawer id in user ``uid``'s chat-memory room (talon-analyst ``chat_memory.room_for``)."""
    return f"drawer_talon chat memory_user {hashlib.sha256(str(uid).encode()).hexdigest()}_{digest}"


#: Ana's (user 2) and the admin's (user 1) chat memories.
CHAT_DRAWER = chat_drawer(2)
ADMIN_CHAT = chat_drawer(1)
THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"


def connector(**overrides):
    attributes = {
        "connector_name": "Talon",
        "connector_url": URL,
        "connector_api_key": TALON_KEY,
        "connector_password": PASSWORD,
    }
    attributes.update(overrides)
    return attributes


def stats_payload(code=ACME, **overrides):
    payload = {
        "customer_code": code,
        "total": 42,
        "checked_at": "2026-10-22T08:00:00Z",
        "rooms": {"alerts": 10, "false_positives": 12, "threat_intel": 5, "assets": 8, "environment": 6, "other": 1},
        "sources": {"investigation": 20, "review_durable": 6, "review_one_off": 10, "chat_remember": 5, "other": 1},
        "testing_hidden": 3,
        "growth": [{"date": f"2026-10-{d:02d}", "filed": d % 4} for d in range(1, 23)],
        "complete": True,
    }
    payload.update(overrides)
    return payload


def item(drawer_id=ONE_OFF, **overrides):
    """A drawer list item as talon-analyst answers it (``browse._item``): the wing it was read from as
    ``customer_code``, read off the id unless given."""
    found = re.fullmatch(r"drawer_(.+?)_(?:alerts|false_positives|threat_intel|assets|environment|notes)_.+", drawer_id)
    owner = found.group(1) if found else ACME
    entry = {
        "drawer_id": drawer_id,
        "customer_code": owner,
        "room": "false_positives",
        "source": "review_one_off",
        "source_ref": {"job_id": "copilot-inv-1-1760601600000", "alert_id": 1},
        "filed_at": "2026-10-21T10:00:00Z",
        "durable": False,
        "testing_hidden": False,
        "visible_to_investigations": True,
        "preview": "Backup job on SRV-01 runs vssadmin nightly",
    }
    entry.update(overrides)
    return entry


def drawer(drawer_id=ONE_OFF, **overrides):
    entry = item(drawer_id)
    entry.update(
        {
            "content": "# Lesson\n\nThe backup job on **SRV-01** runs `vssadmin` nightly.\n",
            "forgettable": True,
            "why_not_forgettable": None,
            "why_hidden": None,
        },
    )
    entry.update(overrides)
    return entry


DRAWERS = {
    ONE_OFF: drawer(),
    DURABLE: drawer(
        DURABLE,
        room="alerts",
        source="investigation",
        durable=True,
        forgettable=False,
        why_not_forgettable="An investigation's own record",
    ),
}


def talon(overrides=None, drawers=None):
    """talon-analyst with the memory API. ``overrides`` maps (method, path) or a path to a response,
    a callable(request) -> response, or an exception to raise."""
    overrides = overrides or {}
    drawers = DRAWERS if drawers is None else drawers

    def respond(request):
        path = request.url.path
        key = (request.method, path)
        answer = overrides.get(key, overrides.get(path))
        if answer is not None:
            if isinstance(answer, Exception):
                raise answer
            return answer(request) if callable(answer) else answer
        parts = path.split("/")[3:]  # after /v2/memory
        if request.method == "GET" and len(parts) == 2 and parts[0] == "chat":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "drawer_id": chat_drawer(parts[1]),
                            "filed_at": "2026-10-20T09:00:00Z",
                            "preview": "Prefers UTC",
                            "thread_id": THREAD,
                            "user_id": parts[1],
                        },
                    ],
                },
            )
        if request.method == "DELETE" and len(parts) == 3 and parts[0] == "chat":
            return httpx.Response(200, json={"success": True, "drawer_id": parts[2], "user_id": parts[1]})
        code = parts[0] if parts else ""
        if code == "chat":  # talon-analyst's reserved name (never reached: chat routes come first)
            return httpx.Response(404, json={"detail": "unknown customer"})
        if request.method == "GET" and parts[1:] == ["stats"]:
            return httpx.Response(200, json=stats_payload(code))
        if request.method == "GET" and parts[1:] == ["drawers"]:
            items = [item(), item(DURABLE, source="investigation", durable=True)] if code == ACME else [item(customer_drawer(code))]
            return httpx.Response(200, json={"items": items, "next_cursor": "c1"})
        if len(parts) == 3 and parts[1] == "drawers":
            found = drawers.get(parts[2])
            if found is None:
                return httpx.Response(404, json={"detail": "drawer not found"})
            if request.method == "GET":
                return httpx.Response(200, json=found)
            if request.method == "DELETE":
                return httpx.Response(200, json={"success": True, "drawer_id": parts[2], "customer_code": code})
        if request.method == "GET" and parts[1:] == ["assets"]:
            return httpx.Response(200, json={"items": [{"asset": "SRV-01", "alerts": 4, "iocs": 2, "last_seen": "2026-10-21T10:00:00Z"}]})
        if request.method == "GET" and len(parts) == 4 and parts[1] == "assets" and parts[3] == "timeline":
            return httpx.Response(
                200,
                json={
                    "asset": parts[2],
                    "facts": [
                        {"subject": parts[2], "predicate": "runs", "object": "vssadmin", "valid_from": "2026-10-01", "valid_to": None},
                    ],
                },
            )
        return httpx.Response(404, json={"detail": "Not Found"})

    return respond


class Fake:
    def __init__(self, respond):
        self.respond = respond
        self.requests = []

    async def handler(self, request):
        self.requests.append(request)
        answer = self.respond(request)
        if asyncio.iscoroutine(answer):
            answer = await answer
        return answer

    def new_client(self, timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=timeout)

    def paths(self):
        return [r.url.path for r in self.requests]


def run(scenario, *, respond=None, attributes="default", enabled=True):
    """Run ``scenario(client, fake, audit)`` against the real router with talon-analyst faked."""
    fake = Fake(respond or talon())
    attrs = connector() if attributes == "default" else attributes
    audit = AsyncMock()

    async def _inner():
        db = await _Db().create()
        try:
            await _seed(db, enabled)
            app = _app(db)

            async def resolve_user(self, request, username):
                if username not in USERS:
                    return None
                uid, role, _, _ = USERS[username]
                return SimpleNamespace(id=uid, username=username, role_id=role)

            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(AuthHandler, "decode_token", lambda self, token: (token, USERS.get(token, (0, 0, [], []))[2])),
                )
                stack.enter_context(patch.object(AuthHandler, "_resolve_user", resolve_user))
                stack.enter_context(patch.object(memory_client, "_new_client", fake.new_client))
                stack.enter_context(patch.object(talon_memory, "get_connector_info_from_db", AsyncMock(return_value=attrs)))
                stack.enter_context(patch.object(talon_memory, "record_audit_event", audit))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    return await scenario(client, fake, audit)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def call(method, path, user="admin", **kwargs):
    async def scenario(client, fake, audit):
        headers = {**as_user(user), **kwargs.pop("headers", {})}
        response = await client.request(method, path, headers=headers, **kwargs)
        return response, fake, audit

    return scenario


def get(path, user="admin", **kwargs):
    return call("GET", f"/talon/memory{path}", user, **kwargs)


def delete(path, user="admin"):
    return call("DELETE", f"/talon/memory{path}", user)


def audits(audit):
    return [c.kwargs for c in audit.await_args_list]


#: Every customer route, with a request that would otherwise be answered.
CUSTOMER_ROUTES = [
    ("GET", "/{code}/stats"),
    ("GET", "/{code}/drawers"),
    ("GET", "/{code}/drawers/drawer_{code}_false_positives_" + HASH),
    ("DELETE", "/{code}/drawers/drawer_{code}_false_positives_" + HASH),
    ("GET", "/{code}/assets"),
    ("GET", "/{code}/assets/SRV-01/timeline"),
]
ALL_ROUTES = CUSTOMER_ROUTES + [("GET", "/chat/mine"), ("DELETE", f"/chat/mine/{CHAT_DRAWER}")]


# ── a customer's memory ───────────────────────────────────────────────────────


def test_stats_are_relayed_field_by_field():
    response, fake, _ = run(get(f"/{ACME}/stats"))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = body_of(response)
    assert body["customer_code"] == ACME and body["total"] == 42 and body["testing_hidden"] == 3
    assert body["rooms"] == {"alerts": 10, "false_positives": 12, "threat_intel": 5, "assets": 8, "environment": 6, "other": 1}
    assert body["sources"]["review_one_off"] == 10 and body["sources"]["chat_remember"] == 5
    assert body["growth"][0] == {"date": "2026-10-01", "filed": 1} and len(body["growth"]) == 22
    assert fake.paths() == [f"/v2/memory/{ACME}/stats"]


def test_only_the_api_key_goes_to_talon_and_no_browser_header():
    _, fake, _ = run(get(f"/{ACME}/stats", headers={"X-Talon-User": "1", "X-Talon-Customers": "*"}))
    (request,) = fake.requests
    assert request.headers["x-api-key"] == TALON_KEY
    assert request.headers["accept-encoding"] == "identity"
    assert not [h for h in request.headers if h.lower().startswith("x-talon")]
    assert "authorization" not in request.headers
    # Asked at the stripped URL: no user-info, query or fragment of the connector's.
    assert str(request.url).startswith("http://talon.invalid:3100/v2/memory/")


def test_drawers_page_and_filters_are_forwarded_checked():
    query = {
        "room": "false_positives",
        "source": "review_one_off",
        "since": "2026-10-01",
        "before": "2026-10-21T00:00:00Z",
        "limit": "500",
        "cursor": "c1",
        "user_id": "1",
        "customer_code": GLOBEX,
    }
    response, fake, _ = run(get(f"/{ACME}/drawers", params=query))
    assert response.status_code == 200
    body = body_of(response)
    assert [i["drawer_id"] for i in body["items"]] == [ONE_OFF, DURABLE]
    assert body["items"][0]["openable"] is True and body["items"][0]["source_ref"] == {
        "job_id": "copilot-inv-1-1760601600000",
        "alert_id": 1,
    }
    assert body["next_cursor"] == "c1"
    (request,) = fake.requests
    assert request.url.path == f"/v2/memory/{ACME}/drawers"
    assert dict(request.url.params) == {
        "room": "false_positives",
        "source": "review_one_off",
        "since": "2026-10-01",
        "before": "2026-10-21T00:00:00+00:00",
        "limit": "100",  # capped
        "cursor": "c1",
    }


def test_default_limit_and_no_empty_filters():
    _, fake, _ = run(get(f"/{ACME}/drawers", params={"room": "", "q": "   "}))
    assert dict(fake.requests[0].url.params) == {"limit": "50"}


@pytest.mark.parametrize(
    "query, detail",
    [
        ({"limit": "0"}, "limit must be at least 1"),
        ({"q": "x" * 201}, "q is too long (at most 200 characters)"),
        ({"q": "a\x00b"}, "q holds a control character"),
        ({"q": "a‮b"}, "q holds a control character"),
        ({"room": "secrets"}, "room must be one of: alerts, false_positives, threat_intel, assets, environment"),
        ({"room": "other"}, "room must be one of: alerts, false_positives, threat_intel, assets, environment"),
        ({"q": "backups", "cursor": "c1"}, "a search has no cursor: it shows its best matches only"),
        ({"source": "model"}, "source must be one of: investigation, review_durable, review_one_off, chat_remember, other"),
        ({"since": "yesterday"}, "since must be a date (YYYY-MM-DD) or an ISO 8601 date-time"),
        ({"before": "2026-13-01"}, "before must be a date (YYYY-MM-DD) or an ISO 8601 date-time"),
        ({"cursor": "a b"}, "cursor is not a page cursor"),
        ({"cursor": "c" * 8001}, "cursor is not a page cursor"),
    ],
)
def test_bad_filters_are_refused_before_talon_is_asked(query, detail):
    response, fake, _ = run(get(f"/{ACME}/drawers", params=query))
    assert response.status_code == 400
    assert body_of(response) == {"detail": detail, "code": "invalid"}
    assert fake.requests == []


def test_a_search_goes_in_the_query_string_only():
    response, fake, _ = run(get(f"/{ACME}/drawers", params={"q": "../../threads?x=1#y"}))
    assert response.status_code == 200
    (request,) = fake.requests
    assert request.url.path == f"/v2/memory/{ACME}/drawers"
    assert request.url.params["q"] == "../../threads?x=1#y"


def test_one_drawer_with_its_content():
    response, fake, _ = run(get(f"/{ACME}/drawers/{ONE_OFF}"))
    assert response.status_code == 200
    body = body_of(response)
    assert body["content"].startswith("# Lesson\n\nThe backup job")
    assert body["forgettable"] is True and body["why_hidden"] is None
    assert fake.paths() == [f"/v2/memory/{ACME}/drawers/{ONE_OFF}"]


def test_assets_and_a_timeline():
    response, fake, _ = run(get(f"/{ACME}/assets", params={"q": "srv", "limit": "20"}))
    assert body_of(response)["items"] == [
        {"asset": "SRV-01", "openable": True, "alerts": 4, "iocs": 2, "last_seen": "2026-10-21T10:00:00Z"},
    ]
    assert dict(fake.requests[0].url.params) == {"q": "srv", "limit": "20"}
    response, fake, _ = run(get(f"/{ACME}/assets/SRV-01/timeline"))
    body = body_of(response)
    assert body["asset"] == "SRV-01"
    assert body["facts"] == [{"subject": "SRV-01", "predicate": "runs", "object": "vssadmin", "valid_from": "2026-10-01", "valid_to": None}]


# ── tenancy ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("method, template", CUSTOMER_ROUTES)
@pytest.mark.parametrize(
    "user, code, status",
    [
        ("ana", GLOBEX, 403),  # not one of hers
        ("gus", ACME, 403),
        ("resp", GLOBEX, 403),
        ("demoted", GLOBEX, 403),  # an admin token, an analyst row: scoped by the database role
        ("ana", "acme", 403),  # not "ACME": codes are exact
        ("admin", "acme", 404),  # an admin: a customer that doesn't exist, exactly as written
        ("admin", "NOPE", 404),
        ("ana", "NOPE", 403),  # a scoped caller learns nothing about whether it exists
        ("admin", "bad code", 400),
        ("admin", "-x", 400),
    ],
)
def test_the_customer_must_be_one_the_caller_may_see(method, template, user, code, status):
    response, fake, _ = run(call(method, f"/talon/memory{template.format(code=code)}", user))
    assert response.status_code == status
    assert fake.requests == []
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("method, template", CUSTOMER_ROUTES)
@pytest.mark.parametrize("user, code", [("admin", GLOBEX), ("ana", ACME), ("ana", DOTTED), ("gus", GLOBEX), ("resp", ACME)])
def test_a_callers_own_customers_are_answered(method, template, user, code):
    own = customer_drawer(code)
    drawers = {own: drawer(own)}
    response, fake, _ = run(call(method, f"/talon/memory{template.format(code=code)}", user), respond=talon(drawers=drawers))
    assert response.status_code == 200, response.content
    assert all(path.startswith(f"/v2/memory/{code}/") for path in fake.paths())


@pytest.mark.parametrize("method, template", CUSTOMER_ROUTES)
def test_a_customer_named_chat_is_never_asked_for(method, template):
    """talon-analyst reserves ``chat`` (its chat-memory routes are matched first): CoPilot never asks,
    or ``/v2/memory/chat/stats`` would be user ``stats``'s chat memory."""
    response, fake, _ = run(call(method, f"/talon/memory{template.format(code=CHAT)}", "ana"))
    assert response.status_code == 404
    assert body_of(response) == {"detail": talon_memory.RESERVED, "code": "unknown_customer"}
    assert fake.requests == []


@pytest.mark.parametrize("method, template", ALL_ROUTES)
@pytest.mark.parametrize("user", ["portal", "sched", "nobody"])
def test_only_soc_roles_reach_it(method, template, user):
    response, fake, _ = run(call(method, f"/talon/memory{template.format(code=ACME)}", user))
    assert response.status_code in (401, 403)
    assert fake.requests == []


@pytest.mark.parametrize("method, template", ALL_ROUTES)
def test_with_talon_v2_off_every_route_is_not_found(method, template):
    response, fake, audit = run(call(method, f"/talon/memory{template.format(code=ACME)}"), enabled=False)
    assert response.status_code == 404
    assert body_of(response) == {"detail": "Not Found"}
    assert fake.requests == [] and audit.await_count == 0


# ── chat memory: the caller's own ─────────────────────────────────────────────


@pytest.mark.parametrize("user, uid", [("admin", 1), ("ana", 2), ("resp", 5)])
def test_chat_memory_is_always_the_callers_own(user, uid):
    response, fake, _ = run(get("/chat/mine", user, params={"user_id": "99", "user": "99"}))
    assert response.status_code == 200
    assert fake.paths() == [f"/v2/memory/chat/{uid}"]
    assert dict(fake.requests[0].url.params) == {"limit": "20"}
    assert body_of(response)["items"] == [
        {
            "drawer_id": chat_drawer(uid),
            "openable": True,
            "filed_at": "2026-10-20T09:00:00Z",
            "preview": "Prefers UTC",
            "thread_id": THREAD,
        },
    ]


@pytest.mark.parametrize(
    "method, path",
    [("GET", "/chat/1"), ("GET", "/chat/2/x"), ("DELETE", f"/chat/1/{CHAT_DRAWER}"), ("DELETE", "/chat/1")],
)
def test_there_is_no_route_naming_another_users_chat_memory(method, path):
    response, fake, audit = run(call(method, f"/talon/memory{path}", "ana"))
    assert response.status_code in (404, 405)
    assert fake.requests == [] and audit.await_count == 0


def test_forgetting_a_chat_memory_is_the_callers_own_and_audited():
    response, fake, audit = run(delete(f"/chat/mine/{CHAT_DRAWER}", "ana"))
    assert response.status_code == 200
    assert body_of(response) == {"success": True, "drawer_id": CHAT_DRAWER}
    (request,) = fake.requests
    assert request.method == "DELETE"
    # The space in the chat wing's id is encoded, never a raw path character.
    assert request.url.raw_path == f"/v2/memory/chat/2/{quote(CHAT_DRAWER, safe='')}".encode()
    assert b"%20chat%20memory_user%20" in request.url.raw_path
    assert json.loads(request.content) == {"actor": "ana"}
    (row,) = audits(audit)
    assert row["action"] == AuditAction.TALON_MEMORY_FORGET and row["result"] == AuditResult.SUCCESS
    assert row["entity_type"] == "talon_chat_memory" and row["entity_id"] == CHAT_DRAWER
    assert row["actor_user_id"] == 2 and row["actor_username"] == "ana" and "customer_code" not in row


@pytest.mark.parametrize(
    "answer, status, detail",
    [
        (httpx.Response(409, json={"success": False, "drawer_id": CHAT_DRAWER, "user_id": "2", "error": "not yours"}), 409, "not yours"),
        (httpx.Response(409, json={"success": False, "drawer_id": CHAT_DRAWER, "error": "not yours"}), 409, talon_memory.FORGET_REFUSED),
        (httpx.Response(404, json={"detail": "drawer not found"}), 404, "Talon has no such memory"),
    ],
)
def test_a_refused_chat_forget_keeps_its_status_and_is_audited(answer, status, detail):
    respond = talon({("DELETE", f"/v2/memory/chat/2/{CHAT_DRAWER}"): answer})
    response, _, audit = run(delete(f"/chat/mine/{CHAT_DRAWER}", "ana"), respond=respond)
    assert response.status_code == status and body_of(response)["detail"] == detail
    (row,) = audits(audit)
    assert row["result"] == AuditResult.FAILURE


# ── forgetting a customer's memory ────────────────────────────────────────────


def test_forgetting_a_one_off_lesson_reads_it_then_deletes_it_as_the_user():
    response, fake, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}", "ana"))
    assert response.status_code == 200
    assert body_of(response) == {"success": True, "drawer_id": ONE_OFF}
    assert [(r.method, r.url.path) for r in fake.requests] == [
        ("GET", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"),
        ("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"),
    ]
    assert json.loads(fake.requests[1].content) == {"actor": "ana"}
    (row,) = audits(audit)
    assert row["action"] == AuditAction.TALON_MEMORY_FORGET and row["result"] == AuditResult.SUCCESS
    assert row["customer_code"] == ACME and row["entity_type"] == "talon_memory" and row["entity_id"] == ONE_OFF
    assert row["old_value"] == {"room": "false_positives", "source": "review_one_off", "durable": False, "filed_at": "2026-10-21T10:00:00Z"}


def test_a_chat_remember_lesson_may_be_forgotten():
    drawers = {ONE_OFF: drawer(source="chat_remember")}
    response, fake, _ = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))
    assert response.status_code == 200 and [r.method for r in fake.requests] == ["GET", "DELETE"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"source": "investigation"},  # an investigation's own record
        {"source": "review_durable"},
        {"durable": True},
        {"forgettable": False},
        {"forgettable": "true"},  # only exactly true
        {"source": "other"},
        {"source": "chat_remember", "forgettable": None},
    ],
)
def test_copilot_refuses_what_may_not_be_forgotten_without_asking_talon_to(overrides):
    drawers = {ONE_OFF: drawer(**overrides)}
    response, fake, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}", "ana"), respond=talon(drawers=drawers))
    assert response.status_code == 409
    assert body_of(response) == {"detail": talon_memory.NOT_FORGETTABLE, "code": "refused"}
    assert [r.method for r in fake.requests] == ["GET"]
    (row,) = audits(audit)
    assert row["result"] == AuditResult.FAILURE and row["entity_id"] == ONE_OFF


@pytest.mark.parametrize(
    "answer, detail",
    [
        (
            httpx.Response(409, json={"success": False, "drawer_id": ONE_OFF, "customer_code": ACME, "error": "a durable lesson"}),
            "a durable lesson",
        ),
        (
            httpx.Response(409, json={"success": False, "drawer_id": ONE_OFF, "customer_code": ACME, "error": "x" * 600}),
            talon_memory.FORGET_REFUSED,
        ),  # not one short line
        (httpx.Response(409, content=b"<html>no</html>"), talon_memory.FORGET_REFUSED),
        (
            httpx.Response(409, json={"success": False, "drawer_id": ONE_OFF, "customer_code": ACME, "error": f"key {TALON_KEY} refused"}),
            "key [redacted] refused",
        ),
        # A refusal that doesn't name this customer: its text isn't shown.
        (
            httpx.Response(409, json={"success": False, "drawer_id": ONE_OFF, "customer_code": GLOBEX, "error": "a durable lesson"}),
            talon_memory.FORGET_REFUSED,
        ),
        (httpx.Response(409, json={"success": False, "drawer_id": ONE_OFF, "error": "a durable lesson"}), talon_memory.FORGET_REFUSED),
    ],
)
def test_talons_refusal_to_forget_is_a_409_with_its_reason(answer, detail):
    respond = talon({("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): answer})
    response, _, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=respond)
    assert response.status_code == 409
    assert body_of(response) == {"detail": detail, "code": "refused"}
    (row,) = audits(audit)
    assert row["result"] == AuditResult.FAILURE and "409" in row["details"]


def test_an_unknown_drawer_is_a_404_and_nothing_is_deleted():
    response, fake, audit = run(delete(f"/{ACME}/drawers/drawer_ACME_alerts_ffffffffffffffffffffffff"))
    assert response.status_code == 404
    assert body_of(response) == {"detail": talon_memory.UNKNOWN_DRAWER, "code": "not_found"}
    assert [r.method for r in fake.requests] == ["GET"]
    assert audits(audit)[0]["result"] == AuditResult.FAILURE


def test_a_drawer_gone_between_the_read_and_the_delete_is_a_404():
    respond = talon({("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): httpx.Response(404, json={"detail": "Not Found"})})
    response, fake, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=respond)
    assert response.status_code == 404 and [r.method for r in fake.requests] == ["GET", "DELETE"]
    assert audits(audit)[0]["result"] == AuditResult.FAILURE


def test_a_2xx_forget_that_says_it_failed_is_not_success():
    respond = talon({("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): httpx.Response(200, json={"success": False})})
    response, _, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=respond)
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.FORGET_UNCONFIRMED
    assert audits(audit)[0]["result"] == AuditResult.FAILURE


def test_a_2xx_forget_with_an_unreadable_answer_is_audited_as_done_but_unconfirmed():
    respond = talon({("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): httpx.Response(200, content=b"ok")})
    response, _, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=respond)
    assert response.status_code == 502
    (row,) = audits(audit)
    assert row["result"] == AuditResult.SUCCESS and "unconfirmed" in row["details"]


def test_a_forget_refused_for_tenancy_is_audited_and_never_asks_talon():
    response, fake, audit = run(delete(f"/{GLOBEX}/drawers/{customer_drawer(GLOBEX)}", "ana"))
    assert response.status_code == 403 and fake.requests == []
    (row,) = audits(audit)
    assert row["result"] == AuditResult.FAILURE and row["customer_code"] == GLOBEX and row["actor_username"] == "ana"


# ── path injection ────────────────────────────────────────────────────────────


#: Drawer ids and asset names that must never reach talon-analyst's path. Each is sent
#: percent-encoded, so it arrives in the route's path parameter as written.
UNSAFE = [
    "..",
    ".",
    "../../threads",
    "..\\..\\threads",
    "drawer/../../threads",
    "drawer%2F..%2Fthreads",
    "%2e%2e",
    "drawer?limit=1000",
    "drawer#frag",
    "drawer\x00",
    "drawer\n",
    " drawer",
    "drawer ",
    "drawer\u202e",
    "drawer\u200b",
    "x" * 256,
    "a..b",
]


def _encoded(value):
    return "".join(f"%{b:02X}" for b in value.encode())


@pytest.mark.parametrize("value", UNSAFE)
@pytest.mark.parametrize(
    "method, template",
    [
        ("GET", "/{code}/drawers/{value}"),
        ("DELETE", "/{code}/drawers/{value}"),
        ("GET", "/{code}/assets/{value}/timeline"),
        ("DELETE", "/chat/mine/{value}"),
    ],
)
def test_unsafe_ids_never_reach_talon(value, method, template):
    path = f"/talon/memory{template.format(code=ACME, value=_encoded(value))}"
    response, fake, _ = run(call(method, path, "ana"))
    assert fake.requests == []
    assert response.status_code in (400, 404, 405)


@pytest.mark.parametrize("value", UNSAFE)
def test_the_unsafe_ids_are_refused_by_the_checks_themselves(value):
    assert not talon_memory.is_safe_drawer_id(value)
    assert not talon_memory.is_safe_asset(value)


@pytest.mark.parametrize("value", [".", "..", "", "a/b", "a\\b", "a%2Fb", "a?b", "a#b", "a\x00b", "a\x85b"])
def test_the_client_refuses_unsafe_segments(value):
    with pytest.raises(memory_client.UnsafePath):
        memory_client.memory_path([ACME, "drawers", value])


def test_the_client_encodes_every_segment():
    assert memory_client.memory_path(["acme.io", "drawers", "drawer_talon chat memory:x"]) == (
        "/v2/memory/acme.io/drawers/drawer_talon%20chat%20memory%3Ax"
    )


def test_a_safe_but_unusual_id_is_encoded_on_the_wire():
    odd = customer_drawer(DOTTED, "assets")
    drawers = {odd: drawer(odd)}
    response, fake, _ = run(get(f"/{DOTTED}/drawers/{odd}", "ana"), respond=talon(drawers=drawers))
    assert response.status_code == 200
    assert fake.requests[0].url.raw_path == f"/v2/memory/acme.io/drawers/drawer_acme.io_assets_{HASH}".encode()


def test_an_asset_with_a_machine_account_name_is_allowed():
    response, fake, _ = run(get(f"/{ACME}/assets/{_encoded('SRV-01$')}/timeline"))
    assert response.status_code == 200
    assert fake.requests[0].url.raw_path == b"/v2/memory/ACME/assets/SRV-01%24/timeline"


def test_a_redirect_is_never_followed():
    respond = talon({f"/v2/memory/{ACME}/stats": httpx.Response(302, headers={"location": "http://elsewhere.invalid/v2/threads"})})
    response, fake, _ = run(get(f"/{ACME}/stats"), respond=respond)
    assert response.status_code == 502 and len(fake.requests) == 1


# ── an old Talon, failures, malformed answers ─────────────────────────────────


@pytest.mark.parametrize("path", [f"/{ACME}/stats", f"/{ACME}/drawers", f"/{ACME}/assets", "/chat/mine"])
def test_an_old_talon_or_its_v2_api_off_is_unsupported(path):
    response, _, _ = run(get(path), respond=lambda request: httpx.Response(404, json={"detail": "Not Found"}))
    assert response.status_code == 404
    assert body_of(response) == {"detail": talon_memory.OLD_TALON, "code": "unsupported"}


@pytest.mark.parametrize(
    "detail, expected",
    [
        ("drawer not found", {"detail": talon_memory.UNKNOWN_DRAWER, "code": "not_found"}),
        ("unknown customer", {"detail": talon_memory.NO_MEMORY, "code": "unknown_customer"}),
        ("Not Found", {"detail": talon_memory.OLD_TALON, "code": "unsupported"}),
    ],
)
def test_talons_404s_are_told_apart(detail, expected):
    respond = lambda request: httpx.Response(404, json={"detail": detail})  # noqa: E731
    for path in (f"/{ACME}/drawers/{ONE_OFF}", f"/{ACME}/stats", f"/{ACME}/assets/SRV-01/timeline"):
        response, _, _ = run(get(path), respond=respond)
        assert response.status_code == 404 and body_of(response) == expected


@pytest.mark.parametrize(
    "answer, status, detail",
    [
        (httpx.Response(401, json={"error": "Unauthorized"}), 502, talon_memory.KEY_REFUSED),
        (httpx.Response(503, json={"detail": "palace down at 10.0.0.5"}), 503, talon_memory.UNAVAILABLE),
        (httpx.Response(503, json={"detail": "MemPalace is not configured"}), 503, talon_memory.NO_PALACE),
        (httpx.Response(502, json={"detail": "MemPalace request failed"}), 502, talon_memory.PALACE_FAILED),
        (httpx.Response(502, json={"detail": "something at 10.0.0.5"}), 502, talon_memory.FAILED),
        (httpx.Response(500, text=f"Traceback ... {TALON_KEY}"), 502, talon_memory.FAILED),
        (httpx.Response(400, json={"detail": "invalid customer_code"}), 400, "Talon refused the request: invalid customer_code"),
        (httpx.Response(400, json={"detail": f"bad {TALON_KEY}"}), 400, "Talon refused the request: bad [redacted]"),
        (httpx.Response(400, text="<html>"), 400, talon_memory.INVALID_REQUEST),
        (httpx.Response(422, json={"detail": "invalid request"}), 400, talon_memory.INVALID_REQUEST),
        (httpx.Response(403, json={"detail": "no"}), 502, talon_memory.FAILED),
        (httpx.Response(200, content=b"not json"), 502, talon_memory.NOT_JSON),
        (httpx.Response(200, json=[1, 2]), 502, talon_memory.WRONG_SHAPE),
        (httpx.Response(200, json=stats_payload(GLOBEX)), 502, talon_memory.WRONG_SHAPE),  # another customer's
        (httpx.Response(200, json={k: v for k, v in stats_payload().items() if k != "customer_code"}), 502, talon_memory.WRONG_SHAPE),
        (
            httpx.Response(200, content=gzip.compress(json.dumps(stats_payload()).encode()), headers={"content-encoding": "gzip"}),
            502,
            "Talon's answer was compressed; not read",
        ),
        (httpx.ConnectError("connection refused to talon.invalid:3100"), 502, "Talon could not be reached (ConnectError)"),
        (httpx.ReadTimeout("read timed out"), 504, "Talon did not answer within 8 s"),
    ],
)
def test_unusable_answers_are_fixed_texts(answer, status, detail):
    response, _, _ = run(get(f"/{ACME}/stats"), respond=talon({f"/v2/memory/{ACME}/stats": answer}))
    assert response.status_code == status
    assert body_of(response)["detail"] == detail
    assert response.headers["cache-control"] == "no-store"
    assert TALON_KEY.encode() not in response.content and b"10.0.0.5" not in response.content


def test_a_huge_answer_is_not_read(monkeypatch):
    monkeypatch.setattr(memory_client, "MAX_BODY_BYTES", 1000)
    respond = talon({f"/v2/memory/{ACME}/drawers": httpx.Response(200, json={"items": [item(preview="x" * 5000)]})})
    response, _, _ = run(get(f"/{ACME}/drawers"), respond=respond)
    assert response.status_code == 502 and body_of(response)["detail"] == "Talon's answer was too large"


def test_a_talon_that_never_answers_times_out(monkeypatch):
    monkeypatch.setattr(memory_client, "TIMEOUT_SECONDS", 0.05)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=stats_payload())

    response, _, _ = run(get(f"/{ACME}/stats"), respond=slow)
    assert response.status_code == 504
    assert body_of(response) == {"detail": "Talon did not answer within 0.05 s", "code": "unavailable"}


def test_no_connector_or_no_url_asks_nothing():
    response, fake, _ = run(get(f"/{ACME}/stats"), attributes=None)
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.NO_CONNECTOR
    response, fake, _ = run(get(f"/{ACME}/stats"), attributes=connector(connector_url=""))
    assert body_of(response)["detail"] == talon_memory.NOT_CONFIGURED and fake.requests == []


def test_malformed_fields_are_dropped_not_fatal():
    items = [
        item(),
        item(),  # a duplicate
        item(
            customer_drawer(ACME, "alerts", "c" * 24),
            room="secrets",
            source=7,
            source_ref={"job_id": "../x", "alert_id": -1},
            durable="yes",
            preview=["a"],
        ),
        item("drawer..odd", preview="an id CoPilot can't use"),
        item("drawer_ACME_x_1", preview="not a MemPalace id of this wing"),
        {"drawer_id": 12},
        {"drawer_id": "drawer‮evil"},
        {"drawer_id": f"drawer_{TALON_KEY}"},  # an id holding the key is dropped, not shown redacted
        "not a dict",
        {"room": "alerts"},
    ]
    page = {"items": items, "next_cursor": "bad cursor", "extra": {"secret": "x"}}
    response, _, _ = run(get(f"/{ACME}/drawers"), respond=talon({f"/v2/memory/{ACME}/drawers": httpx.Response(200, json=page)}))
    assert response.status_code == 200
    body = body_of(response)
    # "drawer_ACME_x_1" is in ACME's wing and names ACME: a room outside the five is listed ("other").
    assert [i["drawer_id"] for i in body["items"]] == [ONE_OFF, customer_drawer(ACME, "alerts", "c" * 24), "drawer_ACME_x_1"]
    assert all(i["openable"] for i in body["items"])
    odd = body["items"][1]
    assert odd["room"] == "other" and odd["source"] == "other" and odd["source_ref"] is None and odd["durable"] is None
    assert odd["preview"] is None
    assert body["next_cursor"] is None and "extra" not in body


def test_more_than_a_page_is_cut_to_100():
    page = {"items": [item(f"drawer_ACME_alerts_{n:024x}") for n in range(150)]}
    response, _, _ = run(get(f"/{ACME}/drawers"), respond=talon({f"/v2/memory/{ACME}/drawers": httpx.Response(200, json=page)}))
    assert len(body_of(response)["items"]) == 100


def test_malformed_stats_are_null_not_zero():
    payload = {
        "customer_code": ACME,
        "total": "42",
        "rooms": {"alerts": -1, "false_positives": 1.5, "threat_intel": True, "assets": 3, "unknown": 9},
        "sources": "all",
        "testing_hidden": None,
        "growth": [{"date": "2026-10-01", "filed": 2}, {"date": "2026-10-01", "filed": 9}, {"date": "Oct 2", "filed": 1}, "x"],
    }
    respond = talon({f"/v2/memory/{ACME}/stats": httpx.Response(200, json=payload)})
    body = body_of(run(get(f"/{ACME}/stats"), respond=respond)[0])
    assert body["total"] is None and body["testing_hidden"] is None
    assert body["rooms"] == {"alerts": None, "false_positives": None, "threat_intel": None, "assets": 3, "environment": None, "other": None}
    assert set(body["sources"].values()) == {None}
    assert body["growth"] == [{"date": "2026-10-01", "filed": 2}]


def test_an_integer_past_pythons_digit_limit_is_not_json():
    respond = talon({f"/v2/memory/{ACME}/stats": httpx.Response(200, content=b'{"total": ' + b"9" * 5000 + b"}")})
    response, _, _ = run(get(f"/{ACME}/stats"), respond=respond)
    assert response.status_code == 502


def test_a_drawer_answer_for_another_id_is_not_shown():
    drawers = {ONE_OFF: drawer(DURABLE)}
    response, _, _ = run(get(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.WRONG_SHAPE


def test_content_keeps_its_lines_and_is_bounded():
    content = "line 1\r\nline 2\n\tindented\x07\x1b[31m\n" + "y" * 200_000
    drawers = {ONE_OFF: drawer(content=content, why_hidden="Filed while testing\nthe lab", forgettable=1)}
    body = body_of(run(get(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))[0])
    assert body["content"].startswith("line 1\nline 2\n\tindented[31m\n")
    assert len(body["content"]) == talon_memory.MAX_CONTENT
    assert body["why_hidden"] == "Filed while testing the lab"
    assert body["forgettable"] is False  # only exactly true


def test_assets_counts_lists_and_odd_names():
    items = [
        {"asset": "SRV-01", "alerts": [1, 2, 3], "iocs": -2},
        {"asset": "10.0.0.5", "alerts": 1, "iocs": 0},
        {"asset": "fe80::1", "alerts": 1},
        {"asset": "WIN/../x", "alerts": 1},
        {"asset": None},
    ]
    respond = talon({f"/v2/memory/{ACME}/assets": httpx.Response(200, json={"items": items})})
    body = body_of(run(get(f"/{ACME}/assets"), respond=respond)[0])
    assert [(a["asset"], a["openable"], a["alerts"], a["iocs"]) for a in body["items"]] == [
        ("SRV-01", True, 3, None),
        ("10.0.0.5", True, 1, 0),
        ("fe80::1", True, 1, None),
        ("WIN/../x", False, 1, None),
    ]


def test_chat_memory_odd_items():
    items = [
        {"drawer_id": ADMIN_CHAT, "user_id": "1", "thread_id": "not-a-uuid"},
        {"drawer_id": ADMIN_CHAT, "user_id": "1"},
        {"drawer_id": chat_drawer(1, "c" * 24), "user_id": "1", "thread_id": THREAD.upper(), "preview": 5},
    ]
    respond = talon({"/v2/memory/chat/1": httpx.Response(200, json={"items": items})})
    body = body_of(run(get("/chat/mine"), respond=respond)[0])
    assert body["items"] == [
        {"drawer_id": ADMIN_CHAT, "openable": True, "filed_at": None, "preview": None, "thread_id": None},
        {"drawer_id": chat_drawer(1, "c" * 24), "openable": True, "filed_at": None, "preview": None, "thread_id": THREAD},
    ]


# ── no secret reaches the browser ─────────────────────────────────────────────


def test_no_key_password_or_user_info_reaches_the_browser():
    leak = f"key {TALON_KEY} pass {PASSWORD} at http://admin:hunter2@talon.invalid/x?api_key=abc123 done"
    stats = stats_payload(checked_at=leak)
    page = {"items": [item(preview=leak, filed_at=leak)]}
    one = drawer(content=leak + "\n" + leak, why_hidden=leak, why_not_forgettable=leak, preview=leak)
    assets = {"items": [{"asset": "SRV-01", "last_seen": leak}]}
    timeline = {"asset": "SRV-01", "facts": [{"subject": leak, "predicate": leak, "object": leak, "valid_from": leak}]}
    chat = {"items": [{"drawer_id": ADMIN_CHAT, "user_id": "1", "preview": leak, "filed_at": leak}]}
    respond = talon(
        {
            f"/v2/memory/{ACME}/stats": httpx.Response(200, json=stats),
            ("GET", f"/v2/memory/{ACME}/drawers"): httpx.Response(200, json=page),
            ("GET", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): httpx.Response(200, json=one),
            f"/v2/memory/{ACME}/assets": httpx.Response(200, json=assets),
            f"/v2/memory/{ACME}/assets/SRV-01/timeline": httpx.Response(200, json=timeline),
            "/v2/memory/chat/1": httpx.Response(200, json=chat),
        },
    )

    async def scenario(client, fake, audit):
        bodies = []
        for path in [
            f"/{ACME}/stats",
            f"/{ACME}/drawers",
            f"/{ACME}/drawers/{ONE_OFF}",
            f"/{ACME}/assets",
            f"/{ACME}/assets/SRV-01/timeline",
            "/chat/mine",
        ]:
            response = await client.get(f"/talon/memory{path}", headers=as_user("admin"))
            assert response.status_code == 200, (path, response.content)
            bodies.append(response.content)
        return bodies

    bodies = run(scenario, respond=respond)
    for content in bodies:
        assert TALON_KEY.encode() not in content
        assert PASSWORD.encode() not in content
        assert b"hunter2" not in content and b"abc123" not in content and b"admin:" not in content
    assert b"[redacted]" in bodies[2] and b"\\n" in bodies[2]  # the content keeps its newline


# ── the client and the session ────────────────────────────────────────────────


def test_the_memory_client_settings():
    async def scenario():
        async with memory_client._new_client(memory_client.TIMEOUT) as client:
            context = client._transport._pool._ssl_context
            return client.follow_redirects, client.trust_env, context.verify_mode, client.timeout

    follow, trust_env, verify_mode, timeout = asyncio.run(scenario())
    assert follow is False and trust_env is False
    # TLS isn't verified, as for the rest of the Talon connector: talon-analyst is on a private network.
    assert verify_mode == ssl.CERT_NONE
    assert timeout.read == memory_client.TIMEOUT_SECONDS == 8.0


def test_the_database_session_is_closed_before_talon_is_asked():
    events = []
    original_close = AsyncSession.close

    async def close(self):
        events.append("close")
        return await original_close(self)

    def respond(request):
        events.append("talon")
        return talon()(request)

    with patch.object(AsyncSession, "close", close):
        response, _, _ = run(get(f"/{ACME}/stats"), respond=respond)
    assert response.status_code == 200
    assert "talon" in events and "close" in events[: events.index("talon")]


# ── drawer ids bound to the customer and the caller (defence in depth) ────────


GLOBEX_DRAWER = customer_drawer(GLOBEX)
NOT_ACMES = [
    GLOBEX_DRAWER,  # another customer's
    customer_drawer("acme"),  # case-sensitive
    customer_drawer("ACMEX"),  # not ACME's prefix ("drawer_ACME_")
    "drawer_ACME_",  # nothing after the wing
    "ACME_alerts_" + HASH,
    CHAT_DRAWER,  # the chat-memory wing
    ADMIN_CHAT,
    "drawer_Talon Chat Memory_user x_" + HASH,
]


@pytest.mark.parametrize("drawer_id", NOT_ACMES)
@pytest.mark.parametrize("method", ["GET", "DELETE"])
def test_a_customer_route_takes_only_that_customers_drawer_ids(method, drawer_id):
    response, fake, audit = run(call(method, f"/talon/memory/{ACME}/drawers/{quote(drawer_id, safe='')}", "ana"))
    assert response.status_code == 400
    assert body_of(response) == {"detail": talon_memory.NOT_THIS_CUSTOMERS, "code": "invalid"}
    assert fake.requests == []
    if method == "DELETE":
        (row,) = audits(audit)
        assert row["result"] == AuditResult.FAILURE and talon_memory.NOT_THIS_CUSTOMERS in row["details"]


def test_the_customer_binding_helpers():
    assert talon_memory.is_customer_drawer(customer_drawer(ACME), ACME)
    assert talon_memory.is_customer_drawer(customer_drawer("ACME_X", "threat_intel"), "ACME_X")
    # The prefix alone can't tell ACME from ACME_X: the answer's required customer_code does.
    assert talon_memory.is_customer_drawer(customer_drawer("ACME_X", "threat_intel"), ACME)
    assert talon_memory.is_customer_drawer(customer_drawer(ACME, "notes", "x"), ACME)  # any room, as written
    assert talon_memory.is_customer_drawer(customer_drawer(DOTTED, "environment"), DOTTED)
    assert not talon_memory.is_customer_drawer(customer_drawer("acmexio"), DOTTED)  # "." is literal
    assert talon_memory.is_chat_drawer(CHAT_DRAWER) and not talon_memory.is_chat_drawer(ONE_OFF)
    assert talon_memory.is_own_chat_drawer(CHAT_DRAWER, "2")
    assert not talon_memory.is_own_chat_drawer(CHAT_DRAWER, "1")
    assert not talon_memory.is_own_chat_drawer(ONE_OFF, "2")


@pytest.mark.parametrize(
    "drawer_id, detail",
    [
        (ADMIN_CHAT, talon_memory.NOT_YOUR_CHAT),  # the admin's chat memory, asked for by ana
        (ONE_OFF, talon_memory.NOT_YOUR_CHAT),  # a customer's drawer
        ("drawer_talon chat memory_user " + "0" * 64 + "_" + HASH, talon_memory.NOT_YOUR_CHAT),
        ("drawer?x", talon_memory.INVALID_DRAWER),
    ],
)
def test_a_chat_route_takes_only_the_callers_own_chat_ids(drawer_id, detail):
    response, fake, audit = run(delete(f"/chat/mine/{quote(drawer_id, safe='')}", "ana"))
    assert response.status_code == 400
    assert body_of(response) == {"detail": detail, "code": "invalid"}
    assert fake.requests == []
    (row,) = audits(audit)
    assert row["result"] == AuditResult.FAILURE and row["entity_type"] == "talon_chat_memory"


@pytest.mark.parametrize(
    "named",
    [{"customer_code": GLOBEX}, {"wing": GLOBEX}, {"customer_code": None}, {"wing": "talon chat memory"}, {"customer_code": "acme"}],
)
def test_a_drawer_answer_naming_another_customer_is_refused(named):
    drawers = {ONE_OFF: drawer(**named)}
    response, _, _ = run(get(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.WRONG_SHAPE
    response, fake, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))
    assert response.status_code == 502 and [r.method for r in fake.requests] == ["GET"]  # nothing deleted
    assert audits(audit)[0]["result"] == AuditResult.FAILURE


def test_a_drawer_answer_naming_its_own_customer_is_shown():
    drawers = {ONE_OFF: drawer(customer_code=ACME, wing=ACME)}
    response, _, _ = run(get(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers=drawers))
    assert response.status_code == 200


def test_a_list_never_shows_another_customers_or_chat_drawers():
    page = {
        "items": [
            item(),
            item(GLOBEX_DRAWER),
            item(customer_drawer("ACME_X")),
            item(CHAT_DRAWER),
            item(customer_drawer(ACME, "alerts"), customer_code=GLOBEX),
            item(customer_drawer(ACME, "assets"), wing="GLOBEX"),
        ],
    }
    respond = talon({("GET", f"/v2/memory/{ACME}/drawers"): httpx.Response(200, json=page)})
    body = body_of(run(get(f"/{ACME}/drawers"), respond=respond)[0])
    assert [i["drawer_id"] for i in body["items"]] == [ONE_OFF]


def test_chat_memory_never_shows_another_users_or_a_customers_drawers():
    items = [
        {"drawer_id": CHAT_DRAWER, "user_id": "2"},
        {"drawer_id": ADMIN_CHAT, "user_id": "2"},  # in the admin's room
        {"drawer_id": ONE_OFF, "user_id": "2"},  # a customer's drawer
        {"drawer_id": chat_drawer(2, "c" * 24), "user_id": "1"},  # names another user
        {"drawer_id": chat_drawer(2, "d" * 24)},  # names nobody
        {"drawer_id": chat_drawer(2, "e" * 24), "user_id": 2},  # not the id as CoPilot sends it
        {"drawer_id": chat_drawer(2, "f" * 24), "user_id": "2", "wing": ACME},
    ]
    respond = talon({"/v2/memory/chat/2": httpx.Response(200, json={"items": items})})
    body = body_of(run(get("/chat/mine", "ana"), respond=respond)[0])
    assert [i["drawer_id"] for i in body["items"]] == [CHAT_DRAWER]


def test_the_chat_list_limit_is_capped():
    _, fake, _ = run(get("/chat/mine", "ana", params={"limit": "500"}))
    assert fake.requests[0].url.params["limit"] == "50"
    response, fake, _ = run(get("/chat/mine", "ana", params={"limit": "0"}))
    assert response.status_code == 400 and fake.requests == []


@pytest.mark.parametrize(
    "answer",
    [
        {"success": True, "drawer_id": CHAT_DRAWER, "user_id": "1"},
        {"success": True, "drawer_id": CHAT_DRAWER},
        {"success": True, "drawer_id": "drawer_other", "user_id": "2"},
    ],
)
def test_a_chat_forget_answer_must_name_the_caller(answer):
    respond = talon({("DELETE", f"/v2/memory/chat/2/{CHAT_DRAWER}"): httpx.Response(200, json=answer)})
    response, _, audit = run(delete(f"/chat/mine/{quote(CHAT_DRAWER, safe='')}", "ana"), respond=respond)
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.FORGET_UNCONFIRMED
    assert "unconfirmed" in audits(audit)[0]["details"]


def test_a_longer_customer_code_is_caught_by_the_answers_owner():
    """``drawer_ACME_X_…`` starts ``drawer_ACME_``: the prefix lets it through to Talon, and the answer,
    which names ACME_X (talon-analyst reads it from ACME_X's wing), is refused."""
    other = customer_drawer("ACME_X")
    drawers = {other: drawer(other, customer_code="ACME_X")}
    response, _, _ = run(get(f"/{ACME}/drawers/{quote(other, safe='')}"), respond=talon(drawers=drawers))
    assert response.status_code == 502
    response, fake, _ = run(delete(f"/{ACME}/drawers/{quote(other, safe='')}"), respond=talon(drawers=drawers))
    assert response.status_code == 502 and [r.method for r in fake.requests] == ["GET"]


@pytest.mark.parametrize(
    "answer",
    [{"success": True, "drawer_id": ONE_OFF}, {"success": True, "drawer_id": ONE_OFF, "customer_code": GLOBEX}],
)
def test_a_forget_answer_must_name_the_customer(answer):
    respond = talon({("DELETE", f"/v2/memory/{ACME}/drawers/{ONE_OFF}"): httpx.Response(200, json=answer)})
    response, _, audit = run(delete(f"/{ACME}/drawers/{ONE_OFF}"), respond=respond)
    assert response.status_code == 502 and "unconfirmed" in audits(audit)[0]["details"]


@pytest.mark.parametrize("missing", ["customer_code"])
def test_drawers_without_an_owner_are_never_shown(missing):
    page = {"items": [{k: v for k, v in item().items() if k != missing}, item(customer_drawer(ACME, "alerts"))]}
    respond = talon({("GET", f"/v2/memory/{ACME}/drawers"): httpx.Response(200, json=page)})
    assert [i["drawer_id"] for i in body_of(run(get(f"/{ACME}/drawers"), respond=respond)[0])["items"]] == [customer_drawer(ACME, "alerts")]
    one = {k: v for k, v in drawer().items() if k != missing}
    response, _, _ = run(get(f"/{ACME}/drawers/{ONE_OFF}"), respond=talon(drawers={ONE_OFF: one}))
    assert response.status_code == 502


def test_stats_complete_and_room_names():
    respond = talon({f"/v2/memory/{ACME}/stats": httpx.Response(200, json=stats_payload(complete=False))})
    assert body_of(run(get(f"/{ACME}/stats"), respond=respond)[0])["complete"] is False
    page = {"items": [item(customer_drawer(ACME, "notes"), room="notes")]}
    respond = talon({("GET", f"/v2/memory/{ACME}/drawers"): httpx.Response(200, json=page)})
    (row,) = body_of(run(get(f"/{ACME}/drawers"), respond=respond)[0])["items"]
    assert (row["room"], row["room_name"]) == ("other", "notes")


def test_assets_and_timelines_naming_another_customer_are_not_shown():
    assets = {"items": [{"asset": "SRV-01"}, {"asset": "GLOBEX-DC", "customer_code": GLOBEX}]}
    respond = talon({f"/v2/memory/{ACME}/assets": httpx.Response(200, json=assets)})
    assert [a["asset"] for a in body_of(run(get(f"/{ACME}/assets"), respond=respond)[0])["items"]] == ["SRV-01"]
    timeline = {"asset": "SRV-01", "customer_code": GLOBEX, "facts": []}
    respond = talon({f"/v2/memory/{ACME}/assets/SRV-01/timeline": httpx.Response(200, json=timeline)})
    assert run(get(f"/{ACME}/assets/SRV-01/timeline"), respond=respond)[0].status_code == 502
