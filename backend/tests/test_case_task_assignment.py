"""Assignment semantics for case tasks.

``CaseTask.assigned_to`` piggybacks on the existing PATCH partial-update rather
than getting its own endpoint, which makes the omitted-vs-explicit-null
distinction load-bearing: omitting the key must preserve the current assignee,
while passing null must unassign. Pydantic collapses both to ``None`` on the
model, so the service reads ``__fields_set__`` — these tests pin that.

Also covers the username validation (the column is a plain string with no FK,
so an unchecked value would create an assignment to a non-existent user) and
the audit event emitted on change.

Unit tests with a mocked session — no real DB.

Run with: cd backend && python -m pytest tests/test_case_task_assignment.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.services.case_tasks as svc  # noqa: E402
from app.incidents.schema.case_templates import CaseEventType  # noqa: E402
from app.incidents.schema.case_templates import CaseTaskUpdate  # noqa: E402

ACTOR = "analyst_one"
KNOWN_USERS = ["analyst_one", "analyst_two"]


def _task(assigned_to=None, status="TODO", mandatory=False):
    return SimpleNamespace(
        id=7,
        case_id=3,
        alert_id=None,
        template_task_id=None,
        title="Contain the host",
        description=None,
        guidelines=None,
        mandatory=mandatory,
        order_index=0,
        status=status,
        evidence_comment=None,
        assigned_to=assigned_to,
        completed_by=None,
        completed_at=None,
        created_by="system",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 1, 12, 0, 0),
    )


def _run(task, request):
    """Invoke update_case_task against a mocked session, returning (response, task, events)."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = task
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.refresh = AsyncMock()

    users = [SimpleNamespace(username=u) for u in KNOWN_USERS]
    events = []

    async def _capture_event(**kwargs):
        events.append(kwargs)

    with (
        patch.object(svc, "select_all_users", AsyncMock(return_value=users)),
        patch("app.incidents.services.case_events.emit_case_event", AsyncMock(side_effect=_capture_event)),
    ):
        response = asyncio.run(svc.update_case_task(task.id, request, ACTOR, session))
    return response, task, events


def _event_types(events):
    return [e["event_type"] for e in events]


# ── omitted vs explicit null ──────────────────────────────────────────────


def test_omitting_assigned_to_preserves_current_assignee():
    """A status-only PATCH must not wipe the assignee.

    This is the regression the __fields_set__ check exists to prevent — reading
    truthiness instead would unassign on every status change.
    """
    task = _task(assigned_to="analyst_two")
    response, task, events = _run(task, CaseTaskUpdate(status="DONE"))

    assert response.success is True
    assert task.assigned_to == "analyst_two"
    assert CaseEventType.TASK_ASSIGNED not in _event_types(events)


def test_explicit_null_unassigns():
    task = _task(assigned_to="analyst_two")
    response, task, events = _run(task, CaseTaskUpdate(assigned_to=None))

    assert response.success is True
    assert task.assigned_to is None
    assert CaseEventType.TASK_ASSIGNED in _event_types(events)


def test_assigning_sets_the_username():
    task = _task(assigned_to=None)
    response, task, _events = _run(task, CaseTaskUpdate(assigned_to="analyst_two"))

    assert response.success is True
    assert task.assigned_to == "analyst_two"


def test_whitespace_is_stripped():
    task = _task(assigned_to=None)
    _response, task, _events = _run(task, CaseTaskUpdate(assigned_to="  analyst_two  "))

    assert task.assigned_to == "analyst_two"


# ── validation ────────────────────────────────────────────────────────────


def test_unknown_username_is_rejected():
    """No FK backs this column, so an unchecked value would silently stick."""
    task = _task(assigned_to=None)
    response, task, events = _run(task, CaseTaskUpdate(assigned_to="ghost_user"))

    assert response.success is False
    assert "does not exist" in response.message
    assert task.assigned_to is None, "rejected assignment must not mutate the row"
    assert events == [], "rejected assignment must not emit an audit event"


def test_unassign_skips_user_validation():
    """Clearing an assignee must not require the username to resolve."""
    task = _task(assigned_to="departed_user")
    response, task, _events = _run(task, CaseTaskUpdate(assigned_to=None))

    assert response.success is True
    assert task.assigned_to is None


# ── audit ─────────────────────────────────────────────────────────────────


def test_no_event_when_assignee_is_unchanged():
    """Re-assigning to the same person is a no-op, not a timeline entry.

    #1006 keys notification dedupe off assignment changes, so a spurious event
    here would become a spurious notification later.
    """
    task = _task(assigned_to="analyst_two")
    _response, _updated, events = _run(task, CaseTaskUpdate(assigned_to="analyst_two"))

    assert CaseEventType.TASK_ASSIGNED not in _event_types(events)


def test_event_carries_both_sides_of_the_change():
    task = _task(assigned_to="analyst_one")
    _response, _updated, events = _run(task, CaseTaskUpdate(assigned_to="analyst_two"))

    assigned = [e for e in events if e["event_type"] == CaseEventType.TASK_ASSIGNED]
    assert len(assigned) == 1
    payload = assigned[0]["payload"]
    assert payload["from_assignee"] == "analyst_one"
    assert payload["to_assignee"] == "analyst_two"
    assert payload["task_id"] == 7
    assert assigned[0]["actor"] == ACTOR


@pytest.mark.parametrize(
    ("field", "value", "expected_event"),
    [
        ("status", "DONE", CaseEventType.TASK_STATUS_CHANGED),
        ("evidence_comment", "ran isolation playbook", CaseEventType.TASK_COMMENTED),
    ],
)
def test_existing_update_paths_still_emit(field, value, expected_event):
    """Assignment must not have disturbed the status/comment audit hooks."""
    task = _task(assigned_to=None)
    _response, _updated, events = _run(task, CaseTaskUpdate(**{field: value}))

    assert expected_event in _event_types(events)


def test_assignment_and_status_in_one_call_emit_both():
    task = _task(assigned_to=None)
    _response, task, events = _run(task, CaseTaskUpdate(status="DONE", assigned_to="analyst_two"))

    types = _event_types(events)
    assert CaseEventType.TASK_ASSIGNED in types
    assert CaseEventType.TASK_STATUS_CHANGED in types
    assert task.assigned_to == "analyst_two"
    assert task.completed_by == ACTOR
