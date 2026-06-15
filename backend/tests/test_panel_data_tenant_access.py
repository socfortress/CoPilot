"""Regression tests for GHSA-ch48-63px-6wp2 — cross-tenant SIEM read.

The SIEM dashboard panel-data endpoint resolves a dashboard's customer_code
server-side from a caller-supplied dashboard_id, then runs indexer queries. It
is reachable by the lowest-privilege customer_user (portal) role, so it must
reject a caller who is not authorized for that dashboard's customer BEFORE any
indexer query runs — otherwise a portal user enumerates dashboard ids to read
another tenant's data.

These are unit tests against get_panel_data with a mocked DB session; no real
DB or indexer is touched. The access gate sits before the event-source load, so
an *authorized* caller falls through to a 404 ("Event source not found") here —
that 404 is the signal the tenant gate was passed, not a failure.

Run with: cd backend && python -m pytest tests/test_panel_data_tenant_access.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

from app.auth.models.users import RoleEnum  # noqa: E402
from app.siem.services.dashboards import get_panel_data  # noqa: E402

DASHBOARD_CUSTOMER = "TENANT_B"


def _scalar_result(*, first=None, all_=None):
    """Build a mock that mimics `await session.execute(...)` → result.scalars()."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = first
    scalars.all.return_value = all_ if all_ is not None else []
    result.scalars.return_value = scalars
    return result


def _session(execute_results):
    session = MagicMock()
    session.execute = AsyncMock(side_effect=execute_results)
    return session


def test_customer_user_without_access_is_denied():
    dashboard = SimpleNamespace(id=1, customer_code=DASHBOARD_CUSTOMER, event_source_id=10)
    user = SimpleNamespace(id=42, role_id=RoleEnum.customer_user.value)
    # 1st execute: dashboard load. 2nd execute: the user's customer-access lookup
    # (assigned only to TENANT_A, NOT the dashboard's TENANT_B).
    session = _session(
        [
            _scalar_result(first=dashboard),
            _scalar_result(all_=["TENANT_A"]),
        ],
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_panel_data(dashboard_id=1, timerange="24h", db=session, current_user=user))
    assert exc.value.status_code == 403
    assert DASHBOARD_CUSTOMER in exc.value.detail


def test_customer_user_with_access_passes_the_gate():
    dashboard = SimpleNamespace(id=1, customer_code=DASHBOARD_CUSTOMER, event_source_id=10)
    user = SimpleNamespace(id=7, role_id=RoleEnum.customer_user.value)
    # Assigned to the dashboard's own tenant -> gate passes -> falls through to
    # the event-source load, which we stub as missing (404).
    session = _session(
        [
            _scalar_result(first=dashboard),
            _scalar_result(all_=[DASHBOARD_CUSTOMER]),
            _scalar_result(first=None),  # event source not found
        ],
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_panel_data(dashboard_id=1, timerange="24h", db=session, current_user=user))
    assert exc.value.status_code == 404  # passed tenant gate, failed later


def test_admin_passes_the_gate_for_any_tenant():
    dashboard = SimpleNamespace(id=1, customer_code=DASHBOARD_CUSTOMER, event_source_id=10)
    user = SimpleNamespace(id=1, role_id=RoleEnum.admin.value)
    # Admin is wildcard: no access-lookup query is issued, so the 2nd execute is
    # the event-source load (stubbed missing).
    session = _session(
        [
            _scalar_result(first=dashboard),
            _scalar_result(first=None),  # event source not found
        ],
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_panel_data(dashboard_id=1, timerange="24h", db=session, current_user=user))
    assert exc.value.status_code == 404  # passed tenant gate, failed later
