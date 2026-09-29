"""Branding field validation, shared by the global settings and the per-customer overrides.

Run with: cd backend && python -m pytest tests/test_customer_portal_validators.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402

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
    # A ValidationError (→ the standard 422), not an HTTPException escaping from Pydantic.
    with pytest.raises(ValidationError) as exc:
        schema(**{field: value})
    assert [error["loc"] for error in exc.value.errors()] == [(field,)]


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


def test_schemas_do_not_depend_on_fastapi():
    import inspect

    import app.customer_portal.schema.branding as branding_schema
    import app.customer_portal.schema.settings as settings_schema

    for module in (validators, settings_schema, branding_schema):
        assert "fastapi" not in inspect.getsource(module), module.__name__


def patch_logger():
    """The 422 handler writes the error to the audit log; stub the DB it would use."""
    from contextlib import ExitStack

    from app.middleware import exception_handlers

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    logger = MagicMock(get_user_id_from_request=AsyncMock(return_value=None), log_error=AsyncMock())

    stack = ExitStack()
    stack.enter_context(patch.object(exception_handlers, "AsyncSession", MagicMock(return_value=session)))
    stack.enter_context(patch.object(exception_handlers, "Logger", MagicMock(return_value=logger)))
    return stack


def test_an_invalid_field_is_a_422_that_names_it():
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from fastapi.testclient import TestClient

    from app.middleware import exception_handlers

    app = FastAPI()
    app.add_exception_handler(RequestValidationError, exception_handlers.validation_exception_handler)

    @app.post("/settings")
    def update(request: UpdatePortalSettingsRequest):
        return {"success": True}

    # The handler logs the error to the DB; this test only cares about the response.
    with patch_logger():
        response = TestClient(app).post("/settings", json={"brand_color": "red"})

    assert response.status_code == 422
    assert response.json()["message"] == "brand_color: Expected a hex color like #RGB or #RRGGBB"
