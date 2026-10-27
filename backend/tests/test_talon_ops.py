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
        self.summary_answer = None  # a summary to send as it is (``leaky``'s), else one by the rules
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
        if path == "/v2/ops/summary":
            if self.summary_answer is not None:
                return httpx.Response(200, json=self.summary_answer)
            return httpx.Response(200, json=fake_summary([f for f in self.findings.values() if self._visible(request, f["customer_code"])]))
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


def counts(total=0, high=0, medium=0, low=0, info=0, stale=0, **extra):
    return {"total": total, "high": high, "medium": medium, "low": low, "info": info, "stale": stale, **extra}


def fake_summary(findings):
    """talon-analyst's ``/v2/ops/summary`` over these findings (the open ones counted)."""
    open_ = [f for f in findings if f["status"] == "open"]

    def tally(rows, **key):
        out = counts(len(rows), **key)
        for f in rows:
            out[f["severity"]] += 1
            out["stale"] += 1 if f["stale_since"] else 0
        return out

    customers = sorted({f["customer_code"] for f in open_}, key=lambda c: c or "")
    jobs = sorted({f["job"] for f in open_})
    return {
        "open": {k: v for k, v in tally(open_).items()},
        "acknowledged": sum(1 for f in findings if f["status"] == "acknowledged"),
        "muted": sum(1 for f in findings if f["status"] == "muted"),
        "by_job": [tally([f for f in open_ if f["job"] == j], job=j) for j in jobs],
        "by_customer": [tally([f for f in open_ if f["customer_code"] == c], customer_code=c) for c in customers],
    }


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
    ("GET", "/talon/ops/summary", None),
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


# ── the summary ───────────────────────────────────────────────────────────────


def leaky_summary():
    """A summary as a talon-analyst ignoring ``X-Talon-Customers`` would send it to anyone."""
    return {
        "open": counts(10, high=2, medium=3, low=4, info=1, stale=3),
        "acknowledged": 5,
        "muted": 2,
        "by_job": [counts(10, high=2, medium=3, low=4, info=1, stale=3, job="quiet_endpoints")],
        "by_customer": [
            counts(4, high=2, medium=1, low=1, stale=2, customer_code=GLOBEX),
            counts(3, medium=1, low=2, stale=1, customer_code=ACME),
            counts(1, info=1, customer_code=None),
            counts(2, medium=1, low=1, customer_code=DOTTED),
        ],
    }


def test_the_summary_is_relayed_for_an_admin_with_the_platform_row():
    fake = FakeTalon(
        findings=[
            finding(1, ACME, severity="high"),
            finding(2, GLOBEX, stale_since=T),
            finding(3, None, severity="low"),
            finding(4, ACME, status="muted"),
        ],
    )

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/summary", headers=as_user("admin"))
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        body = body_of(response)
        assert body["open"] == counts(3, high=1, medium=1, low=1, stale=1)
        assert body["acknowledged"] == 0 and body["muted"] == 1
        assert body["by_job"] == [counts(3, high=1, medium=1, low=1, stale=1, job="quiet_endpoints")]
        assert [row["customer_code"] for row in body["by_customer"]] == [None, ACME, GLOBEX]
        assert body["dropped"] == 0 and body["withheld"] is False
        sent = fake.upstream.requests[0]
        assert sent.url.path == "/v2/ops/summary" and sent.headers["X-Talon-Customers"] == "*"

    scenario_with(fake, scenario)


def test_the_summary_fails_closed_on_another_customers_rows_and_withholds_what_cant_be_split():
    fake = FakeTalon(leaky=True)
    fake.summary_answer = leaky_summary()

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/summary", headers=as_user("ana")))
        # GLOBEX's row and the platform row are dropped; the totals are ACME's and DOTTED's only.
        assert [row["customer_code"] for row in body["by_customer"]] == [ACME, DOTTED]
        assert body["open"] == counts(5, medium=2, low=3, stale=1)
        assert body["dropped"] == 2 and body["withheld"] is True
        # A job's counts and the acknowledged and muted counts can't be split by customer: withheld.
        assert body["by_job"] == [] and body["acknowledged"] is None and body["muted"] is None

    scenario_with(fake, scenario)


def test_the_summary_withholds_when_the_rows_dont_add_up_to_the_totals():
    fake = FakeTalon(leaky=True)
    answer = leaky_summary()
    answer["by_customer"] = [row for row in answer["by_customer"] if row["customer_code"] in (ACME, DOTTED)]
    fake.summary_answer = answer  # GLOBEX's findings in the totals, without its row

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/summary", headers=as_user("ana")))
        assert body["open"] == counts(5, medium=2, low=3, stale=1)
        assert body["dropped"] == 0 and body["withheld"] is True
        assert body["by_job"] == [] and body["acknowledged"] is None

    scenario_with(fake, scenario)


def test_the_summary_keeps_only_the_customer_or_the_platform_asked_for():
    fake = FakeTalon(leaky=True)
    fake.summary_answer = leaky_summary()

    async def scenario(client, ctx):
        body = body_of(await client.get(f"/talon/ops/summary?customer_code={ACME}", headers=as_user("ana")))
        assert fake.upstream.requests[-1].url.params["customer_code"] == ACME
        assert [row["customer_code"] for row in body["by_customer"]] == [ACME]
        assert body["open"]["total"] == 3 and body["withheld"] is True
        body = body_of(await client.get("/talon/ops/summary?platform=true", headers=as_user("admin")))
        assert fake.upstream.requests[-1].url.params["platform"] == "true"
        assert [row["customer_code"] for row in body["by_customer"]] == [None]
        assert body["open"] == counts(1, info=1) and body["dropped"] == 3

    scenario_with(fake, scenario)


def test_the_summary_refuses_a_customer_or_the_platform_the_caller_lacks_before_talon_is_asked():
    fake = FakeTalon()

    async def scenario(client, ctx):
        other = await client.get(f"/talon/ops/summary?customer_code={GLOBEX}", headers=as_user("ana"))
        assert other.status_code == 403 and body_of(other)["detail"] == talon_ops.NOT_ACCESSIBLE
        platform = await client.get("/talon/ops/summary?platform=true", headers=as_user("ana"))
        assert platform.status_code == 403 and body_of(platform)["detail"] == talon_ops.PLATFORM_ONLY
        both = await client.get(f"/talon/ops/summary?platform=true&customer_code={ACME}", headers=as_user("admin"))
        assert both.status_code == 400
        bad = await client.get("/talon/ops/summary?job=../x", headers=as_user("ana"))
        assert bad.status_code == 400
        assert fake.upstream.requests == []

    scenario_with(fake, scenario)


def test_the_summary_drops_malformed_and_repeated_rows():
    fake = FakeTalon(leaky=True)
    fake.summary_answer = {
        "open": counts(6, medium=3, low=3),
        "acknowledged": 0,
        "muted": 0,
        "by_job": [counts(6, medium=3, low=3, job="quiet_endpoints")],
        "by_customer": [
            counts(3, medium=2, low=1, customer_code=ACME),
            counts(3, medium=1, low=2, customer_code=ACME),  # repeated: may hide another customer's
            {"customer_code": DOTTED, "total": -1},
            counts(1, low=1, customer_code="../x"),
        ],
    }

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/summary", headers=as_user("ana")))
        assert body["by_customer"] == [counts(3, medium=2, low=1, customer_code=ACME)]
        assert body["open"] == counts(3, medium=2, low=1)
        assert body["dropped"] == 3 and body["withheld"] is True and body["by_job"] == []

    scenario_with(fake, scenario)


def test_the_summary_at_talons_row_cap_is_trusted_for_an_admin_only():
    fake = FakeTalon(leaky=True)
    rows = [counts(1, low=1, customer_code=f"c{i:02d}") for i in range(talon_ops.SUMMARY_ROWS)]
    fake.summary_answer = {
        "open": counts(60, low=60),
        "acknowledged": 1,
        "muted": 1,
        "by_job": [counts(60, low=60, job="quiet_endpoints")],
        "by_customer": rows,
    }

    async def scenario(client, ctx):
        admin = body_of(await client.get("/talon/ops/summary", headers=as_user("admin")))
        assert admin["open"]["total"] == 60 and admin["withheld"] is False and len(admin["by_job"]) == 1
        assert admin["partial"] is False
        # ana has none of these customers: every row is dropped and nothing is counted.
        ana = body_of(await client.get("/talon/ops/summary", headers=as_user("ana")))
        assert ana["open"]["total"] == 0 and ana["by_customer"] == [] and ana["withheld"] is True
        assert ana["partial"] is True

    scenario_with(fake, scenario)


def capped_summary(total):
    return {
        "open": counts(total, low=total),
        "acknowledged": 2,
        "muted": 1,
        "by_job": [counts(total, low=total, job="quiet_endpoints")],
        "by_customer": [counts(1, low=1, customer_code=f"c{i:02d}") for i in range(talon_ops.SUMMARY_ROWS)],
    }


OWNS_ALL_50 = talon_ops.Caller({}, False, frozenset(f"c{i:02d}" for i in range(talon_ops.SUMMARY_ROWS)))


def test_an_analyst_at_the_row_cap_whose_rows_add_up_gets_talons_counts():
    body = talon_ops.check_summary(capped_summary(50), OWNS_ALL_50, customer_code=None, platform=False)
    assert body.open.total == 50 and body.withheld is False and body.partial is False
    assert body.acknowledged == 2 and body.muted == 1 and len(body.by_job) == 1 and len(body.by_customer) == 50


def test_an_analyst_at_the_row_cap_whose_rows_dont_add_up_gets_a_lower_bound_said_so():
    body = talon_ops.check_summary(capped_summary(60), OWNS_ALL_50, customer_code=None, platform=False)
    assert body.open.total == 50 and body.open.low == 50  # the 50 rows' counts, never Talon's 60
    assert body.partial is True and body.withheld is True and body.dropped == 0
    assert body.by_job == [] and body.acknowledged is None and body.muted is None


def test_a_summary_below_the_cap_is_never_partial():
    answer = leaky_summary()
    answer["by_customer"] = [row for row in answer["by_customer"] if row["customer_code"] == ACME]
    body = talon_ops.check_summary(answer, talon_ops.Caller({}, False, frozenset({ACME})), customer_code=None, platform=False)
    assert body.withheld is True and body.partial is False and body.open.total == 3


def test_a_summary_in_the_wrong_shape_is_a_502():
    fake = FakeTalon(leaky=True)
    fake.summary_answer = {"open": {"total": "7"}, "by_job": [], "by_customer": []}

    async def scenario(client, ctx):
        response = await client.get("/talon/ops/summary", headers=as_user("admin"))
        assert response.status_code == 502 and body_of(response)["detail"] == talon_ops.WRONG_SHAPE

    scenario_with(fake, scenario)


# ── the findings' order ───────────────────────────────────────────────────────


def test_the_order_is_passed_through_and_checked():
    fake = FakeTalon()

    async def scenario(client, ctx):
        await client.get("/talon/ops/findings", headers=as_user("ana"))
        assert "order" not in fake.upstream.requests[-1].url.params  # recent: Talon's default
        await client.get("/talon/ops/findings?order=recent", headers=as_user("ana"))
        assert "order" not in fake.upstream.requests[-1].url.params
        await client.get("/talon/ops/findings?order=severity&cursor=s3.1729740000000000.12", headers=as_user("ana"))
        sent = fake.upstream.requests[-1].url.params
        assert sent["order"] == "severity" and sent["cursor"] == "s3.1729740000000000.12"
        count = len(fake.upstream.requests)
        bad = await client.get("/talon/ops/findings?order=oldest", headers=as_user("ana"))
        assert bad.status_code == 422
        odd = await client.get("/talon/ops/findings?cursor=a%20b", headers=as_user("ana"))
        assert odd.status_code == 400 and body_of(odd)["detail"] == talon_ops.INVALID_CURSOR
        assert len(fake.upstream.requests) == count

    scenario_with(fake, scenario)


def test_talons_severity_cursor_comes_back_to_the_browser():
    fake = FakeTalon()
    respond = fake.upstream.respond

    def paged(request):
        answer = respond(request)
        if request.url.path == "/v2/ops/findings":
            return httpx.Response(200, json={**json.loads(answer.content), "next_cursor": "s3.1729740000000000.7"})
        return answer

    fake.upstream.respond = paged

    async def scenario(client, ctx):
        body = body_of(await client.get("/talon/ops/findings?order=severity", headers=as_user("ana")))
        assert body["next_cursor"] == "s3.1729740000000000.7"

    scenario_with(fake, scenario)
