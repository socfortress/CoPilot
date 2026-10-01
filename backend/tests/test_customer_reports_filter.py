"""The customer reports list honours the portal's global customer filter.

``GET /incidents/customer_reports`` took only a single ``customer_code`` (the analyst
frontend's picker), so the portal sent no filter and the Reports page ignored the
global customer filter. It now also takes ``customer_codes``, intersected with what the
caller may see. Mocked session; no database.

Run with: cd backend && python -m pytest tests/test_customer_reports_filter.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.routes.customer_report as route  # noqa: E402
from app.middleware.customer_access import customer_access_handler  # noqa: E402

PORTAL_USER = SimpleNamespace(id=7, role_id=4)


def _list(accessible, customer_codes=None, customer_code=None):
    listed = AsyncMock(return_value=[])
    with patch.object(customer_access_handler, "get_user_accessible_customers", AsyncMock(return_value=accessible)), patch.object(
        route,
        "list_customer_reports",
        listed,
    ), patch.object(route, "resolve_user_names", AsyncMock(return_value={})):
        asyncio.run(
            route.list_reports(customer_code=customer_code, customer_codes=customer_codes, current_user=PORTAL_USER, db=AsyncMock()),
        )
    args, kwargs = listed.await_args
    return args[1], args[2], kwargs


def test_the_picked_customers_narrow_the_list():
    scope, _, kwargs = _list(["A", "B"], customer_codes=["B"])
    assert scope == ["B"]
    assert kwargs == {"only_customer_visible": True}


def test_no_filter_means_every_accessible_customer():
    scope, _, _ = _list(["A", "B"])
    assert scope == ["A", "B"]


def test_a_customer_the_caller_cannot_see_is_never_added():
    # Resolves to nothing, which the service reads as "no rows", never as "all".
    scope, _, _ = _list(["A"], customer_codes=["Z"])
    assert scope == []


def test_the_analyst_single_customer_filter_still_works():
    _, customer_code, _ = _list(["*"], customer_code="A")
    assert customer_code == "A"
