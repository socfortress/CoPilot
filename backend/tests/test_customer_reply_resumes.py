"""A customer's reply hands a waiting item back to the SOC (#1187).

No database: the status reads and writes are patched, so what is pinned is the rule —
only a ``customer_user`` comment on a ``PENDING_CUSTOMER`` item moves it to
``IN_PROGRESS``; a case brings back only the alerts that were waiting with it.

Run with: cd backend && python -m pytest tests/test_customer_reply_resumes.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.incidents.services import customer_reply  # noqa: E402

PORTAL = SimpleNamespace(username="portal", role_id=4)
ANALYST = SimpleNamespace(username="ana", role_id=2)


def _db(*results):
    """A session whose successive ``execute`` calls answer ``results`` in order."""
    db = AsyncMock()
    answers = []
    for result in results:
        answer = MagicMock()
        answer.scalar_one_or_none.return_value = result
        answer.all.return_value = result
        answers.append(answer)
    db.execute = AsyncMock(side_effect=answers)
    return db


def _run(coro_factory):
    recorder = MagicMock()
    recorder.alert_action = AsyncMock()
    recorder.alerts_action = AsyncMock()
    recorder.case_action = AsyncMock()
    alert_updates, case_updates = AsyncMock(), AsyncMock()
    with patch.object(customer_reply, "SlaLifecycleRecorder", return_value=recorder), patch.object(
        customer_reply,
        "update_alert_status",
        alert_updates,
    ), patch.object(customer_reply, "update_case_status", case_updates), patch(
        "app.incidents.services.case_events.emit_case_event",
        AsyncMock(),
    ):
        moved = asyncio.run(coro_factory())
    return moved, recorder, alert_updates, case_updates


def test_a_customer_reply_resumes_a_waiting_alert():
    moved, recorder, alert_updates, _ = _run(lambda: customer_reply.resume_alert_on_reply(7, PORTAL, _db("PENDING_CUSTOMER")))
    assert moved
    assert alert_updates.await_args.args[0].status.value == "IN_PROGRESS"
    assert recorder.alert_action.await_args.kwargs == {"to_status": "IN_PROGRESS"}


def test_an_analyst_note_or_an_item_not_waiting_does_not_resume():
    for user, status in ((ANALYST, "PENDING_CUSTOMER"), (PORTAL, "OPEN"), (PORTAL, None)):
        moved, recorder, alert_updates, _ = _run(lambda: customer_reply.resume_alert_on_reply(7, user, _db(status)))
        assert not moved and not alert_updates.await_count and not recorder.alert_action.await_count


def test_a_customer_reply_resumes_a_case_and_only_the_alerts_waiting_with_it():
    linked = [(11, "PENDING_CUSTOMER"), (12, "CLOSED"), (13, "PENDING_CUSTOMER")]
    moved, recorder, alert_updates, case_updates = _run(
        lambda: customer_reply.resume_case_on_reply(3, PORTAL, _db("PENDING_CUSTOMER", linked)),
    )
    assert moved
    assert [call.args[0].alert_id for call in alert_updates.await_args_list] == [11, 13]
    assert case_updates.await_args.args[0].status.value == "IN_PROGRESS"
    assert recorder.alerts_action.await_args.args[0] == [11, 13]
