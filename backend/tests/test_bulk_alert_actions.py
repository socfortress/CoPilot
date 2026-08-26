"""Bulk status and assignee actions on selected alerts (#1098).

The point of these endpoints is that a selection is not a homogeneous thing: it
can span customers, contain an alert someone else just deleted, and contain
alerts already at the target value. The contract is therefore partial success —
do the work that is allowed, report what was skipped — and the tests below pin
each part of that.

Access is checked per alert rather than once per request, which is what keeps a
selection from becoming a way to touch a tenant the caller cannot reach. The
sibling bulk-delete route does not do this (#1099); these must not copy it.

Unit tests against the route handlers with a mocked session; no real DB.

Run with: cd backend && python -m pytest tests/test_bulk_alert_actions.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.routes.db_operations as routes  # noqa: E402
from app.incidents.schema.db_operations import BulkAssignedToAlert  # noqa: E402
from app.incidents.schema.db_operations import BulkUpdateAlertStatus  # noqa: E402

ANALYST = SimpleNamespace(id=7, username="analyst", role_id=2)

# Alert 3 belongs to a customer the caller is not entitled to.
FORBIDDEN_ID = 3
# Alert 4 no longer exists.
MISSING_ID = 4


def _alert(alert_id, assigned_to=None, severity="High"):
    return SimpleNamespace(
        id=alert_id,
        alert_name=f"Alert {alert_id}",
        customer_code="TENANT_A",
        assigned_to=assigned_to,
        severity=severity,
    )


def _session(rows=None):
    """AsyncSession whose `execute` yields the ORM row for the requested alert."""
    session = AsyncMock()
    rows = rows or {}

    async def execute(statement):
        result = MagicMock()
        # The bulk assign handler re-reads the ORM row; hand back whichever alert
        # the test registered, in call order.
        result.scalars.return_value.first.return_value = execute.queue.pop(0) if execute.queue else None
        return result

    execute.queue = list(rows)
    session.execute = execute
    return session


def _patch_access(monkeypatch, forbidden=(FORBIDDEN_ID,), missing=(MISSING_ID,)):
    """Per-alert access check: 403 for a foreign customer, 404 for a deleted alert."""

    async def ensure(alert_id, current_user, db):
        if alert_id in forbidden:
            raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id}")
        if alert_id in missing:
            raise HTTPException(status_code=404, detail="Alert not found")
        return _alert(alert_id)

    monkeypatch.setattr(routes, "_ensure_alert_access", ensure)


# --------------------------------------------------------------------------- status


def test_bulk_status_updates_every_accessible_alert(monkeypatch):
    _patch_access(monkeypatch, forbidden=(), missing=())
    updated = []

    async def fake_update(payload, db):
        updated.append((payload.alert_id, payload.status))

    monkeypatch.setattr(routes, "update_alert_status", fake_update)

    response = asyncio.run(
        routes.bulk_update_alert_status_endpoint(
            BulkUpdateAlertStatus(alert_ids=[1, 2], status="CLOSED"),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.updated_alert_ids == [1, 2]
    assert response.not_updated_alert_ids == []
    assert updated == [(1, "CLOSED"), (2, "CLOSED")]


def test_bulk_status_skips_alerts_the_caller_cannot_reach(monkeypatch):
    """A selection spanning customers does the work it is allowed to do.

    The inaccessible alert is reported as skipped rather than 403ing the request,
    so one foreign alert cannot discard the rest of the analyst's selection.
    """
    _patch_access(monkeypatch)
    updated = []

    async def fake_update(payload, db):
        updated.append(payload.alert_id)

    monkeypatch.setattr(routes, "update_alert_status", fake_update)

    response = asyncio.run(
        routes.bulk_update_alert_status_endpoint(
            BulkUpdateAlertStatus(alert_ids=[1, FORBIDDEN_ID, 2, MISSING_ID], status="IN_PROGRESS"),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.updated_alert_ids == [1, 2]
    assert response.not_updated_alert_ids == [FORBIDDEN_ID, MISSING_ID]
    # The forbidden alert was never handed to the mutation.
    assert FORBIDDEN_ID not in updated


def test_bulk_status_does_not_distinguish_forbidden_from_missing(monkeypatch):
    """Both land in the same bucket: telling them apart would confirm that an id
    exists inside a tenant the caller cannot see."""
    _patch_access(monkeypatch)

    async def fake_update(payload, db):
        return None

    monkeypatch.setattr(routes, "update_alert_status", fake_update)

    response = asyncio.run(
        routes.bulk_update_alert_status_endpoint(
            BulkUpdateAlertStatus(alert_ids=[FORBIDDEN_ID, MISSING_ID], status="OPEN"),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.updated_alert_ids == []
    assert response.not_updated_alert_ids == [FORBIDDEN_ID, MISSING_ID]
    assert response.success is True


# ------------------------------------------------------------------------- assignee


def _patch_users(monkeypatch, names=("analyst", "other")):
    async def fake_users():
        return [SimpleNamespace(username=name) for name in names]

    monkeypatch.setattr(routes, "select_all_users", fake_users)


def test_bulk_assign_rejects_an_unknown_user_before_touching_anything(monkeypatch):
    """Fails fast rather than per-alert: assigning half a selection and then
    discovering the username is wrong is worse than doing nothing."""
    _patch_users(monkeypatch)
    _patch_access(monkeypatch, forbidden=(), missing=())
    assigned = []

    async def fake_assign(alert_id, assigned_to, db):
        assigned.append(alert_id)

    monkeypatch.setattr(routes, "update_alert_assigned_to", fake_assign)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.bulk_update_assigned_to_endpoint(
                BulkAssignedToAlert(alert_ids=[1, 2], assigned_to="ghost"),
                current_user=ANALYST,
                db=_session(),
            ),
        )

    assert exc.value.status_code == 400
    assert assigned == []


def test_bulk_assign_notifies_once_per_alert_that_changed_hands(monkeypatch):
    """Alert 2 is already assigned to the target user, so it must stay silent —
    the same rule the single-alert route follows."""
    _patch_users(monkeypatch)
    _patch_access(monkeypatch, forbidden=(), missing=())

    rows = [_alert(1, assigned_to=None), _alert(2, assigned_to="other")]
    events = []

    async def fake_assign(alert_id, assigned_to, db):
        return None

    monkeypatch.setattr(routes, "update_alert_assigned_to", fake_assign)
    monkeypatch.setattr(routes, "emit", lambda event: events.append(event))
    monkeypatch.setattr(
        routes,
        "alert_assigned_event",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    response = asyncio.run(
        routes.bulk_update_assigned_to_endpoint(
            BulkAssignedToAlert(alert_ids=[1, 2], assigned_to="other"),
            current_user=ANALYST,
            db=_session(rows),
        ),
    )

    assert response.updated_alert_ids == [1, 2]
    assert [event.alert_id for event in events] == [1]


def test_bulk_assign_notification_carries_the_alerts_own_severity(monkeypatch):
    """`AlertOut` has no `severity`, so reusing what the access check returned
    would silently notify at the deployment default and a route gating at High
    would miss a Critical handover."""
    _patch_users(monkeypatch)
    _patch_access(monkeypatch, forbidden=(), missing=())

    events = []

    async def fake_assign(alert_id, assigned_to, db):
        return None

    monkeypatch.setattr(routes, "update_alert_assigned_to", fake_assign)
    monkeypatch.setattr(routes, "emit", lambda event: events.append(event))
    monkeypatch.setattr(routes, "alert_assigned_event", lambda **kwargs: SimpleNamespace(**kwargs))

    asyncio.run(
        routes.bulk_update_assigned_to_endpoint(
            BulkAssignedToAlert(alert_ids=[1], assigned_to="other"),
            current_user=ANALYST,
            db=_session([_alert(1, assigned_to=None, severity="Critical")]),
        ),
    )

    assert len(events) == 1
    assert events[0].severity == "Critical"
    assert events[0].customer_code == "TENANT_A"
    assert events[0].actor == "analyst"


def test_bulk_assign_skips_alerts_the_caller_cannot_reach(monkeypatch):
    """Stricter than the single-alert assign route, which checks nothing (#1099)."""
    _patch_users(monkeypatch)
    _patch_access(monkeypatch)

    assigned = []

    async def fake_assign(alert_id, assigned_to, db):
        assigned.append(alert_id)

    monkeypatch.setattr(routes, "update_alert_assigned_to", fake_assign)
    monkeypatch.setattr(routes, "emit", lambda event: None)
    monkeypatch.setattr(routes, "alert_assigned_event", lambda **kwargs: SimpleNamespace(**kwargs))

    response = asyncio.run(
        routes.bulk_update_assigned_to_endpoint(
            BulkAssignedToAlert(alert_ids=[1, FORBIDDEN_ID], assigned_to="other"),
            current_user=ANALYST,
            db=_session([_alert(1, assigned_to=None)]),
        ),
    )

    assert response.updated_alert_ids == [1]
    assert response.not_updated_alert_ids == [FORBIDDEN_ID]
    assert assigned == [1]
