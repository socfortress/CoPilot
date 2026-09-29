"""Global Customer Portal settings: the service behind ``/customer_portal/settings``.

Unit tests with a mocked session; no database.

Run with: cd backend && python -m pytest tests/test_customer_portal_settings.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from pydantic import ValidationError  # noqa: E402

import app.customer_portal.services.settings as settings_service  # noqa: E402
from app.customer_portal.schema.settings import PatchPortalSettingsRequest  # noqa: E402
from app.customer_portal.schema.settings import (  # noqa: E402
    UpdatePortalSettingsRequest,
)
from app.db.universal_models import CustomerPortalSettings  # noqa: E402

PNG_BASE64 = "iVBORw0KGgo="


def _stored(**fields) -> CustomerPortalSettings:
    row = CustomerPortalSettings(
        id=1,
        title="Acme SOC",
        logo_base64=PNG_BASE64,
        logo_mime_type="image/png",
        brand_color="#112233",
    )
    for name, value in fields.items():
        setattr(row, name, value)
    return row


def _with_global(row):
    return patch.object(settings_service, "get_global_settings", AsyncMock(return_value=row))


# ── replace (POST) ────────────────────────────────────────────────────────


def test_replace_writes_every_field_and_stamps_the_author():
    row = _stored()
    request = UpdatePortalSettingsRequest(title="New", logo_base64=PNG_BASE64, logo_mime_type="image/webp", brand_color="#ABCDEF")
    with _with_global(row):
        result = asyncio.run(settings_service.replace_global_settings(MagicMock(), request, user_id=7))

    assert result is row
    assert (row.title, row.logo_mime_type, row.brand_color, row.updated_by) == ("New", "image/webp", "#abcdef", 7)


def test_replace_restores_the_default_of_every_null_field():
    row = _stored()
    with _with_global(row):
        asyncio.run(settings_service.replace_global_settings(MagicMock(), UpdatePortalSettingsRequest(), user_id=1))

    defaults = CustomerPortalSettings.get_default_values()
    assert (row.title, row.logo_base64, row.logo_mime_type, row.brand_color) == (
        defaults["title"],
        defaults["logo_base64"],
        defaults["logo_mime_type"],
        defaults["brand_color"],
    )


def test_replace_creates_the_row_when_it_was_never_saved():
    session = MagicMock()
    with _with_global(None):
        row = asyncio.run(settings_service.replace_global_settings(session, UpdatePortalSettingsRequest(title="First"), user_id=1))

    session.add.assert_called_once_with(row)
    assert row.title == "First"


# ── read ──────────────────────────────────────────────────────────────────


def test_missing_row_reads_as_unsaved_defaults():
    with _with_global(None):
        row = asyncio.run(settings_service.get_global_settings_or_default(MagicMock()))
    assert row.id == 0 and row.title == CustomerPortalSettings.get_default_values()["title"]


def test_stored_row_is_returned_as_is():
    stored = _stored()
    with _with_global(stored):
        assert asyncio.run(settings_service.get_global_settings_or_default(MagicMock())) is stored


# ── patch (PATCH) ─────────────────────────────────────────────────────────


def _patch(row, **body):
    request = PatchPortalSettingsRequest(**body)
    with _with_global(row):
        return asyncio.run(settings_service.patch_global_settings(MagicMock(), request, user_id=9))


def test_patch_changes_only_the_title_and_keeps_the_logo():
    row = _patch(_stored(), title="Renamed")
    assert (row.title, row.logo_base64, row.logo_mime_type, row.brand_color) == ("Renamed", PNG_BASE64, "image/png", "#112233")
    assert row.updated_by == 9


def test_patch_replaces_the_logo_with_its_mime_type():
    row = _patch(_stored(), logo_base64="R0lGODlh", logo_mime_type="image/gif")
    assert (row.logo_base64, row.logo_mime_type, row.title) == ("R0lGODlh", "image/gif", "Acme SOC")


def test_patch_resets_only_what_it_names():
    row = _patch(_stored(), reset=["logo", "brand_color"])
    assert (row.logo_base64, row.logo_mime_type, row.brand_color, row.title) == (None, None, None, "Acme SOC")


def test_patch_creates_the_row_when_it_was_never_saved():
    session = MagicMock()
    with _with_global(None):
        row = asyncio.run(settings_service.patch_global_settings(session, PatchPortalSettingsRequest(title="First"), user_id=1))
    session.add.assert_called_once_with(row)
    assert row.title == "First"


@pytest.mark.parametrize(
    "body,message",
    [
        ({}, "Nothing to update"),
        ({"title": None}, 'title cannot be empty; to restore its default send reset: ["title"]'),
        ({"brand_color": ""}, 'brand_color cannot be empty; to restore its default send reset: ["brand_color"]'),
        ({"logo_base64": PNG_BASE64}, "logo_base64 and logo_mime_type must be sent together"),
        ({"logo_mime_type": "image/png"}, "logo_base64 and logo_mime_type must be sent together"),
        ({"title": "X", "reset": ["title"]}, "Cannot both set and reset: title"),
        ({"reset": ["logo_base64"]}, "reset.0"),
    ],
)
def test_patch_rejects_ambiguous_requests(body, message):
    with pytest.raises(ValidationError) as exc:
        PatchPortalSettingsRequest(**body)
    assert message in str(exc.value)


# ── routes ────────────────────────────────────────────────────────────────


def test_patch_route_is_admin_only():
    from fastapi.routing import APIRoute

    from app.customer_portal.routes.settings import customer_portal_settings_router
    from tests.test_customer_user_write_allowlist import _route_scopes

    route = next(r for r in customer_portal_settings_router.routes if isinstance(r, APIRoute) and "PATCH" in r.methods)
    assert route.path == "/settings"
    assert _route_scopes(route.dependant) == {"admin"}
