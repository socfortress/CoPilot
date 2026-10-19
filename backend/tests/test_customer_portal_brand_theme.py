"""The Customer Portal's interface themed with the brand color, by choice (#1278).

``theme_from_brand_color`` is chosen in CoPilot: globally (``customer_portal_settings``,
off by default) and per customer (``customer_portal_branding``, null inherits the
global choice). It resolves field by field like the rest of the branding and reaches
the portal in the effective branding and, for the login page, in the public settings.

Unit tests, no database: tests/e2e/customer_portal_settings_e2e.py runs it on MySQL.

Run with: cd backend && python -m pytest tests/test_customer_portal_brand_theme.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from pydantic import ValidationError  # noqa: E402

import app.customer_portal.services.settings as settings_service  # noqa: E402
from app.customer_portal.schema.branding import (  # noqa: E402
    UpdateCustomerBrandingRequest,
)
from app.customer_portal.schema.settings import PatchPortalSettingsRequest  # noqa: E402
from app.customer_portal.schema.settings import (  # noqa: E402
    UpdatePortalSettingsRequest,
)
from app.customer_portal.services.branding import build_effective_branding  # noqa: E402
from app.customer_portal.services.branding import to_portal_branding  # noqa: E402
from app.customer_portal.services.branding import upsert_branding_override  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import CustomerPortalSettings  # noqa: E402

CC = "TENANT_A"


def _global(theme=False, color="#fc862e"):
    return CustomerPortalSettings(id=1, title="Global", brand_color=color, theme_from_brand_color=theme)


def _override(**fields):
    return CustomerPortalBranding(id=1, customer_code=CC, **{"enabled": True, **fields})


class TestResolution:
    def test_off_by_default(self):
        assert CustomerPortalSettings.create_default().theme_from_brand_color is False
        assert build_effective_branding(None, None).theme_from_brand_color is False
        assert build_effective_branding(_global(), None, CC).theme_from_brand_color is False

    def test_the_global_choice_reaches_every_customer_without_an_override(self):
        assert build_effective_branding(_global(theme=True), None, CC).theme_from_brand_color is True

    def test_a_customer_inherits_it_until_they_choose(self):
        result = build_effective_branding(_global(theme=True), _override(title="Acme"), CC)
        assert result.theme_from_brand_color is True

    @pytest.mark.parametrize("global_theme,customer,expected", [(False, True, True), (True, False, False)])
    def test_a_customer_choice_wins_either_way(self, global_theme, customer, expected):
        result = build_effective_branding(_global(theme=global_theme), _override(theme_from_brand_color=customer), CC)
        assert result.theme_from_brand_color is expected
        # The choice alone is a custom branding: the customer's, not the defaults.
        assert (result.source, result.customer_code) == ("custom", CC)

    def test_a_disabled_override_keeps_its_choice_but_inherits(self):
        override = _override(enabled=False, theme_from_brand_color=True)
        result = build_effective_branding(_global(theme=False), override, CC)
        assert (result.theme_from_brand_color, result.source) == (False, "global")

    def test_the_color_still_resolves_on_its_own(self):
        # The switch turns the theming on; which color is the usual per-field merge.
        result = build_effective_branding(_global(theme=True, color="#fc862e"), _override(brand_color="#215ac8"), CC)
        assert (result.brand_color, result.theme_from_brand_color) == ("#215ac8", True)

    def test_the_portal_receives_it(self):
        effective = build_effective_branding(_global(theme=True), None, CC)
        assert to_portal_branding(effective).theme_from_brand_color is True


def _with_global(row):
    return patch.object(settings_service, "get_global_settings", AsyncMock(return_value=row))


class TestGlobalSettings:
    def test_post_writes_it_and_a_null_restores_off(self):
        with _with_global(_global(theme=False)):
            row = asyncio.run(
                settings_service.replace_global_settings(
                    MagicMock(),
                    UpdatePortalSettingsRequest(title="T", theme_from_brand_color=True),
                    1,
                ),
            )
        assert row.theme_from_brand_color is True
        with _with_global(row):
            row = asyncio.run(settings_service.replace_global_settings(MagicMock(), UpdatePortalSettingsRequest(title="T"), 1))
        assert row.theme_from_brand_color is False

    def test_patch_changes_only_it(self):
        row = _global(theme=False)
        with _with_global(row):
            asyncio.run(settings_service.patch_global_settings(MagicMock(), PatchPortalSettingsRequest(theme_from_brand_color=True), 1))
        assert (row.theme_from_brand_color, row.brand_color, row.title) == (True, "#fc862e", "Global")

    def test_patch_turns_it_off_with_false_and_resets_it_by_name(self):
        row = _global(theme=True)
        with _with_global(row):
            asyncio.run(settings_service.patch_global_settings(MagicMock(), PatchPortalSettingsRequest(theme_from_brand_color=False), 1))
        assert row.theme_from_brand_color is False
        row.theme_from_brand_color = True
        with _with_global(row):
            asyncio.run(
                settings_service.patch_global_settings(MagicMock(), PatchPortalSettingsRequest(reset=["theme_from_brand_color"]), 1),
            )
        assert row.theme_from_brand_color is False

    @pytest.mark.parametrize(
        "body,message",
        [
            (
                {"theme_from_brand_color": None},
                'theme_from_brand_color cannot be empty; to restore its default send reset: ["theme_from_brand_color"]',
            ),
            ({"theme_from_brand_color": True, "reset": ["theme_from_brand_color"]}, "Cannot both set and reset: theme_from_brand_color"),
            ({"theme_from_brand_color": "maybe"}, "theme_from_brand_color"),
        ],
    )
    def test_patch_refuses_what_it_cannot_read(self, body, message):
        with pytest.raises(ValidationError) as refused:
            PatchPortalSettingsRequest(**body)
        assert message in str(refused.value)

    def test_the_login_page_reads_the_global_choice(self):
        row = SimpleNamespace(
            id=1,
            title="Global",
            logo_mime_type=None,
            brand_color="#215ac8",
            theme_from_brand_color=1,
            updated_at=None,
            logo_length=0,
        )
        session = MagicMock()
        session.execute = AsyncMock(return_value=SimpleNamespace(first=lambda: row))
        public = asyncio.run(settings_service.get_public_portal_settings(session))
        assert (public.brand_color, public.theme_from_brand_color) == ("#215ac8", True)

    def test_the_login_page_reads_off_before_anything_was_saved(self):
        session = MagicMock()
        session.execute = AsyncMock(return_value=SimpleNamespace(first=lambda: None))
        assert asyncio.run(settings_service.get_public_portal_settings(session)).theme_from_brand_color is False


class TestCustomerOverride:
    @pytest.mark.parametrize("value", [None, True, False])
    def test_put_stores_inherit_on_or_off(self, value):
        request = UpdateCustomerBrandingRequest(theme_from_brand_color=value)
        session = MagicMock()
        with patch("app.customer_portal.services.branding.get_branding_override", AsyncMock(return_value=None)):
            row = asyncio.run(
                upsert_branding_override(
                    session,
                    CC,
                    enabled=True,
                    title=None,
                    logo_base64=None,
                    logo_mime_type=None,
                    brand_color=None,
                    user_id=1,
                    theme_from_brand_color=request.theme_from_brand_color,
                ),
            )
        assert row.theme_from_brand_color is value

    def test_a_put_without_it_inherits(self):
        # The override is one row replaced as a whole, like its other fields.
        assert UpdateCustomerBrandingRequest().theme_from_brand_color is None
