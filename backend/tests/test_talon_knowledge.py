"""The customer page's "What Talon sees" panel, ``/api/talon/knowledge/{customer_code}``
(``services/talon_knowledge.py``).

Real routers, a real in-memory database (``talon_v2_support``), talon-analyst's ``/v2/knowledge`` API
as an ``httpx.MockTransport`` plugged in under the real memory client (its 8 s deadline, capped reads,
no redirects, no proxy). No network.
"""
import asyncio
import gzip
import json
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.talon.services import talon_knowledge
from app.connectors.talon.services import talon_memory
from app.connectors.talon.utils import memory_client
from app.middleware.customer_access import customer_access_handler
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
MEASURED = "2026-11-06T05:30:00+00:00"


def connector(**overrides):
    attributes = {
        "connector_name": "Talon",
        "connector_url": URL,
        "connector_api_key": TALON_KEY,
        "connector_password": PASSWORD,
    }
    attributes.update(overrides)
    return attributes


def source(pattern="wazuh-lab_*", **overrides):
    entry = {
        "pattern": pattern,
        "categories": ["endpoint"],
        "events": 3400000,
        "degraded": False,
        "measured_at": MEASURED,
        "fields": {"host": ["agent_name"], "user": ["data_win_eventdata_user"]},
    }
    entry.update(overrides)
    return entry


def payload(code=ACME, **overrides):
    """The answer of the contract, status ``ok``."""
    answer = {
        "customer_code": code,
        "status": "ok",
        "measured_at": MEASURED,
        "field_days": 30,
        "event_days": 7,
        "coverage": {"available": ["endpoint", "email"], "degraded": ["identity"], "unavailable": ["network", "cloud", "waf"]},
        "sources": [source()],
        "not_measured": ["fortinet-lab_*"],
    }
    answer.update(overrides)
    return answer


def empty(code=ACME, status="no_profile", **overrides):
    answer = {
        "customer_code": code,
        "status": status,
        "measured_at": None,
        "field_days": None,
        "event_days": None,
        "coverage": None,
        "sources": [],
        "not_measured": [],
    }
    answer.update(overrides)
    return answer


def talon(answer=None):
    """talon-analyst with the knowledge API. ``answer``: a response, a dict to answer 200 with, an
    exception to raise, or a callable(request); by default the contract's answer for the path's code."""

    def respond(request):
        if answer is None:
            return httpx.Response(200, json=payload(request.url.path.split("/")[3]))
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, dict):
            return httpx.Response(200, json=answer)
        return answer(request) if callable(answer) else answer

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


def get(code=ACME, user="admin", *, answer=None, respond=None, attributes="default", enabled=True, headers=None):
    """``GET /talon/knowledge/{code}`` against the real router, talon-analyst faked."""
    fake = Fake(respond or talon(answer))
    attrs = connector() if attributes == "default" else attributes

    async def _inner():
        db = await _Db().create()
        try:
            await _seed(db, enabled)

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
                transport = httpx.ASGITransport(app=_app(db))
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    return await client.get(f"/talon/knowledge/{code}", headers={**as_user(user), **(headers or {})})
        finally:
            await db.dispose()

    return asyncio.run(_inner()), fake


# ── the answer ────────────────────────────────────────────────────────────────


def test_the_contracts_answer_is_relayed_field_by_field():
    response, fake = get()
    assert response.status_code == 200
    assert body_of(response) == {"success": True, **payload()}
    assert [r.url.path for r in fake.requests] == [f"/v2/knowledge/{ACME}"]
    assert fake.requests[0].method == "GET"


def test_only_the_api_key_goes_to_talon_and_no_browser_header():
    _, fake = get(headers={"X-Talon-User": "1", "X-Talon-Customers": "*"})
    (request,) = fake.requests
    assert request.headers["x-api-key"] == TALON_KEY
    assert request.headers["accept-encoding"] == "identity"
    assert not [h for h in request.headers if h.lower().startswith("x-talon")]
    assert "authorization" not in request.headers
    # Asked at the stripped URL: no user-info, query or fragment of the connector's.
    assert str(request.url) == f"http://talon.invalid:3100/v2/knowledge/{ACME}"


@pytest.mark.parametrize("status", ["no_sources", "no_profile", "no_tenant_map"])
def test_a_status_without_a_measurement_is_relayed_empty(status):
    response, _ = get(answer=empty(status=status))
    assert response.status_code == 200
    assert body_of(response) == {"success": True, **empty(status=status)}


@pytest.mark.parametrize("status", ["no_sources", "no_profile", "no_tenant_map"])
def test_only_ok_carries_measurements_whatever_talon_sent(status):
    response, _ = get(answer=payload(status=status))
    assert body_of(response) == {"success": True, **empty(status=status)}


def test_a_customer_talon_never_heard_of_is_no_sources_not_a_failure():
    assert get(DOTTED, "ana", answer=empty(DOTTED, status="no_sources"))[0].status_code == 200


def test_ok_may_leave_its_windows_and_time_null():
    answer = payload(measured_at=None, field_days=None, event_days=None, coverage={})
    body = body_of(get(answer=answer)[0])
    assert body["status"] == "ok" and body["measured_at"] is None and body["field_days"] is None and body["event_days"] is None
    assert body["coverage"] == {"available": [], "degraded": [], "unavailable": []}


def test_a_timezone_written_z_is_kept_as_a_time():
    assert body_of(get(answer=payload(measured_at="2026-11-06T05:30:00Z"))[0])["measured_at"] == MEASURED


# ── who may ask, and for what ─────────────────────────────────────────────────


@pytest.mark.parametrize("user, code", [("admin", GLOBEX), ("ana", ACME), ("ana", DOTTED), ("gus", GLOBEX), ("resp", ACME)])
def test_admins_and_a_callers_own_customers_are_answered(user, code):
    response, fake = get(code, user)
    assert response.status_code == 200, response.content
    assert [r.url.path for r in fake.requests] == [f"/v2/knowledge/{code}"]


@pytest.mark.parametrize("user", ["portal", "sched", "nobody"])
def test_only_soc_roles_reach_it(user):
    response, fake = get(ACME, user)
    assert response.status_code in (401, 403)
    assert fake.requests == []


def test_a_portal_user_is_refused_even_for_their_own_customer():
    response, fake = get(ACME, "portal")
    assert response.status_code == 403 and fake.requests == []


@pytest.mark.parametrize(
    "user, code, status",
    [
        ("ana", GLOBEX, 403),  # not one of hers
        ("gus", ACME, 403),
        ("resp", GLOBEX, 403),
        ("demoted", GLOBEX, 403),  # an admin token, an analyst row: scoped by the database role
        ("ana", "acme", 403),  # not "ACME": codes are exact
        ("admin", "acme", 404),  # a lowercase path for an uppercase code: no such customer
        ("admin", "NOPE", 404),
        ("ana", "NOPE", 403),  # a scoped caller learns nothing about whether it exists
        ("admin", "bad code", 400),
        ("admin", "-x", 400),
        ("admin", "x" * 65, 400),
    ],
)
def test_the_customer_is_checked_before_talon_is_asked(user, code, status):
    response, fake = get(code, user)
    assert response.status_code == status
    assert fake.requests == []
    assert response.headers["cache-control"] == "no-store"


def test_a_scoped_analyst_cant_tell_another_customer_from_no_customer():
    other, _ = get(GLOBEX, "ana")
    nothing, _ = get("NOPE", "ana")
    assert other.status_code == nothing.status_code == 403
    assert other.content == nothing.content
    assert body_of(other) == {"detail": talon_memory.NOT_ACCESSIBLE, "code": "forbidden"}


def test_a_code_is_matched_exactly_even_where_the_database_ignores_case():
    """MySQL finds ACME for ``acme``; SQLite here wouldn't, so its answer is played."""
    rows = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [ACME]))
    session = SimpleNamespace(execute=AsyncMock(return_value=rows))

    async def scenario():
        with patch.object(customer_access_handler, "check_customer_access", AsyncMock(return_value=True)):
            return await talon_memory.customer_problem(SimpleNamespace(id=1), session, "acme")

    refused = asyncio.run(scenario())
    assert refused.status_code == 404
    assert json.loads(refused.body) == {"detail": talon_memory.UNKNOWN_CUSTOMER, "code": "unknown_customer"}


def test_a_customer_named_chat_is_only_memorys_reserved_word():
    """``/v2/memory/chat/...`` is chat memory; ``/v2/knowledge/`` has no such routes."""
    response, fake = get(CHAT, "ana")
    assert response.status_code == 200
    assert [r.url.path for r in fake.requests] == ["/v2/knowledge/chat"]


def test_with_talon_v2_off_the_route_is_not_found():
    response, fake = get(enabled=False)
    assert response.status_code == 404
    assert body_of(response) == {"detail": "Not Found"}
    assert fake.requests == []


def test_a_dotted_code_goes_in_the_path_as_one_segment():
    _, fake = get(DOTTED, "ana")
    assert fake.requests[0].url.raw_path == b"/v2/knowledge/acme.io"


@pytest.mark.parametrize("value", ["..%2F..%2Fthreads", "%2e%2e", "acme%2Fstats", "a%3Fb", "a%23b", "a%00b", "a%0Ab", "a%E2%80%AEb"])
def test_unsafe_codes_never_reach_talon(value):
    response, fake = get(value)
    assert response.status_code in (400, 404)
    assert fake.requests == []


def test_the_client_builds_the_knowledge_path_with_the_same_rules():
    assert memory_client.memory_path(["acme.io"], talon_knowledge.PREFIX) == "/v2/knowledge/acme.io"
    with pytest.raises(memory_client.UnsafePath):
        memory_client.memory_path([".."], talon_knowledge.PREFIX)
    assert memory_client.memory_path(["acme.io", "stats"]) == "/v2/memory/acme.io/stats"  # Memory's default


def test_the_database_session_is_closed_before_talon_is_asked():
    """The request's own session: the fixture's seeding closes sessions of its own first."""
    closed = []
    seen = {}
    original_close = AsyncSession.close
    original_problem = talon_knowledge.customer_problem

    async def close(self):
        closed.append(self)
        return await original_close(self)

    async def customer_problem(user, session, customer_code):
        seen["session"] = session
        return await original_problem(user, session, customer_code)

    def respond(request):
        seen["closed_first"] = any(session is seen["session"] for session in closed)
        return talon()(request)

    with patch.object(AsyncSession, "close", close), patch.object(talon_knowledge, "customer_problem", customer_problem):
        response, _ = get(respond=respond)
    assert response.status_code == 200
    assert seen["closed_first"] is True


# ── answers that aren't shown ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "answer",
    [
        payload(GLOBEX),  # another customer's
        payload("acme"),  # not exactly the code asked for
        empty(GLOBEX),
        {k: v for k, v in payload().items() if k != "customer_code"},
        payload(customer_code=None),
    ],
)
def test_an_answer_that_isnt_the_customers_is_a_502_and_never_shown(answer):
    response, _ = get(answer=answer)
    assert response.status_code == 502
    assert body_of(response) == {"detail": talon_memory.WRONG_SHAPE, "code": "bad_answer"}
    assert b"wazuh" not in response.content


@pytest.mark.parametrize("status", ["unknown", "OK", "", None, 1, ["ok"]])
def test_an_unknown_status_is_a_502(status):
    response, _ = get(answer=payload(status=status))
    assert response.status_code == 502
    assert body_of(response) == {"detail": talon_memory.WRONG_SHAPE, "code": "bad_answer"}


def test_an_answer_without_a_status_is_a_502():
    answer = {k: v for k, v in payload().items() if k != "status"}
    assert get(answer=answer)[0].status_code == 502


@pytest.mark.parametrize(
    "answer, status, detail, code",
    [
        (httpx.Response(404, json={"detail": "Not Found"}), 404, talon_knowledge.OLD_TALON, "unsupported"),
        (httpx.Response(404, json={"detail": "unknown customer"}), 404, talon_knowledge.OLD_TALON, "unsupported"),  # any 404
        (httpx.Response(404, text="<html>nginx</html>"), 404, talon_knowledge.OLD_TALON, "unsupported"),
        (httpx.Response(400, json={"detail": "invalid customer_code"}), 400, talon_knowledge.REFUSED_CODE, "invalid"),
        (httpx.Response(400, json={"detail": f"bad {TALON_KEY} at 10.0.0.5"}), 400, talon_knowledge.REFUSED_CODE, "invalid"),
        (httpx.Response(422, json={"detail": "invalid request"}), 400, talon_knowledge.REFUSED_CODE, "invalid"),
        (httpx.Response(502, json={"detail": "knowledge read failed"}), 502, talon_knowledge.READ_FAILED, "unavailable"),
        (httpx.Response(502, json={"detail": "mysql at 10.0.0.5 refused"}), 502, talon_knowledge.READ_FAILED, "unavailable"),
        (httpx.Response(401, json={"error": "Unauthorized"}), 502, talon_memory.KEY_REFUSED, "unavailable"),  # never a 401
        (httpx.Response(403, json={"detail": "no"}), 502, talon_memory.FAILED, "unavailable"),
        (httpx.Response(500, text=f"Traceback ... {TALON_KEY} 10.0.0.5"), 502, talon_memory.FAILED, "unavailable"),
        (httpx.Response(503, json={"detail": "down at 10.0.0.5"}), 502, talon_memory.FAILED, "unavailable"),
        (httpx.Response(200, content=b"not json"), 502, talon_memory.NOT_JSON, "bad_answer"),
        (httpx.Response(204), 502, talon_memory.NOT_JSON, "bad_answer"),
        (httpx.Response(200, json=[1, 2]), 502, talon_memory.WRONG_SHAPE, "bad_answer"),
        (
            httpx.Response(200, content=gzip.compress(json.dumps(payload()).encode()), headers={"content-encoding": "gzip"}),
            502,
            talon_memory.WRONG_SHAPE,
            "bad_answer",
        ),
        (httpx.Response(302, headers={"location": "http://elsewhere.invalid/v2/threads"}), 502, talon_memory.FAILED, "unavailable"),
        (httpx.ConnectError("connection refused to talon.invalid:3100"), 502, talon_knowledge.UNREACHABLE, "unavailable"),
        (httpx.ReadTimeout("read timed out from 10.0.0.5"), 504, talon_knowledge.NO_ANSWER, "unavailable"),
    ],
)
def test_talons_refusals_and_failures_are_fixed_texts(answer, status, detail, code):
    response, fake = get(answer=answer)
    assert response.status_code == status
    assert body_of(response) == {"detail": detail, "code": code}
    assert response.headers["cache-control"] == "no-store"
    assert TALON_KEY.encode() not in response.content and b"10.0.0.5" not in response.content
    assert len(fake.requests) == 1  # a redirect is never followed


def test_a_talon_that_never_answers_times_out(monkeypatch):
    monkeypatch.setattr(memory_client, "TIMEOUT_SECONDS", 0.05)

    async def slow(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=payload())

    response, _ = get(respond=slow)
    assert response.status_code == 504
    assert body_of(response) == {"detail": talon_knowledge.NO_ANSWER, "code": "unavailable"}


def test_the_deadline_is_the_clients_default(monkeypatch):
    seen = []
    original = memory_client.request

    async def spy(*args, **kwargs):
        seen.append(kwargs.get("timeout"))
        return await original(*args, **kwargs)

    monkeypatch.setattr(memory_client, "request", spy)
    get()
    assert seen == [None] and memory_client.TIMEOUT_SECONDS == 8.0


def test_a_huge_answer_is_not_read(monkeypatch):
    monkeypatch.setattr(memory_client, "MAX_BODY_BYTES", 1000)
    response, _ = get(answer=payload(not_measured=["x" * 5000]))
    assert response.status_code == 502
    assert body_of(response) == {"detail": talon_memory.WRONG_SHAPE, "code": "bad_answer"}


def test_no_connector_or_no_url_asks_nothing():
    response, fake = get(attributes=None)
    assert response.status_code == 502 and body_of(response)["detail"] == talon_memory.NO_CONNECTOR
    response, fake = get(attributes=connector(connector_url=""))
    assert body_of(response)["detail"] == talon_memory.NOT_CONFIGURED and fake.requests == []


# ── what is shown of an answer ────────────────────────────────────────────────


def test_unknown_fields_are_dropped():
    answer = payload(
        secret="x",
        sources=[{**source(), "index_stats": {"secret": "x"}}],
        coverage={"available": ["endpoint"], "extra": ["network"]},
    )
    body = body_of(get(answer=answer)[0])
    assert set(body) == {
        "success",
        "customer_code",
        "status",
        "measured_at",
        "field_days",
        "event_days",
        "coverage",
        "sources",
        "not_measured",
    }
    assert set(body["sources"][0]) == {"pattern", "categories", "events", "degraded", "measured_at", "fields"}
    assert set(body["coverage"]) == {"available", "degraded", "unavailable"}


def test_categories_are_allowlisted_and_once_each():
    answer = payload(
        coverage={"available": ["endpoint", "endpoint", "printers", 7], "degraded": "identity", "unavailable": None},
        sources=[source(categories=["endpoint", "printers", None, "endpoint", "waf"])],
    )
    body = body_of(get(answer=answer)[0])
    assert body["coverage"] == {"available": ["endpoint"], "degraded": [], "unavailable": []}
    assert body["sources"][0]["categories"] == ["endpoint", "waf"]


@pytest.mark.parametrize("coverage", [None, "all", 7, ["endpoint"]])
def test_a_malformed_coverage_is_none(coverage):
    response, _ = get(answer=payload(coverage=coverage))
    assert response.status_code == 200 and body_of(response)["coverage"] is None


def test_roles_are_allowlisted_and_keep_at_most_three_names():
    names = ["a_name", "b_name", "b_name", "c_name", "d_name"]
    fields = {"host": names, "password": ["pw"], "user": [], "url": "not a list", "process": [7, None, "good_name"]}
    body = body_of(get(answer=payload(sources=[source(fields=fields)]))[0])
    assert body["sources"][0]["fields"] == {"host": ["a_name", "b_name", "c_name"], "process": ["good_name"]}


def test_every_role_of_the_contract_is_kept():
    fields = {role: ["some_field"] for role in talon_knowledge.ROLES}
    assert len(fields) == 12
    assert body_of(get(answer=payload(sources=[source(fields=fields)]))[0])["sources"][0]["fields"] == fields


@pytest.mark.parametrize(
    "bad",
    [
        {"events": "12"},
        {"events": -1},
        {"events": True},
        {"events": 1.5},
        {"degraded": "yes"},
        {"measured_at": "yesterday"},
        {"measured_at": 5},
        {"fields": "all"},
        {"fields": ["host"]},
        {"categories": "endpoint"},
    ],
)
def test_a_malformed_source_field_is_none_or_empty_and_the_source_stays(bad):
    response, _ = get(answer=payload(sources=[source(**bad)]))
    assert response.status_code == 200
    (row,) = body_of(response)["sources"]
    key = next(iter(bad))
    assert row[key] in (None, [], {})
    assert row["pattern"] == "wazuh-lab_*"


def test_a_malformed_top_level_field_is_dropped_not_fatal():
    answer = payload(measured_at="soon", field_days="30", event_days=-7, sources="many", not_measured={"a": 1})
    response, _ = get(answer=answer)
    assert response.status_code == 200
    body = body_of(response)
    assert body["measured_at"] is None and body["field_days"] is None and body["event_days"] is None
    assert body["sources"] == [] and body["not_measured"] == []


def test_unusable_sources_are_dropped_and_patterns_are_bounded():
    good = source("x" * talon_memory.MAX_ID)
    answer = payload(
        sources=[
            source("a_*"),
            source("a_*", events=9),  # a duplicate: the first stays
            source("y" * (talon_memory.MAX_ID + 1)),  # too long: dropped, never cut
            source(""),
            source(7),
            source("evil‮_*"),
            source("line\nbreak"),
            {"events": 1},
            "not a dict",
            good,
        ],
    )
    body = body_of(get(answer=answer)[0])
    assert [s["pattern"] for s in body["sources"]] == ["a_*", good["pattern"]]
    assert body["sources"][0]["events"] == 3400000


def test_field_names_are_bounded_and_taken_whole():
    fields = {"host": ["n" * talon_knowledge.MAX_FIELD, "m" * (talon_knowledge.MAX_FIELD + 1), "bad\x07name"]}
    body = body_of(get(answer=payload(sources=[source(fields=fields)]))[0])
    assert body["sources"][0]["fields"] == {"host": ["n" * talon_knowledge.MAX_FIELD]}


def test_at_most_200_sources_and_200_not_measured():
    answer = payload(sources=[source(f"s{n}_*") for n in range(250)], not_measured=[f"n{n}_*" for n in range(250)])
    body = body_of(get(answer=answer)[0])
    assert len(body["sources"]) == 200 and len(body["not_measured"]) == 200
    assert body["sources"][-1]["pattern"] == "s199_*" and body["not_measured"][-1] == "n199_*"


def test_not_measured_is_bounded_and_once_each():
    answer = payload(not_measured=["a_*", "a_*", "b" * 256, "", 7, None, "c​_*", "d_*"])
    assert body_of(get(answer=answer)[0])["not_measured"] == ["a_*", "d_*"]


def test_no_key_password_or_user_info_reaches_the_browser():
    leak = f"key {TALON_KEY} pass {PASSWORD} at http://admin:hunter2@talon.invalid/x?api_key=abc123 done"
    answer = payload(
        measured_at=leak,
        sources=[
            source(f"wazuh-{TALON_KEY}_*"),
            source(f"wazuh-{PASSWORD}_*"),
            source("http://admin:hunter2@talon.invalid/x"),
            source("wazuh-x?api_key=abc123"),
            source(leak),
            source(measured_at=leak, fields={"host": [leak, f"field_{TALON_KEY}", "agent_name"]}),
        ],
        not_measured=[f"forti-{TALON_KEY}_*", f"forti-{PASSWORD}_*", "http://admin:hunter2@talon.invalid/x", leak, "forti_*"],
    )
    response, _ = get(answer=answer)
    assert response.status_code == 200
    content = response.content
    assert TALON_KEY.encode() not in content and PASSWORD.encode() not in content
    assert b"hunter2" not in content and b"abc123" not in content and b"admin:" not in content
    body = body_of(response)
    assert [s["pattern"] for s in body["sources"]] == ["wazuh-lab_*"]
    assert body["sources"][0]["fields"] == {"host": ["agent_name"]} and body["sources"][0]["measured_at"] is None
    assert body["not_measured"] == ["forti_*"] and body["measured_at"] is None


def test_every_answer_is_no_store():
    for response in (get()[0], get(answer=empty())[0], get(answer=payload(GLOBEX))[0], get(GLOBEX, "ana")[0]):
        assert response.headers["cache-control"] == "no-store"
