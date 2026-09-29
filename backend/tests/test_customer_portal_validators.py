"""Branding field validation, shared by the global settings and the per-customer overrides.

Run with: cd backend && python -m pytest tests/test_customer_portal_validators.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

from app.customer_portal.schema.branding import (  # noqa: E402
    UpdateCustomerBrandingRequest,
)
from app.customer_portal.schema.settings import (  # noqa: E402
    UpdatePortalSettingsRequest,
)
from app.customer_portal.services.customers import ensure_customer_exists  # noqa: E402
from app.customer_portal.utils import validators  # noqa: E402

PNG_BASE64 = "iVBORw0KGgo="
SCHEMAS = [UpdatePortalSettingsRequest, UpdateCustomerBrandingRequest]

INVALID = [
    ("brand_color", "red"),
    ("brand_color", "#12345"),
    ("logo_base64", "not base64!"),
    ("logo_base64", "A" * (validators.MAX_LOGO_BASE64_BYTES + 4)),
    ("logo_mime_type", "application/pdf"),
]


@pytest.mark.parametrize("schema", SCHEMAS, ids=lambda s: s.__name__)
@pytest.mark.parametrize("field,value", INVALID)
def test_settings_and_overrides_reject_the_same_payloads(schema, field, value):
    with pytest.raises(HTTPException):
        schema(**{field: value})


@pytest.mark.parametrize("schema", SCHEMAS, ids=lambda s: s.__name__)
def test_settings_and_overrides_normalise_the_same_way(schema):
    parsed = schema(brand_color=" #ABC ", logo_base64=f"data:image/png;base64,{PNG_BASE64}", logo_mime_type="image/png")
    assert (parsed.brand_color, parsed.logo_base64, parsed.logo_mime_type) == ("#abc", PNG_BASE64, "image/png")


@pytest.mark.parametrize("schema", SCHEMAS, ids=lambda s: s.__name__)
def test_an_empty_value_means_unset(schema):
    parsed = schema(brand_color="  ", logo_base64="", logo_mime_type="")
    assert (parsed.brand_color, parsed.logo_base64, parsed.logo_mime_type) == (None, None, None)


def test_every_allowed_mime_type_is_accepted():
    for mime in validators.ALLOWED_LOGO_MIME_TYPES:
        assert validators.validate_logo_mime_type(mime) == mime


def _session_finding(row):
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    return AsyncMock(execute=AsyncMock(return_value=result))


def test_unknown_customer_is_404():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ensure_customer_exists(_session_finding(None), "NOPE"))
    assert exc.value.status_code == 404


def test_known_customer_passes():
    asyncio.run(ensure_customer_exists(_session_finding("ACME"), "ACME"))
