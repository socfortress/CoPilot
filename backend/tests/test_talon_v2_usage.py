"""CoPilot's proxy of talon-analyst's usage and budgets APIs (plan M5-9a; talon-analyst SPEC §13.5
FR-COST-4/5, D51), and the availability's ``run_view``.

Real routers, a real in-memory database, talon-analyst as an ``httpx.MockTransport``
(``tests/talon_v2_support.py``). Pinned here:
- the setting off: every new route (usage, budgets, the run view) answers 404 ``{"detail": "Not
  Found"}`` with nothing sent upstream or to Phoenix; portal users and the scheduler are refused;
- identity: each of the five headers sent once, the user's own; forged ones dropped;
- ``GET /usage``: the query checked as talon-analyst checks it, with its texts, before any upstream
  call; ``customer_code`` held to the grammar and the caller's customers; only four parameters
  forwarded; an admin's ``group_by=user`` gains usernames, an analyst's doesn't;
- per-investigation cost: the job row, its alert's customer and tags, and the alert being the job's
  customer's, all checked first; unknown and refused answer the same 404 with no upstream call;
- a thread's cost: a UUID, relayed;
- budgets: admin only, by token and by database role (a demoted admin's token is refused); the PUT's
  strict body, customer check, old values read first, and the audit of every outcome;
- refusals keep their status with a fixed text, a 401 becomes 502, every answer is ``no-store``;
- ``run_view`` follows the setting and the connector, with no Phoenix call.

Run with: cd backend && python -m pytest tests/test_talon_v2_usage.py
"""

import json

import httpx
import pytest

from app.connectors.talon.services import talon_usage
from tests.talon_v2_support import ACME
from tests.talon_v2_support import DOTTED
from tests.talon_v2_support import GLOBEX
from tests.talon_v2_support import JOB_ACME
from tests.talon_v2_support import JOB_GLOBEX
from tests.talon_v2_support import JOB_MISMATCH
from tests.talon_v2_support import NEW_ROUTES
from tests.talon_v2_support import TALON_KEY
from tests.talon_v2_support import Upstream
from tests.talon_v2_support import as_user
from tests.talon_v2_support import call
from tests.talon_v2_support import phoenix_connector
from tests.talon_v2_support import restrict_tags

THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
USAGE = "/talon/v2/usage?from=2026-10-01&to=2026-10-16"
IDENTITY = ("x-talon-user", "x-talon-role", "x-talon-customers", "x-talon-tags", "x-talon-untagged")
FORGED = {
    "X-Talon-User": "1",
    "X-Talon-Role": "admin",
    "X-Talon-Customers": "*",
    "X-Talon-Tags": "*",
    "X-Talon-Untagged": "true",
    "x-api-key": "forged-key",
    "Cookie": "session=browser",
}


def report(groups=None):
    return {
        "from": "2026-10-01",
        "to": "2026-10-16",
        "group_by": "customer",
        "customer_code": None,
        "groups": groups or [],
        "truncated": False,
        "total": {},
    }


def budgets_answer(code=ACME, daily=("10", "override"), monthly=(None, "unset")):
    entry = {"customer_code": code}
    for window, (limit, source) in (("daily", daily), ("monthly", monthly)):
        entry[window] = {
            "window": window,
            "limit_usd": limit,
            "source": source,
            "spent_usd": "1.5",
            "remaining_usd": "8.5",
            "warning": False,
            "exhausted": False,
        }
    return {"warn_at": "0.8", "customers": [entry], "user": {}, "general": None}


def by_route(request):
    """talon-analyst's answers by path."""
    path = request.url.path
    if path == "/v2/usage":
        return httpx.Response(200, json=report())
    if path.startswith("/v2/usage/investigations/"):
        return httpx.Response(200, json={"job_id": path.rsplit("/", 1)[1], "runs": [], "total": {}})
    if path.startswith("/v2/usage/threads/"):
        return httpx.Response(200, json={"thread_id": path.rsplit("/", 1)[1], "groups": [], "total": {}})
    if path == "/v2/budgets":
        return httpx.Response(200, json=budgets_answer(request.url.params.get("customer_code") or ACME))
    if path.startswith("/v2/budgets/"):
        return httpx.Response(200, json=budgets_answer(path.rsplit("/", 1)[1], daily=("25", "override"))["customers"][0])
    return httpx.Response(404, json={"detail": "Not Found"})


def upstream():
    return Upstream(by_route)


# ── the gate and the roles ────────────────────────────────────────────────────


@pytest.mark.parametrize("enabled", [None, False], ids=["no row", "off"])
@pytest.mark.parametrize("who", ["ana", "admin"])
def test_with_the_setting_off_every_new_route_is_not_found(enabled, who):
    async def scenario(client, ctx):
        answers = [(m, p, await client.request(m, p, json=b, headers=as_user(who))) for m, p, b in NEW_ROUTES]
        return [(m, p, r.status_code, r.json()) for m, p, r in answers], ctx

    answers, ctx = call(scenario, enabled=enabled, upstream=upstream())
    for method, path, status, body in answers:
        assert (status, body) == (404, {"detail": "Not Found"}), (method, path)
    assert ctx.upstream.requests == [] and ctx.phoenix.requests == [] and ctx.audit.await_count == 0


@pytest.mark.parametrize("who", ["portal", "sched"])
def test_portal_users_and_the_scheduler_are_refused_every_new_route(who):
    async def scenario(client, ctx):
        return [(await client.request(m, p, json=b, headers=as_user(who))).status_code for m, p, b in NEW_ROUTES], ctx

    statuses, ctx = call(scenario, upstream=upstream())
    assert statuses == [403] * len(NEW_ROUTES)
    assert ctx.upstream.requests == [] and ctx.phoenix.requests == []


def test_without_a_token_every_new_route_is_401_even_while_off():
    async def scenario(client, ctx):
        return [(await client.request(m, p, json=b)).status_code for m, p, b in NEW_ROUTES]

    assert call(scenario, enabled=False) == [401] * len(NEW_ROUTES)


# ── identity ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    [USAGE, f"/talon/v2/usage/investigations/{JOB_ACME}", f"/talon/v2/usage/threads/{THREAD}"],
)
def test_the_identity_headers_are_the_users_own_each_once_and_forged_ones_are_dropped(path):
    async def scenario(client, ctx):
        response = await client.get(path, headers=as_user("ana", **FORGED))
        return response, ctx.upstream.requests

    response, (sent,) = call(scenario, upstream=upstream())
    assert response.status_code == 200
    for name in IDENTITY:
        assert len(sent.headers.get_list(name)) == 1, name
    assert sent.headers["x-talon-user"] == "2" and sent.headers["x-talon-role"] == "analyst"
    assert sent.headers["x-talon-customers"] == ",".join(sorted([ACME, DOTTED, "chat"]))
    assert sent.headers["x-api-key"] == TALON_KEY
    assert "cookie" not in sent.headers


def test_a_responder_is_sent_as_one_role():
    async def scenario(client, ctx):
        await client.get(USAGE, headers=as_user("resp"))
        return ctx.upstream.requests

    (sent,) = call(scenario, upstream=upstream())
    assert sent.headers["x-talon-role"] == "responder" and sent.headers["x-talon-customers"] == ACME


# ── GET /usage ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "query, status, detail",
    [
        ("", 422, "invalid request"),
        ("from=2026-10-01", 422, "invalid request"),
        ("from=2026-10-01T00:00:00&to=2026-10-02", 422, "invalid request"),
        ("from=1760000000&to=2026-10-02", 422, "invalid request"),
        ("from=2026-02-30&to=2026-03-02", 422, "invalid request"),
        ("from=2026-10-01&to=2026-10-02&group_by=tenant", 422, "invalid request"),
        ("from=2026-10-01&to=2026-10-02&customer_code=" + "A" * 65, 422, "invalid request"),
        ("from=2026-10-02&to=2026-10-01", 400, "from is after to"),
        ("from=2025-01-01&to=2026-01-02", 400, "the range is longer than 366 days"),
        ("from=9999-12-31&to=9999-12-31", 400, "to is out of range"),
        ("from=2026-10-01&to=2026-10-02&customer_code=a%20b", 400, "invalid customer_code"),
        ("from=2026-10-01&to=2026-10-02&customer_code=.acme", 400, "invalid customer_code"),
        (f"from=2026-10-01&to=2026-10-02&customer_code={GLOBEX}", 403, "customer not accessible"),
    ],
)
def test_a_usage_query_talon_analyst_would_refuse_is_refused_here_with_its_text(query, status, detail):
    async def scenario(client, ctx):
        return await client.get(f"/talon/v2/usage?{query}", headers=as_user("ana")), ctx.upstream.requests

    response, sent = call(scenario, upstream=upstream())
    assert (response.status_code, response.json()) == (status, {"detail": detail})
    assert response.headers["cache-control"] == "no-store"
    assert sent == []


def test_a_full_year_with_its_leap_day_is_allowed_and_only_four_parameters_are_forwarded():
    async def scenario(client, ctx):
        path = f"/talon/v2/usage?from=2024-01-01&to=2024-12-31&group_by=day&customer_code={DOTTED}&cursor=x&user_id=1"
        return await client.get(path, headers=as_user("ana")), ctx.upstream.requests

    response, (sent,) = call(scenario, upstream=upstream())
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert sent.method == "GET" and sent.url.path == "/v2/usage"
    assert dict(sent.url.params) == {"from": "2024-01-01", "to": "2024-12-31", "group_by": "day", "customer_code": DOTTED}


def test_the_usage_answer_is_relayed_as_talon_analyst_sent_it():
    raw = json.dumps(report([{"key": ACME, "cost_usd": "0.100000000001"}]), separators=(",", ":")).encode()

    async def scenario(client, ctx):
        return await client.get(USAGE, headers=as_user("ana"))

    response = call(scenario, upstream=Upstream(lambda request: httpx.Response(200, content=raw)))
    assert response.status_code == 200 and response.content == raw


def test_an_admins_group_by_user_gains_usernames():
    groups = [{"key": "2", "cost_usd": "1"}, {"key": None, "cost_usd": "2"}, {"key": "999", "cost_usd": "3"}, {"key": "1", "cost_usd": "4"}]

    async def scenario(client, ctx):
        return await client.get(USAGE + "&group_by=user", headers=as_user("admin"))

    response = call(scenario, upstream=Upstream(lambda request: httpx.Response(200, json=report(groups))))
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert [(g["key"], g["username"]) for g in response.json()["groups"]] == [("2", "ana"), (None, None), ("999", None), ("1", "admin")]


def test_an_analysts_group_by_user_is_relayed_unchanged():
    groups = [{"key": "2", "cost_usd": "1"}, {"key": None, "cost_usd": "2"}]

    async def scenario(client, ctx):
        return await client.get(USAGE + "&group_by=user", headers=as_user("ana"))

    response = call(scenario, upstream=Upstream(lambda request: httpx.Response(200, json=report(groups))))
    assert all("username" not in g for g in response.json()["groups"])


# ── one investigation's cost ──────────────────────────────────────────────────


def test_an_investigations_cost_is_asked_for_by_the_rows_own_id():
    async def scenario(client, ctx):
        return await client.get(f"/talon/v2/usage/investigations/{JOB_ACME}", headers=as_user("ana")), ctx.upstream.requests

    response, (sent,) = call(scenario, upstream=upstream())
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert sent.url.path == f"/v2/usage/investigations/{JOB_ACME}"


@pytest.mark.parametrize(
    "who, job",
    [
        ("ana", JOB_GLOBEX),  # another customer's job
        ("gus", JOB_ACME),
        ("ana", "copilot-inv-9-0"),  # unknown
        ("ana", JOB_ACME.upper()),  # a job id is exact
        ("ana", "x" * 65),
        ("ana", JOB_MISMATCH),  # the job says ACME; its alert is GLOBEX's
        ("admin", JOB_MISMATCH),
    ],
)
def test_an_investigation_the_caller_may_not_see_is_the_same_404_with_no_upstream_call(who, job):
    async def scenario(client, ctx):
        return await client.get(f"/talon/v2/usage/investigations/{job}", headers=as_user(who)), ctx.upstream.requests

    response, sent = call(scenario, upstream=upstream())
    assert (response.status_code, response.json()) == (404, {"detail": "investigation not found"})
    assert response.headers["cache-control"] == "no-store"
    assert sent == []


def test_an_investigation_whose_alert_is_outside_the_callers_tags_is_refused_with_no_upstream_call():
    async def scenario(client, ctx):
        await restrict_tags(ctx, ctx.acme_alert)
        return await client.get(f"/talon/v2/usage/investigations/{JOB_ACME}", headers=as_user("ana")), ctx.upstream.requests

    response, sent = call(scenario, upstream=upstream())
    assert response.status_code == 404 and sent == []


def test_an_investigation_is_rechecked_on_every_request():
    async def scenario(client, ctx):
        first = await client.get(f"/talon/v2/usage/investigations/{JOB_ACME}", headers=as_user("resp"))
        from sqlalchemy import delete

        from app.auth.models.users import UserCustomerAccess

        async with ctx.db.session() as session:
            await session.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == 5))
            await session.commit()
        second = await client.get(f"/talon/v2/usage/investigations/{JOB_ACME}", headers=as_user("resp"))
        return first.status_code, second.status_code, len(ctx.upstream.requests)

    assert call(scenario, upstream=upstream()) == (200, 404, 1)


# ── one thread's cost ─────────────────────────────────────────────────────────


def test_a_threads_cost_is_relayed_and_a_bad_id_is_refused_here():
    async def scenario(client, ctx):
        good = await client.get(f"/talon/v2/usage/threads/{THREAD.upper()}", headers=as_user("ana"))
        bad = await client.get("/talon/v2/usage/threads/not-a-uuid", headers=as_user("ana"))
        return good, bad, ctx.upstream.requests

    good, bad, sent = call(scenario, upstream=upstream())
    assert good.status_code == 200 and [r.url.path for r in sent] == [f"/v2/usage/threads/{THREAD}"]
    assert (bad.status_code, bad.json()) == (404, {"detail": "thread not found"})
    assert bad.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "status, body, expected_status, expected_detail",
    [
        (404, {"detail": "thread not found"}, 404, "thread not found"),
        (403, {"detail": "access to this thread's customer was removed"}, 403, "access to this thread's customer was removed"),
        (401, {"error": "Unauthorized"}, 502, "Talon request failed"),
        (503, {"detail": "usage queries are busy; try again shortly"}, 503, "Talon request failed"),
        (500, {"detail": "Traceback (most recent call last): secret"}, 500, "Talon request failed"),
        (422, {"detail": [{"loc": ["query"], "msg": "x"}]}, 422, "Talon request failed"),
    ],
)
def test_talon_analysts_refusals_keep_their_status_with_a_fixed_text(status, body, expected_status, expected_detail):
    async def scenario(client, ctx):
        return await client.get(f"/talon/v2/usage/threads/{THREAD}", headers=as_user("ana"))

    response = call(scenario, upstream=Upstream(lambda request: httpx.Response(status, json=body)))
    assert (response.status_code, response.json()) == (expected_status, {"detail": expected_detail})
    assert response.headers["cache-control"] == "no-store"


def test_no_answer_from_talon_analyst_is_a_502():
    def unreachable(request):
        raise httpx.ConnectError("talon.invalid:3100 refused")

    async def scenario(client, ctx):
        return await client.get(USAGE, headers=as_user("ana"))

    response = call(scenario, upstream=Upstream(unreachable))
    assert (response.status_code, response.json()) == (502, {"detail": "Talon request failed"})
    assert "talon.invalid" not in response.text


# ── budgets ───────────────────────────────────────────────────────────────────


def test_an_admin_reads_the_budgets():
    async def scenario(client, ctx):
        everything = await client.get("/talon/v2/budgets", headers=as_user("admin"))
        one = await client.get(f"/talon/v2/budgets?customer_code={GLOBEX}", headers=as_user("admin"))
        return everything, one, ctx.upstream.requests

    everything, one, sent = call(scenario, upstream=upstream())
    assert everything.status_code == one.status_code == 200
    assert everything.headers["cache-control"] == "no-store"
    assert [dict(r.url.params) for r in sent] == [{}, {"customer_code": GLOBEX}]
    assert sent[0].headers["x-talon-role"] == "admin" and sent[0].headers["x-talon-customers"] == "*"


@pytest.mark.parametrize("who, status", [("ana", 403), ("resp", 403), ("demoted", 403)])
def test_budgets_are_refused_for_anyone_but_a_database_admin(who, status):
    async def scenario(client, ctx):
        get = await client.get("/talon/v2/budgets", headers=as_user(who))
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": "25", "monthly_usd": None}, headers=as_user(who))
        return get, put, ctx

    get, put, ctx = call(scenario, upstream=upstream())
    assert get.status_code == put.status_code == status
    assert ctx.upstream.requests == []


def test_a_demoted_admins_put_is_refused_and_audited_as_a_failure():
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": "25", "monthly_usd": None}, headers=as_user("demoted"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert (put.status_code, put.json()) == (403, {"detail": "Only an admin may read or set Talon budgets"})
    assert put.headers["cache-control"] == "no-store"
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["action"].value == "talon_budget.update" and audited.kwargs["result"].value == "failure"
    assert audited.kwargs["actor_user_id"] == 4


def test_an_admins_put_reads_the_old_values_sets_the_new_and_is_audited():
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": "25", "monthly_usd": "unlimited"}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert put.status_code == 200 and put.headers["cache-control"] == "no-store"
    before, change = ctx.upstream.requests
    assert (before.method, before.url.path, dict(before.url.params)) == ("GET", "/v2/budgets", {"customer_code": ACME})
    assert (change.method, change.url.path) == ("PUT", f"/v2/budgets/{ACME}")
    assert json.loads(change.content) == {"daily_usd": "25", "monthly_usd": "unlimited"}
    assert change.headers["x-talon-role"] == "admin"
    (audited,) = ctx.audit.await_args_list
    kwargs = audited.kwargs
    assert kwargs["action"].value == "talon_budget.update" and kwargs["result"].value == "success"
    assert (kwargs["entity_type"], kwargs["entity_id"], kwargs["customer_code"]) == ("talon_budget", ACME, ACME)
    assert kwargs["old_value"] == {"daily": {"limit_usd": "10", "source": "override"}, "monthly": {"limit_usd": None, "source": "unset"}}
    assert kwargs["new_value"] == {"daily_usd": "25", "monthly_usd": "unlimited"}


def test_null_and_null_restores_the_defaults():
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": None, "monthly_usd": None}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert put.status_code == 200
    assert json.loads(ctx.upstream.requests[1].content) == {"daily_usd": None, "monthly_usd": None}


@pytest.mark.parametrize(
    "body",
    [
        {"daily_usd": 25, "monthly_usd": None},  # a number, not a decimal string
        {"daily_usd": 25.5, "monthly_usd": None},
        {"daily_usd": True, "monthly_usd": None},
        {"daily_usd": "25"},  # both are required: the body replaces both
        {"daily_usd": "25", "monthly_usd": None, "customer_code": GLOBEX},
        {"daily_usd": "-5", "monthly_usd": None},
        {"daily_usd": "0", "monthly_usd": None},
        {"daily_usd": "0.0", "monthly_usd": None},
        {"daily_usd": "1e3", "monthly_usd": None},
        {"daily_usd": " 25", "monthly_usd": None},
        {"daily_usd": "", "monthly_usd": None},
        {"daily_usd": "NaN", "monthly_usd": None},
        {"daily_usd": "Infinity", "monthly_usd": None},
        {"daily_usd": "25.0000000000001", "monthly_usd": None},  # 13 places
        {"daily_usd": "1000000000.01", "monthly_usd": None},
        {"daily_usd": "Unlimited", "monthly_usd": None},
        ["25", None],
        "25",
        None,
    ],
)
def test_a_put_body_that_isnt_strictly_an_override_is_refused_and_audited(body):
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", content=json.dumps(body), headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert put.status_code == 422 and isinstance(put.json()["detail"], str)
    assert put.headers["cache-control"] == "no-store"
    assert ctx.upstream.requests == []
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["result"].value == "failure"


def test_a_put_body_that_isnt_json_or_is_too_large_is_refused():
    async def scenario(client, ctx):
        bad = await client.put(f"/talon/v2/budgets/{ACME}", content=b"{daily", headers=as_user("admin"))
        big = await client.put(f"/talon/v2/budgets/{ACME}", content=b" " * 5000 + b"{}", headers=as_user("admin"))
        return bad.status_code, big.status_code, ctx.upstream.requests, ctx.audit.await_count

    assert call(scenario, upstream=upstream()) == (422, 422, [], 2)


@pytest.mark.parametrize("amount", ["25", "12.50", "0.000000000001", "1000000000"])
def test_a_decimal_amount_is_accepted_as_written(amount):
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": amount, "monthly_usd": None}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert put.status_code == 200 and json.loads(ctx.upstream.requests[1].content)["daily_usd"] == amount


@pytest.mark.parametrize(
    "code, status",
    [("a b", 400), ("nosuch", 400), ("acme", 400)],  # not the grammar; no such customer; not exactly a customer's code
)
def test_a_put_for_a_customer_that_isnt_one_is_refused_and_audited(code, status):
    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{code}", json={"daily_usd": "25", "monthly_usd": None}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=upstream())
    assert put.status_code == status and ctx.upstream.requests == []
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["result"].value == "failure"


def test_a_put_talon_analyst_refuses_keeps_its_status_and_is_audited_with_the_old_values():
    def respond(request):
        if request.method == "PUT":
            return httpx.Response(403, json={"detail": "only an admin may set a budget"})
        return by_route(request)

    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": "25", "monthly_usd": None}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=Upstream(respond))
    assert (put.status_code, put.json()) == (403, {"detail": "only an admin may set a budget"})
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["result"].value == "failure" and audited.kwargs["old_value"]["daily"]["limit_usd"] == "10"


@pytest.mark.parametrize("status, expected", [(401, 502), (500, 502), (None, 502), (403, 403)])
def test_without_the_old_values_nothing_is_changed(status, expected):
    def respond(request):
        if request.method == "GET":
            if status is None:
                raise httpx.ConnectError("down")
            return httpx.Response(status, json={"detail": "customer not accessible"})
        return by_route(request)

    async def scenario(client, ctx):
        put = await client.put(f"/talon/v2/budgets/{ACME}", json={"daily_usd": "25", "monthly_usd": None}, headers=as_user("admin"))
        return put, ctx

    put, ctx = call(scenario, upstream=Upstream(respond))
    assert put.status_code == expected
    assert [r.method for r in ctx.upstream.requests] == ["GET"]
    (audited,) = ctx.audit.await_args_list
    assert audited.kwargs["result"].value == "failure"


# ── availability ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enabled, connector, run_view",
    [
        (True, "default", True),
        (False, "default", False),
        (None, "default", False),
        (True, None, False),
        (True, phoenix_connector(connector_api_key=""), False),
        (True, phoenix_connector(connector_api_key=None), False),
        (True, phoenix_connector(connector_url=""), False),
    ],
)
def test_run_view_follows_the_setting_and_the_connector_with_no_phoenix_call(enabled, connector, run_view):
    async def scenario(client, ctx):
        return (await client.get("/talon/v2/availability", headers=as_user("ana"))).json(), ctx.phoenix.requests

    body, phoenix_requests = call(scenario, enabled=enabled, connector=connector)
    assert body["run_view"] is run_view and body["enabled"] is bool(enabled)
    assert phoenix_requests == []


def test_the_usage_rules_mirror_talon_analysts():
    assert talon_usage.GROUP_BY == {"customer", "model", "provider", "role", "stage", "day", "user"}
    assert talon_usage.MAX_DAYS == 366
    assert talon_usage.usage_query_problem({"from": "2026-10-01", "to": "2026-10-01"}) is None
