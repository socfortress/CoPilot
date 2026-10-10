"""A failed Wazuh Manager sign-in is reported, not raised (#1234).

`create_wazuh_manager_client()` returns `None` when the manager is unreachable or
rejects the connector's credentials. `send_put_request` then set a header on that
`None` and died with `TypeError: 'NoneType' object does not support item
assignment`, so `POST /api/active_response/invoke` (and every other PUT caller:
rule uploads, logtest, groups, ossec.conf) ended in a bare HTTP 500 instead of
the route's own 502. POST/DELETE/restart went on to call Wazuh with no
`Authorization` header and reported its 401 instead of the real cause.

What these tests pin:

- **Every helper returns the same failure dict and never reaches the network**
  when sign-in fails.
- **A missing connector still returns `None`**, which the invoke route turns into
  503 "not configured" — that check comes first.
- **The invoke route answers 502 naming the sign-in failure**, through the real
  `send_put_request` rather than a stub of it.

No DB, no network: the connector lookup, the sign-in and `run_blocking` are stubbed.

Run with: cd backend && python -m pytest tests/test_wazuh_manager_auth_failure.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.active_response.routes.active_response as route_mod  # noqa: E402
import app.connectors.wazuh_manager.utils.universal as wazuh  # noqa: E402
from app.active_response.schema.active_response import (  # noqa: E402
    InvokeActiveResponseRequest,
)
from app.auth.models.users import RoleEnum  # noqa: E402

ATTRIBUTES = {"connector_url": "https://wazuh.invalid:55000", "connector_username": "u", "connector_password": "p"}

CALLS = {
    "get": lambda: wazuh.send_get_request("/agents"),
    "post": lambda: wazuh.send_post_request("/agents", data={}),
    "put": lambda: wazuh.send_put_request("/active-response", data="{}"),
    "delete": lambda: wazuh.send_delete_request("/agents"),
    "restart": lambda: wazuh.restart_service(),
}


def run_signed_out(call, attributes=ATTRIBUTES):
    network = AsyncMock()
    with (
        patch.object(wazuh, "create_wazuh_manager_client", AsyncMock(return_value=None)),
        patch.object(wazuh, "get_connector_info_from_db", AsyncMock(return_value=attributes)),
        patch.object(wazuh, "AsyncSessionLocal", MagicMock()),
        patch.object(wazuh, "run_blocking", network),
    ):
        result = asyncio.run(call())
    return result, network


@pytest.mark.parametrize("name", sorted(CALLS))
def test_failed_sign_in_is_reported_not_raised(name):
    result, network = run_signed_out(CALLS[name])

    assert result == {"success": False, "message": wazuh.AUTH_FAILED_MESSAGE}
    network.assert_not_awaited()


@pytest.mark.parametrize("name", ["post", "put", "delete", "restart"])
def test_missing_connector_still_reads_as_not_configured(name):
    result, network = run_signed_out(CALLS[name], attributes=None)

    assert result is None
    network.assert_not_awaited()


def test_invoke_route_answers_502_naming_the_sign_in_failure():
    request = InvokeActiveResponseRequest(
        endpoint="/active-response",
        arguments=[],
        command="windows_firewall",
        custom=True,
        alert={"action": "block", "ip": "1.1.1.1"},
        params={"wait_for_complete": True, "agents_list": ["032"]},
    )
    admin = SimpleNamespace(id=1, username="admin", role_id=RoleEnum.admin)

    with (
        patch.object(wazuh, "create_wazuh_manager_client", AsyncMock(return_value=None)),
        patch.object(wazuh, "get_connector_info_from_db", AsyncMock(return_value=ATTRIBUTES)),
        patch.object(wazuh, "AsyncSessionLocal", MagicMock()),
        patch.object(wazuh, "run_blocking", AsyncMock()),
        pytest.raises(HTTPException) as excinfo,
    ):
        asyncio.run(route_mod.invoke_active_response_route(request, admin, AsyncMock()))

    assert excinfo.value.status_code == 502
    assert excinfo.value.detail == f"Wazuh Active Response failed: {wazuh.AUTH_FAILED_MESSAGE}"
