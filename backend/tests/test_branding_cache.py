"""Resolved Customer Portal branding is cached in-process and dropped on every write.

Run with: cd backend && python -m pytest tests/test_branding_cache.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal.routes.branding as branding_routes  # noqa: E402
import app.customer_portal.routes.settings as settings_routes  # noqa: E402
from app.customer_portal.schema.branding import EffectiveBranding  # noqa: E402
from app.customer_portal.services import branding as branding_service  # noqa: E402
from app.customer_portal.services import branding_cache  # noqa: E402


@pytest.fixture(autouse=True)
def _empty_cache():
    branding_cache.invalidate_all()
    yield
    branding_cache.invalidate_all()


def _resolve(customer_code="ACME", title="Acme"):
    """Resolve through the real service with the two table reads mocked; returns (result, global_read)."""
    global_read = AsyncMock(return_value=None)
    override = AsyncMock(return_value=None)
    with patch.object(branding_service, "get_global_settings", global_read), patch.object(
        branding_service,
        "get_branding_override",
        override,
    ), patch.object(branding_service, "build_effective_branding", lambda g, o, c: EffectiveBranding(title=title)):
        result = asyncio.run(branding_service.resolve_effective_branding(AsyncMock(), customer_code))
    return result, global_read


def test_second_resolution_is_served_from_the_cache():
    _resolve()
    _, second_read = _resolve()
    second_read.assert_not_awaited()


def test_customers_are_cached_separately():
    _resolve("ACME")
    _, other_read = _resolve("OTHER")
    other_read.assert_awaited_once()


def test_invalidate_all_forces_a_reload():
    _resolve(title="Before")
    branding_cache.invalidate_all()
    result, read = _resolve(title="After")
    read.assert_awaited_once()
    assert result.title == "After"


def test_callers_get_a_copy():
    first, _ = _resolve()
    first.title = "mutated by a caller"
    second, _ = _resolve()
    assert second.title == "Acme"


def test_ttl_zero_disables_the_cache():
    with patch.object(branding_cache, "TTL_SECONDS", 0):
        _resolve()
        _, read = _resolve()
    read.assert_awaited_once()


def test_every_write_route_invalidates_after_its_commit():
    # A write path that forgets to invalidate serves the old branding for a whole TTL.
    import inspect

    for route in (
        settings_routes.update_portal_settings,
        branding_routes.set_customer_branding,
        branding_routes.remove_customer_branding,
    ):
        source = inspect.getsource(route)
        commit, invalidate = source.find("session.commit()"), source.find("branding_cache.invalidate_all()")
        assert -1 < commit < invalidate, f"{route.__name__} must invalidate the branding cache after committing"
