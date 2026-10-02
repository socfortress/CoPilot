"""The SLA notification triggers (#1187) across the notification module.

`test_soc_management_notifier.py` pins *when* an SLA notice is owed; this pins what the
notification module does with one:

- it resolves against internal routes only, and a route's severity floor applies;
- the "Send test" event and the template editor's preview event carry the SLA context,
  so a template written against `context.clock` tests and previews as it will send;
- the built-in "SLA — running late" template renders a real SLA event for both triggers
  (under StrictUndefined, like a real dispatch).

Run with: cd backend && python -m pytest tests/test_notification_sla_triggers.py
"""

import asyncio
import json
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.notifications.services.notifications as svc  # noqa: E402
from app.db.universal_models import CustomerNotificationRoute  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import sla_event  # noqa: E402
from app.notifications.services.rendering import render  # noqa: E402
from app.notifications.services.template_seeds import BUILTIN_TEMPLATES  # noqa: E402
from app.notifications.services.templates import sample_event  # noqa: E402

DUE = datetime(2026, 9, 1, 12, 0)
SLA_CONTEXT_KEYS = {"clock", "due_at", "opened_at", "remaining_minutes", "overdue_minutes", "status"}


def _event(breached=True, severity="High", entity_type=EntityType.ALERT, now=None):
    return sla_event(
        breached=breached,
        entity_type=entity_type,
        entity_id=42,
        title="Ransomware note dropped",
        severity=severity,
        customer_code="ACME",
        assignee="ana",
        clock="resolve",
        due_at=DUE,
        opened_at=DUE - timedelta(hours=8),
        now=now or (DUE + timedelta(minutes=20) if breached else DUE - timedelta(minutes=45)),
        status="IN_PROGRESS",
    )


# ── route resolution ─────────────────────────────────────────────────────────


def _route(name, *, scope, customer_code=None, trigger="sla_breached", min_severity="Informational"):
    return CustomerNotificationRoute(
        name=name,
        scope=scope,
        customer_code=customer_code,
        trigger=trigger,
        channel="webhook",
        destination="",
        enabled=True,
        min_severity=min_severity,
        recipient_mode="static",
        config="{}",
        created_at=datetime(2026, 9, 1),
        created_by="admin",
    )


def _matched(event):
    async def run():
        engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables["customer_notification_route"]]))
        async with AsyncSession(engine) as session:
            session.add_all(
                [
                    _route("SOC breaches", scope="internal"),
                    _route("SOC breaches, Critical only", scope="internal", min_severity="Critical"),
                    _route("SOC at risk", scope="internal", trigger="sla_at_risk"),
                    _route("ACME's channel", scope="customer", customer_code="ACME"),
                ],
            )
            await session.commit()
            candidates = await svc.routes_for_event(event, session)
        await engine.dispose()
        return candidates

    candidates = asyncio.run(run())
    return candidates, sorted(
        r.name
        for r in candidates
        if svc._trigger_applies(event.trigger.value, r.trigger) and svc._severity_meets(event.severity.value, r.min_severity)
    )


def test_an_sla_breach_reaches_internal_routes_only_and_honours_their_floor():
    candidates, matched = _matched(_event())
    assert all(r.scope == "internal" for r in candidates)
    assert matched == ["SOC breaches"]  # not the Critical-only route, never the customer's channel


def test_at_risk_and_breached_are_separate_subscriptions():
    _, matched = _matched(_event(breached=False))
    assert matched == ["SOC at risk"]


# ── test send and preview ────────────────────────────────────────────────────


def _internal_route(trigger):
    return SimpleNamespace(
        id=3,
        name="SOC",
        channel="webhook",
        scope="internal",
        customer_code=None,
        trigger=trigger,
        created_by="lead",
        config=json.dumps({"url": "https://example.invalid/hook"}),
    )


@pytest.mark.parametrize("trigger", ["sla_at_risk", "sla_breached"])
def test_the_test_send_event_carries_the_sla_context_and_an_assignee(trigger):
    event = svc._sample_event_for(_internal_route(trigger))
    assert event.trigger.value == trigger
    assert SLA_CONTEXT_KEYS <= set(event.context)
    assert event.assignee_username == "lead"  # so an assignee route can resolve someone


@pytest.mark.parametrize("trigger, timing_key", [("sla_at_risk", "remaining_minutes"), ("sla_breached", "overdue_minutes")])
def test_the_editor_preview_carries_the_sla_context(trigger, timing_key):
    event = sample_event(trigger, None)
    assert SLA_CONTEXT_KEYS <= set(event.context)
    assert event.context[timing_key] is not None


def test_the_editor_preview_of_other_triggers_has_no_sla_context():
    assert "clock" not in sample_event("alert_created", None).context


# ── the built-in template ────────────────────────────────────────────────────

SLA_TEMPLATE = next(spec for spec in BUILTIN_TEMPLATES if spec["name"] == "SLA — running late")


def _render(event):
    return render(SLA_TEMPLATE["subject_template"], event), render(SLA_TEMPLATE["body_template"], event)


def test_the_builtin_template_renders_a_breach():
    subject, body = _render(_event())
    assert subject == "SLA breached: Alert #42 — Ransomware note dropped"
    assert "*SLA breached* — resolve target, severity *High*" in body
    assert "Alert: #42 — Ransomware note dropped" in body
    assert "Customer: `ACME`" in body and "Assigned to: ana" in body
    assert "Due: 2026-09-01 12:00 UTC (20 min overdue)" in body


def test_the_builtin_template_renders_an_at_risk_case():
    _, body = _render(_event(breached=False, entity_type=EntityType.CASE))
    assert "*SLA at risk* — resolve target" in body
    assert "Case: #42" in body
    assert "(45 min left)" in body


def test_the_builtin_template_is_offered_to_both_triggers():
    assert SLA_TEMPLATE["trigger"] is None  # unscoped: one template serves both
    assert {t.value for t in NotificationTrigger} >= {"sla_at_risk", "sla_breached"}
