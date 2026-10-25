"""Talon's ops findings through CoPilot's notification routes (talon-analyst SPEC §5.7
"Notifications", D96; plan OJ-5): the poller, the `talon_ops_finding` trigger and the v1 `ops_finding`
block.

- **The poller** (`services/talon_ops_notify.py`) pages `status=open&notified=false` (no `since`) as its
  own identity, emits each finding once per severity through the outbox, then posts `notified` with
  that severity; a 409 (the severity rose) is left for the next tick, which notifies the new
  severity; an outage marks nothing and raises nothing; a finding whose `notified` failed is never
  emitted twice (its key is found in the outbox); the v2 setting off asks nothing.
- **The trigger** is internal-only: it resolves against internal routes, never a customer's, and a
  customer route can't be saved with it.
- **The payload**: the webhook gets the `ops_finding` block and `ai_report: null`; the default body
  carries code's fields only; an HTML template escapes the model's text, a Markdown one escapes its
  Markdown; the documented example is the real shape.

A real SQLite database in a file (`NullPool`), the outbox and the dispatch loop real; talon-analyst is
an `httpx.MockTransport`, the webhook a recorder.

Run with: cd backend && python -m pytest tests/test_talon_ops_notifications.py
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.channels.webhook as webhook_mod  # noqa: E402
import app.notifications.services.notifications as svc  # noqa: E402
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings  # noqa: E402
from app.connectors.talon.services import talon_ops  # noqa: E402
from app.connectors.talon.services import talon_ops_notify  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import NotificationOutbox  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteCreate  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services import ops_finding_v1  # noqa: E402
from app.notifications.services import outbox  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    talon_ops_finding_event,
)
from app.notifications.services.payload_v1 import SCHEMA_V1  # noqa: E402
from app.notifications.services.payload_v1 import v1_envelope  # noqa: E402
from tests.talon_v2_support import TALON_CONNECTOR  # noqa: E402

T = "2026-10-24T06:00:00+00:00"
HOOK = "https://receiver.example.invalid/hook"
TABLES = ["customer_notification_route", "notification_dispatch_log", "notification_outbox", "talon_connector_settings", "customers"]


def raw_finding(fid, customer="ACME", severity="medium", **over):
    base = {
        "id": fid,
        "fingerprint": f"quiet_endpoints:{customer}:agent:{fid:03d}",
        "job": "quiet_endpoints",
        "job_version": 1,
        "customer_code": customer,
        "kind": "wazuh_quiet",
        "severity": severity,
        "title": f"host-{fid}: not seen by Wazuh for 5 days",
        "evidence": {
            "agent_id": f"{fid:03d}",
            "agent_name": f"host-{fid}",
            "wazuh_days_quiet": 5.1,
            "critical_asset": False,
            "conditions": ["wazuh_quiet"],
        },
        "artifact": None,
        "why": "It <b>stopped</b> reporting (MODELWHY): see [this](http://evil.example) ![x](http://evil.example/p.png)",
        "recommendation": "# Restart\nRun `net start wazuh` *now* (MODELREC)",
        "priority": 2,
        "explained": True,
        "status": "open",
        "first_seen": T,
        "last_seen": T,
        "notified_at": None,
        "updated_at": T,
    }
    base.update(over)
    return base


def parsed(raw):
    return talon_ops.parse_finding(raw, talon_ops.cleaners_for(TALON_CONNECTOR))


class OpsTalon:
    """talon-analyst's `/v2/ops/findings` for the poller: `pages` (lists of findings), `notified`
    answers by id (default 200), and every request recorded."""

    def __init__(self, pages, *, notified=None, down=False):
        self.pages = pages
        self.notified = notified or {}
        self.down = down
        self.requests = []
        self.marked = []

    def handler(self, request):
        self.requests.append(request)
        if self.down:
            raise httpx.ConnectError("talon.invalid refused")
        path = request.url.path
        if path == "/v2/ops/findings":
            index = int(request.url.params.get("cursor", "0.0").split(".")[1])
            page = self.pages[index] if index < len(self.pages) else []
            more = index + 1 < len(self.pages)
            return httpx.Response(200, json={"items": page, "next_cursor": f"1.{index + 1}" if more else None})
        if path.endswith("/notified"):
            fid = int(path.split("/")[4])
            status = self.notified.get(fid, 200)
            if status == 409:
                return httpx.Response(409, json={"detail": talon_ops_notify.ROSE})
            if status != 200:
                return httpx.Response(status, json={"detail": "nope"})
            self.marked.append((fid, json.loads(request.content)["severity"], request.url.params.get("customer_code")))
            return httpx.Response(200, json=raw_finding(fid, notified_at=T))
        if path == "/v2/ops/jobs":
            return httpx.Response(200, json={"items": [{"name": "quiet_endpoints", "title": "Endpoints gone quiet", "enabled": True}]})
        return httpx.Response(404, json={"detail": "Not Found"})

    def new_client(self, timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler), timeout=timeout)

    def finding_pages(self):
        return [r for r in self.requests if r.url.path == "/v2/ops/findings"]


class Harness:
    def __init__(self, path, monkeypatch, talon, *, v2=True):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.talon = talon
        self.v2 = v2
        self.kicked = []
        self.webhooks = []
        monkeypatch.setattr(outbox, "new_session", self.sessions)
        monkeypatch.setattr(outbox, "kick", lambda event: self.kicked.append(event.dedupe_key))
        monkeypatch.setattr(talon_ops_notify, "get_connector_info_from_db", AsyncMock(return_value=TALON_CONNECTOR))
        monkeypatch.setattr(v2_client, "_new_client", talon.new_client)
        monkeypatch.setattr(v2_client, "_connector", AsyncMock(return_value=TALON_CONNECTOR))
        monkeypatch.setenv("COPILOT_URL", "https://copilot.example.com")

        async def webhook(**kwargs):
            self.webhooks.append(kwargs)
            return ("sent", None, 1, None)

        monkeypatch.setattr(webhook_mod, "dispatch_webhook", webhook)

    async def create(self):
        tables = [SQLModel.metadata.tables[t] for t in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        async with self.sessions() as session:
            session.add(TalonConnectorSettings(connector_name="Talon", v2_enabled=self.v2))
            await session.commit()
        return self

    async def outbox_keys(self):
        async with self.sessions() as session:
            result = await session.execute(select(NotificationOutbox.dedupe_key).order_by(NotificationOutbox.id))
            return list(result.scalars().all())

    async def add_route(self, name, *, scope, trigger="talon_ops_finding", min_severity="Informational", config=None, customer_code=None):
        async with self.sessions() as session:
            session.add(
                CustomerNotificationRoute(
                    name=name,
                    scope=scope,
                    customer_code=customer_code,
                    trigger=trigger,
                    channel="webhook",
                    destination="",
                    enabled=True,
                    min_severity=min_severity,
                    recipient_mode="static",
                    config=json.dumps(config or {"url": HOOK, "method": "POST", "headers": None, "include_full_report": False}),
                    created_at=datetime(2026, 10, 1),
                    created_by="admin",
                ),
            )
            await session.commit()

    async def dispatch(self, event):
        async with self.sessions() as session:
            return await svc.dispatch_event(event, session)


def run(tmp_path, monkeypatch, talon, scenario, **kw):
    async def inner():
        h = await Harness(tmp_path / "ops.db", monkeypatch, talon, **kw).create()
        try:
            return await scenario(h)
        finally:
            await h.engine.dispose()

    return asyncio.run(inner())


# ── the poller ────────────────────────────────────────────────────────────────


def test_the_poller_pages_emits_once_per_finding_and_severity_and_records_notified(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1), raw_finding(2, customer=None, severity="high")], [raw_finding(3, severity="low")]])

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["emitted"] == 3 and counts["marked"] == 3 and counts["failed"] == 0
        assert await h.outbox_keys() == ["ops:1:medium", "ops:2:high", "ops:3:low"]
        assert h.kicked == ["ops:1:medium", "ops:2:high", "ops:3:low"]
        assert talon.marked == [(1, "medium", "ACME"), (2, "high", None), (3, "low", "ACME")]
        pages = talon.finding_pages()
        assert len(pages) == 2
        for page in pages:
            assert page.url.params["status"] == "open" and page.url.params["notified"] == "false"
            assert "since" not in page.url.params
        assert pages[1].url.params["cursor"] == "1.1"
        identity = pages[0].headers
        assert identity["X-Talon-User"] == "copilot-ops-poller"
        assert identity["X-Talon-Role"] == "admin" and identity["X-Talon-Customers"] == "*"
        assert identity["X-Talon-Tags"] == "*" and identity["X-Talon-Untagged"] == "true"

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_finding_whose_notified_failed_is_never_emitted_twice(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1)]], notified={1: 500})

    async def scenario(h):
        first = await talon_ops_notify.run_poll()
        assert first["emitted"] == 1 and first["marked"] == 0 and first["failed"] == 1
        talon.notified = {}
        second = await talon_ops_notify.run_poll()  # talon-analyst still lists it as unnotified
        assert second["emitted"] == 0 and second["already_queued"] == 1 and second["marked"] == 1
        assert await h.outbox_keys() == ["ops:1:medium"]

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_severity_that_rose_is_left_for_the_next_tick_which_notifies_it_again(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1, severity="medium")]], notified={1: 409})

    async def scenario(h):
        first = await talon_ops_notify.run_poll()
        assert first["rose"] == 1 and first["marked"] == 0
        talon.pages = [[raw_finding(1, severity="high")]]
        talon.notified = {}
        second = await talon_ops_notify.run_poll()
        assert second["emitted"] == 1 and second["marked"] == 1
        assert await h.outbox_keys() == ["ops:1:medium", "ops:1:high"]
        assert talon.marked == [(1, "high", "ACME")]

    run(tmp_path, monkeypatch, talon, scenario)


def test_an_outage_marks_nothing_and_raises_nothing(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1)]], down=True)

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["failed"] == 1 and counts["emitted"] == 0
        assert await h.outbox_keys() == []
        assert not [r for r in talon.requests if r.url.path.endswith("/notified")]

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_malformed_page_marks_nothing(tmp_path, monkeypatch):
    talon = OpsTalon([[]])
    talon.handler = lambda request: httpx.Response(200, content=b"<html>")

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["failed"] == 1 and await h.outbox_keys() == []

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_finding_that_cant_be_queued_is_not_marked(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1)]])
    monkeypatch.setattr(outbox, "queue", AsyncMock(return_value=False))

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["failed"] == 1 and talon.marked == []

    run(tmp_path, monkeypatch, talon, scenario)


def test_with_talon_v2_off_nothing_is_asked(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1)]])

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["skipped"] == "v2_off" and talon.requests == []

    run(tmp_path, monkeypatch, talon, scenario, v2=False)


def test_a_tick_that_doesnt_hold_the_lock_does_nothing(tmp_path, monkeypatch):
    talon = OpsTalon([[raw_finding(1)]])

    class NotHeld:
        async def __aenter__(self):
            return False

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(talon_ops_notify, "poll_lock", lambda: NotHeld())

    async def scenario(h):
        counts = await talon_ops_notify.run_poll()
        assert counts["skipped"] == "locked" and talon.requests == []

    run(tmp_path, monkeypatch, talon, scenario)


def test_the_lock_is_mysqls_named_lock_taken_without_waiting():
    """On MySQL the tick takes ``GET_LOCK(name, 0)`` and releases it; a lock another replica holds (0) skips the tick."""
    statements = []

    class Session:
        def __init__(self, got):
            self.got = got

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="mysql"))

        async def execute(self, statement, params):
            statements.append((str(statement), params))
            return SimpleNamespace(scalar=lambda: self.got)

        async def close(self):
            statements.append(("close", None))

    async def held(got):
        statements.clear()
        original = outbox.new_session
        outbox.new_session = lambda: Session(got)
        try:
            async with talon_ops_notify.poll_lock() as ok:
                return ok, list(statements)
        finally:
            outbox.new_session = original

    ok, inside = asyncio.run(held(1))
    assert ok is True and inside == [("SELECT GET_LOCK(:name, 0)", {"name": talon_ops_notify.LOCK_NAME})]
    assert statements[-2:] == [("SELECT RELEASE_LOCK(:name)", {"name": talon_ops_notify.LOCK_NAME}), ("close", None)]
    ok, _ = asyncio.run(held(0))
    assert ok is False and all("RELEASE_LOCK" not in s for s, _ in statements)


def test_the_job_is_registered_in_both_scheduler_registries():
    from app.schedulers import scheduler

    assert scheduler.get_function_by_name("invoke_talon_ops_notifications").__name__ == "invoke_talon_ops_notifications"
    assert "invoke_talon_ops_notifications" in Path(scheduler.__file__).read_text()


# ── the trigger routes internally only ────────────────────────────────────────


def test_the_trigger_is_internal_only():
    assert NotificationTrigger.TALON_OPS_FINDING.value in INTERNAL_TRIGGERS


def test_an_ops_finding_reaches_internal_routes_only_and_their_severity_floor(tmp_path, monkeypatch):
    talon = OpsTalon([])

    async def scenario(h):
        await h.add_route("SOC ops", scope="internal")
        await h.add_route("SOC ops, High only", scope="internal", min_severity="High")
        await h.add_route("ACME's channel", scope="customer", customer_code="ACME")
        await h.add_route("SOC assignments", scope="internal", trigger="alert_assigned")
        event = talon_ops_finding_event(parsed(raw_finding(1, severity="medium")))
        response = await h.dispatch(event)
        assert response.dispatched == 1
        assert len(h.webhooks) == 1
        async with h.sessions() as session:
            candidates = await svc.routes_for_event(event, session)
        assert {r.name for r in candidates} == {"SOC ops", "SOC ops, High only", "SOC assignments"}  # never ACME's

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_customer_route_on_the_trigger_never_fires_even_saved_directly(tmp_path, monkeypatch):
    talon = OpsTalon([])

    async def scenario(h):
        await h.add_route("ACME's channel", scope="customer", customer_code="ACME")
        response = await h.dispatch(talon_ops_finding_event(parsed(raw_finding(1, severity="high"))))
        assert response.routes_matched == 0 and h.webhooks == []

    run(tmp_path, monkeypatch, talon, scenario)


def test_a_customer_route_cant_be_saved_with_the_trigger():
    payload = NotificationRouteCreate(
        name="ACME ops",
        trigger="talon_ops_finding",
        channel="webhook",
        config={"url": HOOK},
        min_severity="Informational",
    )
    with pytest.raises(HTTPException) as refused:
        asyncio.run(svc.create_route("ACME", payload, "admin", AsyncMock()))
    assert refused.value.status_code == 400 and "internal routes only" in refused.value.detail
    with pytest.raises(HTTPException):
        svc._refuse_internal_only_trigger("customer", NotificationTrigger.TALON_OPS_FINDING)
    svc._refuse_internal_only_trigger("internal", NotificationTrigger.TALON_OPS_FINDING)


# ── severity, subject and summary ─────────────────────────────────────────────


@pytest.mark.parametrize("ops,copilot", [("info", "Informational"), ("low", "Low"), ("medium", "Medium"), ("high", "High")])
def test_severity_maps_to_copilots(ops, copilot):
    event = talon_ops_finding_event(parsed(raw_finding(7, severity=ops)))
    assert event.severity.value == copilot
    assert event.dedupe_key == f"ops:7:{ops}"


def test_the_subject_and_summary_are_codes_fields_only():
    event = talon_ops_finding_event(parsed(raw_finding(7)), job_title="Endpoints gone quiet")
    assert event.subject == "Talon ops: host-7: not seen by Wazuh for 5 days"
    assert "Endpoints gone quiet" in event.summary and "customer ACME" in event.summary
    for text in (event.subject, event.summary, svc._format_default_body(event)):
        assert "MODELWHY" not in text and "evil" not in text and "MODELREC" not in text
    platform = talon_ops_finding_event(parsed(raw_finding(8, customer=None)))
    assert "the platform" in platform.summary and platform.customer_code is None


# ── the v1 block ──────────────────────────────────────────────────────────────

OPS_KEYS = [
    "id",
    "job",
    "kind",
    "severity",
    "title",
    "customer_code",
    "evidence_summary",
    "why",
    "recommendation",
    "explained",
    "artifact",
    "status",
    "first_seen",
    "last_seen",
    "ops_url",
    "truncated_fields",
]


def test_the_webhook_gets_the_ops_finding_block_and_a_null_ai_report(tmp_path, monkeypatch):
    talon = OpsTalon([])

    async def scenario(h):
        await h.add_route("SOC ops", scope="internal", config={"url": HOOK, "method": "POST", "headers": None, "include_full_report": True})
        await h.dispatch(talon_ops_finding_event(parsed(raw_finding(1))))
        payload = h.webhooks[0]["structured_payload"]
        assert payload["schema"] == SCHEMA_V1 and payload["ai_report"] is None
        assert "report_markdown" not in payload  # no flat report fields: there is no alert
        block = payload["ops_finding"]
        assert list(block) == OPS_KEYS
        assert block["id"] == 1 and block["job"] == "quiet_endpoints" and block["kind"] == "wazuh_quiet"
        assert block["severity"] == "medium" and block["customer_code"] == "ACME" and block["status"] == "open"
        assert (
            block["evidence_summary"]
            == "agent_id: 001; agent_name: host-1; wazuh_days_quiet: 5.1; critical_asset: no; conditions: wazuh_quiet"
        )
        assert block["why"].startswith("It <b>stopped</b>")  # as written: plain text for the receiver
        assert block["first_seen"] == "2026-10-24T06:00:00Z" and block["last_seen"] == "2026-10-24T06:00:00Z"
        assert block["ops_url"] == "https://copilot.example.com/ai-analyst?tab=ops&finding=1"
        assert block["artifact"] is None and block["truncated_fields"] == []

    run(tmp_path, monkeypatch, talon, scenario)


def test_the_shuffle_envelope_carries_the_block_too():
    event = talon_ops_finding_event(parsed(raw_finding(1)))
    envelope = v1_envelope(event, None)
    assert envelope["ai_report"] is None and envelope["ops_finding"]["id"] == 1


def test_the_block_is_bounded():
    raw = raw_finding(1, why="w" * 50_000, recommendation="r" * 50_000, artifact={"type": "xml", "body": "é" * 50_000})
    block = ops_finding_v1.build_ops_finding_v1(parsed(raw), ops_url=None)
    assert ops_finding_v1.serialized_size(block) <= ops_finding_v1.MAX_OPS_FINDING_V1_BYTES
    assert "why" in block["truncated_fields"] and "artifact.body" in block["truncated_fields"]


# ── escaping ──────────────────────────────────────────────────────────────────


def _template(fmt, body):
    return SimpleNamespace(id=1, format=fmt, body_template=body, subject_template="{{ context.ops_finding.title }}", customer_code=None)


@pytest.mark.parametrize(
    "fmt,body,check",
    [
        (
            "html",
            "<p>{{ context.ops_finding.why }}</p><p>{{ context.ops_finding.recommendation }}</p>",
            lambda out: "&lt;b&gt;stopped&lt;/b&gt;" in out and "<b>" not in out,
        ),
        (
            "markdown",
            "{{ context.ops_finding.why }}\n\n{{ context.ops_finding.recommendation }}",
            lambda out: r"\[this\]\(http://evil\.example\)" in out and r"\!\[x\]" in out and out.count(r"\# Restart") == 1,
        ),
    ],
)
def test_the_models_text_is_escaped_in_html_and_markdown_templates(monkeypatch, fmt, body, check):
    monkeypatch.setattr(svc, "resolve_template_for_route", AsyncMock(return_value=_template(fmt, body)))
    monkeypatch.setattr(svc, "_branding_context", AsyncMock(return_value={}))
    route = SimpleNamespace(id=3, format_template=None, scope="internal", channel="resend", template_id=1)
    event = talon_ops_finding_event(parsed(raw_finding(1)))
    message, error = asyncio.run(svc._render_body(route, event, AsyncMock()))
    assert error is None and check(message.body)
    # The shared event is untouched: other routes get the block as sent.
    assert event.context["ops_finding"]["why"].startswith("It <b>")


def test_a_markdown_rendering_of_the_escaped_text_shows_it_as_written():
    from app.notifications.utils.markdown_html import markdown_to_html

    escaped = ops_finding_v1.escape_markdown("see [this](http://evil.example) ![x](http://e/p.png) **bold** # h")
    html = str(markdown_to_html(escaped))
    assert "<a " not in html and "<img" not in html and "<strong>" not in html and "<h1>" not in html


def test_the_default_body_has_no_model_text(monkeypatch):
    monkeypatch.setenv("COPILOT_URL", "https://copilot.example.com")
    body = svc._format_default_body(talon_ops_finding_event(parsed(raw_finding(1))))
    assert body.startswith("*Talon ops finding* — severity: *Medium*")
    assert "Finding: #1 — host-1: not seen by Wazuh for 5 days" in body
    assert "Customer: `ACME`" in body and "Open in CoPilot: https://copilot.example.com/ai-analyst?tab=ops&finding=1" in body
    assert "MODELWHY" not in body and "MODELREC" not in body


def test_the_test_send_and_the_preview_carry_the_ops_context():
    route = SimpleNamespace(id=3, name="SOC", trigger="talon_ops_finding", customer_code=None, created_by="lead")
    event = svc._sample_event_for(route)
    assert event.entity_type == "ops_finding" and event.assignee_username is None
    assert event.context["ops_finding"] == ops_finding_v1.sample_ops_finding_v1()
    from app.notifications.services.templates import sample_event

    assert sample_event("talon_ops_finding", None).context["ops_finding"]["job"] == "quiet_endpoints"


# ── the docs ──────────────────────────────────────────────────────────────────


def test_the_documented_ops_finding_example_is_the_real_shape():
    doc = (Path(__file__).resolve().parents[2] / "docs" / "user" / "notifications.md").read_text()
    section = doc[doc.index("### The `ops_finding` block") :]
    start = section.index("```json\n") + len("```json\n")
    example = json.loads(section[start : section.index("\n```", start)])
    assert example["schema"] == SCHEMA_V1 and example["ai_report"] is None
    assert example["ops_finding"] == ops_finding_v1.sample_ops_finding_v1()
