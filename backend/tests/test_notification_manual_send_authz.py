"""Guardrails on manually sending an alert or case to a notification channel.

**Written before the endpoint existed**, deliberately. Prose saying "enforce this
server-side" decays into "the UI hides it"; a red test does not.

Manual send is a **data egress control point**, not a convenience feature.
Someone with the button can push a customer's alert to an outside channel on
demand, bypassing the trigger and severity filters that govern automatic
notifications. Every check below must hold in the service layer, independently of
what the route form chooses to offer — the cross-tenant case in particular is
something the UI would never present, which is exactly why it needs a test.

Unit tests with mocked sessions — no DB, no network.

Run with: cd backend && python -m pytest tests/test_notification_manual_send_authz.py
"""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.notifications.services.manual_send as ms  # noqa: E402

ADMIN, ANALYST, CUSTOMER_USER = 1, 2, 4
OWNER, OTHER = "TENANT_A", "TENANT_B"


def _user(role_id=ANALYST, username="analyst_one"):
    return SimpleNamespace(id=7, username=username, role_id=role_id)


def _alert(alert_id=42, customer_code=OWNER):
    return SimpleNamespace(
        id=alert_id,
        alert_name="Mimikatz signature",
        customer_code=customer_code,
        severity="Critical",
        assigned_to=None,
    )


def _route(route_id=1, scope="customer", customer_code=OWNER, channel="webhook"):
    return SimpleNamespace(
        id=route_id,
        name="SOC webhook",
        channel=channel,
        scope=scope,
        customer_code=customer_code,
        trigger="alert_created",
        min_severity="Informational",
        destination="",
        format_template=None,
        config=json.dumps({"url": "https://example.invalid/hook"}),
        shuffle_integration_id=None,
        notify_on_self_assign=False,
        created_by="admin",
    )


def _session(alert=None, route=None):
    """Mocked session returning `alert` then `route` from successive lookups."""
    session = AsyncMock()
    results = []
    for obj in (alert, route):
        r = MagicMock()
        r.scalars.return_value.first.return_value = obj
        results.append(r)
    session.execute = AsyncMock(side_effect=results * 4)
    return session


#: Stands in for a loaded AI report. These tests are about authorization, not
#: content, so the shape only has to be truthy — but it must be *present*, or a
#: send asking for the report is refused for having nothing to attach, which
#: would fail these tests for a reason none of them are testing.
_A_REPORT = {"markdown": "# Report", "html": "<h1>Report</h1>", "summary": "s", "severity": "Medium", "iocs": []}


def _send(
    user,
    alert,
    route,
    *,
    tag_ok=True,
    customer_ok=True,
    ai_enabled=True,
    include_ai_report=False,
    report=_A_REPORT,
):
    sent = AsyncMock(return_value=SimpleNamespace(status="sent", error_message=None, latency_ms=5, provider_reference="r"))
    with (
        patch.object(ms, "_load_entity", AsyncMock(return_value=alert)),
        patch.object(ms, "_load_route", AsyncMock(return_value=route)),
        patch("app.incidents.middleware.tag_access.tag_access_handler.can_user_access_alert", AsyncMock(return_value=tag_ok)),
        patch("app.middleware.customer_access.customer_access_handler.check_customer_access", AsyncMock(return_value=customer_ok)),
        patch.object(ms, "is_ai_reports_enabled", AsyncMock(return_value=ai_enabled)),
        patch.object(ms, "safe_load_ai_report_context", AsyncMock(return_value=report)),
        patch.object(ms, "_deliver", sent),
    ):
        outcome = asyncio.run(
            ms.send_manual(
                entity_type="alert",
                entity_id=alert.id if alert else 1,
                route_id=route.id if route else 1,
                user=user,
                session=AsyncMock(),
                include_ai_report=include_ai_report,
            ),
        )
    return outcome, sent


def _expect_denied(**kw):
    with pytest.raises(HTTPException) as exc:
        _send(**kw)
    return exc.value


# ── who may send where ────────────────────────────────────────────────────


def test_an_analyst_cannot_send_to_a_customer_facing_route():
    """Sending out to an end customer bypasses the severity and trigger filters
    by definition, so it gets a second pair of eyes."""
    err = _expect_denied(user=_user(ANALYST), alert=_alert(), route=_route(scope="customer"))
    assert err.status_code == 403


def test_an_admin_may_send_to_a_customer_facing_route():
    outcome, sent = _send(user=_user(ADMIN), alert=_alert(), route=_route(scope="customer"))
    assert outcome.status.value == "sent"
    assert sent.await_count == 1


def test_an_analyst_may_send_to_an_internal_route():
    """Routine internal sharing stays frictionless."""
    outcome, sent = _send(user=_user(ANALYST), alert=_alert(), route=_route(scope="internal", customer_code=None))
    assert outcome.status.value == "sent"


def test_a_customer_user_may_never_send():
    """Portal users have no business pushing data anywhere."""
    err = _expect_denied(user=_user(CUSTOMER_USER), alert=_alert(), route=_route(scope="internal", customer_code=None))
    assert err.status_code == 403


# ── tenancy ───────────────────────────────────────────────────────────────


def test_a_route_belonging_to_another_customer_is_refused():
    """The UI would never offer this pairing — which is exactly why the server
    must reject it rather than trust the submitted route_id."""
    err = _expect_denied(
        user=_user(ADMIN),
        alert=_alert(customer_code=OWNER),
        route=_route(scope="customer", customer_code=OTHER),
    )
    assert err.status_code == 400
    assert "customer" in err.detail.lower()


def test_an_internal_route_is_not_bound_to_the_entitys_customer():
    """Internal routes belong to no tenant, so the cross-tenant check must not
    reject them for having no customer_code."""
    outcome, _sent = _send(user=_user(ADMIN), alert=_alert(), route=_route(scope="internal", customer_code=None))
    assert outcome.status.value == "sent"


# ── object-level authorization ────────────────────────────────────────────


def test_an_alert_the_user_cannot_see_is_refused():
    """Without this, manual send becomes a read primitive: sending an alert to a
    channel you can read is a way to view alerts the tag rules deny you."""
    err = _expect_denied(user=_user(ADMIN), alert=_alert(), route=_route(), tag_ok=False)
    assert err.status_code == 403


def test_a_customer_the_user_cannot_access_is_refused():
    err = _expect_denied(user=_user(ADMIN), alert=_alert(), route=_route(), customer_ok=False)
    assert err.status_code == 403


def test_a_missing_entity_is_a_404_not_a_500():
    with patch.object(ms, "_load_entity", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                ms.send_manual(
                    entity_type="alert",
                    entity_id=999,
                    route_id=1,
                    user=_user(ADMIN),
                    session=AsyncMock(),
                    include_ai_report=False,
                ),
            )
    assert exc.value.status_code == 404


# ── the AI opt-out gate ───────────────────────────────────────────────────


def test_ai_report_cannot_be_attached_when_the_customer_opted_out():
    """Otherwise this button is the hole in the opt-out that #1014 established —
    an analyst could hand-deliver AI findings to a customer who declined them."""
    err = _expect_denied(
        user=_user(ADMIN),
        alert=_alert(),
        route=_route(scope="customer"),
        ai_enabled=False,
        include_ai_report=True,
    )
    assert err.status_code == 400
    assert "ai" in err.detail.lower()


def test_a_send_without_the_ai_report_is_unaffected_by_the_gate():
    """The gate governs AI-written content, not every notification."""
    outcome, _sent = _send(
        user=_user(ADMIN),
        alert=_alert(),
        route=_route(scope="customer"),
        ai_enabled=False,
        include_ai_report=False,
    )
    assert outcome.status.value == "sent"


def test_the_gate_does_not_apply_to_internal_routes():
    """Keeping AI findings in-house is a supported configuration."""
    outcome, _sent = _send(
        user=_user(ADMIN),
        alert=_alert(),
        route=_route(scope="internal", customer_code=None),
        ai_enabled=False,
        include_ai_report=True,
    )
    assert outcome.status.value == "sent"


# ── repeatability ─────────────────────────────────────────────────────────


def test_every_manual_send_gets_a_unique_dedupe_key():
    """DELIBERATE EXCEPTION to the engine's core idempotency rule.

    Every other trigger dedupes so a repeat is a no-op. Manual send must be
    repeatable — clicking "send" twice on purpose has to send twice — so the key
    carries a uuid and each click is its own audit row.

    If a future reader "fixes" this to match the other triggers, repeat sends
    break silently. That is why this test exists.
    """
    first = ms.build_manual_event(entity_type="alert", entity_id=42, entity=_alert(), user=_user())
    second = ms.build_manual_event(entity_type="alert", entity_id=42, entity=_alert(), user=_user())

    assert first.dedupe_key != second.dedupe_key
    assert first.dedupe_key.startswith("alert:42:manual:")


def test_the_manual_event_records_who_sent_it():
    """Who pushed which customer's data where is a compliance question."""
    event = ms.build_manual_event(entity_type="alert", entity_id=42, entity=_alert(), user=_user(username="alice"))
    assert event.actor_username == "alice"
