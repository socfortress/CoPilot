"""Per-alert customer access on the routes that were missing it (#1099).

Two alert routes mutated by id without ever asking whether the caller was
entitled to that alert's customer:

* `DELETE /alerts` (bulk) took no `current_user` at all, so any holder of the
  `admin|analyst` scope could delete any tenant's alerts by passing their ids.
  Deletion is unrecoverable and alert ids are sequential.
* `PUT /alert/assigned-to` (single) took `current_user` only to stamp the
  notification actor. Reassigning a foreign alert also emitted an
  `ALERT_ASSIGNED` event carrying that alert's title, customer code and
  severity, so it leaked cross-tenant metadata to whatever route was listening.

Analysts are not necessarily deployment-wide: `user_customer_access` narrows one
to specific customers, and every other alert mutation route honours that.

Unit tests against the route handlers with a mocked session; no real DB.

Run with: cd backend && python -m pytest tests/test_alert_access_enforcement.py
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
from app.incidents.schema.db_operations import AssignedToAlert  # noqa: E402
from app.incidents.schema.db_operations import DeleteAlertsRequest  # noqa: E402

ANALYST = SimpleNamespace(id=7, username="analyst", role_id=2)

OWN_ID = 1
FOREIGN_ID = 2
LINKED_ID = 3
MISSING_ID = 4


def _alert(alert_id, assigned_to=None, severity="High"):
    """Carries every field `AlertOut` requires, so the success path can build its
    response model rather than failing validation on a too-thin stub."""
    return SimpleNamespace(
        id=alert_id,
        alert_creation_time="2026-08-26T12:00:00.000Z",
        alert_name=f"Alert {alert_id}",
        alert_description=f"Description {alert_id}",
        status="OPEN",
        customer_code="TENANT_A",
        source="wazuh",
        assigned_to=assigned_to,
        severity=severity,
        comments=[],
        assets=[],
        tags=[],
        linked_cases=[],
        iocs=[],
    )


def _session(rows=None):
    session = AsyncMock()
    queue = list(rows or [])

    async def execute(statement):
        result = MagicMock()
        result.scalars.return_value.first.return_value = queue.pop(0) if queue else None
        return result

    session.execute = execute
    return session


def _patch_access(monkeypatch, forbidden=(FOREIGN_ID,), missing=(MISSING_ID,)):
    async def ensure(alert_id, current_user, db):
        if alert_id in forbidden:
            raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id}")
        if alert_id in missing:
            raise HTTPException(status_code=404, detail="Alert not found")
        return _alert(alert_id)

    monkeypatch.setattr(routes, "_ensure_alert_access", ensure)


# ---------------------------------------------------------------------- bulk delete


def _patch_delete(monkeypatch, deleted, linked=(LINKED_ID,)):
    async def fake_linked_check(alert_id, db):
        if alert_id in linked:
            raise HTTPException(status_code=400, detail="Alert is linked to a case")

    async def fake_delete(alert_id, db):
        deleted.append(alert_id)

    monkeypatch.setattr(routes, "is_alert_linked_to_case", fake_linked_check)
    monkeypatch.setattr(routes, "delete_alert", fake_delete)


def test_bulk_delete_refuses_a_foreign_customers_alert(monkeypatch):
    """The reported hole: ids alone were enough to delete another tenant's alerts."""
    _patch_access(monkeypatch)
    deleted = []
    _patch_delete(monkeypatch, deleted, linked=())

    response = asyncio.run(
        routes.delete_alerts_endpoint(
            DeleteAlertsRequest(alert_ids=[OWN_ID, FOREIGN_ID]),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.deleted_alert_ids == [OWN_ID]
    assert response.not_deleted_alert_ids == [FOREIGN_ID]
    # The important assertion: the foreign alert never reached the delete.
    assert deleted == [OWN_ID]


def test_bulk_delete_still_skips_case_linked_alerts(monkeypatch):
    """Pre-existing behaviour must survive the new check."""
    _patch_access(monkeypatch)
    deleted = []
    _patch_delete(monkeypatch, deleted)

    response = asyncio.run(
        routes.delete_alerts_endpoint(
            DeleteAlertsRequest(alert_ids=[OWN_ID, LINKED_ID]),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.deleted_alert_ids == [OWN_ID]
    assert response.not_deleted_alert_ids == [LINKED_ID]


def test_bulk_delete_treats_denied_and_missing_alike(monkeypatch):
    """Distinguishing them would confirm an id exists in an unreachable tenant."""
    _patch_access(monkeypatch)
    _patch_delete(monkeypatch, [], linked=())

    response = asyncio.run(
        routes.delete_alerts_endpoint(
            DeleteAlertsRequest(alert_ids=[FOREIGN_ID, MISSING_ID]),
            current_user=ANALYST,
            db=_session(),
        ),
    )

    assert response.deleted_alert_ids == []
    assert response.not_deleted_alert_ids == [FOREIGN_ID, MISSING_ID]
    assert response.success is True


def test_bulk_delete_still_raises_on_an_unexpected_error(monkeypatch):
    """Only 400/403/404 mean "skip this one". A 500 must not be swallowed into
    a partial success that looks like the alert was merely skipped."""
    _patch_access(monkeypatch, forbidden=(), missing=())

    async def fake_linked_check(alert_id, db):
        raise HTTPException(status_code=500, detail="database is on fire")

    monkeypatch.setattr(routes, "is_alert_linked_to_case", fake_linked_check)
    monkeypatch.setattr(routes, "delete_alert", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.delete_alerts_endpoint(
                DeleteAlertsRequest(alert_ids=[OWN_ID]),
                current_user=ANALYST,
                db=_session(),
            ),
        )

    assert exc.value.status_code == 500


# -------------------------------------------------------------------- single assign


def _patch_assign(monkeypatch, assigned, events):
    async def fake_users():
        return [SimpleNamespace(username=name) for name in ("analyst", "other")]

    async def fake_assign(alert_id, assigned_to, db):
        assigned.append(alert_id)
        return _alert(alert_id, assigned_to=assigned_to)

    monkeypatch.setattr(routes, "select_all_users", fake_users)
    monkeypatch.setattr(routes, "update_alert_assigned_to", fake_assign)
    monkeypatch.setattr(routes, "emit", lambda event: events.append(event))
    monkeypatch.setattr(routes, "alert_assigned_event", lambda **kwargs: SimpleNamespace(**kwargs))


def test_single_assign_refuses_a_foreign_customers_alert(monkeypatch):
    """403 rather than a silent reassignment, and crucially no notification:
    the event would have carried the foreign alert's title, customer and severity."""
    _patch_access(monkeypatch)
    assigned, events = [], []
    _patch_assign(monkeypatch, assigned, events)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.update_assigned_to_endpoint(
                AssignedToAlert(alert_id=FOREIGN_ID, assigned_to="other"),
                current_user=ANALYST,
                db=_session([_alert(FOREIGN_ID)]),
            ),
        )

    assert exc.value.status_code == 403
    assert assigned == []
    assert events == []


def test_single_assign_still_works_for_an_accessible_alert(monkeypatch):
    """The check must not break the normal path."""
    _patch_access(monkeypatch)
    assigned, events = [], []
    _patch_assign(monkeypatch, assigned, events)

    response = asyncio.run(
        routes.update_assigned_to_endpoint(
            AssignedToAlert(alert_id=OWN_ID, assigned_to="other"),
            current_user=ANALYST,
            db=_session([_alert(OWN_ID, assigned_to=None)]),
        ),
    )

    assert response.success is True
    assert assigned == [OWN_ID]
    assert [event.alert_id for event in events] == [OWN_ID]


def test_single_assign_rejects_an_unknown_user_before_the_access_check(monkeypatch):
    """A bad username is a bad request regardless of the alert, and checking it
    first keeps the existing 400 rather than turning it into a 403."""
    _patch_access(monkeypatch)
    assigned, events = [], []
    _patch_assign(monkeypatch, assigned, events)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.update_assigned_to_endpoint(
                AssignedToAlert(alert_id=FOREIGN_ID, assigned_to="ghost"),
                current_user=ANALYST,
                db=_session(),
            ),
        )

    assert exc.value.status_code == 400
