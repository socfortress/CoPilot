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
    alert = SimpleNamespace(id=3, customer_code="TENANT_A")
    with patch.object(svc, "ensure_alert_visible", AsyncMock(return_value=alert)), patch.object(
        svc,
        "is_ai_reports_enabled",
        AsyncMock(return_value=True),
    ), patch.object(svc, "get_alert_analysis", AsyncMock(return_value=(None, None, []))):
        enabled, investigation, report, iocs = asyncio.run(svc.get_portal_alert_analysis(3, _user(), AsyncMock()))
    assert enabled is True
    assert investigation is None
    assert report is None
    assert iocs == []


# ── Per-customer AI report switch ─────────────────────────────────────────


def test_disabled_customer_reads_no_report_data():
    """The switch short-circuits before any report row is touched."""
    alert = SimpleNamespace(id=3, customer_code="TENANT_A")
    get_alert_analysis = AsyncMock(return_value=(object(), object(), [object()]))
    with patch.object(svc, "ensure_alert_visible", AsyncMock(return_value=alert)), patch.object(
        svc,
        "is_ai_reports_enabled",
        AsyncMock(return_value=False),
    ), patch.object(svc, "get_alert_analysis", get_alert_analysis):
        enabled, investigation, report, iocs = asyncio.run(svc.get_portal_alert_analysis(3, _user(), AsyncMock()))

    assert enabled is False
    assert (investigation, report, iocs) == (None, None, [])
    get_alert_analysis.assert_not_awaited()


def test_missing_settings_row_means_disabled():
    """Opt-in: no row for the customer must never read as enabled."""
    with patch.object(svc, "get_ai_report_settings", AsyncMock(return_value=None)):
        assert asyncio.run(svc.is_ai_reports_enabled("TENANT_A", AsyncMock())) is False


def test_availability_denies_foreign_customer_code():
    with patch.object(svc.customer_access_handler, "check_customer_access", AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(svc.is_ai_reports_enabled_for_user(_user(), AsyncMock(), customer_code=VICTIM))
    assert exc.value.status_code == 403


def test_insight_filters_restrict_to_enabled_customers():
    """The overview aggregate must carry the switch subquery, not just tenancy."""
    with patch.object(
        svc.customer_access_handler,
        "resolve_effective_customers",
        AsyncMock(return_value=["TENANT_A"]),
    ), patch.object(
        svc.tag_access_handler,
        "build_alert_query_filters",
        AsyncMock(return_value={"accessible_tags": {"*"}, "include_untagged": True, "default_tag_id": None}),
    ):
        filters = asyncio.run(svc._alert_visibility_filters(_user(), AsyncMock()))

    rendered = " ".join(str(f) for f in filters)
    assert "customer_portal_ai_report_settings" in rendered


# ── Read-only + no-leak structure ─────────────────────────────────────────

# Everything the portal reads is a GET. The only write in this router is the
# operator switch, which is admin-scoped and never reachable by a portal user.
PORTAL_READ_PATHS = {"/ai_reports/availability", "/ai_reports/insights", "/ai_reports/alert/{alert_id}"}
OPERATOR_WRITE_PATH = "/ai_reports/settings/{customer_code}"


def _routes_by_path():
    out = {}
    for route in routes.customer_portal_ai_reports_router.routes:
        out.setdefault(route.path, set()).update(route.methods)
    return out


def test_portal_facing_routes_are_read_only():
    """No write path for customers: review, palace lessons and replay stay analyst-only."""
    by_path = _routes_by_path()
    assert PORTAL_READ_PATHS <= set(by_path), f"portal read routes changed shape: {sorted(by_path)}"
    for path in PORTAL_READ_PATHS:
        assert by_path[path] == {"GET"}, f"{path} gained a write method: {sorted(by_path[path])}"


def _route_scopes(source: str):
    """Map each (METHOD, path) -> the require_any_scope(...) arg string for it."""
    lines = source.split("\n")
    out = {}
    i = 0
    while i < len(lines):
        mm = re.search(r"_router\.(get|post|put|delete|patch)\(", lines[i])
        if mm:
            method = mm.group(1).upper()
            deco = []
            j = i
            while j < len(lines) and not re.match(r"\s*(async )?def ", lines[j]):
                deco.append(lines[j])
                j += 1
            decotext = " ".join(deco)
            pm = re.search(r'\.\w+\(\s*"([^"]*)"', decotext)
            sc = re.search(r"require_any_scope\(([^)]*)\)", decotext)
            if pm:
                out[(method, pm.group(1))] = sc.group(1) if sc else ""
            i = j
        else:
            i += 1
    return out


def test_portal_read_routes_admit_customer_user():
    scopes = _route_scopes(open(routes.__file__).read())
    missing = [path for path in PORTAL_READ_PATHS if "customer_user" not in scopes.get(("GET", path), "")]
    assert not missing, f"these portal routes no longer admit customer_user: {missing}"


def test_switch_write_route_is_admin_only():
    scopes = _route_scopes(open(routes.__file__).read())
    write_scope = scopes.get(("PUT", OPERATOR_WRITE_PATH), "")
    assert "admin" in write_scope, "the AI report switch lost its scope dependency"
    assert "customer_user" not in write_scope, "a portal user must never flip its own AI report switch"
    assert "analyst" not in write_scope, "the AI report switch is an admin decision"


# Investigation internals the customer must not see. job_id/template_used point
# at the agent's prompt templates; error_message can carry Talon stack traces.
LEAKY_FIELDS = {"job_id", "template_used", "error_message"}


def test_portal_schemas_hide_agent_internals():
    exposed = set(PortalAiReport.model_fields) | set(PortalAiInvestigation.model_fields)
    assert not (exposed & LEAKY_FIELDS), f"portal schema leaks agent internals: {sorted(exposed & LEAKY_FIELDS)}"
