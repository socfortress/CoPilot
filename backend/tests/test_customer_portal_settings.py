"""Global Customer Portal settings: the service behind ``/customer_portal/settings``.

Unit tests with a mocked session; no database.

Run with: cd backend && python -m pytest tests/test_customer_portal_settings.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_portal.services.settings as settings_service  # noqa: E402
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
