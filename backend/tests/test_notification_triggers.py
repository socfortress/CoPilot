"""CoPilot-originated notification triggers.

Until #1006 the dispatch loop was only ever reached from Talon's HTTP call.
These triggers fire from inside CoPilot, which introduces three ways to be
wrong that the AI path never had:

1. **Scope.** An assignment is about who is working on something, so it must
   resolve against internal routes. Leaking it to the customer's channel would
   tell ACME which analyst picked up their alert.
2. **Spam.** `alert_created` sits on the ingest hot path and assignments fire on
   every PATCH. Emitting on recurrence, or on a write that changed nothing,
   multiplies straight into someone's inbox.
3. **Blocking.** A slow provider must not back up alert ingestion.

Unit tests with mocked sessions — no DB, no network.

Run with: cd backend && python -m pytest tests/test_notification_triggers.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.channels import CHANNEL_REGISTRY  # noqa: E402
from app.notifications.channels.base import SendResult  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import alert_assigned_event  # noqa: E402
from app.notifications.services.event_builders import alert_created_event  # noqa: E402
from app.notifications.services.event_builders import case_assigned_event  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    case_task_assigned_event,
)

CUSTOMER = "TENANT_A"


def _route(trigger, scope, route_id=1, notify_on_self_assign=False, min_severity="Informational"):
    return SimpleNamespace(
        id=route_id,
        name=f"{scope} route",
        channel="webhook",
        scope=scope,
        enabled=True,
        trigger=trigger,
        min_severity=min_severity,
        destination="",
        format_template=None,
        config='{"url": "https://example.invalid/hook"}',
        shuffle_integration_id=None,
        notify_on_self_assign=notify_on_self_assign,
    )


def _dispatch(event, routes):
    """Run dispatch_event with the route query and providers stubbed."""
    with (
        patch.object(svc, "routes_for_event", AsyncMock(return_value=routes)) as lookup,
        patch.object(svc, "is_ai_reports_enabled", AsyncMock(return_value=True)),
        patch.object(svc, "_record_log", AsyncMock(return_value=True)),
        patch.object(
            type(CHANNEL_REGISTRY["webhook"]),
            "send",
            AsyncMock(return_value=SendResult(status="sent", latency_ms=1)),
        ) as send,
        patch.object(type(CHANNEL_REGISTRY["webhook"]), "after_send", AsyncMock()),
    ):
        response = asyncio.run(svc.dispatch_event(event, AsyncMock()))
    return response, send, lookup


# ── scope: the tenancy guarantee ──────────────────────────────────────────


@pytest.mark.parametrize(
    "event",
    [
        alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="alice", customer_code=CUSTOMER),
        case_assigned_event(case_id=1, title="t", assignee="bob", actor="alice", customer_code=CUSTOMER),
        case_task_assigned_event(task_id=1, case_id=2, title="t", assignee="bob", actor="alice", customer_code=CUSTOMER),
    ],
    ids=["alert", "case", "case_task"],
)
def test_assignments_resolve_against_internal_routes(event):
    """The whole point of the scope dimension: telling a customer which analyst
    picked up their alert is a tenancy leak, not a feature."""
    assert event.trigger.value in INTERNAL_TRIGGERS


def test_alert_created_resolves_against_customer_routes():
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t")
    assert event.trigger.value not in INTERNAL_TRIGGERS


def test_route_query_filters_by_scope_not_just_customer():
    """A stale query filtering only on customer_code would hand assignment
    notifications to customer-facing routes."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)

    event = alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="alice", customer_code=CUSTOMER)
    asyncio.run(svc.routes_for_event(event, session))

    where = str(session.execute.await_args.args[0])
    assert "scope" in where


# ── self-assignment suppression ───────────────────────────────────────────


def test_self_assignment_is_suppressed_by_default():
    """An analyst picking up their own alert doesn't need an email about it."""
    event = alert_assigned_event(alert_id=1, title="t", assignee="alice", actor="alice", customer_code=CUSTOMER)
    response, send, _ = _dispatch(event, [_route("alert_assigned", "internal")])

    assert send.await_count == 0
    assert response.routes_matched == 0


def test_self_assignment_fires_when_the_route_opts_in():
    event = alert_assigned_event(alert_id=1, title="t", assignee="alice", actor="alice", customer_code=CUSTOMER)
    response, send, _ = _dispatch(event, [_route("alert_assigned", "internal", notify_on_self_assign=True)])

    assert send.await_count == 1
    assert response.dispatched == 1


def test_assigning_to_someone_else_always_fires():
    event = alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="alice", customer_code=CUSTOMER)
    _response, send, _ = _dispatch(event, [_route("alert_assigned", "internal")])
    assert send.await_count == 1


def test_suppression_does_not_apply_to_non_assignment_triggers():
    """actor == assignee is meaningless for alert_created; the check must not
    accidentally swallow it."""
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t")
    event.actor_username = "alice"
    event.assignee_username = "alice"
    _response, send, _ = _dispatch(event, [_route("alert_created", "customer")])
    assert send.await_count == 1


# ── dedupe keys: the anti-spam guarantee ──────────────────────────────────


def test_reassigning_back_to_someone_notifies_them_again():
    """A → B → A must reach A twice. A key of just (entity, trigger) could not
    express that, which is why the assignee is in it."""
    a1 = alert_assigned_event(alert_id=1, title="t", assignee="alice", actor="x", customer_code=CUSTOMER)
    b = alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="x", customer_code=CUSTOMER)
    a2 = alert_assigned_event(alert_id=1, title="t", assignee="alice", actor="x", customer_code=CUSTOMER)

    assert a1.dedupe_key != b.dedupe_key
    assert a1.dedupe_key == a2.dedupe_key, "same assignee, same key — the log's idempotency handles the rest"


def test_unassignment_has_its_own_key():
    assigned = alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="x", customer_code=CUSTOMER)
    cleared = alert_assigned_event(alert_id=1, title="t", assignee=None, actor="x", customer_code=CUSTOMER)
    assert assigned.dedupe_key != cleared.dedupe_key
    assert cleared.dedupe_key.endswith("unassigned")


def test_entity_types_do_not_collide():
    """Case #7 and task #7 are different things."""
    case = case_assigned_event(case_id=7, title="t", assignee="bob", actor="x")
    task = case_task_assigned_event(task_id=7, case_id=1, title="t", assignee="bob", actor="x")
    assert case.dedupe_key != task.dedupe_key


# ── severity ──────────────────────────────────────────────────────────────


def test_assignments_are_informational_so_routes_filter_by_trigger():
    """Assignments carry no security severity. Anything higher would be an
    invention; anything lower doesn't exist."""
    event = alert_assigned_event(alert_id=1, title="t", assignee="bob", actor="x")
    assert event.severity.value == "Informational"


def test_alert_created_uses_the_payloads_derived_severity():
    """rule_level -> severity is already computed upstream (issue #980); this
    must not re-derive it differently."""
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t", severity="Critical", rule_level=14)
    assert event.severity.value == "Critical"
    assert event.context["rule_level"] == 14


def test_alert_without_a_severity_defaults_to_medium_not_informational():
    """Sources with no rule level would otherwise be filtered out of every route
    gating above Informational."""
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t", severity=None)
    assert event.severity.value == "Medium"


def test_unknown_severity_string_falls_back_rather_than_raising():
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t", severity="Catastrophic")
    assert event.severity.value == "Medium"


def test_min_severity_still_gates_alert_created():
    event = alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="t", severity="Low")
    _response, send, _ = _dispatch(event, [_route("alert_created", "customer", min_severity="High")])
    assert send.await_count == 0


# ── body rendering ────────────────────────────────────────────────────────


def test_each_trigger_gets_wording_that_fits_it():
    created = svc._format_default_body(alert_created_event(alert_id=1, customer_code=CUSTOMER, alert_title="Mimikatz"))
    assigned = svc._format_default_body(alert_assigned_event(alert_id=1, title="Mimikatz", assignee="bob", actor="alice"))

    assert "New alert" in created
    assert "assigned" in assigned.lower()
    assert "bob" in assigned
    assert "AI investigation" not in created


def test_investigation_wording_is_unchanged_for_existing_customers():
    """This is the text customers already receive; #1006 must not reword it."""
    from app.notifications.schema.events import event_from_dispatch_request
    from app.notifications.schema.notifications import DispatchRequest
    from app.notifications.schema.notifications import NotificationSeverity

    req = DispatchRequest(
        customer_code=CUSTOMER,
        alert_id=42,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity_assessment=NotificationSeverity.CRITICAL,
        summary="Credential dumping observed.",
        report_url="https://copilot.invalid/42",
        alert_name="Mimikatz signature",
    )
    body = svc._format_default_body(event_from_dispatch_request(req))

    assert body.startswith("*AI investigation complete* — severity: *Critical*")
    assert "Alert: #42 — Mimikatz signature" in body
    assert "Full report: https://copilot.invalid/42" in body


def test_existing_template_tokens_still_render():
    """Stored format_templates predate the envelope and must keep working."""
    route = _route("alert_created", "customer")
    route.format_template = "{{severity}} on {{customer_code}} alert {{alert_id}}: {{alert_name}}"
    body, err = svc._render_body(route, alert_created_event(alert_id=9, customer_code=CUSTOMER, alert_title="X", severity="High"))
    assert body == f"High on {CUSTOMER} alert 9: X"
    assert err is None, "an existing template must render cleanly under Jinja"


def test_new_assignment_tokens_are_available():
    route = _route("alert_assigned", "internal")
    route.format_template = "{{assignee}} <- {{actor}} ({{entity_type}}#{{entity_id}})"
    body, err = svc._render_body(route, alert_assigned_event(alert_id=3, title="t", assignee="bob", actor="alice"))
    assert body == "bob <- alice (alert#3)"
    assert err is None
