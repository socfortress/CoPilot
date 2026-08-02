"""Resend connector verification.

Backs the Verify button on the Connectors page, via the same
`service_map` -> `verify_authentication` mechanism every other connector uses.

**The reason this file exists at all:** a valid Resend key can answer 401.

Resend supports restricted, send-only API keys — the right shape for a service
that only ever sends mail, which is exactly what CoPilot does. Such a key
authenticates but is refused on management endpoints. Empirically:

    valid, send-only  ->  401  {"name": "restricted_api_key"}
    invalid           ->  400  {"name": "validation_error"}

So the obvious implementation — "200 means healthy" — reports a correctly
configured production key as broken. Most of these tests pin that distinction.

Unit tests with stubbed HTTP — no network.

Run with: cd backend && python -m pytest tests/test_resend_connector_verification.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.resend.utils.universal as verifier  # noqa: E402

ATTRS = {"connector_url": "https://api.resend.com", "connector_api_key": "re_test_key"}


def _response(status, body=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    if body is None:
        r.json.side_effect = ValueError("not json")
    else:
        r.json.return_value = body
    return r


def _verify(response=None, attrs=None, raises=None):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(side_effect=raises) if raises else AsyncMock(return_value=response)

    with patch.object(verifier.httpx, "AsyncClient", return_value=client):
        return asyncio.run(verifier.verify_resend_credentials(attrs or ATTRS))


# ── the restricted-key trap ───────────────────────────────────────────────


def test_a_send_only_restricted_key_verifies_successfully():
    """The whole point. A 401 named restricted_api_key means the key was
    recognised and simply lacks scope for the probed endpoint — which is a
    correct, arguably preferable, configuration for CoPilot."""
    result = _verify(_response(401, {"name": "restricted_api_key", "message": "This API key is restricted to only send emails"}))

    assert result["connectionSuccessful"] is True
    assert "send-only" in result["message"]


def test_an_invalid_key_fails():
    result = _verify(_response(400, {"name": "validation_error", "message": "API key is invalid"}))

    assert result["connectionSuccessful"] is False
    assert "API key is invalid" in result["message"]


def test_an_unrelated_401_still_fails():
    """Only restricted_api_key is special. Any other auth rejection is real."""
    result = _verify(_response(401, {"name": "unauthorized", "message": "Nope"}))
    assert result["connectionSuccessful"] is False


# ── full-access keys ──────────────────────────────────────────────────────


def test_a_verified_domain_is_reported_by_name():
    result = _verify(_response(200, {"data": [{"name": "socfortress.co", "status": "verified"}]}))

    assert result["connectionSuccessful"] is True
    assert "socfortress.co" in result["message"]


def test_no_verified_domain_succeeds_but_warns():
    """The key works, and the next thing that bites is having nowhere to send
    from — mail is then limited to the account owner's own address."""
    result = _verify(_response(200, {"data": []}))

    assert result["connectionSuccessful"] is True
    assert "no verified sending domain" in result["message"].lower()


def test_an_unverified_domain_does_not_count_as_verified():
    result = _verify(_response(200, {"data": [{"name": "pending.example", "status": "pending"}]}))

    assert result["connectionSuccessful"] is True
    assert "no verified sending domain" in result["message"].lower()


# ── failure paths ─────────────────────────────────────────────────────────


def test_a_missing_key_fails_without_calling_out():
    client = MagicMock()
    client.get = AsyncMock()
    with patch.object(verifier.httpx, "AsyncClient", return_value=client):
        result = asyncio.run(
            verifier.verify_resend_credentials({"connector_url": "https://api.resend.com", "connector_api_key": ""}),
        )

    assert result["connectionSuccessful"] is False
    assert "No API key set" in result["message"]
    assert client.get.await_count == 0


def test_a_network_error_is_reported_not_raised():
    """Verification must never raise — the Connectors page would 500."""
    result = _verify(raises=ConnectionError("nodename nor servname provided"))

    assert result["connectionSuccessful"] is False
    assert "ConnectionError" in result["message"]


def test_a_non_json_error_body_still_reports_something_useful():
    result = _verify(_response(502, body=None, text="<html>Bad Gateway</html>"))

    assert result["connectionSuccessful"] is False
    assert "502" in result["message"]


def test_the_base_url_defaults_when_unset():
    """A connector row with no URL should still verify against Resend's API
    rather than failing on an empty host."""
    captured = {}
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    async def _get(url, **kwargs):
        captured["url"] = url
        return _response(200, {"data": []})

    client.get = AsyncMock(side_effect=_get)
    with patch.object(verifier.httpx, "AsyncClient", return_value=client):
        asyncio.run(verifier.verify_resend_credentials({"connector_url": None, "connector_api_key": "re_x"}))

    assert captured["url"] == "https://api.resend.com/domains"


# ── wiring ────────────────────────────────────────────────────────────────


def test_resend_is_registered_in_the_connector_service_map():
    """Without this the Verify button silently does nothing — get_connector_service
    returns None and verify_connector_by_id logs 'not supported'."""
    from app.connectors.services import get_connector_service

    assert get_connector_service("Resend") is not None


@pytest.mark.parametrize("missing", ["connector_url", "connector_api_key"])
def test_absent_attribute_keys_do_not_raise(missing):
    """A hand-edited connector row shouldn't KeyError the Connectors page."""
    attrs = dict(ATTRS)
    attrs.pop(missing)
    result = _verify(_response(200, {"data": []}), attrs=attrs)
    assert "connectionSuccessful" in result
