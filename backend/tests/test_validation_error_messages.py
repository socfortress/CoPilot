"""What a 422 actually tells the caller (issue #960).

The Active Response bug in #960 was a one-line schema mistake, but it cost a
support round-trip because the response said only "Invalid value." — no field,
no reason. That text is `ErrorType.GENERAL`'s canned message, and GENERAL is
where every code the v1-era enum doesn't map ends up, plus every custom
validator that raises `ValueError`. So the single most common validation
failure in the app was also its least readable one.

These tests pin the contract the handler now offers:

- **GENERAL carries Pydantic's own message through**, prefixed with the field
  path, so "which field and why" survives to the UI.
- **Mapped codes keep their hand-written wording.** "Missing data for required
  field." reads better than Pydantic's "Field required"; the fallback must not
  swallow it.
- **`message` accepts an explicit None.** `ValidationErrorItem.message` was
  annotated a bare `str = None`; Pydantic 2 applies a default only when the key
  is *absent* and rejects an explicitly-passed None. A handler that passes
  `message=None` on the non-GENERAL path would therefore raise inside the error
  handler — turning every ordinary 422 in the app into a 500.
- **A list index in `loc` doesn't crash the handler.** `loc[-1]` is an int
  there, and `field` is typed `str` with no coercion in Pydantic 2.

Run with: cd backend && python -m pytest tests/test_validation_error_messages.py
"""

import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.middleware.exception_handlers import _describe  # noqa: E402
from app.utils import ErrorType  # noqa: E402
from app.utils import ValidationErrorItem  # noqa: E402
from app.utils import ValidationErrorResponse  # noqa: E402

# ---------------------------------------------------------------------------
# ValidationErrorItem
# ---------------------------------------------------------------------------


def test_explicit_none_message_is_accepted_and_falls_back():
    """The handler passes message=None on every non-GENERAL error."""
    item = ValidationErrorItem(field="params", error_type=ErrorType.MISSING_V2, message=None)

    assert item.message == "Missing data for required field."


def test_explicit_message_is_kept():
    item = ValidationErrorItem(field="ip", error_type=ErrorType.GENERAL, message="ip: 'nope' is not a valid IP address")

    assert item.message == "ip: 'nope' is not a valid IP address"


def test_general_without_a_message_still_has_the_canned_text():
    item = ValidationErrorItem(field="ip", error_type=ErrorType.GENERAL)

    assert item.message == "Invalid value."


@pytest.mark.parametrize("error_type", list(ErrorType))
def test_every_error_type_resolves_to_a_message(error_type):
    """ValidationErrorResponse.message is a required str — None anywhere here is a 500."""
    item = ValidationErrorItem(field="f", error_type=error_type, message=None)

    assert item.message
    assert ValidationErrorResponse(message=item.message, details=[item]).message


# ---------------------------------------------------------------------------
# _describe
# ---------------------------------------------------------------------------


def test_describe_names_the_field_and_the_reason():
    error = {"type": "value_error", "msg": "Value error, '10.0.0' is not a valid IP address"}

    assert _describe(error, ("body", "alert", "ip")) == "alert.ip: '10.0.0' is not a valid IP address"


def test_describe_drops_the_request_location_prefix():
    error = {"type": "string_type", "msg": "Input should be a valid string"}

    assert _describe(error, ("query", "customer_code")) == "customer_code: Input should be a valid string"


def test_describe_handles_a_list_index_in_loc():
    error = {"type": "string_type", "msg": "Input should be a valid string"}

    assert _describe(error, ("body", "arguments", 0)) == "arguments.0: Input should be a valid string"


def test_describe_without_a_path_returns_the_bare_reason():
    error = {"type": "value_error", "msg": "Value error, boom"}

    assert _describe(error, ("body",)) == "boom"


@pytest.mark.parametrize("msg", ["", "   ", None])
def test_describe_returns_none_when_pydantic_says_nothing(msg):
    """None means 'use the canned text' — never an empty message on the wire."""
    assert _describe({"type": "value_error", "msg": msg}, ("body", "ip")) is None
