"""Tenancy + read-only guarantees for the Customer Portal AI report surface.

The AI Analyst routes under /ai_analyst are admin/analyst-scoped and do no
per-request tenant check — they trust the caller. The portal surface reaches the
same data through app/customer_portal/services/ai_reports.py, so *that* module
is where a customer_user is stopped from reading another tenant's investigation.

These are unit tests against the access helper with a mocked session (no real
DB), plus structural assertions that the portal router stays GET-only and the
portal schema keeps agent internals (job id, template, error message) out of the
customer-facing payload.

Run with: cd backend && python -m pytest tests/test_customer_portal_ai_reports_access.py
"""

import asyncio
import os
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.customer_portal.routes.ai_reports as routes  # noqa: E402
import app.customer_portal.services.ai_reports as svc  # noqa: E402
from app.customer_portal.schema.ai_reports import PortalAiInvestigation  # noqa: E402
from app.customer_portal.schema.ai_reports import PortalAiReport  # noqa: E402

VICTIM = "TENANT_B"


def _user(role_id=4):
    # role_id 4 == customer_user
    return SimpleNamespace(id=99, username="tenanta_user", role_id=role_id)


def _session_returning(alert):
    """Mock AsyncSession whose single execute() yields ``alert``."""
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = alert
    session.execute = AsyncMock(return_value=result)
    return session


# ── ensure_alert_visible ──────────────────────────────────────────────────


def test_missing_alert_is_404():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.ensure_alert_visible(3, _user(), _session_returning(None)))
    assert exc.value.status_code == 404


def test_foreign_tenant_alert_is_denied():
    alert = SimpleNamespace(id=3, customer_code=VICTIM)
    with patch.object(svc.customer_access_handler, "check_customer_access", AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(svc.ensure_alert_visible(3, _user(), _session_returning(alert)))
    assert exc.value.status_code == 403
    assert "customer permissions" in exc.value.detail


def test_tag_restricted_alert_is_denied():
    alert = SimpleNamespace(id=3, customer_code="TENANT_A")
    with patch.object(svc.customer_access_handler, "check_customer_access", AsyncMock(return_value=True)), patch.object(
        svc.tag_access_handler,
        "can_user_access_alert",
        AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(svc.ensure_alert_visible(3, _user(), _session_returning(alert)))
    assert exc.value.status_code == 403
    assert "tag permissions" in exc.value.detail


def test_own_tenant_alert_is_allowed():
    alert = SimpleNamespace(id=3, customer_code="TENANT_A")
    with patch.object(svc.customer_access_handler, "check_customer_access", AsyncMock(return_value=True)), patch.object(
        svc.tag_access_handler,
        "can_user_access_alert",
        AsyncMock(return_value=True),
    ):
        assert asyncio.run(svc.ensure_alert_visible(3, _user(), _session_returning(alert))) is alert


# ── get_portal_alert_analysis ─────────────────────────────────────────────


def test_analysis_is_gated_by_visibility_before_any_read():
    """A denied alert must never reach get_alert_analysis()."""
    get_alert_analysis = AsyncMock(return_value=(None, None, []))
    with patch.object(svc, "ensure_alert_visible", AsyncMock(side_effect=HTTPException(status_code=403, detail="nope"))), patch.object(
        svc,
        "get_alert_analysis",
        get_alert_analysis,
    ):
        with pytest.raises(HTTPException):
            asyncio.run(svc.get_portal_alert_analysis(3, _user(), AsyncMock()))
    get_alert_analysis.assert_not_awaited()


def test_analysis_is_empty_when_no_job_ran():
    with patch.object(svc, "ensure_alert_visible", AsyncMock()), patch.object(
        svc,
        "get_alert_analysis",
        AsyncMock(return_value=(None, None, [])),
    ):
        investigation, report, iocs = asyncio.run(svc.get_portal_alert_analysis(3, _user(), AsyncMock()))
    assert investigation is None
    assert report is None
    assert iocs == []


# ── Read-only + no-leak structure ─────────────────────────────────────────


def test_portal_ai_report_router_is_read_only():
    """No write path: review, palace lessons and replay stay analyst-only."""
    methods = set()
    for route in routes.customer_portal_ai_reports_router.routes:
        methods |= set(route.methods)
    assert methods == {"GET"}, f"portal AI report router gained a write method: {sorted(methods)}"


def test_portal_ai_report_routes_admit_customer_user():
    src = open(routes.__file__).read()
    scopes = re.findall(r"require_any_scope\(([^)]*)\)", src)
    assert scopes, "portal AI report routes lost their scope dependency"
    assert all("customer_user" in scope for scope in scopes)


# Investigation internals the customer must not see. job_id/template_used point
# at the agent's prompt templates; error_message can carry Talon stack traces.
LEAKY_FIELDS = {"job_id", "template_used", "error_message"}


def test_portal_schemas_hide_agent_internals():
    exposed = set(PortalAiReport.model_fields) | set(PortalAiInvestigation.model_fields)
    assert not (exposed & LEAKY_FIELDS), f"portal schema leaks agent internals: {sorted(exposed & LEAKY_FIELDS)}"
