"""The AI-report opt-out must gate notifications, not just the portal.

``customer_portal_ai_report_settings`` is the operator's opt-in switch for
publishing AI analyst findings to an end customer. It was enforced only on the
portal's read paths, so a notification route was a second way the same content
reached the same customer — bypassing the opt-out entirely. See issue #1001.

``test_customer_portal_ai_reports_access.py`` locks the portal side of this
invariant; this module locks the notification side. The two enforcement points
deliberately share one predicate (``is_ai_reports_enabled``) so they cannot
drift, and the first test below asserts exactly that wiring.

Unit tests with a mocked session — no real DB.

Run with: cd backend && python -m pytest tests/test_notification_ai_report_gating.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels.base import SendResult  # noqa: E402
from app.notifications.schema.notifications import AI_SOURCED_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import DispatchRequest  # noqa: E402
from app.notifications.schema.notifications import DispatchStatus  # noqa: E402
from app.notifications.schema.notifications import NotificationChannel  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402

CUSTOMER = "TENANT_A"


def _route(route_id=1, name="SOC webhook", channel=NotificationChannel.WEBHOOK.value):
    """A route that matches any Informational-or-above investigation dispatch."""
    return SimpleNamespace(
        id=route_id,
        name=name,
        channel=channel,
        enabled=True,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE.value,
        min_severity=NotificationSeverity.INFORMATIONAL.value,
        destination="#soc",
        format_template=None,
        webhook_url="https://example.invalid/hook",
        webhook_method="POST",
        webhook_headers=None,
        include_full_report=False,
        shuffle_app_id=None,
        shuffle_integration_id=None,
    )


def _request(trigger=NotificationTrigger.INVESTIGATION_COMPLETE, severity=NotificationSeverity.CRITICAL):
    return DispatchRequest(
        customer_code=CUSTOMER,
        alert_id=42,
        trigger=trigger,
        severity_assessment=severity,
        summary="Credential dumping observed on WKSTN-04.",
        report_url="https://copilot.invalid/alerts/42",
        alert_name="Mimikatz signature",
    )


def _dispatch(routes, *, ai_enabled):
    """Run dispatch() with the route list and gate state stubbed out.

    Patches at the channel-provider seam rather than at the underlying HTTP
    dispatchers: `provider.send` is what the loop actually calls, so asserting
    on it answers "did anything reach a channel" directly and survives changes
    to how a given provider talks to its vendor.
    """
    with (
        patch.object(svc, "list_routes", AsyncMock(return_value=routes)),
        patch.object(svc, "is_ai_reports_enabled", AsyncMock(return_value=ai_enabled)) as gate,
        patch.object(svc, "_record_log", AsyncMock(return_value=True)) as record,
        patch.object(
            type(CHANNEL_REGISTRY["webhook"]),
            "send",
            AsyncMock(return_value=SendResult(status="sent", latency_ms=12)),
        ) as webhook,
        patch.object(
            type(CHANNEL_REGISTRY["shuffle"]),
            "send",
            AsyncMock(return_value=SendResult(status="sent", latency_ms=12, provider_reference="exec-1")),
        ) as shuffle,
        patch.object(type(CHANNEL_REGISTRY["webhook"]), "after_send", AsyncMock()),
        patch.object(type(CHANNEL_REGISTRY["shuffle"]), "after_send", AsyncMock()),
    ):
        response = asyncio.run(svc.dispatch(_request(), AsyncMock()))
    return response, gate, record, webhook, shuffle


# ── the two enforcement points share one predicate ────────────────────────


def test_gate_uses_the_portal_services_own_predicate():
    """Regression guard against the two checks drifting apart.

    If someone re-implements the lookup inside the notifications module, the
    portal could say "disabled" while notifications say "enabled". Asserting on
    identity keeps a single source of truth.
    """
    from app.customer_portal.services import ai_reports as portal_svc

    assert svc.is_ai_reports_enabled is portal_svc.is_ai_reports_enabled


# ── the gate itself ───────────────────────────────────────────────────────


def test_disabled_customer_receives_nothing():
    response, _gate, _record, webhook, shuffle = _dispatch([_route()], ai_enabled=False)

    assert webhook.await_count == 0, "provider was called despite the AI opt-out"
    assert shuffle.await_count == 0
    assert response.dispatched == 0
    assert response.skipped == 1


def test_enabled_customer_still_receives():
    """The gate must not become a blanket block."""
    response, _gate, _record, webhook, _shuffle = _dispatch([_route()], ai_enabled=True)

    assert webhook.await_count == 1
    assert response.dispatched == 1
    assert response.skipped == 0


def test_missing_settings_row_is_treated_as_disabled():
    """Opt-in semantics: absent row == disabled, not == enabled.

    ``is_ai_reports_enabled`` returns False for a missing row, so this asserts
    the dispatch path honours that rather than defaulting open.
    """
    session = AsyncMock()
    with patch.object(svc, "is_ai_reports_enabled", AsyncMock(return_value=False)):
        permitted = asyncio.run(
            svc._ai_reports_permitted(NotificationTrigger.INVESTIGATION_COMPLETE.value, CUSTOMER, session),
        )
    assert permitted is False


def test_suppression_is_recorded_per_route_not_silent():
    """Every suppressed route gets an audit row with a reason.

    Silence here would be indistinguishable from "no routes configured" when
    someone is debugging why a customer stopped receiving notifications.
    """
    routes = [_route(1, "SOC webhook"), _route(2, "Ops webhook")]
    response, _gate, record, _webhook, _shuffle = _dispatch(routes, ai_enabled=False)

    assert record.await_count == 2
    assert response.routes_matched == 2
    for outcome in response.outcomes:
        assert outcome.status == DispatchStatus.SKIPPED
        assert outcome.error_message and "not enabled" in outcome.error_message

    for call in record.await_args_list:
        assert call.kwargs["status"] == DispatchStatus.SKIPPED.value
        assert call.kwargs["error_message"]


def test_gate_not_consulted_when_no_routes_match():
    """No matched routes means no reason to query the settings table."""
    disabled_route = _route()
    disabled_route.enabled = False
    _response, gate, _record, _webhook, _shuffle = _dispatch([disabled_route], ai_enabled=False)

    assert gate.await_count == 0


# ── scope of the gate ─────────────────────────────────────────────────────


def test_only_ai_sourced_triggers_are_gated():
    """Non-AI triggers must pass regardless of the switch.

    The switch governs AI-written content. Alert-creation and assignment
    notifications (#1006) carry no AI output and must not be suppressed by it.
    """
    session = AsyncMock()
    with patch.object(svc, "is_ai_reports_enabled", AsyncMock(return_value=False)) as gate:
        permitted = asyncio.run(svc._ai_reports_permitted("alert_created", CUSTOMER, session))

    assert permitted is True
    assert gate.await_count == 0, "non-AI trigger should not even consult the switch"


@pytest.mark.parametrize("trigger", sorted(AI_SOURCED_TRIGGERS))
def test_every_ai_sourced_trigger_is_gated(trigger):
    """Includes the legacy `severity_critical_or_high` value.

    Routes saved against an older schema still dispatch AI content through the
    same path (see `_trigger_applies`), so they must be gated too.
    """
    session = AsyncMock()
    with patch.object(svc, "is_ai_reports_enabled", AsyncMock(return_value=False)):
        permitted = asyncio.run(svc._ai_reports_permitted(trigger, CUSTOMER, session))
    assert permitted is False
