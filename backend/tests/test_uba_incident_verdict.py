"""A verdict given on the UBA page reaches the CoPilot incident alert too (#1239).

UBA already reads incident verdicts (its worker polls them); this is the other direction.
What these tests pin:

- the verdict lands on the linked incident alert, attributed to the analyst, audited and
  on the SLA clock like a verdict given on the alert itself;
- an incident verdict already set is never overwritten;
- a false positive saved *without* suppression is not written back while another UBA alert
  merged into the same incident is open (UBA's poller would suppress its rules);
- the incident alert must belong to the path's customer and be visible to the caller;
- nothing here can fail the request: UBA already holds the verdict.

No database, no network. Run with: cd backend && python -m pytest tests/test_uba_incident_verdict.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.connectors.uba.routes.uba as routes  # noqa: E402
from app.connectors.uba.schema.uba import UbaFeedbackRequest  # noqa: E402
from app.connectors.uba.schema.uba import UbaResponse  # noqa: E402
from app.connectors.uba.services import incident_verdict  # noqa: E402
from app.connectors.uba.utils.universal import UbaRequestError  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402

ANALYST = SimpleNamespace(id=2, username="ana", role_id=2)
FP = UbaFeedbackRequest(verdict="FALSE_POSITIVE", reason="AUTHORIZED_USER", note="travel", suppress=True)
TP = UbaFeedbackRequest(verdict="TRUE_POSITIVE")


def _uba_alert(copilot_alert_id=42):
    return UbaResponse(alert={"id": "a1", "entity_key": "upn:jdoe@x", "copilot_alert_id": copilot_alert_id}, signals=[])


def _incident(customer_code="acme", verdict=None):
    return SimpleNamespace(id=42, customer_code=customer_code, verdict=verdict)


def _record(body, *, uba_alert=None, incident=None, open_alerts=(), update=None):
    """record_on_incident with UBA and the incidents services stubbed; returns (result, update mock)."""
    update = update or AsyncMock(
        side_effect=lambda **kw: (SimpleNamespace(id=kw["alert_id"], customer_code="acme", verdict=kw["verdict"]), {"verdict": None}),
    )
    get_incident = AsyncMock(side_effect=incident) if isinstance(incident, Exception) else AsyncMock(return_value=incident or _incident())
    with patch.object(incident_verdict.svc, "get_alert", AsyncMock(return_value=uba_alert or _uba_alert())), patch.object(
        incident_verdict.svc,
        "list_alerts",
        AsyncMock(return_value=UbaResponse(alerts=list(open_alerts))),
    ), patch.object(incident_verdict, "get_alert_by_id", get_incident), patch.object(incident_verdict, "update_alert_verdict", update):
        result = asyncio.run(incident_verdict.record_on_incident("acme", "a1", body, ANALYST, MagicMock()))
    return result, update


def test_a_false_positive_lands_on_the_incident_with_its_reason_and_the_analyst():
    (outcome, updated, previous), update = _record(FP)
    assert outcome.status == "recorded" and outcome.incident_alert_id == 42 and outcome.verdict == "FALSE_POSITIVE"
    kwargs = update.await_args.kwargs
    assert kwargs["alert_id"] == 42
    assert (kwargs["verdict"], kwargs["verdict_reason"], kwargs["verdict_note"], kwargs["actor"]) == (
        "FALSE_POSITIVE",
        "AUTHORIZED_USER",
        "travel",
        "ana",
    )
    assert updated is not None and previous == {"verdict": None}


def test_a_true_positive_carries_no_reason():
    (outcome, _, _), update = _record(TP)
    assert outcome.status == "recorded"
    assert update.await_args.kwargs["verdict_reason"] is None


def test_a_reason_outside_copilots_vocabulary_becomes_other():
    assert incident_verdict.incident_reason("FALSE_POSITIVE", "something UBA-only") == "OTHER"
    assert incident_verdict.incident_reason("FALSE_POSITIVE", None) == "OTHER"
    assert incident_verdict.incident_reason("FALSE_POSITIVE", "RULE_TOO_SENSITIVE") == "RULE_TOO_SENSITIVE"
    assert incident_verdict.incident_reason("TRUE_POSITIVE", "RULE_TOO_SENSITIVE") is None


def test_an_existing_incident_verdict_is_never_overwritten():
    (outcome, updated, _), update = _record(FP, incident=_incident(verdict="TRUE_POSITIVE"))
    assert outcome.status == "already_set" and outcome.verdict == "TRUE_POSITIVE"
    assert updated is None
    update.assert_not_awaited()


def test_an_alert_without_an_incident_is_not_linked():
    (outcome, updated, _), update = _record(FP, uba_alert=_uba_alert(copilot_alert_id=None))
    assert outcome.status == "not_linked" and outcome.incident_alert_id is None
    update.assert_not_awaited()


def test_a_deleted_incident_alert_is_not_linked():
    (outcome, _, _), update = _record(FP, incident=HTTPException(status_code=404, detail="Alert not found"))
    assert outcome.status == "not_linked"
    update.assert_not_awaited()


def test_an_incident_hidden_by_tag_access_is_skipped():
    (outcome, _, _), update = _record(FP, incident=HTTPException(status_code=403, detail="tags"))
    assert outcome.status == "skipped"
    update.assert_not_awaited()


def test_an_incident_of_another_customer_is_skipped():
    (outcome, _, _), update = _record(FP, incident=_incident(customer_code="other"))
    assert outcome.status == "skipped"
    update.assert_not_awaited()


def test_an_unsuppressed_false_positive_leaves_a_shared_incident_alone():
    """UBA's poller would give the incident's FALSE_POSITIVE to the sibling, and suppress its rules."""
    body = UbaFeedbackRequest(verdict="FALSE_POSITIVE", reason="OTHER", suppress=False)
    siblings = [{"id": "a2", "copilot_alert_id": 42}, {"id": "a3", "copilot_alert_id": 7}]
    (outcome, _, _), update = _record(body, open_alerts=siblings)
    assert outcome.status == "skipped" and "1 other open UBA alert" in outcome.message
    update.assert_not_awaited()


def test_an_unsuppressed_false_positive_alone_on_its_incident_is_recorded():
    body = UbaFeedbackRequest(verdict="FALSE_POSITIVE", reason="OTHER", suppress=False)
    (outcome, _, _), _update = _record(body, open_alerts=[{"id": "a3", "copilot_alert_id": 7}])
    assert outcome.status == "recorded"


# -- the route ----------------------------------------------------------------------------------------


def _route(*, feedback=None, record=None):
    """submit_feedback with UBA, the write-back, the audit log and the SLA recorder stubbed."""
    feedback = feedback or AsyncMock(return_value=UbaResponse(verdict="FALSE_POSITIVE", suppressed_rules=["r1"], suppressed_until=None))
    audit, recorder = AsyncMock(), MagicMock()
    recorder.return_value.alert_action = AsyncMock()
    db = MagicMock()
    db.rollback = AsyncMock()
    with patch.object(routes.svc, "submit_feedback", feedback), patch.object(
        routes.incident_verdict,
        "record_on_incident",
        record,
    ), patch.object(routes, "record_audit_event", audit), patch.object(routes, "SlaLifecycleRecorder", recorder):
        response = asyncio.run(routes.submit_feedback("acme", "a1", FP, MagicMock(), ANALYST, db))
    return response, audit, recorder.return_value.alert_action, db


def test_a_recorded_verdict_is_audited_and_on_the_sla_clock():
    updated = SimpleNamespace(
        id=42,
        customer_code="acme",
        verdict="FALSE_POSITIVE",
        verdict_reason="AUTHORIZED_USER",
        verdict_note="travel",
    )
    outcome = incident_verdict.UbaIncidentVerdict(status="recorded", incident_alert_id=42, verdict="FALSE_POSITIVE")
    response, audit, sla, _ = _route(record=AsyncMock(return_value=(outcome, updated, {"verdict": None})))
    assert response.model_extra["suppressed_rules"] == ["r1"]
    assert response.model_extra["incident"]["status"] == "recorded"
    kwargs = audit.await_args.kwargs
    assert kwargs["entity_id"] == 42 and kwargs["customer_code"] == "acme" and kwargs["new_value"]["via"] == "uba"
    alert_id, action, actor = sla.await_args.args
    assert (alert_id, action, actor.username, actor.is_soc) == (42, LifecycleAction.VERDICT_SET, "ana", True)


def test_nothing_is_audited_when_the_incident_was_left_alone():
    outcome = incident_verdict.UbaIncidentVerdict(status="already_set", incident_alert_id=42, verdict="TRUE_POSITIVE")
    response, audit, sla, _ = _route(record=AsyncMock(return_value=(outcome, None, None)))
    assert response.model_extra["incident"]["status"] == "already_set"
    audit.assert_not_awaited()
    sla.assert_not_awaited()


def test_a_failed_write_back_never_fails_the_request():
    response, audit, _, db = _route(record=AsyncMock(side_effect=RuntimeError("database gone")))
    assert response.success is True
    incident = response.model_extra["incident"]
    assert incident["status"] == "failed" and "database gone" not in incident["message"]
    db.rollback.assert_awaited()
    audit.assert_not_awaited()


def test_a_refused_verdict_touches_no_incident():
    record = AsyncMock()
    response, _, _, _ = _route(feedback=AsyncMock(side_effect=UbaRequestError("not_found", "unknown alert a1", 404)), record=record)
    assert response.status_code == 404
    record.assert_not_awaited()
