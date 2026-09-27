"""DELETE /siem/dashboards/disable/{dashboard_id} checks the caller owns the dashboard's customer.

The route is admin/analyst-only, but it disabled whichever enabled dashboard the id
named: an analyst assigned to one customer could switch off another tenant's
dashboards by guessing ids. The owner is now resolved from the row and enforced
with ``enforce_owned_object_access``, like every other object-addressed route.

Run with: cd backend && python -m pytest tests/test_dashboard_disable_access.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

import app.siem.routes.dashboards as routes  # noqa: E402
from app.siem.services.dashboards import (  # noqa: E402
    get_enabled_dashboard_customer_code,
)

ANALYST = SimpleNamespace(id=2, username="analyst1", role_id=2)


def _session_returning(value):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    session.execute = AsyncMock(return_value=result)
    return session


def _accessible(codes):
    return patch(
        "app.middleware.customer_access.customer_access_handler.get_user_accessible_customers",
        AsyncMock(return_value=codes),
    )


def test_scoped_analyst_cannot_disable_another_tenants_dashboard():
    disable = AsyncMock()
    with _accessible(["TENANT_A"]), patch.object(routes, "disable_dashboard", disable):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.disable_dashboard_endpoint(7, ANALYST, _session_returning("TENANT_B")))
    assert exc.value.status_code == 403
    disable.assert_not_awaited()


def test_scoped_analyst_can_disable_their_own_tenants_dashboard():
    disable = AsyncMock()
    with _accessible(["TENANT_A"]), patch.object(routes, "disable_dashboard", disable):
        asyncio.run(routes.disable_dashboard_endpoint(7, ANALYST, _session_returning("TENANT_A")))
    disable.assert_awaited_once()


def test_deployment_wide_caller_can_disable_any_dashboard():
    disable = AsyncMock()
    with _accessible(["*"]), patch.object(routes, "disable_dashboard", disable):
        asyncio.run(routes.disable_dashboard_endpoint(7, ANALYST, _session_returning("TENANT_B")))
    disable.assert_awaited_once()


def test_unknown_dashboard_is_404():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_enabled_dashboard_customer_code(7, _session_returning(None)))
    assert exc.value.status_code == 404
