"""A Customer Portal user asking the AI analyst to analyse an alert (#1215).

The rules (``refusal``) are pure and tested on plain values; the request flow is tested
with the database and Talon mocked: what reaches Talon, what is recorded, and that a
refused or failed request costs the customer nothing. Also here: the operator settings'
partial update, the analyst route's tenant check, and the ingest trigger no longer
waiting for Talon.

Run with: cd backend && python -m pytest tests/test_customer_portal_ai_requests.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.connectors.talon.services.talon as talon_svc  # noqa: E402
import app.customer_portal.services.ai_reports as reports_svc  # noqa: E402
import app.customer_portal.services.ai_requests as svc  # noqa: E402
import app.incidents.services.incident_alert as ingest  # noqa: E402
from app.connectors.talon.schema.talon import TalonInvestigateRequest  # noqa: E402

NOW = datetime(2026, 10, 9, 12, 0, 0)


def _settings(enabled=True, allow=True, limit=None):
    return SimpleNamespace(enabled=enabled, allow_customer_requests=allow, daily_request_limit=limit)


def _job(status="completed", minutes_ago=120):
    return SimpleNamespace(status=status, created_at=NOW - timedelta(minutes=minutes_ago))


def _request(minutes_ago):
    return SimpleNamespace(requested_at=NOW - timedelta(minutes=minutes_ago))


def _user():
    return SimpleNamespace(id=7, username="acme_user", role_id=4)


# ── The rules ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "settings",
    [None, _settings(enabled=False), _settings(allow=False), _settings(enabled=False, allow=True)],
)
def test_requests_need_both_switches(settings):
    refused = svc.refusal(settings, None, None, 0, NOW)
    assert refused.status_code == 403


def test_a_first_request_goes_ahead():
    assert svc.refusal(_settings(), None, None, 0, NOW) is None


@pytest.mark.parametrize("status", ["pending", "running"])
def test_an_analysis_in_progress_is_not_started_twice(status):
    refused = svc.refusal(_settings(), _job(status, minutes_ago=50), None, 0, NOW)
    assert refused.status_code == 409


def test_a_job_stuck_for_hours_no_longer_blocks_the_alert():
    assert svc.refusal(_settings(), _job("running", minutes_ago=3 * 60), None, 0, NOW) is None


def test_cooldown_counts_from_the_last_analysis_whoever_started_it():
    # An analyst's (or the auto trigger's) job 10 minutes ago.
    refused = svc.refusal(_settings(), _job("completed", minutes_ago=10), None, 0, NOW)
    assert refused.status_code == 429
    assert "in 20 minutes" in refused.detail


def test_cooldown_counts_from_a_request_talon_has_not_picked_up_yet():
    refused = svc.refusal(_settings(), _job("completed", minutes_ago=300), _request(minutes_ago=29), 0, NOW)
    assert refused.status_code == 429
    assert "in 1 minute." in refused.detail


def test_a_completed_analysis_can_be_rerun_after_the_cooldown():
    assert svc.refusal(_settings(), _job("completed", minutes_ago=30), _request(minutes_ago=31), 0, NOW) is None


def test_the_daily_limit_refuses_without_naming_it():
    refused = svc.refusal(_settings(limit=3), None, None, 3, NOW)
    assert refused.status_code == 429
    assert "daily limit" in refused.detail
    assert "3" not in refused.detail


def test_under_the_limit_or_without_one_the_request_goes_ahead():
    assert svc.refusal(_settings(limit=3), None, None, 2, NOW) is None
    assert svc.refusal(_settings(limit=None), None, None, 10_000, NOW) is None


# ── The flow ──────────────────────────────────────────────────────────────


class _Session:
    """Just enough AsyncSession for the request flow: records adds, commits and rollbacks."""

    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.executed = []

    def add(self, row):
        row.id = 41
        self.added.append(row)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, row):
        return None

    async def execute(self, statement):
        self.executed.append(statement)
        return MagicMock()


def _run(settings, job=None, last_request=None, recent=0, talon=None):
    session = _Session()
    alert = SimpleNamespace(id=5, customer_code="ACME")
    talon = talon or AsyncMock(return_value=SimpleNamespace(success=True))
    with patch.object(svc, "ensure_alert_visible", AsyncMock(return_value=alert)), patch.object(
        svc,
        "_locked_settings",
        AsyncMock(return_value=settings),
    ), patch.object(svc, "_latest_job", AsyncMock(return_value=job)), patch.object(
        svc,
        "_latest_request",
        AsyncMock(return_value=last_request),
    ), patch.object(
        svc,
        "count_recent_requests",
        AsyncMock(return_value=recent),
    ), patch.object(
        svc,
        "investigate_alert",
        talon,
    ), patch.object(
        svc,
        "record_audit_event",
        AsyncMock(),
    ) as audit, patch.object(
        svc,
        "create_comment",
        AsyncMock(),
    ) as comment:
        try:
            result = asyncio.run(svc.request_alert_analysis(5, _user(), session))
        except HTTPException as e:
            result = e
    return result, session, talon, audit, comment


def test_a_request_reaches_talon_for_the_alerts_customer_and_is_recorded():
    request, session, talon, audit, comment = _run(_settings())

    sent = talon.await_args.args[0]
    assert (sent.alert_id, sent.customer_code, sent.sender) == (5, "ACME", "customer-portal")
    assert request.customer_code == "ACME" and request.alert_id == 5 and request.requested_by == "acme_user"
    assert session.added == [request]
    assert audit.await_args.kwargs["result"].value == "success"
    assert "Customer Portal" in comment.await_args.args[0].comment


def test_the_request_is_recorded_before_talon_is_called():
    """The row (and the lock's release) must come first, or a double click starts two analyses."""
    order = []
    session = _Session()
    session.commit = AsyncMock(side_effect=lambda: order.append("commit"))
    talon = AsyncMock(side_effect=lambda *_: order.append("talon"))
    alert = SimpleNamespace(id=5, customer_code="ACME")
    with patch.object(svc, "ensure_alert_visible", AsyncMock(return_value=alert)), patch.object(
        svc,
        "_locked_settings",
        AsyncMock(return_value=_settings()),
    ), patch.object(svc, "_latest_job", AsyncMock(return_value=None)), patch.object(
        svc,
        "_latest_request",
        AsyncMock(return_value=None),
    ), patch.object(
        svc,
        "investigate_alert",
        talon,
    ), patch.object(
        svc,
        "record_audit_event",
        AsyncMock(),
    ), patch.object(
        svc,
        "create_comment",
        AsyncMock(),
    ):
        asyncio.run(svc.request_alert_analysis(5, _user(), session))
    assert order[:2] == ["commit", "talon"]


def test_a_refused_request_records_nothing_and_never_calls_talon():
    error, session, talon, audit, _ = _run(_settings(limit=2), recent=2)

    assert error.status_code == 429
    assert session.added == []
    assert session.rollbacks == 1
    talon.assert_not_awaited()
    assert audit.await_args.kwargs["result"].value == "failure"


def test_when_talon_fails_the_request_is_given_back_and_its_error_is_not_shown():
    talon = AsyncMock(side_effect=HTTPException(status_code=500, detail="Traceback: talon internals"))
    error, session, _, _, comment = _run(_settings(), talon=talon)

    assert error.status_code == 502
    assert "internals" not in error.detail
    # The recorded request is deleted again: no cooldown, no use of the daily limit.
    assert any("DELETE FROM customer_portal_ai_request" in str(statement) for statement in session.executed)
    comment.assert_not_awaited()


def test_the_daily_count_is_only_read_when_a_limit_is_set():
    session = _Session()
    count = AsyncMock(return_value=0)
    alert = SimpleNamespace(id=5, customer_code="ACME")
    with patch.object(svc, "ensure_alert_visible", AsyncMock(return_value=alert)), patch.object(
        svc,
        "_locked_settings",
        AsyncMock(return_value=_settings(limit=None)),
    ), patch.object(svc, "_latest_job", AsyncMock(return_value=None)), patch.object(
        svc,
        "_latest_request",
        AsyncMock(return_value=None),
    ), patch.object(
        svc,
        "count_recent_requests",
        count,
    ), patch.object(
        svc,
        "investigate_alert",
        AsyncMock(),
    ), patch.object(
        svc,
        "record_audit_event",
        AsyncMock(),
    ), patch.object(
        svc,
        "create_comment",
        AsyncMock(),
    ):
        asyncio.run(svc.request_alert_analysis(5, _user(), session))
    count.assert_not_awaited()


def test_an_alert_the_user_cannot_see_is_refused_before_anything_else():
    locked = AsyncMock()
    with patch.object(svc, "ensure_alert_visible", AsyncMock(side_effect=HTTPException(status_code=403, detail="no"))), patch.object(
        svc,
        "_locked_settings",
        locked,
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(svc.request_alert_analysis(5, _user(), _Session()))
    assert exc.value.status_code == 403
    locked.assert_not_awaited()


# ── Operator settings ─────────────────────────────────────────────────────


def _upsert(row, **kwargs):
    with patch.object(reports_svc, "get_ai_report_settings", AsyncMock(return_value=row)):
        return asyncio.run(reports_svc.upsert_ai_report_settings("ACME", True, MagicMock(), user_id=1, **kwargs))


def test_settings_keep_what_the_client_did_not_send():
    row = SimpleNamespace(enabled=False, allow_customer_requests=True, daily_request_limit=20, updated_at=None, updated_by=None)
    saved = _upsert(row)
    assert (saved.enabled, saved.allow_customer_requests, saved.daily_request_limit) == (True, True, 20)


def test_an_explicit_null_limit_means_unlimited():
    row = SimpleNamespace(enabled=True, allow_customer_requests=True, daily_request_limit=20, updated_at=None, updated_by=None)
    saved = _upsert(row, allow_customer_requests=False, daily_request_limit=None)
    assert (saved.allow_customer_requests, saved.daily_request_limit) == (False, None)


def test_a_new_customer_starts_with_requests_off_and_no_limit():
    saved = _upsert(None)
    assert saved.allow_customer_requests is False
    assert saved.daily_request_limit is None


# ── The analyst route's tenant check (pre-existing gap) ───────────────────


def _session_with_alert(alert):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = alert
    session.execute = AsyncMock(return_value=result)
    return session


def _investigate(alert, customer_code="ACME", allowed=True):
    investigate = AsyncMock(return_value="ok")
    with patch.object(talon_svc, "investigate_alert", investigate), patch.object(
        talon_svc.customer_access_handler,
        "check_customer_access",
        AsyncMock(return_value=allowed),
    ):
        try:
            result = asyncio.run(
                talon_svc.investigate_alert_for_user(
                    TalonInvestigateRequest(alert_id=5, customer_code=customer_code),
                    SimpleNamespace(id=1, username="ana"),
                    _session_with_alert(alert),
                ),
            )
        except HTTPException as e:
            result = e
    return result, investigate


def test_analysts_investigate_only_existing_alerts_of_their_customers_under_the_alerts_code():
    alert = SimpleNamespace(id=5, customer_code="ACME")
    assert _investigate(None)[0].status_code == 404
    assert _investigate(alert, allowed=False)[0].status_code == 403
    assert _investigate(alert, customer_code="OTHER")[0].status_code == 400
    result, investigate = _investigate(alert)
    assert result == "ok"
    investigate.assert_awaited_once()


# ── Ingest no longer waits for Talon ──────────────────────────────────────


def test_the_ingest_trigger_hands_talon_off_instead_of_waiting():
    async def scenario():
        release = asyncio.Event()

        async def slow_talon(*_):
            await release.wait()

        with patch.object(ingest, "get_customer_ai_trigger", AsyncMock(return_value=[SimpleNamespace(enabled=True)])), patch.object(
            ingest,
            "talon_investigate_alert",
            AsyncMock(side_effect=slow_talon),
        ) as talon:
            await asyncio.wait_for(ingest.handle_talon_investigation(5, "ACME", AsyncMock()), timeout=1)
            assert ingest._pending_investigations, "the Talon call should be running in the background"
            release.set()
            await asyncio.gather(*list(ingest._pending_investigations))
            talon.assert_awaited_once()
        assert not ingest._pending_investigations

    asyncio.run(scenario())


# ── The settings route ────────────────────────────────────────────────────


def _put(body: dict, before=None):
    import app.customer_portal.routes.ai_reports as routes
    from app.customer_portal.schema.ai_reports import (
        UpdatePortalAiReportSettingsRequest,
    )

    saved = SimpleNamespace(
        customer_code="ACME",
        enabled=True,
        allow_customer_requests=body.get("allow_customer_requests", False),
        daily_request_limit=body.get("daily_request_limit"),
        updated_at=None,
        updated_by=1,
    )
    upsert = AsyncMock(return_value=saved)
    with patch.object(routes, "ensure_customer_exists", AsyncMock()), patch.object(
        routes,
        "upsert_ai_report_settings",
        upsert,
    ), patch.object(
        routes,
        "get_ai_report_settings",
        AsyncMock(return_value=before),
    ), patch.object(
        routes,
        "count_recent_requests",
        AsyncMock(return_value=4),
    ), patch.object(
        routes,
        "record_audit_event",
        AsyncMock(),
    ) as audit:
        response = asyncio.run(
            routes.set_customer_ai_report_settings(
                "ACME",
                UpdatePortalAiReportSettingsRequest(**body),
                session=AsyncMock(),
                current_user=SimpleNamespace(id=1, username="admin"),
            ),
        )
    return response, upsert, audit


def test_the_settings_route_writes_only_the_request_settings_sent():
    _, upsert, _ = _put({"enabled": True})
    assert upsert.await_args.kwargs.keys() == {"user_id"}

    _, upsert, _ = _put({"enabled": True, "allow_customer_requests": True, "daily_request_limit": 5})
    assert upsert.await_args.kwargs["allow_customer_requests"] is True
    assert upsert.await_args.kwargs["daily_request_limit"] == 5

    _, upsert, _ = _put({"enabled": True, "daily_request_limit": None})
    assert upsert.await_args.kwargs["daily_request_limit"] is None


def test_the_settings_route_reports_usage_and_audits_a_change():
    response, _, audit = _put({"enabled": True, "allow_customer_requests": True, "daily_request_limit": 5})
    assert response.settings.requests_last_24h == 4
    assert (response.settings.allow_customer_requests, response.settings.daily_request_limit) == (True, 5)
    assert audit.await_args.kwargs["old_value"]["allow_customer_requests"] is False
    assert audit.await_args.kwargs["new_value"] == {"enabled": True, "allow_customer_requests": True, "daily_request_limit": 5}


def test_a_limit_must_be_at_least_one():
    from pydantic import ValidationError

    from app.customer_portal.schema.ai_reports import (
        UpdatePortalAiReportSettingsRequest,
    )

    with pytest.raises(ValidationError):
        UpdatePortalAiReportSettingsRequest(enabled=True, daily_request_limit=0)
