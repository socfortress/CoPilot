"""SOCFortress UBA connector: transport, error mapping, verification, route guards.

**The traps this file exists for:**

- A UBA 401/403 must never reach the browser as a CoPilot 401/403: the frontend
  reads a 401 from our own API as the analyst's session ending and logs them out.
  Upstream auth failures are 502 with a ``reason`` (``key_rejected``,
  ``insufficient_scope``), like the Customer WAF routes.
- Every route but ``/availability`` is keyed by ``{customer_code}`` and must carry
  ``verify_customer_code_access``; UBA's own key scoping is a second line, not the first.
- Entity keys (``windows-demo\\jdoe``, ``upn:jane@contoso.com``) are sent encoded.

Unit tests with a stubbed HTTP transport: no network, no database.

Run with: cd backend && python -m pytest tests/test_uba_connector.py
"""

import asyncio
import json
import os
from unittest.mock import patch

import httpx
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.uba.utils.universal as transport  # noqa: E402
from app.connectors.uba.schema.uba import UbaFeedbackRequest  # noqa: E402
from app.connectors.uba.services import uba as services  # noqa: E402
from app.connectors.uba.utils.universal import UbaRequestError  # noqa: E402

ATTRS = {"connector_url": "http://uba.example:8010/", "connector_api_key": "uba_testkey", "connector_verified": True}


class Recorder:
    """httpx.MockTransport handler: records requests, answers with the next (status, body)."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.answers.pop(0)
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)


def _run(coro, recorder, attrs=ATTRS):
    real = httpx.AsyncClient

    def client(**kwargs):
        return real(transport=httpx.MockTransport(recorder), **kwargs)

    async def attributes():
        return attrs

    with patch.object(transport.httpx, "AsyncClient", client), patch.object(transport, "get_uba_attributes", attributes), patch.object(
        services,
        "get_uba_attributes",
        attributes,
    ):
        return asyncio.run(coro)


# ── transport ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("stored", ["http://uba:8010", "http://uba:8010/", "http://uba:8010/v1", " http://uba:8010/v1/ "])
def test_base_url_with_or_without_v1(stored):
    assert transport.normalize_base_url(stored) == "http://uba:8010"


def test_request_sends_key_actor_and_encoded_entity_key():
    rec = Recorder((200, {"success": True, "message": "ok", "identity": None}))
    body = _run(services.get_entity("lab", "windows-demo\\jdoe"), rec)
    [req] = rec.requests
    assert req.url.raw_path == b"/v1/tenants/lab/entities/windows-demo%5Cjdoe"
    assert req.headers["x-api-key"] == "uba_testkey"
    assert body.success is True and body.model_extra["identity"] is None


def test_none_params_are_dropped_and_actor_is_sent_on_writes():
    rec = Recorder(
        (200, {"success": True, "message": "ok", "entities": []}),
        (200, {"success": True, "message": "ok", "verdict": "FALSE_POSITIVE"}),
    )
    _run(services.list_entities("lab", entity_type=None, q="jane", page=1), rec)
    assert dict(rec.requests[0].url.params) == {"q": "jane", "page": "1"}
    _run(services.submit_feedback("lab", "a1", UbaFeedbackRequest(verdict="FALSE_POSITIVE", reason="EXPECTED_ACTIVITY"), "analyst1"), rec)
    req = rec.requests[1]
    assert req.method == "POST" and req.headers["x-uba-actor"] == "analyst1"
    assert json.loads(req.content)["verdict"] == "FALSE_POSITIVE"


def test_backtests_send_only_given_params_and_the_catalog_list_is_wrapped():
    from app.connectors.uba.schema.uba import UbaBacktestRequest

    rec = Recorder(
        (202, {"success": True, "message": "ok", "backtest": {"id": "b1", "status": "queued"}}),
        (200, [{"id": "auth.new_country", "name": "New country"}]),
    )
    created = _run(services.create_backtest("lab", UbaBacktestRequest(days=2, rules=["auth.new_country"]), "analyst1"), rec)
    req = rec.requests[0]
    assert req.method == "POST" and req.url.path == "/v1/tenants/lab/backtests" and req.headers["x-uba-actor"] == "analyst1"
    assert json.loads(req.content) == {"days": 2.0, "warmup_days": 0.0, "rules": ["auth.new_country"]}
    assert created.backtest["status"] == "queued"
    catalog = _run(services.list_rule_catalog(), rec)
    assert rec.requests[1].url.path == "/v1/rules" and catalog.rules[0]["id"] == "auth.new_country"


@pytest.mark.parametrize(
    "status,body,reason,code",
    [
        (401, {"detail": "invalid or revoked API key"}, "key_rejected", 502),
        (403, {"detail": "this API key has scope read; write is required"}, "insufficient_scope", 502),
        (404, {"detail": "unknown tenant acme"}, "not_found", 404),
        (422, {"detail": [{"loc": ["query", "since"], "msg": "bad duration"}]}, "invalid_request", 422),
        (500, {"detail": "boom"}, "upstream_error", 502),
        (200, "<html>not the API</html>", "bad_response", 502),
    ],
)
def test_upstream_errors_never_become_401_or_403(status, body, reason, code):
    with pytest.raises(UbaRequestError) as err:
        _run(transport.uba_request("GET", "/v1/status"), Recorder((status, body)))
    assert (err.value.reason, err.value.status_code) == (reason, code)
    assert err.value.status_code not in (401, 403)


def test_missing_or_incomplete_connector_is_409():
    with pytest.raises(UbaRequestError) as err:
        _run(transport.uba_request("GET", "/v1/status"), Recorder(), attrs=None)
    assert (err.value.reason, err.value.status_code) == ("not_configured", 409)
    with pytest.raises(UbaRequestError) as err:
        _run(transport.uba_request("GET", "/v1/status"), Recorder(), attrs={**ATTRS, "connector_api_key": ""})
    assert err.value.status_code == 409


def test_unreachable_uba_is_502():
    def refuse(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(UbaRequestError) as err:
        _run(transport.uba_request("GET", "/v1/status"), refuse)
    assert (err.value.reason, err.value.status_code) == ("unreachable", 502)


# ── verification, availability, status ──────────────────────────────────────


def test_verify_reports_version_and_tenants():
    rec = Recorder((200, {"success": True, "message": "ok", "version": "0.1.0", "tenants": [{"tenant": "lab"}]}))
    result = _run(transport.verify_uba_credentials(ATTRS), rec)
    assert result == {"connectionSuccessful": True, "message": "Connected to SOCFortress UBA 0.1.0; tenants: lab"}
    bad = _run(transport.verify_uba_credentials(ATTRS), Recorder((401, {"detail": "invalid"})))
    assert bad["connectionSuccessful"] is False and "rejected the API key" in bad["message"]


def test_availability_reads_the_connector_row_only():
    result = _run(services.get_availability(), Recorder())  # no answers queued: UBA must not be called
    assert (result.configured, result.verified) == (True, True)
    unset = _run(services.get_availability(), Recorder(), attrs={**ATTRS, "connector_url": ""})
    assert (unset.configured, unset.verified) == (False, False)


def test_customer_status_picks_the_customers_row():
    body = {"success": True, "message": "ok", "version": "0.1.0", "tenants": [{"tenant": "lab", "open_alerts": 2}, {"tenant": "acme"}]}
    status = _run(services.get_customer_status("lab"), Recorder((200, body)))
    assert status.status.tenant == "lab" and status.status.open_alerts == 2
    missing = _run(services.get_customer_status("nobody"), Recorder((200, body)))
    assert missing.status is None


# ── route guards ─────────────────────────────────────────────────────────────


def _dependency_names(route):
    return {getattr(d.call, "__name__", "") for d in route.dependant.dependencies}


def test_every_tenant_route_checks_customer_access():
    from app.connectors.uba.routes.uba import uba_router

    for route in uba_router.routes:
        if route.path == "/availability":
            continue
        assert route.path.startswith("/{customer_code}/"), route.path
        assert "verify_customer_code_access" in _dependency_names(route), route.path


def test_native_override_writes_are_admin_only():
    from app.connectors.uba.routes import uba as routes

    writes = [r for r in routes.uba_router.routes if "native-overrides/{rule_id}" in r.path]
    assert writes and all(r.dependencies == routes._ADMIN for r in writes)


def test_identity_source_actions_are_admin_only_and_reads_are_not():
    from app.connectors.uba.routes import uba as routes

    by_path = {(r.path, tuple(r.methods)): r for r in routes.uba_router.routes}
    actions = [r for (path, _), r in by_path.items() if path.startswith("/{customer_code}/identity-sources/{source_id}/")]
    assert {r.path.rsplit("/", 1)[1] for r in actions} == {"test", "sync"}
    assert all(r.dependencies == routes._ADMIN for r in actions)
    assert by_path[("/{customer_code}/identity-sources", ("GET",))].dependencies == routes._READ


def test_route_errors_carry_reason_not_auth_status():
    from app.connectors.uba.routes.uba import _error

    response = _error(UbaRequestError("key_rejected", "UBA rejected the API key"))
    assert response.status_code == 502
    assert json.loads(response.body) == {"detail": "UBA rejected the API key", "reason": "key_rejected", "success": False}
