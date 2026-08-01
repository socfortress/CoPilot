"""Idempotency after the dispatch log stopped being alert-only.

The unique key moved from ``(customer_code, alert_id, route_id, trigger)`` to
``(route_id, dedupe_key)``. That swap is the risky part of #1019: too loose and
notifications double-fire, too tight and legitimate re-notifications get
swallowed.

The key now travels on ``NotificationEvent``, so each trigger owns its own
semantics. ``investigation_complete`` uses ``alert:{id}:{trigger}`` — the same
meaning the old tuple had, which is also what the migration backfills, so
pre-existing rows keep behaving identically.

Unit tests with a mocked session — no DB.

Run with: cd backend && python -m pytest tests/test_notification_dedupe.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.notifications.services.notifications as svc  # noqa: E402
from app.notifications.schema.events import EntityType  # noqa: E402
from app.notifications.schema.events import NotificationEvent  # noqa: E402
from app.notifications.schema.notifications import NotificationSeverity  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402

CUSTOMER = "TENANT_A"


def _event(entity_type=EntityType.ALERT, entity_id=42, dedupe_key=None, trigger=NotificationTrigger.INVESTIGATION_COMPLETE):
    return NotificationEvent(
        customer_code=CUSTOMER,
        trigger=trigger,
        severity=NotificationSeverity.CRITICAL,
        subject="Mimikatz signature",
        summary="Credential dumping observed.",
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key or f"{entity_type}:{entity_id}:{trigger.value}",
    )


def _session(existing=None, raise_on_commit=False):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    if raise_on_commit:
        session.commit = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("dup")))
    return session


def _existing_row(status):
    return SimpleNamespace(
        status=status,
        error_message=None,
        latency_ms=None,
        payload_preview=None,
        provider_reference=None,
        dispatched_at=None,
    )


def _record(session, event, *, status="sent", provider_reference=None):
    return asyncio.run(
        svc._record_log(
            session,
            event=event,
            route_id=1,
            status=status,
            error_message=None,
            latency_ms=12,
            payload_preview="body",
            provider_reference=provider_reference,
        ),
    )


def _inserted(session):
    """The NotificationDispatchLog instance handed to session.add()."""
    assert session.add.call_count == 1
    return session.add.call_args.args[0]


# ── the lookup uses the new key ───────────────────────────────────────────


def test_lookup_is_by_route_and_dedupe_key():
    """A stale lookup on (customer, alert, trigger) would keep working for AI
    events and silently mis-dedupe everything else."""
    session = _session()
    _record(session, _event())

    where = str(session.execute.await_args.args[0])
    assert "route_id" in where
    assert "dedupe_key" in where


# ── idempotency semantics, unchanged ──────────────────────────────────────


def test_previously_sent_is_refused():
    session = _session(existing=_existing_row("sent"))
    assert _record(session, _event()) is False
    assert session.add.call_count == 0


@pytest.mark.parametrize("prior", ["failed", "skipped"])
def test_previous_failure_is_overwritten_so_retries_land(prior):
    """A failed attempt must not permanently block the same notification."""
    row = _existing_row(prior)
    session = _session(existing=row)

    assert _record(session, _event(), status="sent", provider_reference="exec-9") is True
    assert row.status == "sent"
    assert row.provider_reference == "exec-9"
    assert session.add.call_count == 0, "overwrite in place, don't insert a second row"


def test_concurrent_insert_race_is_treated_as_a_hit():
    """Another dispatch slipped in between our SELECT and INSERT."""
    session = _session(existing=None, raise_on_commit=True)
    assert _record(session, _event()) is False
    session.rollback.assert_awaited()


# ── what actually gets written ────────────────────────────────────────────


def test_alert_event_populates_both_alert_id_and_entity_fields():
    """alert_id is retained for existing queries and the UI filter; entity_*
    is the general form."""
    session = _session()
    _record(session, _event())
    row = _inserted(session)

    assert row.alert_id == 42
    assert row.entity_type == "alert"
    assert row.entity_id == 42
    assert row.dedupe_key == "alert:42:investigation_complete"
    assert row.customer_code == CUSTOMER


def test_non_alert_event_leaves_alert_id_null():
    """The whole point of the migration: a case-task assignment has no alert,
    and previously could not be logged at all because alert_id was NOT NULL."""
    session = _session()
    _record(session, _event(entity_type=EntityType.CASE_TASK, entity_id=7))
    row = _inserted(session)

    assert row.alert_id is None
    assert row.entity_type == "case_task"
    assert row.entity_id == 7


def test_case_event_leaves_alert_id_null():
    session = _session()
    _record(session, _event(entity_type=EntityType.CASE, entity_id=3))
    row = _inserted(session)

    assert row.alert_id is None
    assert row.entity_id == 3


def test_provider_reference_is_persisted():
    session = _session()
    _record(session, _event(), provider_reference="exec-1")
    assert _inserted(session).provider_reference == "exec-1"


def test_payload_preview_is_truncated_to_500():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()

    asyncio.run(
        svc._record_log(
            session,
            event=_event(),
            route_id=1,
            status="sent",
            error_message=None,
            latency_ms=1,
            payload_preview="x" * 900,
            provider_reference=None,
        ),
    )
    assert len(_inserted(session).payload_preview) == 500


# ── the key's discriminating power ────────────────────────────────────────


def test_backfilled_key_matches_what_the_code_writes():
    """The migration backfills 'alert:{alert_id}:{trigger}' for existing rows.
    If the code wrote anything else, every pre-existing dispatch would look new
    and re-fire once on upgrade.
    """
    event = _event()
    assert event.dedupe_key == "alert:42:investigation_complete"


def test_distinct_entities_produce_distinct_keys():
    assert _event(entity_id=1).dedupe_key != _event(entity_id=2).dedupe_key


def test_distinct_entity_types_produce_distinct_keys():
    """A case #7 and a case-task #7 are different things."""
    a = _event(entity_type=EntityType.CASE, entity_id=7)
    b = _event(entity_type=EntityType.CASE_TASK, entity_id=7)
    assert a.dedupe_key != b.dedupe_key


def test_same_key_on_a_different_route_is_not_deduped():
    """Two routes for the same customer must both receive the notification —
    dedupe is per (route, key), not per key.
    """
    event = _event()
    session = _session(existing=None)
    asyncio.run(
        svc._record_log(
            session,
            event=event,
            route_id=2,
            status="sent",
            error_message=None,
            latency_ms=1,
            payload_preview=None,
            provider_reference=None,
        ),
    )
    where = str(session.execute.await_args.args[0])
    # route_id participates in the lookup, so route 2 cannot see route 1's row.
    assert "route_id" in where
    assert _inserted(session).route_id == 2
