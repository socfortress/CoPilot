"""Test-send: deliver one real notification through a route on demand.

Uses the normal send path rather than a per-provider probe. A probe tests the
wrong thing — the Resend key in use is send-only restricted, so an account-state
check 401s while sending works fine. What an operator wants to know is "will a
real notification arrive", and only a real send answers that.

The outcome IS logged. A test send consumes provider quota exactly like a live
one; leaving it out would make the Resend monthly counter under-report and hide
test traffic from the audit trail.

Two of these tests exist because the live run caught bugs the rest of the suite
missed: an unimported name in the sample-event builder, and a field name left
behind by #1022's rename. Both survived a green suite because nothing exercised
this path.

Run with: cd backend && python -m pytest tests/test_notification_test_send.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels.base import SendResult  # noqa: E402
from app.notifications.schema.notifications import DispatchStatus  # noqa: E402


def _route(trigger="investigation_complete", channel="webhook", scope="customer", customer_code="TENANT_A"):
    return SimpleNamespace(
        id=7,
        name="SOC webhook",
        channel=channel,
        scope=scope,
        customer_code=customer_code,
        trigger=trigger,
        min_severity="Informational",
        destination="",
        format_template=None,
        created_by="analyst_one",
        config=json.dumps({"url": "https://example.invalid/hook"}),
        recipient_mode="static",
        shuffle_integration_id=None,
        notify_on_self_assign=False,
    )


def _run(route, send_result=None, record=None):
    send = AsyncMock(return_value=send_result or SendResult(status="sent", latency_ms=12, provider_reference="ref-1"))
    rec = record or AsyncMock(return_value=True)
    with (
        patch.object(type(CHANNEL_REGISTRY["webhook"]), "send", send),
        patch.object(svc, "_record_log", rec),
    ):
        outcome = asyncio.run(svc.send_test_notification(route, AsyncMock()))
    return outcome, send, rec


# ── the two bugs the live run caught ──────────────────────────────────────


def test_sample_event_builds_for_every_trigger():
    """Regression: NotificationSeverity was unimported, so this raised NameError
    for every trigger — invisible because nothing exercised the builder."""
    for trigger in ["investigation_complete", "alert_created", "alert_assigned", "case_assigned", "case_task_assigned"]:
        event = svc._sample_event_for(_route(trigger=trigger))
        assert event.severity is not None
        assert event.trigger.value == trigger


def test_outcome_uses_the_current_field_name():
    """Regression: this passed `shuffle_execution_id`, renamed to
    `provider_reference` in #1022. Pydantic accepted the construction and failed
    on read — rename residue that survives a green suite."""
    outcome, _send, _rec = _run(_route())
    assert outcome.provider_reference == "ref-1"
    assert not hasattr(outcome, "shuffle_execution_id")


# ── the sample event ──────────────────────────────────────────────────────


def test_dedupe_key_is_unique_per_test_so_repeats_always_send():
    """A test that silently no-ops the second time would be worse than useless."""
    first = svc._sample_event_for(_route()).dedupe_key
    second = svc._sample_event_for(_route()).dedupe_key
    assert first != second
    assert first.startswith("test:7:")


def test_entity_type_follows_the_trigger():
    assert svc._sample_event_for(_route(trigger="case_assigned")).entity_type == "case"
    assert svc._sample_event_for(_route(trigger="case_task_assigned")).entity_type == "case_task"
    assert svc._sample_event_for(_route(trigger="alert_created")).entity_type == "alert"


def test_assignment_triggers_get_an_assignee_so_assignee_mode_can_resolve():
    """Without one, testing an assignee-mode route would always skip with
    'this event has no assignee' and tell the operator nothing."""
    event = svc._sample_event_for(_route(trigger="alert_assigned"))
    assert event.assignee_username == "analyst_one"


def test_non_assignment_triggers_have_no_assignee():
    assert svc._sample_event_for(_route(trigger="alert_created")).assignee_username is None


def test_unknown_trigger_falls_back_rather_than_raising():
    """A hand-edited row shouldn't make the test button 500."""
    event = svc._sample_event_for(_route(trigger="something_removed"))
    assert event.trigger.value == "investigation_complete"


# ── dispatch behaviour ────────────────────────────────────────────────────


def test_a_successful_test_is_reported_and_logged():
    outcome, send, rec = _run(_route())

    assert outcome.status == DispatchStatus.SENT
    assert send.await_count == 1
    assert rec.await_count == 1, "a test send consumes quota; it belongs in the log"


def test_a_failed_test_reports_the_providers_message():
    outcome, _send, _rec = _run(_route(), send_result=SendResult.failed("Domain not verified"))
    assert outcome.status == DispatchStatus.FAILED
    assert outcome.error_message == "Domain not verified"


def test_a_raising_provider_is_reported_not_propagated():
    """The button must return a result, never a 500."""
    send = AsyncMock(side_effect=RuntimeError("boom"))
    with (
        patch.object(type(CHANNEL_REGISTRY["webhook"]), "send", send),
        patch.object(svc, "_record_log", AsyncMock(return_value=True)),
    ):
        outcome = asyncio.run(svc.send_test_notification(_route(), AsyncMock()))

    assert outcome.status == DispatchStatus.FAILED
    assert "RuntimeError" in outcome.error_message


def test_unknown_channel_is_reported_without_touching_a_provider():
    outcome = asyncio.run(svc.send_test_notification(_route(channel="carrier-pigeon"), AsyncMock()))
    assert outcome.status == DispatchStatus.FAILED
    assert "Unsupported channel" in outcome.error_message


@pytest.mark.parametrize("scope,customer_code", [("customer", "TENANT_A"), ("internal", None)])
def test_both_scopes_can_be_tested(scope, customer_code):
    outcome, send, _rec = _run(_route(scope=scope, customer_code=customer_code))
    assert outcome.status == DispatchStatus.SENT
    assert send.await_count == 1
