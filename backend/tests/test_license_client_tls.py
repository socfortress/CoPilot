"""The license client verifies the license server's TLS certificate (#1233).

`send_get_request` / `send_post_request` used to pass `verify=False`, so anyone
able to intercept the backend's outbound traffic could read `COPILOT_API_KEY`
from the `x-api-key` header and forge license, feature and seat answers.
`requests` verifies by default; these tests pin that neither helper turns it off.

No DB, no network: `run_blocking` is stubbed.

Run with: cd backend && python -m pytest tests/test_license_client_tls.py
"""

import asyncio
import os
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.middleware.license as license_mod  # noqa: E402


def _ok_response():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    return response


def _call_kwargs(helper, *args):
    stub = AsyncMock(return_value=_ok_response())
    with patch.object(license_mod, "run_blocking", stub):
        asyncio.run(helper(*args))
    stub.assert_awaited_once()
    return stub.await_args.kwargs


def test_get_request_verifies_tls():
    kwargs = _call_kwargs(license_mod.send_get_request, "features")
    assert kwargs.get("verify", True) is not False


def test_post_request_verifies_tls():
    kwargs = _call_kwargs(license_mod.send_post_request, "verify-license", {"license_key": "x"})
    assert kwargs.get("verify", True) is not False
