"""AI-sourced notification emission from CoPilot itself.

Two changes, both about the AI analyst path:

**Write-back emit.** Talon's `POST /notifications/dispatch` is single-attempt —
a network blip or a CoPilot restart loses the notification even though the
report is already durably stored in `ai_analyst_report`. CoPilot now emits at
write-back too. Both paths must converge on ONE notification, which they do by
building the same dedupe key; the log's idempotency does the rest.

**`ai_report_reviewed`.** A separate trigger rather than a flag on the route, so
an operator can run an internal route on submission AND a customer-facing route
only after an analyst signs off — two audiences at two moments, which a boolean
can't express.

Unit tests — no DB, no network.

Run with: cd backend && python -m pytest tests/test_notification_ai_emit_paths.py
"""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.notifications.schema.events import event_from_dispatch_request  # noqa: E402
from app.notifications.schema.notifications import AI_SOURCED_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import INTERNAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import DispatchRequest  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    ai_report_reviewed_event,
)
from app.notifications.services.event_builders import alert_created_event  # noqa: E402
from app.notifications.services.event_builders import (  # noqa: E402
    investigation_complete_event,
)

CUSTOMER = "TENANT_A"


def _talon_push(alert_id=42, alert_name="Mimikatz signature", report_url="https://talon.invalid/42"):
    """The event Talon's dispatch POST produces."""
    return event_from_dispatch_request(
        DispatchRequest(
            customer_code=CUSTOMER,
            alert_id=alert_id,
            trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
            severity_assessment=NotificationSeverity.CRITICAL,
            summary="Credential dumping observed.",
            report_url=report_url,
            alert_name=alert_name,
        ),
    )


def _copilot_writeback(alert_id=42, alert_name="Mimikatz signature"):
    """The event CoPilot's own write-back produces."""
    return investigation_complete_event(
        alert_id=alert_id,
        customer_code=CUSTOMER,
        severity="Critical",
        summary="Credential dumping observed.",
        alert_name=alert_name,
    )


# ── convergence: the reason this can't double-notify ──────────────────────


def test_both_paths_produce_the_same_dedupe_key():
    """The whole safety property. If these ever diverged, every investigation
    would notify twice — once from Talon's push and once from write-back."""
    assert _copilot_writeback().dedupe_key == _talon_push().dedupe_key


def test_the_shared_key_is_the_one_the_migration_backfilled():
    """#1019 backfilled 'alert:{id}:{trigger}' for pre-existing rows. A
    different key here would make every historical dispatch look new."""
    assert _copilot_writeback().dedupe_key == "alert:42:investigation_complete"


def test_different_alerts_still_key_apart():
    assert _copilot_writeback(alert_id=1).dedupe_key != _copilot_writeback(alert_id=2).dedupe_key


def test_both_paths_agree_on_trigger_and_entity():
    ours, theirs = _copilot_writeback(), _talon_push()
    assert ours.trigger == theirs.trigger
    assert (ours.entity_type, ours.entity_id) == (theirs.entity_type, theirs.entity_id)
    assert ours.customer_code == theirs.customer_code


# ── the deep link, which write-back had to solve ──────────────────────────


def test_no_link_when_the_base_url_is_unset():
    """Unset COPILOT_URL means no link — the same state as a Talon push that
    omitted one. Deliberately not an error."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("COPILOT_URL", None)
        assert _copilot_writeback().link_url is None


def test_link_is_built_when_the_base_url_is_set():
    """Write-back wins the dedupe over Talon's push, so without this the link
    Talon used to supply would silently disappear."""
    with patch.dict(os.environ, {"COPILOT_URL": "https://copilot.example.com"}):
        assert _copilot_writeback().link_url == "https://copilot.example.com/alerts/42"


def test_a_trailing_slash_does_not_double_up():
    with patch.dict(os.environ, {"COPILOT_URL": "https://copilot.example.com/"}):
        assert _copilot_writeback().link_url == "https://copilot.example.com/alerts/42"


def test_alert_created_gains_a_link_too():
    """It never had one — Talon only ever supplied report_url for
    investigations."""
    with patch.dict(os.environ, {"COPILOT_URL": "https://copilot.example.com"}):
        event = alert_created_event(alert_id=7, customer_code=CUSTOMER, alert_title="New alert")
        assert event.link_url == "https://copilot.example.com/alerts/7"


def test_an_explicit_link_is_not_overridden():
    with patch.dict(os.environ, {"COPILOT_URL": "https://copilot.example.com"}):
        event = alert_created_event(
            alert_id=7,
            customer_code=CUSTOMER,
            alert_title="New alert",
            link_url="https://explicit.invalid/7",
        )
        assert event.link_url == "https://explicit.invalid/7"


# ── ai_report_reviewed ────────────────────────────────────────────────────


def test_review_is_a_distinct_trigger_from_submission():
    """The point of it being a trigger and not a route flag: an operator can
    have both, firing at different moments for different audiences."""
    assert (
        ai_report_reviewed_event(
            alert_id=42,
            report_id=1,
            customer_code=CUSTOMER,
            severity="High",
            summary="s",
        ).dedupe_key
        != _copilot_writeback().dedupe_key
    )


def test_review_is_keyed_on_the_alert_not_the_report():
    """'This alert's findings have been reviewed' happens once. A second
    reviewer must not re-notify the customer."""
    first = ai_report_reviewed_event(alert_id=42, report_id=1, customer_code=CUSTOMER, severity="High", summary="s")
    second = ai_report_reviewed_event(alert_id=42, report_id=2, customer_code=CUSTOMER, severity="High", summary="s")
    assert first.dedupe_key == second.dedupe_key


def test_review_carries_the_reviewer_and_verdict_for_templates():
    event = ai_report_reviewed_event(
        alert_id=42,
        report_id=1,
        customer_code=CUSTOMER,
        severity="High",
        summary="s",
        reviewer="analyst_one",
        verdict="accurate",
    )
    assert event.actor_username == "analyst_one"
    assert event.context["verdict"] == "accurate"
    assert event.context["report_id"] == 1


# ── scope and gating ──────────────────────────────────────────────────────


def test_review_is_ai_sourced_so_the_opt_out_gate_applies():
    """It carries AI-written findings, so a customer who opted out of AI
    reports must not receive it."""
    assert NotificationTrigger.AI_REPORT_REVIEWED.value in AI_SOURCED_TRIGGERS


def test_review_is_customer_facing_not_internal():
    """Sign-off is the moment findings become publishable — the opposite of an
    assignment, which is internal."""
    assert NotificationTrigger.AI_REPORT_REVIEWED.value not in INTERNAL_TRIGGERS


@pytest.mark.parametrize("severity", [None, "Nonsense"])
def test_unknown_severity_falls_back_to_the_deployment_default(severity):
    """A report with no assessed severity must not be filtered out of every
    route gating above Informational.

    Asserted against `default_severity()` rather than a literal: the fallback is
    deployment-configurable (#1040), and hardcoding it here would fail for
    anyone who changed the setting rather than catching a real bug.
    """
    from app.incidents.services.alert_severity import default_severity

    event = investigation_complete_event(alert_id=1, customer_code=CUSTOMER, severity=severity, summary="s")
    assert event.severity.value == default_severity()


def test_a_supplied_severity_is_used_verbatim():
    event = investigation_complete_event(alert_id=1, customer_code=CUSTOMER, severity="Critical", summary="s")
    assert event.severity.value == "Critical"
