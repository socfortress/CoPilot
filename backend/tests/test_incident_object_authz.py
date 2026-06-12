"""Regression tests for GHSA-wjpw-xrg8-vmf9 — broken object-level authorization.

A customer_user (multi-tenant portal role) could read and modify another
tenant's incident data via single-object/config routes in
app/incidents/routes/db_operations.py that performed no ownership check. The
fix adds shared per-object ownership helpers — _ensure_alert_access,
_ensure_case_access, _ensure_customer_access — that resolve the owning
customer_code from the looked-up object (not request input) and reject a caller
who is not entitled to it.

These are unit tests against those helpers with a mocked DB/session; no real DB.
A second test asserts the route-scope hardening: the global parsing-config and
per-object routes the portal never calls no longer admit customer_user.

Run with: cd backend && python -m pytest tests/test_incident_object_authz.py
"""

import os
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.incidents.routes.db_operations as dbo  # noqa: E402

VICTIM = "TENANT_B"


def _user(role_id=4):
    # role_id 4 == customer_user
    return SimpleNamespace(id=99, username="tenanta_user", role_id=role_id)


# ── _ensure_alert_access ──────────────────────────────────────────────────


def test_ensure_alert_access_denies_foreign_tenant():
    alert = SimpleNamespace(id=3, customer_code=VICTIM)
    with patch.object(dbo, "get_alert_by_id", AsyncMock(return_value=alert)), patch.object(
        dbo.customer_access_handler,
        "check_customer_access",
        AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            import asyncio

            asyncio.run(dbo._ensure_alert_access(3, _user(), db=AsyncMock()))
    assert exc.value.status_code == 403
    assert "alert 3" in exc.value.detail


def test_ensure_alert_access_allows_own_tenant():
    import asyncio

    alert = SimpleNamespace(id=3, customer_code="TENANT_A")
    with patch.object(dbo, "get_alert_by_id", AsyncMock(return_value=alert)), patch.object(
        dbo.customer_access_handler,
        "check_customer_access",
        AsyncMock(return_value=True),
    ):
        result = asyncio.run(dbo._ensure_alert_access(3, _user(), db=AsyncMock()))
    assert result is alert


# ── _ensure_case_access ───────────────────────────────────────────────────


def test_ensure_case_access_denies_foreign_tenant():
    import asyncio

    case = SimpleNamespace(id=7, customer_code=VICTIM)
    with patch.object(dbo, "get_case_by_id", AsyncMock(return_value=case)), patch.object(
        dbo.customer_access_handler,
        "check_customer_access",
        AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(dbo._ensure_case_access(7, _user(), db=AsyncMock()))
    assert exc.value.status_code == 403
    assert "case 7" in exc.value.detail


# ── _ensure_customer_access ───────────────────────────────────────────────


def test_ensure_customer_access_denies_foreign_code():
    import asyncio

    with patch.object(dbo.customer_access_handler, "check_customer_access", AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(dbo._ensure_customer_access(VICTIM, _user(), db=AsyncMock()))
    assert exc.value.status_code == 403


def test_ensure_customer_access_allows_own_code():
    import asyncio

    with patch.object(dbo.customer_access_handler, "check_customer_access", AsyncMock(return_value=True)):
        # Returns None and does not raise.
        assert asyncio.run(dbo._ensure_customer_access("TENANT_A", _user(), db=AsyncMock())) is None


# ── Route-scope hardening ─────────────────────────────────────────────────


def _route_scopes(source: str):
    """Map each (METHOD, path) -> the require_any_scope(...) arg string for it."""
    lines = source.split("\n")
    n = len(lines)
    i = 0
    out = {}
    while i < n:
        mm = re.search(r"_router\.(get|post|put|delete|patch)\(", lines[i])
        if mm:
            method = mm.group(1).upper()
            j = i
            deco = []
            while j < n and not re.match(r"\s*(async )?def ", lines[j]):
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


# Routes the customer portal never calls. After the fix none of them may admit
# customer_user — they pass caller-controlled ids/codes to the indexer/DB or
# mutate the deployment-wide parsing config (platform-wide DoS vector).
PORTAL_FORBIDDEN = [
    ("PUT", "/ai_trigger"),
    ("PUT", "/notification"),
    ("DELETE", "/configured/sources/{source}"),
    ("POST", "/fields-assets-title-and-timefield"),
    ("DELETE", "/delete-fields-assets-title-and-timefield"),
    ("POST", "/alert"),  # low-level create
    ("GET", "/alert/context/{alert_context_id}"),
    ("DELETE", "/alert/ioc"),
    ("POST", "/alert/tag"),
    ("DELETE", "/alerts"),  # bulk delete
    ("GET", "/case/data-store"),
    ("POST", "/case-report-template/upload"),
]


def test_portal_forbidden_routes_drop_customer_user():
    src = open(dbo.__file__).read()
    scopes = _route_scopes(src)
    offenders = [(method, path) for method, path in PORTAL_FORBIDDEN if "customer_user" in scopes.get((method, path), "")]
    assert not offenders, f"these routes still admit customer_user: {offenders}"


# Portal-used routes that MUST keep customer_user (and now enforce ownership in
# the handler). Guards against an over-broad scope removal.
PORTAL_REQUIRED = [
    ("PUT", "/alert/status"),
    ("POST", "/case/create"),
    ("POST", "/case/alert-link"),
    ("POST", "/case/alert-unlink"),
    ("POST", "/case/from-alert"),
    ("GET", "/alerts"),
    ("GET", "/cases"),
]


def test_portal_required_routes_keep_customer_user():
    src = open(dbo.__file__).read()
    scopes = _route_scopes(src)
    missing = [(method, path) for method, path in PORTAL_REQUIRED if "customer_user" not in scopes.get((method, path), "")]
    assert not missing, f"these portal routes lost customer_user: {missing}"
