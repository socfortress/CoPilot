"""Unit tests for per-customer Customer Portal branding resolution.

``build_effective_branding`` is the single place the inherit-vs-override rules
live (see ``app/customer_portal/services/branding.py``), and every consumer — the
portal API and the PDF report theming — goes through it. These tests pin the
rules that are easy to regress:

* no override (or a disabled one) -> the global defaults, ``source="global"``
* an override only overrides the fields it actually sets
* logo + mime type always travel together (a custom logo must never inherit the
  global mime type, which would render a broken image)
* empty strings count as "not set", so clearing a field in the UI falls back

The model objects are constructed in memory — no DB — because the merge is pure.

Run with: cd backend && python -m pytest tests/test_customer_portal_branding_resolution.py
"""
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.customer_portal.services.branding import build_effective_branding  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from app.db.universal_models import CustomerPortalSettings  # noqa: E402

CC = "TENANT_A"


def _global(title="Global Portal", logo="Z2xvYmFs", mime="image/png", color="#fc862e") -> CustomerPortalSettings:
    return CustomerPortalSettings(
        id=1,
        title=title,
        logo_base64=logo,
        logo_mime_type=mime,
        brand_color=color,
    )


def _override(**kwargs) -> CustomerPortalBranding:
    payload = {"customer_code": CC, "enabled": True}
    payload.update(kwargs)
    return CustomerPortalBranding(id=1, **payload)


def test_no_override_uses_global_defaults():
    result = build_effective_branding(_global(), None, CC)

    assert result.source == "global"
    assert result.customer_code is None
    assert result.title == "Global Portal"
    assert result.logo_base64 == "Z2xvYmFs"
    assert result.logo_mime_type == "image/png"
    assert result.brand_color == "#fc862e"


def test_disabled_override_inherits_global_without_losing_stored_values():
    override = _override(enabled=False, title="Acme", logo_base64="YWNtZQ==", logo_mime_type="image/jpeg", brand_color="#215ac8")

    result = build_effective_branding(_global(), override, CC)

    assert result.source == "global"
    assert result.title == "Global Portal"
    assert result.logo_base64 == "Z2xvYmFs"
    assert result.brand_color == "#fc862e"
    # The row keeps its values so the operator can toggle it back on.
    assert override.title == "Acme"


def test_full_override_wins_on_every_field():
    override = _override(title="Acme Security", logo_base64="YWNtZQ==", logo_mime_type="image/jpeg", brand_color="#215ac8")

    result = build_effective_branding(_global(), override, CC)

    assert result.source == "custom"
    assert result.customer_code == CC
    assert result.title == "Acme Security"
    assert result.logo_base64 == "YWNtZQ=="
    assert result.logo_mime_type == "image/jpeg"
    assert result.brand_color == "#215ac8"


def test_partial_override_inherits_the_unset_fields():
    result = build_effective_branding(_global(), _override(title="Acme Security"), CC)

    assert result.source == "custom"
    assert result.title == "Acme Security"
    # Logo and colour still come from the global defaults.
    assert result.logo_base64 == "Z2xvYmFs"
    assert result.logo_mime_type == "image/png"
    assert result.brand_color == "#fc862e"


def test_custom_logo_never_inherits_the_global_mime_type():
    # A custom logo stored without a mime type must default to png rather than
    # borrowing the global one, which could describe a different format.
    result = build_effective_branding(_global(mime="image/svg+xml"), _override(logo_base64="YWNtZQ=="), CC)

    assert result.logo_base64 == "YWNtZQ=="
    assert result.logo_mime_type == "image/png"


def test_empty_strings_are_treated_as_unset():
    override = _override(title="   ", logo_base64="", brand_color="")

    result = build_effective_branding(_global(), override, CC)

    assert result.source == "global"
    assert result.title == "Global Portal"
    assert result.logo_base64 == "Z2xvYmFs"
    assert result.brand_color == "#fc862e"


def test_missing_global_settings_still_resolve():
    # Nothing has ever been saved globally: the title falls back to the product
    # default so the portal (and the PDF report) can always render.
    assert build_effective_branding(None, None, None).title == "CoPilot"

    result = build_effective_branding(None, _override(title="Acme Security"), CC)
    assert result.title == "Acme Security"
    assert result.logo_base64 is None
    assert result.brand_color is None
