"""SOC Management (#1187) — every human action on an alert or case reaches the SLA recorder.

The SLA clocks are only as good as the actions recorded into them, and the recording is
explicit: each incidents route calls the recorder after its mutation succeeded. These
tests call the route functions directly (services mocked, as in
``test_comment_authorship.py``) and assert the exact action, actor and payload recorded.

They also pin the other half of the rule: the *services* automation shares (comment
creation) never record a response, while the *creation* services always open a clock.

Run with: cd backend && python -m pytest tests/test_soc_management_incident_hooks.py
"""

import asyncio
import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.routes.db_operations as dbo  # noqa: E402
import app.incidents.services.case_events as case_events  # noqa: E402
import app.incidents.services.db_operations as dbo_services  # noqa: E402
import app.incidents.services.incident_alert as incident_alert  # noqa: E402
from app.incidents.schema.db_operations import AlertStatus  # noqa: E402
from app.incidents.schema.db_operations import AssignedToAlert  # noqa: E402
from app.incidents.schema.db_operations import AssignedToCase  # noqa: E402
from app.incidents.schema.db_operations import BulkAssignedToAlert  # noqa: E402
from app.incidents.schema.db_operations import BulkUpdateAlertStatus  # noqa: E402
from app.incidents.schema.db_operations import CaseAlertLinkCreate  # noqa: E402
from app.incidents.schema.db_operations import CaseAlertUnLink  # noqa: E402
from app.incidents.schema.db_operations import CaseCommentCreate  # noqa: E402
from app.incidents.schema.db_operations import CaseCreateFromAlert  # noqa: E402
from app.incidents.schema.db_operations import CommentCreate  # noqa: E402
from app.incidents.schema.db_operations import EscalateAlert  # noqa: E402
from app.incidents.schema.db_operations import EscalateCase  # noqa: E402
from app.incidents.schema.db_operations import UpdateAlertStatus  # noqa: E402
from app.incidents.schema.db_operations import UpdateAlertVerdict  # noqa: E402
from app.incidents.schema.db_operations import UpdateCaseSeverity  # noqa: E402
from app.incidents.schema.db_operations import UpdateCaseStatus  # noqa: E402
from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402

ANALYST = SimpleNamespace(id=2, username="ana", role_id=2)
PORTAL = SimpleNamespace(id=10, username="portal", role_id=4)
ANA = Actor(username="ana", is_soc=True)


class FakeRecorder:
    """Stands in for SlaLifecycleRecorder; every instance writes to one shared log."""

    calls: list = []

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        async def record(*args, **kwargs):
            FakeRecorder.calls.append((name, args, kwargs))

        return record


def recorded():
    return list(FakeRecorder.calls)


def _patches(**services):
    """The route module with the recorder replaced, access checks passing and ``services`` mocked."""
    stack = ExitStack()
    FakeRecorder.calls = []
    stack.enter_context(patch.object(dbo, "SlaLifecycleRecorder", FakeRecorder))
    for name in ("_ensure_alert_access", "_ensure_case_access", "_ensure_customer_access"):
        stack.enter_context(patch.object(dbo, name, AsyncMock()))
    stack.enter_context(patch.object(dbo.customer_access_handler, "check_customer_access", AsyncMock(return_value=True)))
    stack.enter_context(patch.object(dbo, "emit", MagicMock()))
    stack.enter_context(patch.object(dbo, "record_audit_event", AsyncMock()))
    stack.enter_context(patch.object(case_events, "emit_case_event", AsyncMock()))
    stack.enter_context(patch.object(dbo, "select_all_users", AsyncMock(return_value=[SimpleNamespace(username="ana")])))
    for name, value in services.items():
        stack.enter_context(patch.object(dbo, name, value))
    return stack


def _session_with_alert(alert):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = alert
    result.__iter__ = lambda self: iter([])
    session.execute = AsyncMock(return_value=result)
    return session


ALERT = SimpleNamespace(id=7, assigned_to=None, alert_name="Brute force", customer_code="ACME", severity="High")


# ── alerts ───────────────────────────────────────────────────────────────────


def test_status_change_is_recorded_with_the_new_status():
    with _patches(update_alert_status=AsyncMock(return_value=ALERT), AlertResponse=lambda **kw: kw):
        asyncio.run(dbo.update_alert_status_endpoint(UpdateAlertStatus(alert_id=7, status="CLOSED"), ANALYST, AsyncMock()))
    assert recorded() == [("alert_action", (7, LifecycleAction.STATUS_CHANGED, ANA), {"to_status": "CLOSED"})]


def test_a_portal_status_change_is_recorded_with_a_non_soc_actor():
    with _patches(update_alert_status=AsyncMock(return_value=ALERT), AlertResponse=lambda **kw: kw):
        asyncio.run(dbo.update_alert_status_endpoint(UpdateAlertStatus(alert_id=7, status="CLOSED"), PORTAL, AsyncMock()))
    ((_, args, _),) = recorded()
    assert args[2] == Actor(username="portal", is_soc=False)


def test_bulk_status_records_only_the_alerts_that_changed():
    async def access(alert_id, user, db):
        if alert_id == 2:
            raise dbo.HTTPException(status_code=403, detail="no")

    with _patches(update_alert_status=AsyncMock(), _ensure_alert_access=access):
        asyncio.run(
            dbo.bulk_update_alert_status_endpoint(
                BulkUpdateAlertStatus(alert_ids=[1, 2, 3], status=AlertStatus.IN_PROGRESS),
                ANALYST,
                AsyncMock(),
            ),
        )
    assert recorded() == [("alerts_action", ([1, 3], LifecycleAction.STATUS_CHANGED, ANA), {"to_status": "IN_PROGRESS"})]


def test_verdict_is_recorded():
    with _patches(update_alert_verdict=AsyncMock(return_value=(ALERT, {})), AlertResponse=lambda **kw: kw):
        asyncio.run(
            dbo.update_alert_verdict_endpoint(UpdateAlertVerdict(alert_id=7, verdict="TRUE_POSITIVE"), MagicMock(), ANALYST, AsyncMock()),
        )
    assert recorded() == [("alert_action", (7, LifecycleAction.VERDICT_SET, ANA), {})]


def test_escalation_is_recorded():
    with _patches(
        get_alert_by_id=AsyncMock(return_value=ALERT),
        update_alert_escalated=AsyncMock(return_value=ALERT),
        AlertResponse=lambda **kw: kw,
    ):
        asyncio.run(dbo.update_alert_escalated_endpoint(EscalateAlert(alert_id=7, escalated=True), ANALYST, AsyncMock()))
    assert recorded() == [("alert_action", (7, LifecycleAction.ESCALATED, ANA), {})]


def test_a_comment_through_the_api_is_recorded():
    with _patches(
        get_alert_by_id=AsyncMock(return_value=ALERT),
        create_comment=AsyncMock(return_value=SimpleNamespace(id=1)),
        CommentResponse=lambda **kw: kw,
    ):
        asyncio.run(dbo.create_comment_endpoint(CommentCreate(alert_id=7, comment="looking", user_name="x"), ANALYST, AsyncMock()))
    assert recorded() == [("alert_action", (7, LifecycleAction.COMMENTED, ANA), {})]


def test_assignment_is_recorded_with_the_assignee():
    with _patches(update_alert_assigned_to=AsyncMock(return_value=ALERT), AlertResponse=lambda **kw: kw):
        asyncio.run(dbo.update_assigned_to_endpoint(AssignedToAlert(alert_id=7, assigned_to="ana"), ANALYST, _session_with_alert(ALERT)))
    assert recorded() == [("alert_action", (7, LifecycleAction.ASSIGNED, ANA), {"assignee": "ana"})]


def test_bulk_assignment_is_recorded_for_the_assigned_alerts():
    with _patches(update_alert_assigned_to=AsyncMock()):
        asyncio.run(
            dbo.bulk_update_assigned_to_endpoint(
                BulkAssignedToAlert(alert_ids=[4, 5], assigned_to="ana"),
                ANALYST,
                _session_with_alert(ALERT),
            ),
        )
    assert recorded() == [("alerts_action", ([4, 5], LifecycleAction.ASSIGNED, ANA), {"assignee": "ana"})]


def test_a_hand_filed_alert_is_recorded_as_created_by_its_author():
    body = MagicMock(customer_code="ACME")
    with _patches(create_alert=AsyncMock(return_value=SimpleNamespace(id=42))):
        asyncio.run(dbo.create_alert_endpoint(body, ANALYST, AsyncMock()))
    assert recorded() == [("alert_action", (42, LifecycleAction.CREATED, ANA), {})]


# ── cases ────────────────────────────────────────────────────────────────────


def test_linking_records_the_alert_and_retargets_the_case():
    with _patches(create_case_alert_link=AsyncMock(return_value=MagicMock()), CaseAlertLinkResponse=lambda **kw: kw):
        asyncio.run(dbo.create_case_alert_link_endpoint(CaseAlertLinkCreate(case_id=3, alert_id=7), ANALYST, AsyncMock()))
    assert recorded() == [
        ("alert_action", (7, LifecycleAction.LINKED_TO_CASE, ANA), {}),
        ("case_links_changed", (3,), {}),
    ]


def test_unlinking_retargets_the_case():
    with _patches(case_alert_unlink=AsyncMock(return_value=SimpleNamespace(tasks_orphaned=0))):
        asyncio.run(dbo.case_alert_unlink_endpoint(CaseAlertUnLink(case_id=3, alert_id=7), ANALYST, AsyncMock()))
    assert recorded() == [("case_links_changed", (3,), {})]


def test_a_case_from_an_alert_takes_its_severity_before_the_creation_is_recorded():
    with _patches(
        create_case_from_alert=AsyncMock(return_value=SimpleNamespace(id=3)),
        create_case_alert_link=AsyncMock(return_value=MagicMock()),
        CaseAlertLinkResponse=lambda **kw: kw,
    ):
        asyncio.run(dbo.create_case_from_alert_endpoint(CaseCreateFromAlert(alert_id=7), None, ANALYST, AsyncMock()))
    assert recorded() == [
        ("case_links_changed", (3,), {}),
        ("case_action", (3, LifecycleAction.CREATED, ANA), {}),
        ("alert_action", (7, LifecycleAction.LINKED_TO_CASE, ANA), {}),
    ]


def _case_status_change(old_status, new_status, linked):
    session = AsyncMock()
    links = MagicMock()
    links.all = lambda: linked
    session.execute = AsyncMock(return_value=links)
    case = SimpleNamespace(customer_code="ACME", case_status=old_status)
    moved = AsyncMock()
    with _patches(
        get_case_by_id=AsyncMock(return_value=case),
        update_alert_status=moved,
        update_case_status=AsyncMock(),
        CaseOutResponse=lambda **kw: kw,
    ), patch("app.incidents.services.case_tasks.get_incomplete_mandatory_tasks", AsyncMock(return_value=[])):
        asyncio.run(dbo.update_case_status_endpoint(UpdateCaseStatus(case_id=3, status=new_status), False, ANALYST, session))
    return [call.args[0].alert_id for call in moved.await_args_list]


def test_closing_a_case_records_it_and_every_alert_the_cascade_closed():
    moved = _case_status_change("IN_PROGRESS", "CLOSED", [(11, "OPEN"), (12, "PENDING_CUSTOMER")])
    assert moved == [11, 12]
    assert recorded() == [
        ("case_action", (3, LifecycleAction.STATUS_CHANGED, ANA), {"to_status": "CLOSED"}),
        ("alerts_action", ([11, 12], LifecycleAction.STATUS_CHANGED, ANA), {"to_status": "CLOSED"}),
    ]


def test_a_case_waiting_on_the_customer_takes_only_its_active_alerts_with_it():
    moved = _case_status_change("IN_PROGRESS", "PENDING_CUSTOMER", [(11, "OPEN"), (12, "CLOSED"), (13, "IN_PROGRESS")])
    assert moved == [11, 13]
    assert recorded()[-1] == ("alerts_action", ([11, 13], LifecycleAction.STATUS_CHANGED, ANA), {"to_status": "PENDING_CUSTOMER"})


def test_case_assignment_escalation_and_comment_are_recorded():
    case = SimpleNamespace(customer_code="ACME", assigned_to=None, case_name="Case")
    with _patches(
        get_case_by_id=AsyncMock(return_value=case),
        update_case_assigned_to=AsyncMock(),
        update_case_escalated=AsyncMock(),
        create_case_comment=AsyncMock(return_value=SimpleNamespace(id=1, comment="c")),
        CaseOutResponse=lambda **kw: kw,
        CaseCommentResponse=lambda **kw: kw,
    ):
        asyncio.run(dbo.update_case_assigned_to_endpoint(AssignedToCase(case_id=3, assigned_to="ana"), ANALYST, AsyncMock()))
        asyncio.run(dbo.update_case_escalated_endpoint(EscalateCase(case_id=3, escalated=True), ANALYST, AsyncMock()))
        asyncio.run(dbo.create_case_comment_endpoint(CaseCommentCreate(case_id=3, comment="c", user_name="x"), ANALYST, AsyncMock()))
    assert recorded() == [
        ("case_action", (3, LifecycleAction.ASSIGNED, ANA), {"assignee": "ana"}),
        ("case_action", (3, LifecycleAction.ESCALATED, ANA), {}),
        ("case_action", (3, LifecycleAction.COMMENTED, ANA), {}),
    ]


def test_case_severity_change_retargets_through_the_recorder():
    with _patches(
        update_case_severity=AsyncMock(return_value=(SimpleNamespace(), None)),
        get_case_by_id=AsyncMock(return_value=MagicMock()),
        CaseOutResponse=lambda **kw: kw,
    ):
        asyncio.run(dbo.update_case_severity_endpoint(UpdateCaseSeverity(case_id=3, severity="Critical"), ANALYST, AsyncMock()))
    assert recorded() == [("case_severity_changed", (3, ANA), {})]


# ── services: creation opens clocks, comments never respond ─────────────────


def test_creation_services_open_a_clock_and_the_comment_service_does_not_record():
    with patch.object(dbo_services, "SlaLifecycleRecorder", FakeRecorder), patch.object(
        incident_alert,
        "SlaLifecycleRecorder",
        FakeRecorder,
    ):
        FakeRecorder.calls = []
        session = AsyncMock()
        session.add = MagicMock()
        alert = asyncio.run(
            incident_alert.create_alert_in_copilot(
                SimpleNamespace(alert_title_payload="t", source="wazuh", severity=None),
                "ACME",
                session,
            ),
        )
        assert recorded() == [("alert_opened", (alert,), {})]

        FakeRecorder.calls = []
        comment_session = _session_with_alert(ALERT)
        comment_session.add = MagicMock()
        asyncio.run(
            dbo_services.create_comment(CommentCreate(alert_id=7, comment="Full Event Payload", user_name="admin"), comment_session),
        )
        assert recorded() == []


# ── waiting on the customer ──────────────────────────────────────────────────


def _resumers():
    """resume_*_on_reply replaced by mocks that log into the recorder's sequence."""

    def tracer(name):
        async def resume(item_id, user, db):
            FakeRecorder.calls.append((name, (item_id, user.username), {}))
            return True

        return AsyncMock(side_effect=resume)

    return {"resume_alert_on_reply": tracer("resume_alert"), "resume_case_on_reply": tracer("resume_case")}


def test_a_comment_hands_a_waiting_item_back_after_it_is_recorded():
    case = SimpleNamespace(customer_code="ACME", assigned_to=None, case_name="Case")
    with _patches(
        get_alert_by_id=AsyncMock(return_value=ALERT),
        get_case_by_id=AsyncMock(return_value=case),
        create_comment=AsyncMock(return_value=SimpleNamespace(id=1)),
        create_case_comment=AsyncMock(return_value=SimpleNamespace(id=2, comment="c")),
        CommentResponse=lambda **kw: kw,
        CaseCommentResponse=lambda **kw: kw,
        **_resumers(),
    ):
        asyncio.run(dbo.create_comment_endpoint(CommentCreate(alert_id=7, comment="yes", user_name="x"), PORTAL, AsyncMock()))
        asyncio.run(dbo.create_case_comment_endpoint(CaseCommentCreate(case_id=3, comment="logs", user_name="x"), PORTAL, AsyncMock()))
    portal = Actor(username="portal", is_soc=False)
    assert recorded() == [
        ("alert_action", (7, LifecycleAction.COMMENTED, portal), {}),
        ("resume_alert", (7, "portal"), {}),
        ("case_action", (3, LifecycleAction.COMMENTED, portal), {}),
        ("resume_case", (3, "portal"), {}),
    ]


def test_a_customer_cannot_put_an_alert_or_a_case_on_hold():
    from fastapi import HTTPException

    updated = AsyncMock(return_value=ALERT)
    case_updated = AsyncMock()
    with _patches(update_alert_status=updated, update_case_status=case_updated, AlertResponse=lambda **kw: kw):
        for call in (
            lambda: dbo.update_alert_status_endpoint(UpdateAlertStatus(alert_id=7, status="PENDING_CUSTOMER"), PORTAL, AsyncMock()),
            lambda: dbo.update_case_status_endpoint(UpdateCaseStatus(case_id=3, status="PENDING_CUSTOMER"), False, PORTAL, AsyncMock()),
        ):
            try:
                asyncio.run(call())
                raise AssertionError("a portal user set PENDING_CUSTOMER")
            except HTTPException as e:
                assert e.status_code == 403 and "Only the SOC" in e.detail
        bulk = asyncio.run(
            dbo.bulk_update_alert_status_endpoint(BulkUpdateAlertStatus(alert_ids=[7, 8], status="PENDING_CUSTOMER"), PORTAL, AsyncMock()),
        )
    assert updated.await_count == 0 and case_updated.await_count == 0
    assert bulk.updated_alert_ids == [] and bulk.not_updated_alert_ids == [7, 8]
    assert [name for name, *_ in recorded() if name != "alerts_action"] == []


def test_a_customer_may_still_move_an_item_and_the_soc_may_put_it_on_hold():
    with _patches(update_alert_status=AsyncMock(return_value=ALERT), AlertResponse=lambda **kw: kw):
        asyncio.run(dbo.update_alert_status_endpoint(UpdateAlertStatus(alert_id=7, status="IN_PROGRESS"), PORTAL, AsyncMock()))
        asyncio.run(dbo.update_alert_status_endpoint(UpdateAlertStatus(alert_id=7, status="PENDING_CUSTOMER"), ANALYST, AsyncMock()))
    assert [call[2] for call in recorded()] == [{"to_status": "IN_PROGRESS"}, {"to_status": "PENDING_CUSTOMER"}]
