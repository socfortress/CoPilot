"""The versioned notification payload, `copilot.notification.v1` (`services/payload_v1.py`).

What these pin:

- the webhook's structured payload gains `schema` and, with `include_full_report`, a nested
  `ai_report` block, while the **old flat keys** (names, values, nulls, order) stay exactly as
  they were: existing receivers parse them;
- the block's fields, its IOC cap and its truncation markers, and a byte bound on it whatever
  the characters;
- Shuffle carries the same block as the last line of its text input;
- templates reach it as `context.ai_report_v1`, and naming it does not load `context.ai_report`;
- the AI report switch: a customer route never gets the block while it is off (whatever the
  trigger), internal routes are not gated, and only internal routes see the job id;
- the outbox: the block is loaded when a row is delivered, never stored on it, so a replay
  carries the report as it is then.

A real SQLite database in a file (`NullPool`, each session its own connection) behind the real
dispatch loop, providers and outbox; only the outbound HTTP calls are replaced by recorders.

Run with: cd backend && python -m pytest tests/test_notification_payload_v1.py
"""

import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.dialects.mysql import LONGTEXT  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.channels.shuffle as shuffle_mod  # noqa: E402
import app.notifications.channels.webhook as webhook_mod  # noqa: E402
import app.notifications.services.notifications as svc  # noqa: E402
from app.db.universal_models import AiAnalystIoc  # noqa: E402
from app.db.universal_models import AiAnalystJob  # noqa: E402
from app.db.universal_models import AiAnalystReport  # noqa: E402
from app.db.universal_models import AiAnalystReview  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.db.universal_models import CustomerPortalAiReportSettings  # noqa: E402
from app.db.universal_models import CustomerShuffleIntegration  # noqa: E402
from app.db.universal_models import NotificationOutbox  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from app.notifications.channels.base import DispatchContext  # noqa: E402
from app.notifications.channels.shuffle import ShuffleConfig  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteCreate  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services import outbox  # noqa: E402
from app.notifications.services import payload_v1  # noqa: E402
from app.notifications.services.ai_report_context import MAX_IOCS  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    ai_report_reviewed_event,
)
from app.notifications.services.event_builders import alert_assigned_event  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    investigation_complete_event,
)
from app.notifications.services.payload_v1 import MAX_AI_REPORT_V1_BYTES  # noqa: E402
from app.notifications.services.payload_v1 import SCHEMA_V1  # noqa: E402
from app.notifications.services.payload_v1 import SHUFFLE_JSON_MARKER  # noqa: E402
from app.notifications.services.payload_v1 import TRUNCATION_MARK  # noqa: E402
from app.notifications.services.payload_v1 import build_ai_report_v1  # noqa: E402
from app.notifications.services.payload_v1 import serialized_size  # noqa: E402


@compiles(LONGTEXT, "sqlite")
def _longtext_on_sqlite(type_, compiler, **kw):
    """`ai_analyst_report.report_markdown` is MySQL's LONGTEXT; SQLite stores it as TEXT."""
    return "TEXT"


CC = "TENANT_A"
OTHER = "TENANT_B"
ALERT = 14
JOB = "copilot-inv-14-1700000000000"
T0 = datetime(2026, 10, 1, 12, 0, 0)
LINK = "https://copilot.example.com/alerts/14"
HOOK = "https://receiver.example.invalid/hook"

TABLES = [
    "customers",
    "customer_portal_ai_report_settings",
    "customer_shuffle_integration",
    "customer_notification_route",
    "notification_dispatch_log",
    "notification_outbox",
    "ai_analyst_job",
    "ai_analyst_report",
    "ai_analyst_ioc",
    "ai_analyst_review",
    "incident_management_alert",
    "incident_management_asset",
]


# ── the harness ──────────────────────────────────────────────────────────────


class Harness:
    def __init__(self, path, monkeypatch):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.webhooks = []
        self.shuffles = []
        monkeypatch.setattr(outbox, "new_session", self.sessions)
        monkeypatch.setenv("COPILOT_URL", "https://copilot.example.com")

        async def webhook(**kwargs):
            self.webhooks.append(kwargs)
            return ("sent", None, 1, None)

        async def shuffle(**kwargs):
            self.shuffles.append(kwargs)
            return ("sent", None, 1, "exec-1")

        monkeypatch.setattr(webhook_mod, "dispatch_webhook", webhook)
        monkeypatch.setattr(shuffle_mod, "dispatch_shuffle", shuffle)
        monkeypatch.setattr(shuffle_mod, "get_shuffle_connector", AsyncMock(return_value=("https://shuffle.example.invalid", "key")))

    async def create(self):
        tables = [SQLModel.metadata.tables[t] for t in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    async def add(self, *rows):
        async with self.sessions() as session:
            session.add_all(rows)
            await session.commit()
            return [getattr(r, "id", None) for r in rows]

    async def ai_switch(self, customer_code=CC, enabled=True):
        await self.add(CustomerPortalAiReportSettings(customer_code=customer_code, enabled=enabled))

    async def seed(self, *, iocs=None, customer_code=CC):
        """Alert 14 with one asset, its job, one report and two IOCs."""
        await self.add(
            Alert(
                id=ALERT,
                alert_name="Administrators Group Changed",
                alert_description="A user was added to a privileged group.",
                status="OPEN",
                customer_code=customer_code,
                source="wazuh",
                alert_creation_time=T0,
            ),
        )
        await self.add(
            Asset(
                alert_linked=ALERT,
                asset_name="WIN-DC01",
                alert_context_id=1,
                customer_code=customer_code,
                index_name="wazuh-alerts-1",
                index_id="abc",
            ),
            AiAnalystJob(id=JOB, alert_id=ALERT, customer_code=customer_code, triggered_by="webhook", created_at=T0),
        )
        (report_id,) = await self.add(
            AiAnalystReport(
                job_id=JOB,
                alert_id=ALERT,
                customer_code=customer_code,
                severity_assessment="High",
                summary="Credential dumping observed.",
                report_markdown="# Report\n\nFindings.",
                recommended_actions="Isolate the host.",
                created_at=T0,
            ),
        )
        if iocs is None:
            iocs = [
                dict(ioc_value="203.0.113.7", ioc_type="ip", vt_verdict="malicious", vt_score="12/90", details="C2 beacon"),
                dict(ioc_value="example.invalid", ioc_type="domain", vt_verdict="unknown", vt_score=None, details=None),
            ]
        await self.add(
            *[
                AiAnalystIoc(report_id=report_id, alert_id=ALERT, customer_code=customer_code, created_at=T0 + timedelta(seconds=n), **i)
                for n, i in enumerate(iocs)
            ],
        )
        return report_id

    async def route(self, name="Automation", *, channel="webhook", scope="customer", trigger="investigation_complete", **over):
        config = over.pop("config", None)
        if config is None:
            config = {"url": HOOK, "method": "POST", "headers": None, "include_full_report": True}
        base = dict(
            name=name,
            scope=scope,
            customer_code=CC if scope == "customer" else None,
            trigger=trigger,
            channel=channel,
            destination="",
            enabled=True,
            min_severity="Informational",
            recipient_mode="static",
            config=json.dumps(config),
            created_at=T0,
            created_by="admin",
        )
        base.update(over)
        (route_id,) = await self.add(CustomerNotificationRoute(**base))
        return route_id

    async def dispatch(self, event):
        async with self.sessions() as session:
            return await svc.dispatch_event(event, session)

    async def dispose(self):
        await self.engine.dispose()


def run(tmp_path, monkeypatch, scenario):
    async def inner():
        harness = await Harness(tmp_path / "payload.db", monkeypatch).create()
        try:
            return await scenario(harness)
        finally:
            await harness.dispose()

    return asyncio.run(inner())


def _investigation():
    return investigation_complete_event(
        alert_id=ALERT,
        customer_code=CC,
        severity="High",
        summary="Credential dumping observed.",
        alert_name="Administrators Group Changed",
        asset_name="WIN-DC01",
    )


def _expected_block(report_id, *, job_id=None, reviewed=False, review_verdict=None, summary="Credential dumping observed."):
    return {
        "report_id": report_id,
        "job_id": job_id,
        "severity": "High",
        "summary": summary,
        "recommended_actions": "Isolate the host.",
        "created_at": "2026-10-01T12:00:00Z",
        "report_url": LINK,
        "alert": {"id": ALERT, "name": "Administrators Group Changed", "source": "wazuh", "asset_name": "WIN-DC01"},
        "iocs": [
            {"value": "203.0.113.7", "type": "ip", "verdict": "malicious", "score": "12/90", "details": "C2 beacon", "truncated": False},
            {"value": "example.invalid", "type": "domain", "verdict": "unknown", "score": None, "details": None, "truncated": False},
        ],
        "ioc_count": 2,
        "iocs_truncated": False,
        "reviewed": reviewed,
        "review_verdict": review_verdict,
        "truncated_fields": [],
    }


# ── the webhook payload: v1 added, the old shape kept ───────────────────────────


#: The structured payload's keys before v1, in order. Receivers read these names.
OLD_BASE_KEYS = ["customer_code", "alert_id", "alert_name", "severity", "summary", "report_url", "text"]
#: What `include_full_report` merged flat before v1, in order.
OLD_FLAT_KEYS = ["report_id", "recommended_actions", "report_markdown", "report_created_at", "iocs"]


def test_with_the_full_report_the_old_flat_shape_is_unchanged_and_v1_is_nested(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch()
        await h.route()
        await h.dispatch(_investigation())
        return report_id, h.webhooks

    report_id, sent = run(tmp_path, monkeypatch, scenario)
    assert len(sent) == 1
    payload = dict(sent[0]["structured_payload"])
    assert sent[0]["rendered_template"] is None

    # The old shape, pinned whole: names, values, nulls and order.
    assert list(payload) == OLD_BASE_KEYS + ["schema"] + OLD_FLAT_KEYS + ["ai_report"]
    assert isinstance(payload.pop("text"), str)
    ai_report = payload.pop("ai_report")
    assert payload == {
        "customer_code": CC,
        "alert_id": ALERT,
        "alert_name": "Administrators Group Changed",
        "severity": "High",
        "summary": "Credential dumping observed.",
        "report_url": LINK,
        "schema": SCHEMA_V1,
        "report_id": report_id,
        "recommended_actions": "Isolate the host.",
        "report_markdown": "# Report\n\nFindings.",
        # Naive isoformat, no `Z`: the old field's format, unchanged.
        "report_created_at": "2026-10-01T12:00:00",
        # Newest first, by alert, with the old key names and null semantics.
        "iocs": [
            {"ioc_value": "example.invalid", "ioc_type": "domain", "vt_verdict": "unknown", "vt_score": None, "details": None},
            {"ioc_value": "203.0.113.7", "ioc_type": "ip", "vt_verdict": "malicious", "vt_score": "12/90", "details": "C2 beacon"},
        ],
    }
    # The customer route never sees the job id.
    assert ai_report == _expected_block(report_id)


def test_without_the_full_report_there_is_a_schema_and_no_block(tmp_path, monkeypatch):
    async def scenario(h):
        await h.seed()
        await h.ai_switch()
        await h.route(config={"url": HOOK, "method": "POST", "headers": None, "include_full_report": False})
        await h.dispatch(_investigation())
        return h.webhooks

    (sent,) = run(tmp_path, monkeypatch, scenario)
    payload = sent["structured_payload"]
    assert list(payload) == OLD_BASE_KEYS + ["schema"]
    assert payload["schema"] == SCHEMA_V1


def test_with_the_full_report_and_no_report_the_block_is_null_and_nothing_flat(tmp_path, monkeypatch):
    async def scenario(h):
        await h.ai_switch()
        await h.route()
        await h.dispatch(_investigation())
        return h.webhooks

    (sent,) = run(tmp_path, monkeypatch, scenario)
    assert list(sent["structured_payload"]) == OLD_BASE_KEYS + ["schema", "ai_report"]
    assert sent["structured_payload"]["ai_report"] is None


def test_a_review_event_carries_the_reviewed_report_and_its_verdict(tmp_path, monkeypatch):
    """`ai_report_reviewed` names its report: a newer one for the same alert doesn't replace it.
    An internal route (the trigger is dual-scope) also sees the job id."""

    async def scenario(h):
        reviewed_id = await h.seed()
        await h.add(AiAnalystJob(id="copilot-inv-14-2", alert_id=ALERT, customer_code=CC, triggered_by="manual", created_at=T0))
        await h.add(
            AiAnalystReport(
                job_id="copilot-inv-14-2",
                alert_id=ALERT,
                customer_code=CC,
                severity_assessment="Low",
                summary="A later run.",
                created_at=T0 + timedelta(hours=1),
            ),
        )
        await h.route("SOC", scope="internal", trigger="ai_report_reviewed")
        event = ai_report_reviewed_event(
            alert_id=ALERT,
            report_id=reviewed_id,
            customer_code=CC,
            severity="High",
            summary="Credential dumping observed.",
            reviewer="asmith",
            verdict="up",
            alert_name="Administrators Group Changed",
        )
        await h.dispatch(event)
        return reviewed_id, h.webhooks

    reviewed_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    assert sent["structured_payload"]["ai_report"] == _expected_block(reviewed_id, job_id=JOB, reviewed=True, review_verdict="up")


def test_reviewed_reflects_a_stored_review_on_other_triggers(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.add(AiAnalystReview(report_id=report_id, alert_id=ALERT, customer_code=CC, reviewer_user_id=3, overall_verdict="down"))
        await h.ai_switch()
        await h.route()
        await h.dispatch(_investigation())
        return h.webhooks

    (sent,) = run(tmp_path, monkeypatch, scenario)
    block = sent["structured_payload"]["ai_report"]
    # The verdict is announced only by the review trigger; elsewhere it stays null.
    assert (block["reviewed"], block["review_verdict"]) == (True, None)


# ── the AI report switch and the scopes ─────────────────────────────────────────


def test_an_ai_trigger_with_the_switch_off_still_sends_nothing_to_the_customer(tmp_path, monkeypatch):
    async def scenario(h):
        await h.seed()
        await h.ai_switch(enabled=False)
        await h.route()
        result = await h.dispatch(_investigation())
        return result, h.webhooks

    result, sent = run(tmp_path, monkeypatch, scenario)
    assert sent == []
    assert result.skipped == 1


def test_a_customer_route_on_a_non_ai_trigger_gets_no_block_while_the_switch_is_off(tmp_path, monkeypatch):
    """The dispatch gate only covers AI triggers. The block has its own check, so a customer route
    on `alert_created` with the full report on can't receive it while the switch is off."""

    async def scenario(h):
        await h.seed()
        await h.route(trigger="alert_created")
        event = NotificationEvent(
            customer_code=CC,
            trigger=NotificationTrigger.ALERT_CREATED,
            severity=NotificationSeverity.HIGH,
            subject="Administrators Group Changed",
            summary="A new alert was created.",
            entity_type=EntityType.ALERT,
            entity_id=ALERT,
            dedupe_key=f"alert:{ALERT}:alert_created",
            context={"alert_name": "Administrators Group Changed"},
        )
        await h.dispatch(event)
        off = h.webhooks[-1]["structured_payload"]["ai_report"]
        await h.ai_switch()
        await h.dispatch(event)
        on = h.webhooks[-1]["structured_payload"]["ai_report"]
        return off, on

    off, on = run(tmp_path, monkeypatch, scenario)
    assert off is None
    assert on is not None and on["job_id"] is None


def test_an_internal_route_is_not_gated_and_sees_the_job_id(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch(enabled=False)
        await h.route("SOC", scope="internal", trigger="alert_assigned")
        event = alert_assigned_event(
            alert_id=ALERT,
            title="Administrators Group Changed",
            assignee="jdoe",
            actor="asmith",
            customer_code=CC,
            severity="High",
        )
        await h.dispatch(event)
        return report_id, h.webhooks

    report_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    # An assignment carries no link, so neither does its block.
    assert sent["structured_payload"]["ai_report"] == {**_expected_block(report_id, job_id=JOB), "report_url": None}


def test_a_report_of_another_customer_or_alert_is_never_sent(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed(customer_code=OTHER)
        await h.ai_switch()
        async with h.sessions() as session:
            # The event says TENANT_A; the alert and its report are TENANT_B's.
            mismatched = await payload_v1.load_ai_report_v1(_investigation(), session)
            # A review event naming a report of another alert.
            foreign = _investigation().model_copy(update={"entity_id": 99, "context": {"report_id": report_id}})
            other_alert = await payload_v1.load_ai_report_v1(foreign, session)
            case = _investigation().model_copy(update={"entity_type": EntityType.CASE})
            not_an_alert = await payload_v1.load_ai_report_v1(case, session)
        return mismatched, other_alert, not_an_alert

    assert run(tmp_path, monkeypatch, scenario) == (None, None, None)


def test_a_review_of_a_report_that_is_gone_is_not_replaced_by_another(tmp_path, monkeypatch):
    async def scenario(h):
        await h.seed()
        async with h.sessions() as session:
            event = _investigation().model_copy(update={"context": {"report_id": 999}})
            return await payload_v1.load_ai_report_v1(event, session)

    assert run(tmp_path, monkeypatch, scenario) is None


def test_a_route_without_a_scope_is_treated_as_a_customer_route():
    event = _investigation()
    session = AsyncMock()

    async def scenario():
        ctx = DispatchContext(session=session, event=event)
        enabled = AsyncMock(return_value=False)
        load = AsyncMock(return_value={"job_id": JOB, "truncated_fields": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.customer_portal.services.ai_reports.is_ai_reports_enabled", enabled)
            mp.setattr(payload_v1, "safe_load_ai_report_v1", load)
            gated = await payload_v1.ai_report_v1_for_route(None, event, session, ctx)
            internal = await payload_v1.ai_report_v1_for_route("internal", event, session, ctx)
        return gated, internal, load.await_count

    gated, internal, loads = asyncio.run(scenario())
    assert gated is None
    assert internal == {"job_id": JOB, "truncated_fields": []}
    assert loads == 1


# ── the AI report setting governs every report field ───────────────────────────


def _alert_created():
    return NotificationEvent(
        customer_code=CC,
        trigger=NotificationTrigger.ALERT_CREATED,
        severity=NotificationSeverity.HIGH,
        subject="Administrators Group Changed",
        summary="A new alert was created.",
        entity_type=EntityType.ALERT,
        entity_id=ALERT,
        dedupe_key=f"alert:{ALERT}:alert_created",
        context={"alert_name": "Administrators Group Changed"},
    )


#: Reaches every report surface a template has: `context.ai_report` and the v1 block.
REPORT_TEMPLATE = (
    "{% if context.ai_report %}SUMMARY={{ context.ai_report.summary }} MD={{ context.ai_report.markdown }}"
    "{% else %}NO-REPORT{% endif %} V1={{ context.ai_report_v1 | tojson }}"
)


@pytest.mark.parametrize("enabled", [False, True])
def test_the_setting_governs_the_flat_fields_on_a_non_ai_trigger(tmp_path, monkeypatch, enabled):
    """Off: exactly the "no report yet" payload, a shape receivers already handle. On: unchanged."""

    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch(enabled=enabled)
        await h.route(trigger="alert_created")
        await h.dispatch(_alert_created())
        return report_id, h.webhooks

    report_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    payload = sent["structured_payload"]
    if enabled:
        assert list(payload) == OLD_BASE_KEYS + ["schema"] + OLD_FLAT_KEYS + ["ai_report"]
        assert payload["report_id"] == report_id
        assert payload["ai_report"]["report_id"] == report_id
    else:
        assert list(payload) == OLD_BASE_KEYS + ["schema", "ai_report"]
        assert payload["ai_report"] is None


#: The `{{report}}` token is substituted by the webhook after rendering, so a Jinja template has
#: to emit it literally (`{% raw %}`); a bare `{{report}}` is an undefined variable.
@pytest.mark.parametrize("enabled", [False, True])
def test_the_setting_governs_the_report_token(tmp_path, monkeypatch, enabled):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch(enabled=enabled)
        await h.route(
            trigger="alert_created",
            config={"url": HOOK, "method": "POST", "headers": None},
            format_template='{"r": {% raw %}{{report}}{% endraw %}}',
        )
        await h.dispatch(_alert_created())
        return report_id, h.webhooks

    report_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    body = json.loads(sent["rendered_template"])
    if enabled:
        assert body["r"]["report_id"] == report_id
        assert body["r"]["recommended_actions"] == "Isolate the host."
    else:
        # The token's "no report yet" value.
        assert body == {"r": None}


@pytest.mark.parametrize("enabled", [False, True])
def test_the_setting_governs_template_access_on_a_webhook(tmp_path, monkeypatch, enabled):
    async def scenario(h):
        await h.seed()
        await h.ai_switch(enabled=enabled)
        await h.route(trigger="alert_created", config={"url": HOOK, "method": "POST", "headers": None}, format_template=REPORT_TEMPLATE)
        await h.dispatch(_alert_created())
        return h.webhooks

    (sent,) = run(tmp_path, monkeypatch, scenario)
    body = sent["rendered_template"]
    if enabled:
        assert "SUMMARY=Credential dumping observed." in body and "MD=# Report" in body
        assert "V1=null" not in body
    else:
        assert body == "NO-REPORT V1=null"


@pytest.mark.parametrize("enabled", [False, True])
def test_the_setting_governs_a_shuffle_route(tmp_path, monkeypatch, enabled):
    async def scenario(h):
        await h.seed()
        await h.ai_switch(enabled=enabled)
        (integration_id,) = await h.add(CustomerShuffleIntegration(customer_code=CC, display_name="Acme", shuffle_org_id="org-1"))
        await h.route(
            "Shuffle Slack",
            channel="shuffle",
            trigger="alert_created",
            destination="#soc",
            shuffle_integration_id=integration_id,
            format_template=REPORT_TEMPLATE,
            config={"app_id": "app-1", "app_name": "Slack", "include_full_report": True},
        )
        await h.dispatch(_alert_created())
        return h.shuffles

    (sent,) = run(tmp_path, monkeypatch, scenario)
    head, payload = _shuffle_input(sent["input_text"])
    text = "\n".join(head)
    if enabled:
        assert "SUMMARY=Credential dumping observed." in text
        assert payload["ai_report"] is not None
    else:
        assert "Credential dumping" not in sent["input_text"]
        assert text.startswith("Send to #soc: NO-REPORT V1=null")
        assert payload["ai_report"] is None


def test_an_internal_route_gets_every_report_field_with_the_setting_off(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch(enabled=False)
        await h.route("SOC full", scope="internal", trigger="alert_assigned")
        await h.route(
            "SOC template",
            scope="internal",
            trigger="alert_assigned",
            config={"url": HOOK, "method": "POST", "headers": None},
            format_template="{% if context.ai_report %}{{ context.ai_report.summary }}{% endif %} {% raw %}{{report}}{% endraw %}",
        )
        await h.dispatch(
            alert_assigned_event(alert_id=ALERT, title="Administrators Group Changed", assignee="jdoe", actor="asmith", customer_code=CC),
        )
        return report_id, h.webhooks

    report_id, sent = run(tmp_path, monkeypatch, scenario)
    full, templated = sorted(sent, key=lambda kw: kw["rendered_template"] is not None)
    assert list(full["structured_payload"]) == OLD_BASE_KEYS + ["schema"] + OLD_FLAT_KEYS + ["ai_report"]
    assert full["structured_payload"]["report_id"] == report_id
    assert templated["rendered_template"].startswith("Credential dumping observed. {")
    assert json.loads(templated["rendered_template"][len("Credential dumping observed. ") :])["report_id"] == report_id


def _admin():
    from app.auth.models.users import RoleEnum

    return SimpleNamespace(id=1, username="admin", role_id=RoleEnum.admin.value)


@pytest.mark.parametrize("enabled", [False, True])
def test_a_manual_send_without_the_report_follows_the_setting(tmp_path, monkeypatch, enabled):
    """`include_ai_report=False` to a customer route whose config has `include_full_report`:
    off, no report fields (and no report in the template); on, the route's config as before."""
    import app.notifications.services.manual_send as ms

    monkeypatch.setattr(ms, "_require_object_access", AsyncMock(return_value=None))

    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch(enabled=enabled)
        full = await h.route("Full", trigger="alert_created")
        templated = await h.route(
            "Templated",
            trigger="alert_created",
            config={"url": HOOK, "method": "POST", "headers": None},
            format_template=REPORT_TEMPLATE + " T={% raw %}{{report}}{% endraw %}",
        )
        for route_id in (full, templated):
            async with h.sessions() as session:
                outcome = await ms.send_manual(entity_type="alert", entity_id=ALERT, route_id=route_id, user=_admin(), session=session)
                assert outcome.status.value == "sent"
        return report_id, h.webhooks

    report_id, (full, templated) = run(tmp_path, monkeypatch, scenario)
    if enabled:
        assert full["structured_payload"]["report_id"] == report_id
        assert full["structured_payload"]["ai_report"]["report_id"] == report_id
        assert "SUMMARY=Credential dumping observed." in templated["rendered_template"]
    else:
        assert list(full["structured_payload"]) == OLD_BASE_KEYS + ["schema", "ai_report"]
        assert full["structured_payload"]["ai_report"] is None
        assert templated["rendered_template"] == "NO-REPORT V1=null T=null"


def test_a_manual_send_asking_for_the_report_is_still_refused_with_the_setting_off(tmp_path, monkeypatch):
    from fastapi import HTTPException

    import app.notifications.services.manual_send as ms

    monkeypatch.setattr(ms, "_require_object_access", AsyncMock(return_value=None))

    async def scenario(h):
        await h.seed()
        await h.ai_switch(enabled=False)
        route_id = await h.route("Full", trigger="alert_created")
        async with h.sessions() as session:
            with pytest.raises(HTTPException) as refused:
                await ms.send_manual(
                    entity_type="alert",
                    entity_id=ALERT,
                    route_id=route_id,
                    user=_admin(),
                    session=session,
                    include_ai_report=True,
                )
        return refused.value.status_code, h.webhooks

    assert run(tmp_path, monkeypatch, scenario) == (400, [])


def test_the_flat_fields_and_the_block_name_the_same_report_on_a_timestamp_tie(tmp_path, monkeypatch):
    async def scenario(h):
        first = await h.seed()
        await h.add(AiAnalystJob(id="copilot-inv-14-2", alert_id=ALERT, customer_code=CC, triggered_by="manual", created_at=T0))
        (second,) = await h.add(
            AiAnalystReport(job_id="copilot-inv-14-2", alert_id=ALERT, customer_code=CC, summary="Same second.", created_at=T0),
        )
        await h.ai_switch()
        await h.route()
        await h.dispatch(_investigation())
        return first, second, h.webhooks

    first, second, (sent,) = run(tmp_path, monkeypatch, scenario)
    assert second > first
    payload = sent["structured_payload"]
    assert payload["report_id"] == payload["ai_report"]["report_id"] == second


# ── caps, truncation and the size bound ────────────────────────────────────────


def _row(**over):
    base = dict(
        id=1,
        job_id=JOB,
        alert_id=ALERT,
        severity_assessment="High",
        summary="s",
        recommended_actions="a",
        created_at=T0,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _ioc(n=0, **over):
    base = dict(ioc_value=f"198.51.100.{n % 250}", ioc_type="ip", vt_verdict="unknown", vt_score=None, details=None)
    base.update(over)
    return SimpleNamespace(**base)


def _build(report=None, iocs=(), **over):
    kw = dict(
        report=report or _row(),
        iocs=list(iocs),
        job_id=JOB,
        alert=SimpleNamespace(alert_name="Alert", source="wazuh"),
        asset_name="WIN-DC01",
        reviewed=False,
        review_verdict=None,
        report_url=LINK,
    )
    kw.update(over)
    return build_ai_report_v1(**kw)


def test_the_ioc_list_is_capped_and_says_so():
    block = _build(iocs=[_ioc(n) for n in range(MAX_IOCS + 7)])
    assert len(block["iocs"]) == MAX_IOCS
    assert block["ioc_count"] == MAX_IOCS + 7
    assert block["iocs_truncated"] is True

    exact = _build(iocs=[_ioc(n) for n in range(MAX_IOCS)])
    assert (len(exact["iocs"]), exact["iocs_truncated"]) == (MAX_IOCS, False)


def test_long_strings_are_cut_and_marked():
    block = _build(
        report=_row(summary="x" * 10_000, recommended_actions="y" * 10_000),
        iocs=[_ioc(details="d" * 5000), _ioc(1, details="short")],
    )
    assert len(block["summary"]) == payload_v1.MAX_SUMMARY_CHARS
    assert block["summary"].endswith(TRUNCATION_MARK)
    assert len(block["recommended_actions"]) == payload_v1.MAX_RECOMMENDED_ACTIONS_CHARS
    assert block["recommended_actions"].endswith(TRUNCATION_MARK)
    assert block["truncated_fields"] == ["summary", "recommended_actions"]
    first, second = block["iocs"]
    assert len(first["details"]) == payload_v1.MAX_IOC_DETAILS_CHARS and first["details"].endswith(TRUNCATION_MARK)
    assert first["truncated"] is True
    assert (second["details"], second["truncated"]) == ("short", False)


def test_nothing_is_marked_when_nothing_was_cut():
    block = _build(iocs=[_ioc()])
    assert block["truncated_fields"] == []
    assert block["iocs"][0]["truncated"] is False
    assert TRUNCATION_MARK not in json.dumps(block, ensure_ascii=False)


def test_empty_values_are_null_not_empty_strings():
    block = _build(report=_row(summary="", recommended_actions=None, severity_assessment=None), asset_name=None, report_url=None)
    assert (block["summary"], block["recommended_actions"], block["severity"], block["report_url"]) == (None, None, None, None)
    assert block["alert"]["asset_name"] is None


def test_created_at_is_iso_8601_utc():
    from datetime import timezone

    assert _build(report=_row(created_at=datetime(2026, 1, 2, 3, 4, 5, 678))).get("created_at") == "2026-01-02T03:04:05Z"
    aware = datetime(2026, 1, 2, 5, 4, 5, tzinfo=timezone(timedelta(hours=2)))
    assert _build(report=_row(created_at=aware))["created_at"] == "2026-01-02T03:04:05Z"


@pytest.mark.parametrize("char", ["a", "é", "\U0001f600", " ", '"'])
def test_the_block_stays_under_its_bound_whatever_the_characters(char):
    """Characters are capped per field, and the bytes are checked as well: escaping can make one
    character twelve bytes. IOCs go first, then the long texts."""
    block = _build(
        report=_row(summary=char * 100_000, recommended_actions=char * 100_000),
        iocs=[_ioc(n, ioc_value=char * 2000, details=char * 20_000, vt_score=char * 200) for n in range(500)],
        alert=SimpleNamespace(alert_name=char * 5000, source=char * 500),
        asset_name=char * 5000,
    )
    assert serialized_size(block) <= MAX_AI_REPORT_V1_BYTES
    assert len(json.dumps(block, separators=(",", ":")).encode()) <= MAX_AI_REPORT_V1_BYTES
    assert block["ioc_count"] == 500 and block["iocs_truncated"] is True
    assert "summary" in block["truncated_fields"]
    # A webhook payload around it stays under 64 KB.
    envelope = payload_v1.v1_envelope(_investigation(), block)
    assert len(json.dumps(envelope).encode()) < 64 * 1024


# ── Shuffle ──────────────────────────────────────────────────────────────────


def _shuffle_input(text):
    """How a workflow reads it: the line after the marker is the JSON."""
    lines = text.split("\n")
    assert lines[-1].startswith(SHUFFLE_JSON_MARKER + " ")
    return lines[:-1], json.loads(lines[-1][len(SHUFFLE_JSON_MARKER) + 1 :])


def test_shuffle_carries_the_block_as_the_last_line_of_its_input(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch()
        (integration_id,) = await h.add(CustomerShuffleIntegration(customer_code=CC, display_name="Acme", shuffle_org_id="org-1"))
        await h.route(
            "Shuffle Slack",
            channel="shuffle",
            destination="#soc",
            shuffle_integration_id=integration_id,
            config={"app_id": "app-1", "app_name": "Slack", "include_full_report": True},
        )
        await h.dispatch(_investigation())
        return report_id, h.shuffles

    report_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    text = sent["input_text"]
    head, payload = _shuffle_input(text)
    assert head[0].startswith("Send to #soc: ")
    assert head[-1] == ""
    assert text.split("\n")[-1].isascii()
    assert payload == {
        "schema": SCHEMA_V1,
        "customer_code": CC,
        "alert_id": ALERT,
        "alert_name": "Administrators Group Changed",
        "severity": "High",
        "summary": "Credential dumping observed.",
        "report_url": LINK,
        "ai_report": _expected_block(report_id),
    }
    assert [i["value"] for i in payload["ai_report"]["iocs"]] == ["203.0.113.7", "example.invalid"]


def test_shuffle_without_the_option_sends_what_it_always_sent(tmp_path, monkeypatch):
    async def scenario(h):
        await h.seed()
        await h.ai_switch()
        (integration_id,) = await h.add(CustomerShuffleIntegration(customer_code=CC, display_name="Acme", shuffle_org_id="org-1"))
        await h.route(
            "Shuffle Slack",
            channel="shuffle",
            destination="#soc",
            shuffle_integration_id=integration_id,
            config={"app_id": "app-1", "app_name": "Slack"},
        )
        await h.dispatch(_investigation())
        return h.shuffles

    (sent,) = run(tmp_path, monkeypatch, scenario)
    assert SHUFFLE_JSON_MARKER not in sent["input_text"]
    assert sent["input_text"].startswith("Send to #soc: *AI investigation complete*")


def test_shuffle_json_line_is_one_ascii_line_whatever_the_report_holds():
    block = _build(report=_row(summary="line one\nline two é\U0001f600"))
    event = _investigation()
    session = AsyncMock()
    session.get = AsyncMock(return_value=SimpleNamespace(id=7, customer_code=CC, enabled=True, shuffle_org_id="org-1"))
    sent = AsyncMock(return_value=("sent", None, 1, "exec-1"))
    route = SimpleNamespace(
        id=1,
        name="Shuffle",
        channel="shuffle",
        scope="customer",
        destination="",
        shuffle_integration_id=7,
        config=json.dumps({"app_id": "app-1", "include_full_report": True}),
    )
    from app.notifications.channels import CHANNEL_REGISTRY
    from app.notifications.channels.base import RenderedMessage

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(shuffle_mod, "dispatch_shuffle", sent)
        mp.setattr(shuffle_mod, "get_shuffle_connector", AsyncMock(return_value=("https://shuffle.example.invalid", "k")))
        mp.setattr(shuffle_mod, "ai_report_v1_for_route", AsyncMock(return_value=block))
        asyncio.run(
            CHANNEL_REGISTRY["shuffle"].send(
                route=route,
                event=event,
                message=RenderedMessage(body="BODY"),
                ctx=DispatchContext(session=session, event=event),
            ),
        )
    text = sent.await_args.kwargs["input_text"]
    head, payload = _shuffle_input(text)
    assert head == ["BODY", ""]
    assert text.split("\n")[-1].isascii()
    assert payload["ai_report"]["summary"] == "line one\nline two é\U0001f600"


def test_a_shuffle_route_accepts_the_option_and_defaults_it_off():
    assert ShuffleConfig().include_full_report is False
    route = NotificationRouteCreate(
        name="Shuffle",
        trigger="investigation_complete",
        channel="shuffle",
        destination="#soc",
        shuffle_integration_id=7,
        config={"app_id": "app-1", "include_full_report": True},
    )
    assert route.config["include_full_report"] is True


# ── templates ────────────────────────────────────────────────────────────────


def test_a_template_reaches_the_block_as_context_ai_report_v1(tmp_path, monkeypatch):
    template = '{"alert": {{ alert_id }}, "summary": {{ summary | tojson }}, "report": {{ context.ai_report_v1 | tojson }}}'

    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch()
        await h.route(config={"url": HOOK, "method": "POST", "headers": None, "include_full_report": False}, format_template=template)
        old_loader = AsyncMock(return_value=None)
        monkeypatch.setattr(svc, "safe_load_ai_report_context", old_loader)
        await h.dispatch(_investigation())
        return report_id, h.webhooks, old_loader.await_count

    report_id, (sent,), old_loads = run(tmp_path, monkeypatch, scenario)
    rendered = json.loads(sent["rendered_template"])
    # The existing variables mean what they did; the block is beside them.
    assert rendered["alert"] == ALERT
    assert rendered["summary"] == "Credential dumping observed."
    assert rendered["report"] == _expected_block(report_id)
    # Naming `ai_report_v1` doesn't load `context.ai_report` (the markdown and HTML) as well.
    assert old_loads == 0


def test_a_template_on_a_gated_route_gets_null(tmp_path, monkeypatch):
    template = '{"report": {{ context.ai_report_v1 | tojson }}}'

    async def scenario(h):
        await h.seed()
        await h.route(trigger="alert_created", config={"url": HOOK, "method": "POST", "headers": None}, format_template=template)
        event = _investigation().model_copy(
            update={"trigger": NotificationTrigger.ALERT_CREATED, "dedupe_key": f"alert:{ALERT}:alert_created"},
        )
        await h.dispatch(event)
        return event, h.webhooks

    event, (sent,) = run(tmp_path, monkeypatch, scenario)
    assert json.loads(sent["rendered_template"]) == {"report": None}
    # The block went on a copy: the shared event's context is unchanged.
    assert "ai_report_v1" not in event.context


def test_ai_report_templates_still_load_the_old_context():
    """`context.ai_report` keeps its loader; only a template naming nothing but the v1 block skips it."""
    assert svc._MENTIONS_AI_REPORT.search("{{ context.ai_report.html }}")
    assert svc._MENTIONS_AI_REPORT.search("{{ context.ai_report_v1 }} {{ context.ai_report.summary }}")
    assert not svc._MENTIONS_AI_REPORT.search("{{ context.ai_report_v1 | tojson }}")


# ── the outbox: loaded at delivery, never stored ───────────────────────────────


def test_a_replayed_outbox_row_carries_the_report_as_it_is_at_delivery(tmp_path, monkeypatch):
    async def scenario(h):
        report_id = await h.seed()
        await h.ai_switch()
        await h.route()
        event = _investigation()
        assert await outbox.queue(event)

        # The report changes after the event was queued (a correction, a retry hours later).
        async with h.sessions() as session:
            await session.execute(update(AiAnalystReport).where(AiAnalystReport.id == report_id).values(summary="Corrected summary."))
            await session.commit()

        await outbox.drain_key(event.dedupe_key, outbox.OutboxSettings(jitter=0.0))

        async with h.sessions() as session:
            row = (await session.execute(select(NotificationOutbox))).scalars().one()
            # What a direct delivery of the deserialized event would carry now.
            replayed = NotificationEvent.model_validate_json(row.event_json)
            direct = await payload_v1.ai_report_v1_for_route("customer", replayed, session)
        return report_id, row, direct, h.webhooks

    report_id, row, direct, (sent,) = run(tmp_path, monkeypatch, scenario)
    assert row.status == "done"
    # Nothing of the block is stored on the row.
    assert "ai_report" not in row.event_json
    delivered = sent["structured_payload"]["ai_report"]
    assert delivered == _expected_block(report_id, summary="Corrected summary.")
    assert delivered == direct


def test_a_review_event_survives_the_outbox_round_trip(tmp_path, monkeypatch):
    """The review's report id and verdict travel in the event's context, through JSON and back."""

    async def scenario(h):
        report_id = await h.seed()
        await h.route("SOC", scope="internal", trigger="ai_report_reviewed")
        event = ai_report_reviewed_event(
            alert_id=ALERT,
            report_id=report_id,
            customer_code=CC,
            severity="High",
            summary="Credential dumping observed.",
            reviewer="asmith",
            verdict="down",
            alert_name="Administrators Group Changed",
        )
        assert await outbox.queue(event)
        await outbox.drain_key(event.dedupe_key, outbox.OutboxSettings(jitter=0.0))
        return report_id, h.webhooks

    report_id, (sent,) = run(tmp_path, monkeypatch, scenario)
    assert sent["structured_payload"]["ai_report"] == _expected_block(report_id, job_id=JOB, reviewed=True, review_verdict="down")
