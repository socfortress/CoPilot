"""Customer Portal routes never return an exception's text, and never turn a 403/404 into a 500.

Run with: cd backend && python -m pytest tests/test_customer_portal_route_errors.py
"""

import asyncio
import inspect
import os
import pkgutil
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

import app.customer_portal.routes as portal_routes  # noqa: E402
from app.customer_portal.routes.errors import internal_errors  # noqa: E402

SQL_ERROR = OperationalError("SELECT secret_column FROM customer_portal_branding", {}, Exception("Lost connection"))


def _run(error, session=None):
    async def body():
        async with internal_errors("save customer branding", session):
            raise error

    asyncio.run(body())


def test_an_unexpected_error_is_a_generic_500():
    with pytest.raises(HTTPException) as exc:
        _run(SQL_ERROR)
    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to save customer branding"


def test_the_failed_transaction_is_rolled_back():
    session = AsyncMock()
    with pytest.raises(HTTPException):
        _run(SQL_ERROR, session)
    session.rollback.assert_awaited_once()


@pytest.mark.parametrize("status_code", [403, 404])
def test_a_services_http_error_passes_through(status_code):
    session = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        _run(HTTPException(status_code=status_code, detail="Customer ACME not found"), session)
    assert (exc.value.status_code, exc.value.detail) == (status_code, "Customer ACME not found")
    session.rollback.assert_not_awaited()


def _route_modules():
    for info in pkgutil.iter_modules(portal_routes.__path__):
        yield __import__(f"{portal_routes.__name__}.{info.name}", fromlist=[info.name])


@pytest.mark.parametrize("module", list(_route_modules()), ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_no_route_hand_rolls_its_error_handling(module):
    source = inspect.getsource(module)
    if module.__name__.endswith(".errors"):
        return
    assert "except Exception" not in source, "use internal_errors() instead"
    assert "str(e)" not in source, "an exception's text must not reach the client"


def test_saving_the_ai_report_switch_returns_the_saved_state():
    # internal_errors() wraps only the write; the response must still be returned after it.
    from types import SimpleNamespace
    from unittest.mock import patch

    import app.customer_portal.routes.ai_reports as ai_reports_routes
    from app.customer_portal.schema.ai_reports import (
        UpdatePortalAiReportSettingsRequest,
    )

    saved = SimpleNamespace(
        customer_code="ACME",
        enabled=True,
        allow_customer_requests=False,
        daily_request_limit=None,
        updated_at=None,
        updated_by=3,
    )
    with patch.object(ai_reports_routes, "ensure_customer_exists", AsyncMock()), patch.object(
        ai_reports_routes,
        "upsert_ai_report_settings",
        AsyncMock(return_value=saved),
    ), patch.object(ai_reports_routes, "get_ai_report_settings", AsyncMock(return_value=None)), patch.object(
        ai_reports_routes,
        "count_recent_requests",
        AsyncMock(return_value=0),
    ), patch.object(
        ai_reports_routes,
        "record_audit_event",
        AsyncMock(),
    ):
        response = asyncio.run(
            ai_reports_routes.set_customer_ai_report_settings(
                "ACME",
                UpdatePortalAiReportSettingsRequest(enabled=True),
                session=AsyncMock(),
                current_user=SimpleNamespace(id=3),
            ),
        )

    assert response is not None and response.success is True
    assert (response.settings.customer_code, response.settings.enabled) == ("ACME", True)
