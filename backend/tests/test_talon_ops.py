"""The Talon Ops tab's proxy routes (``/api/talon/ops/...``; talon-analyst SPEC §5.7, D96; plan OJ-5).

Real routers, a real in-memory database and real request parsing (``tests/talon_v2_support.py``);
talon-analyst is an ``httpx.MockTransport``. ``FakeTalon`` keeps findings by talon-analyst's rules
(``api/ops.py``), or, ``leaky``, answers everything to everyone, to show CoPilot's own checks hold
when talon-analyst's don't:

- the identity sent is the signed-in user's, built as v2 chat builds it; the actor is the username;
- a customer finding only for the caller's customers, a platform one only for ``*``; a list drops
  the rest, a detail or an action answers 404;
- an action reads the finding first, sends its stored customer, and refuses an answer naming another;
- run now is an admin's, by the database role; every action is audited;
- off, every route is the "Not Found" of an unknown path; upstream errors keep fixed texts.

Run with: cd backend && python -m pytest tests/test_talon_ops.py
"""

import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import AsyncMock
from unittest.mock import patch

import httpx
import pytest

from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditResult  # noqa: E402
from app.connectors.talon.services import talon_ops  # noqa: E402
from tests.talon_v2_support import ACME  # noqa: E402
from tests.talon_v2_support import DOTTED  # noqa: E402
from tests.talon_v2_support import GLOBEX  # noqa: E402
from tests.talon_v2_support import TALON_CONNECTOR  # noqa: E402
from tests.talon_v2_support import TALON_KEY  # noqa: E402
from tests.talon_v2_support import Upstream  # noqa: E402
from tests.talon_v2_support import as_user  # noqa: E402
from tests.talon_v2_support import body_of  # noqa: E402
from tests.talon_v2_support import call  # noqa: E402

T = "2026-10-24T06:00:00+00:00"


def finding(fid, customer, **over):
    base = {
        "id": fid,
        "fingerprint": f"quiet_endpoints:{customer}:agent:{fid:03d}",
        "job": "quiet_endpoints",
        "job_version": 1,
        "customer_code": customer,
        "kind": "wazuh_quiet",
        "severity": "medium",
        "title": f"host-{fid}: not seen by Wazuh for 5 days",
        "evidence": {"agent_id": f"{fid:03d}", "agent_name": f"host-{fid}", "wazuh_days_quiet": 5.1, "conditions": ["wazuh_quiet"]},
        "artifact": None,
        "why": "It **stopped** reporting. <img src=x onerror=alert(1)>",
        "recommendation": "Check the agent [service](http://evil.example).",
        "priority": 2,
        "explained": True,
        "status": "open",
        "first_seen": T,
        "last_seen": T,
        "resolved_at": None,
        "resolved_reason": None,
        "stale_since": None,
        "explain_attempted_at": T,
        "muted_until": None,
        "acted_by": None,
        "acted_at": None,
        "notified_at": None,
        "updated_at": T,
    }
    base.update(over)
    return base


class FakeTalon:
    """talon-analyst's ``/v2/ops`` as ``api/ops.py`` serves it, or ``leaky``: no checks at all."""

    def __init__(self, *, leaky=False, findings=None):
        self.leaky = leaky
        self.findings = {f["id"]: f for f in (findings or [finding(1, ACME), finding(2, GLOBEX), finding(3, None), finding(4, DOTTED)])}
        self.post_override = None  # a dict merged into an action's answer
        self.upstream = Upstream(self.respond)

    def _customers(self, request):
        raw = request.headers["X-Talon-Customers"]
        return None if raw == "*" else set(filter(None, raw.split(",")))

    def _visible(self, request, code):
        if self.leaky:
            return True
        customers = self._customers(request)
        if code is None:
            return customers is None
        return customers is None or code in customers

    def respond(self, request):
        path = request.url.path
        params = request.url.params
        if path == "/v2/ops/findings":
            items = [f for f in self.findings.values() if self._visible(request, f["customer_code"])]
            if not self.leaky and params.get("platform") == "true":
                items = [f for f in items if f["customer_code"] is None]
            if not self.leaky and params.get("customer_code"):
                items = [f for f in items if f["customer_code"] == params["customer_code"]]
            return httpx.Response(200, json={"items": items, "next_cursor": None})
        if path.startswith("/v2/ops/findings/"):
            parts = path.split("/")
            fid = int(parts[4])
            row = self.findings.get(fid)
            named = params.get("customer_code")
            if (
                row is None
                or not self._visible(request, row["customer_code"])
                or (not self.leaky and named and row["customer_code"] != named)
            ):
                return httpx.Response(404, json={"detail": "finding not found"})
            if request.method == "POST":
                action = parts[5]
                status = {"acknowledge": "acknowledged", "mute": "muted", "reopen": "open"}[action]
                body = json.loads(request.content)
                row = {**row, "status": status, "acted_by": body["actor"], "muted_until": body.get("until")}
                if self.post_override:
                    row.update(self.post_override)
                self.findings[fid] = row
            return httpx.Response(200, json=row)
        if path == "/v2/ops/jobs":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "name": "quiet_endpoints",
                            "title": "Endpoints gone quiet",
                            "version": 1,
                            "scope": "customer",
                            "enabled": True,
                            "schedule": "0 6 * * *",
                            "schedule_status": "ACTIVE",
                            "last_fired_at": T,
                            "needs": ["copilot_db"],
                            "settings": {"warn_days": 3, "high_days": 14, "nested": {"x": 1}},
                            "last_run": run(GLOBEX),
                            "last_runs": [run(GLOBEX), run(ACME)],
                            "next_run": "2026-10-25T06:00:00+00:00",
                        },
                        {"name": "silent_log_sources", "title": "Log sources gone silent", "enabled": False, "last_runs": []},
                    ],
                },
            )
        if path == "/v2/ops/runs":
            return httpx.Response(200, json={"items": [run(ACME), run(GLOBEX), run(None)]})
        if path.startswith("/v2/ops/jobs/") and path.endswith("/run"):
            if request.headers["X-Talon-Role"] != "admin":
                return httpx.Response(403, json={"detail": "only an admin may run an ops job"})
            return httpx.Response(
                202,
                json={"job": path.split("/")[4], "workflow_id": "sched-talon-ops:quiet_endpoints-trigger-1", "status": "queued"},
            )
        return httpx.Response(404, json={"detail": "Not Found"})


def run(customer):
    return {
        "id": f"quiet_endpoints:{customer}:{T}",
        "job": "quiet_endpoints",
        "job_version": 1,
        "customer_code": customer,
        "tick": T,
        "triggered_by": "schedule",
        "status": "ok",
        "collected": True,
        "explained": "explained",
        "candidates": 2,
        "new": 1,
        "updated": 1,
        "resolved": 0,
        "error": None,
        "detail": {"stale": 0},
        "cost_usd": "0.0012",
        "duration_ms": 1520,
        "started_at": T,
        "finished_at": T,
    }


def scenario_with(fake, scenario, *, enabled=True):
    audit = AsyncMock()
    with patch.object(talon_ops, "record_audit_event", audit), patch.object(
        talon_ops,
        "get_connector_info_from_db",
        AsyncMock(return_value=TALON_CONNECTOR),
    ):

        async def wrapped(client, ctx):
            ctx.fake, ctx.ops_audit = fake, audit
            return await scenario(client, ctx)

        return call(wrapped, enabled=enabled, upstream=fake.upstream)


def ids(response):
    return [item["id"] for item in body_of(response)["items"]]


# ── who may ask, and the setting ──────────────────────────────────────────────

ROUTES = [
    ("GET", "/talon/ops/findings", None),
    ("GET", "/talon/ops/findings/1", None),
    ("POST", "/talon/ops/findings/1/acknowledge", None),
    ("POST", "/talon/ops/findings/1/mute", {"until": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}),
    ("POST", "/talon/ops/findings/1/reopen", None),
    ("GET", "/talon/ops/jobs", None),
    ("GET", "/talon/ops/runs", None),
    ("POST", "/talon/ops/jobs/quiet_endpoints/run", None),
]


@pytest.mark.parametrize("method,path,body", ROUTES)
def test_off_every_route_is_an_unknown_path_and_talon_is_never_asked(method, path, body):
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.request(method, path, json=body, headers=as_user("admin"))
        assert response.status_code == 404 and body_of(response) == {"detail": "Not Found"}
        assert fake.upstream.requests == []

    scenario_with(fake, scenario, enabled=False)


@pytest.mark.parametrize("who", ["portal", "sched"])
@pytest.mark.parametrize("method,path,body", ROUTES)
def test_only_the_soc_roles_reach_the_routes(who, method, path, body):
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.request(method, path, json=body, headers=as_user(who))
        assert response.status_code in (401, 403)
        assert fake.upstream.requests == []

    scenario_with(fake, scenario)


# ── the identity sent ─────────────────────────────────────────────────────────


def test_the_identity_is_the_signed_in_users_as_v2_chat_builds_it_and_nothing_from_the_browser():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.get(
            "/talon/ops/findings",
            headers=as_user("ana", **{"X-Talon-Customers": "*", "X-Talon-Role": "admin", "X-Talon-User": "1"}),
        )
        assert response.status_code == 200
        sent = fake.upstream.requests[0]
        assert sent.headers["x-api-key"] == TALON_KEY
        assert sent.headers["X-Talon-User"] == "2"
        assert sent.headers["X-Talon-Role"] == "analyst"
        assert sent.headers["X-Talon-Customers"] == ",".join(sorted([ACME, DOTTED, "chat"]))
        assert sent.headers.get_list("X-Talon-Customers") == [sent.headers["X-Talon-Customers"]]
        assert response.headers["cache-control"] == "no-store"

    scenario_with(fake, scenario)


# ── customers ─────────────────────────────────────────────────────────────────


def test_a_list_shows_only_the_callers_customers_even_when_talon_sends_more():
    fake = FakeTalon(leaky=True)

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/findings", headers=as_user("ana"))
        assert response.status_code == 200
        assert ids(response) == [1, 4]  # GLOBEX's and the platform finding are dropped
        assert body_of(response)["dropped"] == 2

    scenario_with(fake, scenario)


def test_an_admin_sees_every_customer_and_the_platform():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/findings", headers=as_user("admin"))
        assert sorted(ids(response)) == [1, 2, 3, 4]
        assert fake.upstream.requests[0].headers["X-Talon-Customers"] == "*"

    scenario_with(fake, scenario)


def test_platform_findings_are_only_for_a_caller_with_every_customer():
    fake = FakeTalon(leaky=True)

    async def scenario(client, ctx):
        refused = await client.get("/talon/ops/findings?platform=true", headers=as_user("ana"))
        assert refused.status_code == 403 and body_of(refused)["detail"] == talon_ops.PLATFORM_ONLY
        assert fake.upstream.requests == []
        allowed = await client.get("/talon/ops/findings?platform=true", headers=as_user("admin"))
        assert allowed.status_code == 200
        assert fake.upstream.requests[0].url.params["platform"] == "true"
        assert ids(allowed) == [3]  # the leaky answer's customer findings are dropped

    scenario_with(fake, scenario)


def test_a_platform_finding_is_a_404_for_a_scoped_analyst_even_when_talon_answers():
    fake = FakeTalon(leaky=True)

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/findings/3", headers=as_user("ana"))
        assert response.status_code == 404 and body_of(response)["code"] == "not_found"
        response = await client.get("/talon/ops/findings/3", headers=as_user("admin"))
        assert response.status_code == 200 and body_of(response)["finding"]["customer_code"] is None

    scenario_with(fake, scenario)


def test_a_customer_filter_for_a_customer_the_caller_lacks_is_refused_before_talon_is_asked():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.get(f"/talon/ops/findings?customer_code={GLOBEX}", headers=as_user("ana"))
        assert response.status_code == 403 and body_of(response)["detail"] == talon_ops.NOT_ACCESSIBLE
        bad = await client.get("/talon/ops/findings?customer_code=../x", headers=as_user("ana"))
        assert bad.status_code == 400
        assert fake.upstream.requests == []
        mine = await client.get(f"/talon/ops/findings?customer_code={ACME}", headers=as_user("ana"))
        assert ids(mine) == [1]
        assert fake.upstream.requests[-1].url.params["customer_code"] == ACME

    scenario_with(fake, scenario)


def test_another_customers_finding_is_the_same_404_as_an_unknown_one():
    fake = FakeTalon(leaky=True)

    async def scenario(client, ctx):
        other = await client.get("/talon/ops/findings/2", headers=as_user("ana"))
        unknown = await client.get("/talon/ops/findings/99", headers=as_user("ana"))
        assert other.status_code == unknown.status_code == 404
        assert body_of(other) == body_of(unknown)

    scenario_with(fake, scenario)


def test_a_named_customer_must_be_the_stored_one():
    fake = FakeTalon(leaky=True)

    async def scenario(client, ctx):
        response = await client.get(f"/talon/ops/findings/1?customer_code={DOTTED}", headers=as_user("ana"))
        assert response.status_code == 404  # finding 1 is ACME's, though ana has both
        response = await client.post(f"/talon/ops/findings/1/acknowledge?customer_code={DOTTED}", headers=as_user("ana"))
        assert response.status_code == 404
        assert all(r.method == "GET" for r in fake.upstream.requests)  # never acted on
        ctx.ops_audit.assert_not_awaited()

    scenario_with(fake, scenario)


# ── actions ───────────────────────────────────────────────────────────────────


def test_an_action_reads_the_finding_sends_its_stored_customer_and_the_session_actor():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.post("/talon/ops/findings/1/acknowledge", headers=as_user("ana"))
        assert response.status_code == 200
        assert body_of(response)["finding"]["status"] == "acknowledged"
        read, act = fake.upstream.requests
        assert read.method == "GET" and read.url.path == "/v2/ops/findings/1"
        assert act.method == "POST" and act.url.path == "/v2/ops/findings/1/acknowledge"
        assert act.url.params["customer_code"] == ACME
        assert json.loads(act.content) == {"actor": "ana"}
        assert act.headers["X-Talon-User"] == "2"
        audit = ctx.ops_audit.await_args.kwargs
        assert audit["action"] == AuditAction.TALON_OPS_ACKNOWLEDGE and audit.get("result", AuditResult.SUCCESS) == AuditResult.SUCCESS
        assert audit["actor_username"] == "ana" and audit["customer_code"] == ACME and audit["entity_id"] == "1"
        assert audit["old_value"]["status"] == "open" and audit["new_value"]["status"] == "acknowledged"

    scenario_with(fake, scenario)


@pytest.mark.parametrize("action", ["acknowledge", "reopen"])
def test_the_actor_can_never_come_from_the_body(action):
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.post(f"/talon/ops/findings/1/{action}", json={"actor": "someone-else"}, headers=as_user("ana"))
        assert response.status_code == 422
        assert fake.upstream.requests == []

    scenario_with(fake, scenario)


def test_a_mute_takes_until_only_and_checks_it_first():
    fake = FakeTalon()
    soon = datetime.now(timezone.utc) + timedelta(days=2)

    async def scenario(client, ctx):
        for until in [datetime.now(timezone.utc) - timedelta(hours=1), datetime.now(timezone.utc) + timedelta(days=91)]:
            refused = await client.post("/talon/ops/findings/1/mute", json={"until": until.isoformat()}, headers=as_user("ana"))
            assert refused.status_code == 400 and body_of(refused)["detail"] == talon_ops.INVALID_UNTIL
        extra = await client.post("/talon/ops/findings/1/mute", json={"until": soon.isoformat(), "actor": "x"}, headers=as_user("ana"))
        assert extra.status_code == 422
        assert fake.upstream.requests == []
        response = await client.post("/talon/ops/findings/1/mute", json={"until": soon.isoformat()}, headers=as_user("ana"))
        assert response.status_code == 200 and body_of(response)["finding"]["status"] == "muted"
        sent = json.loads(fake.upstream.requests[-1].content)
        assert sent["actor"] == "ana"
        assert datetime.fromisoformat(sent["until"]) == soon.replace(microsecond=soon.microsecond)
        assert ctx.ops_audit.await_args.kwargs["action"] == AuditAction.TALON_OPS_MUTE

    scenario_with(fake, scenario)


def test_an_action_answer_naming_another_customer_is_a_404_and_audited_as_failed():
    fake = FakeTalon()
    fake.post_override = {"customer_code": GLOBEX}

    async def scenario(client, ctx):
        response = await client.post("/talon/ops/findings/1/acknowledge", headers=as_user("admin"))
        assert response.status_code == 404 and body_of(response)["code"] == "not_found"
        assert ctx.ops_audit.await_args.kwargs["result"] == AuditResult.FAILURE

    scenario_with(fake, scenario)


def test_talons_refusal_of_an_action_keeps_its_status_and_reason():
    fake = FakeTalon()
    original = fake.respond

    def respond(request):
        if request.method == "POST":
            return httpx.Response(409, json={"detail": "a resolved finding can't be acknowledged"})
        return original(request)

    fake.upstream.respond = respond

    async def scenario(client, ctx):
        response = await client.post("/talon/ops/findings/1/acknowledge", headers=as_user("ana"))
        assert response.status_code == 409
        assert body_of(response) == {"detail": "a resolved finding can't be acknowledged", "code": "conflict"}
        assert ctx.ops_audit.await_args.kwargs["result"] == AuditResult.FAILURE

    scenario_with(fake, scenario)


# ── run now ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("who", ["ana", "resp", "demoted"])
def test_run_now_is_an_admins_by_the_database_role(who):
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.post("/talon/ops/jobs/quiet_endpoints/run", headers=as_user(who))
        assert response.status_code == 403 and body_of(response)["detail"] == talon_ops.ADMIN_ONLY
        assert fake.upstream.requests == []
        audit = ctx.ops_audit.await_args.kwargs
        assert audit["action"] == AuditAction.TALON_OPS_RUN and audit["result"] == AuditResult.FAILURE

    scenario_with(fake, scenario)


def test_an_admin_runs_a_job_now():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.post("/talon/ops/jobs/quiet_endpoints/run", headers=as_user("admin"))
        assert response.status_code == 202
        assert body_of(response)["status"] == "queued" and body_of(response)["job"] == "quiet_endpoints"
        sent = fake.upstream.requests[0]
        assert sent.url.path == "/v2/ops/jobs/quiet_endpoints/run" and sent.headers["X-Talon-Role"] == "admin"
        assert ctx.ops_audit.await_args.kwargs["action"] == AuditAction.TALON_OPS_RUN
        bad = await client.post("/talon/ops/jobs/..%2Fthreads/run", headers=as_user("admin"))
        assert bad.status_code in (400, 404)
        assert len(fake.upstream.requests) == 1

    scenario_with(fake, scenario)


# ── jobs and runs ─────────────────────────────────────────────────────────────


def test_jobs_show_only_the_callers_runs_and_whether_any_job_is_on():
    fake = FakeTalon()

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/jobs", headers=as_user("ana"))
        body = body_of(response)
        assert body["any_enabled"] is True
        quiet = body["items"][0]
        assert [r["customer_code"] for r in quiet["last_runs"]] == [ACME]
        assert quiet["last_run"]["customer_code"] == ACME  # Talon's GLOBEX "last_run" is not shown
        assert quiet["settings"] == {"warn_days": 3, "high_days": 14}
        assert body["items"][1]["enabled"] is False
        runs = await client.get("/talon/ops/runs", headers=as_user("ana"))
        assert [r["customer_code"] for r in body_of(runs)["items"]] == [ACME]

    scenario_with(fake, scenario)


def test_no_job_enabled_reads_as_off():
    fake = FakeTalon()
    fake.upstream.respond = lambda request: httpx.Response(200, json={"items": [{"name": "quiet_endpoints", "enabled": False}]})

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/jobs", headers=as_user("admin")))
        assert body["any_enabled"] is False

    scenario_with(fake, scenario)


# ── upstream errors and answers ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "status,body,expected,code",
    [
        (401, {"error": "Unauthorized"}, 502, "unavailable"),
        (404, {"detail": "Not Found"}, 404, "unsupported"),
        (500, {"detail": "secret stack trace"}, 502, "unavailable"),
        (422, {"detail": "invalid request"}, 400, "invalid"),
    ],
)
def test_upstream_errors_are_fixed_texts(status, body, expected, code):
    fake = FakeTalon()
    fake.upstream.respond = lambda request: httpx.Response(status, json=body)

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/findings", headers=as_user("admin"))
        assert response.status_code == expected and body_of(response)["code"] == code
        assert "secret" not in response.text

    scenario_with(fake, scenario)


def test_no_answer_is_a_502():
    fake = FakeTalon()

    def down(request):
        raise httpx.ConnectError("talon.invalid:8000 refused")

    fake.upstream.respond = down

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/findings", headers=as_user("admin"))
        assert response.status_code == 502 and "talon.invalid" not in response.text

    scenario_with(fake, scenario)


def test_answers_are_copied_field_by_field_and_the_models_text_stays_plain_text():
    secret = TALON_CONNECTOR["connector_api_key"]
    fake = FakeTalon(
        findings=[
            finding(1, ACME, why=f"line one\nline two\x07 key {secret}", unknown_field="leak", evidence={"a" * 70: 1, "ok": "x\x00y"}),
            finding(5, ACME, severity="critical"),  # not a severity talon-analyst writes: dropped
        ],
    )

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/findings", headers=as_user("ana")))
        assert ids_of(body) == [1] and body["dropped"] == 1
        item = body["items"][0]
        assert "unknown_field" not in item
        assert item["why"] == "line one\nline two key [redacted]"
        assert item["recommendation"] == "Check the agent [service](http://evil.example)."  # as written: the UI shows it as text
        assert item["evidence"] == {"ok": "x y"}

    scenario_with(fake, scenario)


def ids_of(body):
    return [item["id"] for item in body["items"]]
