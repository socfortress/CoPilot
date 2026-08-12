"""Active Response invoke payload validation (issue #960).

An analyst blocking an IP from the Active Response wizard was told "Invalid
value." on a perfectly good IPv4 address, with nothing naming the field or the
reason. The request never reached Wazuh: `InvokeActiveResponseRequest`'s
before-validator replaced the `alert` dict with a `WindowsFirewallAlert`
*instance* while the field stayed typed `Dict[str, Any]`, and Pydantic 2 — unlike
v1 — refuses a model instance for a dict field. FastAPI turned that into a 422
whose only human-readable text was the generic fallback.

What these tests pin:

- **A valid payload validates, and `alert` survives as a plain JSON-ready dict.**
  The route `json.dumps()` it straight onto the wire, so a model instance there
  is not merely a typing detail — it is the bug.
- **Garbage in the alert is still rejected**, per command, so the fix didn't
  widen the door it was meant to unstick.
- **A genuinely bad IP fails with a message that says so.** The endpoint-side
  script only logs its rejection to a file on the agent; catching it at the API
  is the difference between an error and a silent no-op.
- **The command accepts the casing the UI displays.** `_missing_` used to look up
  a member name that does not exist, turning an uppercase command into a 500.
- **The body and query string Wazuh receives.** With the endpoint dead since the
  Pydantic 2 migration, nothing downstream of the schema had been exercised
  either, so the wire format is pinned rather than assumed.
- **A rejection from Wazuh is not reported as success.** The route used to return
  `success=True` unconditionally, which makes an unreachable manager look exactly
  like a completed block.

Schema and route tests — no DB, and the Wazuh PUT is stubbed.

Run with: cd backend && python -m pytest tests/test_active_response_invoke.py
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.active_response.routes.active_response as route_mod  # noqa: E402
from app.active_response.schema.active_response import (  # noqa: E402
    ActiveResponseCommand,
)
from app.active_response.schema.active_response import (  # noqa: E402
    InvokeActiveResponseRequest,
)


def build_payload(**overrides):
    """The exact body the frontend posts for a Windows firewall block."""
    payload = {
        "endpoint": "/active-response",
        "arguments": [],
        "command": "windows_firewall",
        "custom": True,
        "alert": {"action": "block", "ip": "1.1.1.1"},
        "params": {"wait_for_complete": True, "agents_list": ["032"]},
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# The regression itself
# ---------------------------------------------------------------------------


def test_valid_windows_firewall_payload_is_accepted():
    request = InvokeActiveResponseRequest(**build_payload())

    assert request.command is ActiveResponseCommand.windows_firewall
    assert request.alert == {"action": "block", "ip": "1.1.1.1"}


def test_alert_stays_a_plain_dict_so_the_route_can_serialise_it():
    """The route json.dumps() `alert` — a model instance there breaks the wire format."""
    request = InvokeActiveResponseRequest(**build_payload())

    assert type(request.alert) is dict
    # Mirrors what invoke_active_response_route builds before the PUT.
    assert json.loads(json.dumps({"alert": request.alert}))["alert"]["ip"] == "1.1.1.1"


@pytest.mark.parametrize("ip", ["1.1.1.1", "8.8.8.8", "192.168.1.50", "2606:4700:4700::1111"])
def test_valid_addresses_are_not_rejected(ip):
    request = InvokeActiveResponseRequest(**build_payload(alert={"action": "block", "ip": ip}))

    assert request.alert["ip"] == ip


def test_unblock_is_accepted_too():
    request = InvokeActiveResponseRequest(**build_payload(alert={"action": "unblock", "ip": "1.1.1.1"}))

    assert request.alert == {"action": "unblock", "ip": "1.1.1.1"}


# ---------------------------------------------------------------------------
# The door stays shut on bad input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ip", ["not-an-ip", "", "1.1.1.1; shutdown", "999.999.999.999", "1.1.1.1/24"])
def test_invalid_ip_is_rejected_with_a_message_naming_the_reason(ip):
    with pytest.raises(ValidationError) as excinfo:
        InvokeActiveResponseRequest(**build_payload(alert={"action": "block", "ip": ip}))

    assert "not a valid IP address" in str(excinfo.value)


def test_unknown_action_is_rejected():
    with pytest.raises(ValidationError):
        InvokeActiveResponseRequest(**build_payload(alert={"action": "detonate", "ip": "1.1.1.1"}))


def test_missing_ip_is_rejected():
    with pytest.raises(ValidationError):
        InvokeActiveResponseRequest(**build_payload(alert={"action": "block"}))


def test_non_object_alert_is_rejected_rather_than_crashing():
    with pytest.raises((ValidationError, ValueError)):
        InvokeActiveResponseRequest(**build_payload(alert="1.1.1.1"))


def test_unknown_command_is_a_400_not_a_500():
    with pytest.raises(HTTPException) as excinfo:
        InvokeActiveResponseRequest(**build_payload(command="format_c_drive"))

    assert excinfo.value.status_code == 400


def test_a_missing_command_names_the_missing_field():
    payload = {k: v for k, v in build_payload().items() if k != "command"}

    with pytest.raises(ValidationError) as excinfo:
        InvokeActiveResponseRequest(**payload)

    assert excinfo.value.errors()[0]["loc"] == ("command",)


# ---------------------------------------------------------------------------
# Command casing — the UI shows WINDOWS_FIREWALL, the API used to 500 on it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["windows_firewall", "WINDOWS_FIREWALL", "Windows_Firewall"])
def test_command_accepts_the_casing_the_ui_displays(command):
    request = InvokeActiveResponseRequest(**build_payload(command=command))

    assert request.command is ActiveResponseCommand.windows_firewall


def test_sysmon_config_reload_needs_no_ip():
    request = InvokeActiveResponseRequest(
        **build_payload(command="sysmon_config_reload", alert={"action": "sysmon_config_reload"}),
    )

    assert request.alert == {"action": "sysmon_config_reload"}


# ---------------------------------------------------------------------------
# The route — what actually reaches Wazuh, and what the analyst is told back
# ---------------------------------------------------------------------------


def invoke(response, payload=None):
    """Run the route with the Wazuh PUT stubbed out; returns (result, call kwargs)."""
    request = InvokeActiveResponseRequest(**(payload or build_payload()))
    stub = AsyncMock(return_value=response)
    with patch.object(route_mod, "send_put_request", new=stub):
        result = asyncio.run(route_mod.invoke_active_response_route(request))
    return result, stub.call_args.kwargs


def test_wire_format_matches_what_wazuh_expects():
    _, kwargs = invoke({"success": True, "data": {}})

    body = json.loads(kwargs["data"])
    # Wazuh addresses the AR script by name with a "0" suffix.
    assert body["command"] == "windows_firewall0"
    assert body["alert"] == {"action": "block", "ip": "1.1.1.1"}
    assert kwargs["endpoint"] == "/active-response"


def test_wait_for_complete_is_sent_as_a_json_boolean():
    """requests would URL-encode a Python bool as "True", which Wazuh does not accept."""
    _, kwargs = invoke({"success": True, "data": {}})

    assert kwargs["params"]["wait_for_complete"] == "true"
    assert kwargs["params"]["agents_list"] == ["032"]


def test_wildcard_agent_selection_sends_no_agent_filter():
    """The UI posts ["*"] for "all agents"; Wazuh spells that as an absent filter."""
    payload = build_payload(params={"wait_for_complete": True, "agents_list": ["*"]})
    _, kwargs = invoke({"success": True, "data": {}}, payload)

    assert kwargs["params"]["agents_list"] == []


def test_a_wazuh_rejection_is_not_reported_as_success():
    with pytest.raises(HTTPException) as excinfo:
        invoke({"success": False, "message": "HTTP error 400", "error_detail": "Invalid agent ID"})

    assert excinfo.value.status_code == 502
    assert "Invalid agent ID" in excinfo.value.detail


def test_a_missing_wazuh_connector_is_reported_as_unavailable():
    with pytest.raises(HTTPException) as excinfo:
        invoke(None)

    assert excinfo.value.status_code == 503


def test_a_successful_invocation_reports_success():
    result, _ = invoke({"success": True, "data": {}})

    assert result.success is True
