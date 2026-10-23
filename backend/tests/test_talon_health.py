"""The Talon health dashboard's backend, ``GET /api/talon/health`` (``services/talon_health.py``).

Real routers, a real in-memory database (``talon_v2_support``), talon-analyst as an
``httpx.MockTransport`` plugged in under the real health client (its 5 s deadline, capped reads, no
redirects, no proxy). No network.
"""
import asyncio
import json
import ssl
from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlmodel import SQLModel

from app.auth.utils import AuthHandler
from app.connectors.talon.models.talon_v2 import TalonInvestigationTrigger
from app.connectors.talon.services import talon_health
from app.connectors.talon.utils import health_client
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import AiAnalystReport
from app.incidents.models import AIAnalystTriggerEnabled
from tests.talon_v2_support import ACME
from tests.talon_v2_support import CHAT
from tests.talon_v2_support import COMPLETED
from tests.talon_v2_support import DOTTED
from tests.talon_v2_support import GLOBEX
from tests.talon_v2_support import TALON_KEY
from tests.talon_v2_support import USERS
from tests.talon_v2_support import _app
from tests.talon_v2_support import _Db
from tests.talon_v2_support import _seed
from tests.talon_v2_support import as_user
from tests.talon_v2_support import body_of
from tests.talon_v2_support import bomb_response


@compiles(LONGTEXT, "sqlite")
def _longtext_on_sqlite(type_, compiler, **kw):
    """`ai_analyst_report.report_markdown` is MySQL's LONGTEXT; SQLite stores it as TEXT."""
    return "TEXT"


URL = "http://talon-user:talon-pass@talon.invalid:3100/?token=abc#frag"
STRIPPED = "http://talon.invalid:3100/"


def connector(**overrides):
    attributes = {
        "connector_name": "Talon",
        "connector_url": URL,
        "connector_api_key": TALON_KEY,
        "connector_configured": True,
        "connector_verified": True,
        "connector_last_updated": COMPLETED,
    }
    attributes.update(overrides)
    return attributes


def component(cid, group="core", status="ok", **extra):
    return {
        "id": cid,
        "name": cid.replace("_", " ").title(),
        "group": group,
        "status": status,
        "latency_ms": 12.5,
        "detail": f"{cid} fine",
        "fix": None,
        "checked_at": "2026-10-22T08:00:00Z",
        **extra,
    }


def health_payload(**overrides):
    payload = {
        "status": "degraded",
        "version": "0.1.3",
        "image_browser": False,
        "uptime_seconds": 3600,
        "checked_at": "2026-10-22T08:00:00Z",
        "components": [
            component("api"),
            component("database"),
            component("wazuh_mcp", group="mcp", status="warn", fix="Check the Wazuh API account"),
            component("model_provider", group="model", status="fail", detail="429 from the provider"),
            component("web_search", group="tools", status="off", detail="No Tavily API key"),
        ],
        "config": {
            "writeback_mode": "live",
            "live_customers": [ACME, GLOBEX, DOTTED],
            "automation_max_level": 1,
            "automation_policy_source": "copilot",
            "v2_api": True,
            "action_tools": False,
            "endpoint_actions": True,
            "intel": True,
            "workspace_tools": False,
            "chat_browser": False,
            "models": {"chat": "claude-sonnet-5-5", "investigation": "claude-opus-5-5"},
            "budgets": {"daily_usd": "25.00", "monthly_usd": "unlimited", "spent_today_usd": 3.5, "spent_month_usd": "41.20"},
        },
    }
    payload.update(overrides)
    return payload


HISTORY = {
    "bucket_minutes": 60,
    "components": {
        "api": [{"t": "2026-10-22T07:00:00Z", "ok": 12, "warn": 0, "fail": 0}],
        "wazuh_mcp": [{"t": "2026-10-22T07:00:00Z", "ok": 10, "warn": 2, "fail": 0}],
    },
}
METRICS = {
    "bucket_minutes": 60,
    "series": [
        {
            "t": "2026-10-22T07:00:00Z",
            "investigations_completed": 4,
            "investigations_failed": 1,
            "queue_depth_max": 2,
            "duration_p50_s": 61.5,
            "duration_p95_s": 140,
            "tool_calls": 50,
            "tool_errors": 2,
            "model_errors": 0,
            "cost_usd": "1.2345",
        },
        {"t": "2026-10-22T08:00:00Z", "investigations_completed": None, "cost_usd": None},
    ],
}


def talon(overrides=None):
    """talon-analyst 0.1.3: every route answers; ``overrides`` maps a path to a response or a
    callable(request) -> response (or an exception to raise)."""
    overrides = overrides or {}
    defaults = {
        "/health": lambda r: httpx.Response(200, json={"status": "ok", "channel": "http"}),
        "/v2/health": lambda r: httpx.Response(200, json=health_payload()),
        "/v2/health/history": lambda r: httpx.Response(200, json=HISTORY),
        "/v2/health/metrics": lambda r: httpx.Response(200, json=METRICS),
        "/templates": lambda r: httpx.Response(200, json={"templates": []}),
    }

    def respond(request):
        answer = overrides.get(request.url.path, defaults.get(request.url.path))
        if answer is None:
            return httpx.Response(404, json={"detail": "Not Found"})
        if isinstance(answer, Exception):
            raise answer
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

    def paths(self):
        return [r.url.path for r in self.requests]


async def _extra_rows(db):
    async with db.engine.begin() as conn:
        tables = [AiAnalystReport.__table__, TalonInvestigationTrigger.__table__, AIAnalystTriggerEnabled.__table__]
        await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
    async with db.session() as session:
        session.add_all(
            [
                AIAnalystTriggerEnabled(customer_code=ACME, enabled=True),
                AIAnalystTriggerEnabled(customer_code=GLOBEX, enabled=True),
                AIAnalystTriggerEnabled(customer_code=DOTTED, enabled=False),
                TalonInvestigationTrigger(alert_id=1, customer_code=ACME, source="pipeline", assets=[], sent_at=COMPLETED),
                TalonInvestigationTrigger(
                    alert_id=2,
                    customer_code=GLOBEX,
                    source="analyst",
                    assets=[],
                    sent_at=COMPLETED + timedelta(minutes=5),
                ),
            ],
        )
        # GLOBEX's job is the newest and it failed; ACME's report the newest of ACME's.
        recent = talon_health._naive_utc_now() - timedelta(hours=1)
        session.add(
            AiAnalystJob(
                id="copilot-inv-2-9",
                alert_id=2,
                customer_code=GLOBEX,
                status="failed",
                triggered_by="webhook",
                created_at=recent,
                completed_at=recent,
            ),
        )
        await session.commit()
        session.add_all(
            [
                AiAnalystReport(job_id="copilot-inv-1-1760601600000", alert_id=1, customer_code=ACME, created_at=COMPLETED),
                AiAnalystReport(job_id="copilot-inv-2-9", alert_id=2, customer_code=GLOBEX, created_at=COMPLETED + timedelta(minutes=9)),
            ],
        )
        await session.commit()


def run(scenario, *, respond=None, attributes="default", enabled=False):
    """Run ``scenario(client, fake)`` against the real router with talon-analyst faked."""
    fake = Fake(respond or talon())
    attrs = connector() if attributes == "default" else attributes

    async def _inner():
        db = await _Db().create()
        try:
            await _seed(db, enabled)
            await _extra_rows(db)
            app = _app(db)

            async def resolve_user(self, request, username):
                if username not in USERS:
                    return None
                uid, role, _, _ = USERS[username]
                return SimpleNamespace(id=uid, username=username, role_id=role)

            talon_health.clear_cache()
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(AuthHandler, "decode_token", lambda self, token: (token, USERS.get(token, (0, 0, [], []))[2])),
                )
                stack.enter_context(patch.object(AuthHandler, "_resolve_user", resolve_user))
                stack.enter_context(patch.object(health_client, "_new_client", fake.new_client))
                stack.enter_context(patch.object(talon_health, "get_connector_info_from_db", AsyncMock(return_value=attrs)))
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://copilot") as client:
                    return await scenario(client, fake)
        finally:
            talon_health.clear_cache()
            await db.dispose()

    return asyncio.run(_inner())


def get(user="admin", query=""):
    async def scenario(client, fake):
        response = await client.get(f"/talon/health{query}", headers=as_user(user))
        return response, fake

    return scenario


# ── a healthy talon-analyst ───────────────────────────────────────────────────


def test_reachable_talon_fills_every_section():
    response, fake = run(get())
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = body_of(response)
    copilot = body["copilot"]
    assert copilot["connector"] == {"exists": True, "configured": True, "verified": True, "url": STRIPPED}
    assert copilot["reachable"]["ok"] is True and copilot["reachable"]["latency_ms"] >= 0
    assert copilot["auth"]["ok"] is True
    assert copilot["v2_enabled"] is False  # works with v2 off (decision b)
    assert copilot["scope"] == "deployment"
    health = body["health"]
    assert health["error"] is None and health["unsupported"] is False
    data = health["data"]
    assert data["status"] == "degraded" and data["version"] == "0.1.3" and data["uptime_seconds"] == 3600
    assert [c["id"] for c in data["components"]] == ["api", "database", "wazuh_mcp", "model_provider", "web_search"]
    assert (data["components"][4]["group"], data["components"][4]["status"]) == ("tools", "off")
    assert data["components"][2]["fix"] == "Check the Wazuh API account"
    assert data["config"]["budgets"] == {
        "daily_usd": "25.00",
        "monthly_usd": "unlimited",
        "spent_today_usd": "3.5",
        "spent_month_usd": "41.20",
    }
    assert body["history"]["data"]["components"]["wazuh_mcp"][0] == {"t": "2026-10-22T07:00:00Z", "ok": 10, "warn": 2, "fail": 0}
    series = body["metrics"]["data"]["series"]
    assert series[0]["cost_usd"] == "1.2345" and series[0]["duration_p95_s"] == 140
    # Missing and null stay null ("no data"), never 0.
    assert series[1]["investigations_completed"] is None and series[1]["tool_calls"] is None and series[1]["cost_usd"] is None
    assert body["hours"] == 24
    assert sorted(fake.paths()) == ["/health", "/v2/health", "/v2/health/history", "/v2/health/metrics"]


def test_the_key_goes_to_talon_only_on_its_authenticated_routes():
    _, fake = run(get())
    for request in fake.requests:
        if request.url.path == "/health":
            assert "x-api-key" not in request.headers
        else:
            assert request.headers["x-api-key"] == TALON_KEY
        assert request.headers["accept-encoding"] == "identity"
    queries = {r.url.path: r.url.params.get("hours") for r in fake.requests}
    assert queries["/v2/health/history"] == "24" and queries["/v2/health/metrics"] == "24"


def test_hours_is_forwarded_and_bounded():
    response, fake = run(get(query="?hours=168"))
    assert response.status_code == 200 and body_of(response)["hours"] == 168
    assert {r.url.params.get("hours") for r in fake.requests if "history" in r.url.path or "metrics" in r.url.path} == {"168"}
    for bad in ("0", "1", "48", "169", "abc"):
        response, fake = run(get(query=f"?hours={bad}"))
        assert response.status_code == 422
        assert fake.requests == []


# ── unreachable, a wrong key, an old Talon ────────────────────────────────────


def test_unreachable_talon_keeps_copilots_checks_and_names_the_reason():
    def refuse(request):
        raise httpx.ConnectError("[Errno 61] Connection refused to talon.invalid:3100")

    response, _ = run(get(), respond=refuse)
    assert response.status_code == 200
    body = body_of(response)
    assert body["copilot"]["connector"]["verified"] is True
    assert body["copilot"]["reachable"] == {
        "ok": False,
        "latency_ms": None,
        "status_code": None,
        "error": "Talon could not be reached (ConnectError)",
    }
    assert body["copilot"]["auth"]["ok"] is None
    for name in ("health", "history", "metrics"):
        assert body[name]["data"] is None and body[name]["error"] == "Talon could not be reached (ConnectError)"
    # The exception's own text (hosts, ports) never reaches the browser.
    assert "Errno" not in response.text and "talon.invalid:3100" not in response.text.replace(STRIPPED, "")
    # CoPilot's own tables are still read.
    assert body["copilot"]["last_job"]["customer_code"] == GLOBEX


def test_a_talon_that_never_answers_times_out(monkeypatch):
    monkeypatch.setattr(health_client, "TIMEOUT_SECONDS", 0.2)

    async def hang(request):
        await asyncio.sleep(5)
        return httpx.Response(200, json={})

    response, _ = run(get(), respond=lambda r: hang(r))
    body = body_of(response)
    assert body["copilot"]["reachable"]["ok"] is False
    assert body["copilot"]["reachable"]["error"].startswith("Talon did not answer within 0.2 s (")
    assert body["health"]["error"].startswith("Talon did not answer")


def test_a_wrong_key_is_401_and_says_so():
    unauthorized = lambda r: httpx.Response(401, json={"error": "Unauthorized"})  # noqa: E731
    respond = talon(
        {"/v2/health": unauthorized, "/v2/health/history": unauthorized, "/v2/health/metrics": unauthorized, "/templates": unauthorized},
    )
    response, fake = run(get(), respond=respond)
    body = body_of(response)
    assert response.status_code == 200  # never a 401: the browser would read it as its own session ending
    assert body["copilot"]["reachable"]["ok"] is True
    assert body["copilot"]["auth"] == {"ok": False, "latency_ms": None, "status_code": 401, "error": talon_health.KEY_REFUSED}
    assert body["health"]["error"] == talon_health.KEY_REFUSED and body["health"]["status_code"] == 401
    assert "/templates" not in fake.paths()  # /v2/health already said


def test_a_talon_still_running_its_first_check_says_so():
    starting = lambda r: httpx.Response(503, json={"detail": "the first health check is still running"})  # noqa: E731
    respond = talon({"/v2/health": starting})
    response, fake = run(get(), respond=respond)
    body = body_of(response)
    assert response.status_code == 200
    assert body["health"]["error"] == talon_health.STARTING and body["health"]["status_code"] == 503
    assert body["health"]["data"] is None and not body["health"].get("unsupported")


def test_an_old_talon_without_the_health_api_is_unsupported():
    gone = lambda r: httpx.Response(404, json={"detail": "Not Found"})  # noqa: E731
    respond = talon({"/v2/health": gone, "/v2/health/history": gone, "/v2/health/metrics": gone})
    response, fake = run(get(), respond=respond)
    body = body_of(response)
    for name in ("health", "history", "metrics"):
        assert body[name] == {"data": None, "error": talon_health.OLD_TALON, "status_code": 404, "unsupported": True}
    assert talon_health.OLD_TALON == "This Talon version has no health endpoint; upgrade to talon-analyst 0.1.3 or later"
    # The key is still checked, on a route every Talon has always authenticated.
    assert "/templates" in fake.paths()
    assert body["copilot"]["auth"]["ok"] is True
    assert body["copilot"]["reachable"]["ok"] is True


def test_an_old_talon_with_a_wrong_key():
    gone = lambda r: httpx.Response(404, json={"detail": "Not Found"})  # noqa: E731
    respond = talon({"/v2/health": gone, "/templates": lambda r: httpx.Response(401, json={"error": "Unauthorized"})})
    body = body_of(run(get(), respond=respond)[0])
    assert body["copilot"]["auth"]["ok"] is False and body["copilot"]["auth"]["error"] == talon_health.KEY_REFUSED


def test_one_failing_section_does_not_blank_the_others():
    respond = talon({"/v2/health/metrics": lambda r: httpx.Response(500, text="Traceback: secret things")})
    body = body_of(run(get(), respond=respond)[0])
    assert body["health"]["data"] is not None and body["history"]["data"] is not None
    assert body["metrics"] == {"data": None, "error": "Talon answered 500", "status_code": 500, "unsupported": False}


def test_no_connector_or_no_url_asks_talon_nothing():
    response, fake = run(get(), attributes=None)
    body = body_of(response)
    assert fake.requests == []
    assert body["copilot"]["connector"] == {"exists": False, "configured": False, "verified": False, "url": None}
    assert body["health"]["error"] == talon_health.NO_CONNECTOR
    response, fake = run(get(), attributes=connector(connector_url="", connector_verified=False))
    body = body_of(response)
    assert fake.requests == []
    assert body["copilot"]["connector"]["configured"] is False
    assert body["copilot"]["reachable"]["error"] == talon_health.NOT_CONFIGURED


# ── what talon-analyst says, defensively ──────────────────────────────────────


def test_malformed_fields_are_dropped_not_fatal():
    payload = health_payload(
        status="exploded",
        uptime_seconds="forever",
        image_browser="yes",
        unexpected={"secret": "x"},
        components=[
            component("api", status="purple", latency_ms=-3, group="weird"),
            {"id": "../etc/passwd", "status": "ok"},
            "not a component",
            component("api"),  # a duplicate id: the first one wins
            component("x" * 65),
        ],
        config={
            "live_customers": "everyone",
            "automation_max_level": True,
            "budgets": {"daily_usd": "lots", "monthly_usd": float("nan")},
            "v2_api": {"nested": True},
        },
    )
    history = {"bucket_minutes": -5, "components": {"api": [{"t": "x", "ok": 1.5, "warn": "2", "fail": 3}, {"ok": 1}], "bad id!": []}}
    metrics = {"series": [{"t": "x", "tool_calls": True, "tool_errors": float("inf"), "cost_usd": 1e400}, 7]}
    respond = talon(
        {
            "/v2/health": lambda r: httpx.Response(200, content=json.dumps(payload, allow_nan=True).encode()),
            "/v2/health/history": lambda r: httpx.Response(200, json=history),
            "/v2/health/metrics": lambda r: httpx.Response(200, content=json.dumps(metrics, allow_nan=True).encode()),
        },
    )
    response, _ = run(get(), respond=respond)
    assert response.status_code == 200
    body = body_of(response)
    data = body["health"]["data"]
    assert data["status"] == "unknown" and data["uptime_seconds"] is None and data["image_browser"] is None
    assert "unexpected" not in data
    assert [c["id"] for c in data["components"]] == ["api"]
    assert data["components"][0]["status"] == "unknown" and data["components"][0]["group"] == "other"
    assert data["components"][0]["latency_ms"] is None
    config = data["config"]
    assert config["live_customers"] == [] and config["automation_max_level"] is None and config["v2_api"] is None
    assert config["budgets"] == {"daily_usd": None, "monthly_usd": None, "spent_today_usd": None, "spent_month_usd": None}
    assert body["history"]["data"] == {"bucket_minutes": None, "components": {"api": [{"t": "x", "ok": None, "warn": None, "fail": 3}]}}
    bucket = body["metrics"]["data"]["series"][0]
    assert bucket["tool_calls"] is None and bucket["tool_errors"] is None and bucket["cost_usd"] is None


@pytest.mark.parametrize(
    "answer, error",
    [
        (lambda r: httpx.Response(200, content=b"<html>proxy</html>"), talon_health.NOT_JSON),
        (lambda r: httpx.Response(200, json=["a", "list"]), talon_health.WRONG_SHAPE),
        (lambda r: httpx.Response(200, content=b"[" * 100_000 + b"]" * 100_000), talon_health.NOT_JSON),
        (lambda r: bomb_response(200), "Talon's answer was compressed; not read"),
        (
            lambda r: httpx.Response(200, content=b'{"pad": "' + b"x" * (talon_health.MAX_HEALTH_BYTES + 10) + b'"}'),
            "Talon's answer was too large",
        ),
    ],
)
def test_unusable_answers_are_a_fixed_error(answer, error):
    body = body_of(run(get(), respond=talon({"/v2/health": answer}))[0])
    assert body["health"]["data"] is None and body["health"]["error"] == error


def test_no_secret_reaches_the_browser():
    leaky = health_payload(
        components=[
            component(
                "indexer_mcp",
                status="fail",
                detail=f"https://reader:hunter2@indexer.internal:9200 refused key {TALON_KEY}",
                fix=f"Set TALON_API_KEY={TALON_KEY}\x1b[31m again",
            ),
        ],
    )
    response, _ = run(get(), respond=talon({"/v2/health": lambda r: httpx.Response(200, json=leaky)}))
    text = response.text
    assert TALON_KEY not in text
    assert "hunter2" not in text and "reader:" not in text
    assert "talon-pass" not in text and "talon-user" not in text and "token=abc" not in text
    assert "\x1b" not in body_of(response)["health"]["data"]["components"][0]["fix"]
    detail = body_of(response)["health"]["data"]["components"][0]["detail"]
    assert detail == "https://indexer.internal:9200 refused key [redacted]"


def test_amounts_are_written_out():
    assert talon_health._amount(1e-06) == "0.000001"
    assert talon_health._amount(0.123456) == "0.123456"
    assert talon_health._amount(25) == "25"
    assert talon_health._amount("12.50") == "12.50"
    assert talon_health._amount("1e5") is None
    assert talon_health._amount(None) is None


def test_strip_url():
    assert talon_health.strip_url("https://u:p@host.example:8443/base?x=1#y") == "https://host.example:8443/base"
    assert talon_health.strip_url("http://[::1]:3100") == "http://[::1]:3100"
    assert talon_health.strip_url("not a url") is None
    assert talon_health.strip_url("http://host:notaport/") is None
    assert talon_health.strip_url(None) is None


# ── tenancy ───────────────────────────────────────────────────────────────────


def test_live_customers_and_per_customer_items_are_scoped():
    admin = body_of(run(get("admin"))[0])
    assert admin["copilot"]["scope"] == "deployment"
    assert admin["health"]["data"]["config"]["live_customers"] == [ACME, GLOBEX, DOTTED]
    assert admin["copilot"]["last_job"]["customer_code"] == GLOBEX
    assert admin["copilot"]["last_sent"] == {"customer_code": GLOBEX, "status": "analyst", "at": "2026-10-16T08:10:30"}
    assert admin["copilot"]["last_report"]["customer_code"] == GLOBEX
    assert admin["copilot"]["jobs_failed_24h"] == 1
    assert admin["copilot"]["ai_trigger_customers"] == 2

    ana = body_of(run(get("ana"))[0])  # ACME, acme.io, chat
    assert ana["copilot"]["scope"] == "assigned"
    assert ana["health"]["data"]["config"]["live_customers"] == [ACME, DOTTED]
    assert ana["copilot"]["last_job"]["customer_code"] in (ACME, DOTTED, CHAT)
    assert ana["copilot"]["last_sent"]["customer_code"] == ACME
    assert ana["copilot"]["last_report"]["customer_code"] == ACME
    assert ana["copilot"]["jobs_failed_24h"] == 0
    assert ana["copilot"]["ai_trigger_customers"] == 1
    assert GLOBEX not in json.dumps(ana)

    gus = body_of(run(get("gus"))[0])  # GLOBEX only
    assert gus["health"]["data"]["config"]["live_customers"] == [GLOBEX]
    assert gus["copilot"]["jobs_failed_24h"] == 1
    # Everything else (the components, the charts) is the same for everyone (decision a).
    assert gus["health"]["data"]["components"] == admin["health"]["data"]["components"]


def test_a_demoted_admin_is_scoped_by_their_database_role():
    demoted = body_of(run(get("demoted"))[0])  # an admin token, an analyst row, ACME only
    assert demoted["copilot"]["scope"] == "assigned"
    assert demoted["health"]["data"]["config"]["live_customers"] == [ACME]


def test_a_caller_without_customers_sees_no_per_customer_item():
    async def scenario():
        return await talon_health._copilot_tables(session=None, customers=[])

    assert asyncio.run(scenario()) == {}


@pytest.mark.parametrize("user", ["portal", "sched", "nobody"])
def test_only_soc_roles_may_read_it(user):
    response, fake = run(get(user))
    assert response.status_code in (401, 403)
    assert fake.requests == []


def test_a_responder_may_read_it():
    response, _ = run(get("resp"))
    assert response.status_code == 200
    assert body_of(response)["health"]["data"]["config"]["live_customers"] == [ACME]


# ── the cache ─────────────────────────────────────────────────────────────────


def test_talon_is_asked_once_per_30_seconds_per_hours_value():
    async def scenario(client, fake):
        for _ in range(3):
            assert (await client.get("/talon/health", headers=as_user("admin"))).status_code == 200
        first = len(fake.requests)
        # Another user, same window: the cache, scoped for them.
        ana = body_of(await client.get("/talon/health", headers=as_user("ana")))
        assert ana["health"]["data"]["config"]["live_customers"] == [ACME, DOTTED]
        assert len(fake.requests) == first
        # A different window is a different entry.
        await client.get("/talon/health?hours=168", headers=as_user("admin"))
        assert len(fake.requests) == 2 * first
        # Once it expires, Talon is asked again.
        for key, (_, value) in list(talon_health._CACHE.items()):
            talon_health._CACHE[key] = (0.0, value)
        await client.get("/talon/health", headers=as_user("admin"))
        return first, len(fake.requests)

    first, total = run(scenario)
    assert first == 4
    assert total == 12


def test_the_cache_holds_the_unscoped_answer_and_admin_still_sees_all():
    async def scenario(client, fake):
        await client.get("/talon/health", headers=as_user("gus"))
        admin = body_of(await client.get("/talon/health", headers=as_user("admin")))
        return admin, len(fake.requests)

    admin, count = run(scenario)
    assert admin["health"]["data"]["config"]["live_customers"] == [ACME, GLOBEX, DOTTED]
    assert count == 4


def test_concurrent_requests_share_one_round_of_calls():
    async def scenario(client, fake):
        answers = await asyncio.gather(*[client.get("/talon/health", headers=as_user("admin")) for _ in range(5)])
        assert all(a.status_code == 200 for a in answers)
        return len(fake.requests)

    assert run(scenario) == 4


def test_a_changed_connector_is_not_served_from_the_cache():
    a = talon_health._cache_key(connector(), 24)
    b = talon_health._cache_key(connector(connector_api_key="another-key-123"), 24)
    c = talon_health._cache_key(connector(), 168)
    assert len({a, b, c}) == 3
    assert TALON_KEY not in repr(a)


# ── review fixes: overflow, scrubbing, missing config, client settings, session order ──


def test_huge_numbers_never_fail_the_route_or_reach_the_browser():
    huge = 10**400
    payload = health_payload(uptime_seconds=huge, components=[component("api", latency_ms=huge)])
    payload["config"]["automation_max_level"] = huge
    payload["config"]["budgets"] = {"daily_usd": 10**4000, "monthly_usd": 10**20, "spent_today_usd": huge, "spent_month_usd": "1" * 400}
    metrics = {"bucket_minutes": huge, "series": [{"t": "x", "tool_calls": huge, "cost_usd": huge}]}
    history = {"bucket_minutes": 5, "components": {"api": [{"t": "x", "ok": huge, "warn": 1, "fail": 0}]}}
    respond = talon(
        {
            "/v2/health": lambda r: httpx.Response(200, content=json.dumps(payload).encode()),
            "/v2/health/history": lambda r: httpx.Response(200, content=json.dumps(history).encode()),
            "/v2/health/metrics": lambda r: httpx.Response(200, content=json.dumps(metrics).encode()),
        },
    )
    response, _ = run(get(), respond=respond)
    assert response.status_code == 200
    body = body_of(response)
    data = body["health"]["data"]
    assert data["uptime_seconds"] is None and data["components"][0]["latency_ms"] is None
    assert data["config"]["automation_max_level"] is None
    assert data["config"]["budgets"] == {"daily_usd": None, "monthly_usd": None, "spent_today_usd": None, "spent_month_usd": None}
    assert body["history"]["data"]["components"]["api"][0]["ok"] is None
    assert body["metrics"]["data"]["bucket_minutes"] is None
    assert body["metrics"]["data"]["series"][0]["tool_calls"] is None and body["metrics"]["data"]["series"][0]["cost_usd"] is None
    assert len(response.text) < 20_000


def test_an_integer_past_pythons_digit_limit_is_not_json():
    content = b'{"status": "ok", "uptime_seconds": 1' + b"0" * 5000 + b"}"
    body = body_of(run(get(), respond=talon({"/v2/health": lambda r: httpx.Response(200, content=content)}))[0])
    assert body["health"]["error"] == talon_health.NOT_JSON


def test_amount_and_number_helpers():
    assert talon_health._number(10**400) is None
    assert talon_health._count(10**400) is None
    assert talon_health._amount(10**4000) is None
    assert talon_health._amount(10**20) is None
    assert talon_health._amount(1e300) is None
    assert talon_health._amount("1" * 400) is None
    assert talon_health._amount(123456789012345) == "123456789012345"


def test_an_unforeseen_parse_failure_is_the_wrong_shape_error(monkeypatch):
    def broken(raw, scrub):
        raise RuntimeError("boom")

    monkeypatch.setattr(talon_health, "parse_health", broken)
    response, _ = run(get())
    assert response.status_code == 200
    body = body_of(response)
    assert body["health"] == {"data": None, "error": talon_health.WRONG_SHAPE, "status_code": 200, "unsupported": False}
    assert body["metrics"]["data"] is not None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("https://u:p@ss/w@rd@indexer:9200/x down", "https://indexer:9200/x down"),
        ("https://reader:pa@ss@indexer:9200", "https://indexer:9200"),
        ("http://user@host/path", "http://host/path"),
        ("http://host:9200/path fine", "http://host:9200/path fine"),
        (
            "GET /x?token=abc&b=1 key=zzz api_key=q Password=hunter2 sig=s1",
            "GET /x?token=[redacted]&b=1 key=[redacted] api_key=[redacted] Password=[redacted] sig=[redacted]",
        ),
        ("the connector password is s3cret-pass-1", "the connector password is [redacted]"),
    ],
)
def test_scrub(text, expected):
    scrub = talon_health.make_scrub([TALON_KEY, "s3cret-pass-1"])
    assert scrub(text, 500) == expected


def test_the_connector_password_never_reaches_the_browser():
    leaky = health_payload(components=[component("api", detail="logged in with s3cret-pass-1 as talon")])
    response, _ = run(
        get(),
        respond=talon({"/v2/health": lambda r: httpx.Response(200, json=leaky)}),
        attributes=connector(connector_password="s3cret-pass-1"),
    )
    assert "s3cret-pass-1" not in response.text
    assert body_of(response)["health"]["data"]["components"][0]["detail"] == "logged in with [redacted] as talon"


def test_a_missing_configuration_is_none_and_budgets_tell_absent_from_unlimited():
    for config in ({}, {"unexpected": 1}, None, "text"):
        body = body_of(run(get(), respond=talon({"/v2/health": lambda r, c=config: httpx.Response(200, json=health_payload(config=c))}))[0])
        assert body["health"]["data"]["config"] is None
    no_budgets = health_payload(config={"writeback_mode": "off"})
    config = body_of(run(get(), respond=talon({"/v2/health": lambda r: httpx.Response(200, json=no_budgets)}))[0])["health"]["data"][
        "config"
    ]
    assert config["writeback_mode"] == "off" and config["budgets"] is None
    partial = health_payload(config={"budgets": {"daily_usd": None, "spent_today_usd": None}})
    config = body_of(run(get(), respond=talon({"/v2/health": lambda r: httpx.Response(200, json=partial)}))[0])["health"]["data"]["config"]
    # A reported null ceiling is unlimited; a missing one is not reported; a null spend is no data.
    assert config["budgets"] == {"daily_usd": "unlimited", "monthly_usd": None, "spent_today_usd": None, "spent_month_usd": None}


def test_the_health_client_settings():
    async def scenario():
        async with health_client._new_client(health_client.TIMEOUT) as client:
            context = client._transport._pool._ssl_context
            return client.follow_redirects, client.trust_env, context.verify_mode, context.check_hostname, client.timeout

    follow, trust_env, verify_mode, check_hostname, timeout = asyncio.run(scenario())
    assert follow is False and trust_env is False
    # TLS isn't verified, as for the rest of the Talon connector: talon-analyst is on a private network.
    assert verify_mode == ssl.CERT_NONE and check_hostname is False
    assert timeout.read == health_client.TIMEOUT_SECONDS


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
        response, _ = run(get(), respond=respond)
    assert response.status_code == 200
    assert "talon" in events and "close" in events[: events.index("talon")]


def test_the_cache_drops_expired_entries_and_their_idle_locks():
    async def scenario(client, fake):
        await client.get("/talon/health", headers=as_user("admin"))
        await client.get("/talon/health?hours=168", headers=as_user("admin"))
        assert len(talon_health._CACHE) == 2 and len(talon_health._LOCKS) == 2
        for key, (_, value) in list(talon_health._CACHE.items()):
            talon_health._CACHE[key] = (0.0, value)
        await client.get("/talon/health", headers=as_user("admin"))
        return len(talon_health._CACHE), len(talon_health._LOCKS)

    assert run(scenario) == (1, 1)
