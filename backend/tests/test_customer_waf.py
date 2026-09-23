"""Customer WAF (#1166): token encryption, WAF transport, tenancy and write-only token.

**What this file pins:**

- The service token is write-only: it never appears in a response model or a log
  line, only in the outgoing ``Authorization`` header.
- A WAF id belongs to a tenant: another customer's ``waf_id`` under your path is a 404.
- A WAF 401/403 never becomes a CoPilot 401/403 — the frontend would log the analyst
  out (``frontend/src/api/session-expiry.ts``). Upstream failures are 502 + ``reason``.
- The encryption key is dedicated and has no fallback; a rotated key is reported as
  "re-enter the token", not as a WAF auth failure.

Unit tests with an httpx MockTransport and a mocked session — no network, no database.

Run with: cd backend && python -m pytest tests/test_customer_waf.py
"""

import asyncio
import inspect
import os
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_waf.utils.universal as transport  # noqa: E402
from app.customer_waf.routes.customer_waf import customer_waf_router  # noqa: E402
from app.customer_waf.schema.customer_waf import WafInstanceCreate  # noqa: E402
from app.customer_waf.schema.customer_waf import WafInstanceResponse  # noqa: E402
from app.customer_waf.schema.customer_waf import WafInstanceUpdate  # noqa: E402
from app.customer_waf.services import crypto  # noqa: E402
from app.customer_waf.services import customer_waf as svc  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402
from app.middleware.customer_access import verify_customer_code_access  # noqa: E402

TOKEN = "wafst_" + "A" * 43
REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def waf_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv(crypto.KEY_ENV_VAR, key)
    return key


def _row(**overrides) -> CustomerWafInstance:
    row = CustomerWafInstance(
        id=7,
        customer_code="ACME",
        name="prod",
        api_url="https://waf.example.com:8080",
        service_token_encrypted=crypto.encrypt_token(TOKEN),
        token_prefix=crypto.display_prefix(TOKEN),
        verify_tls=True,
        ca_cert_pem=None,
        enabled=True,
        created_at=datetime(2026, 9, 1),
    )
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


def _stub_waf(monkeypatch, handler):
    """Route every WAF call through ``handler(request) -> httpx.Response``; returns the seen requests."""
    seen = []

    def _handler(request):
        seen.append(request)
        return handler(request)

    def _client(**kwargs):
        kwargs.pop("verify", None)
        return REAL_ASYNC_CLIENT(transport=httpx.MockTransport(_handler), **kwargs)

    monkeypatch.setattr(transport.httpx, "AsyncClient", _client)
    return seen


def _session():
    s = AsyncMock()
    s.add = MagicMock()
    return s


# ── encryption ─────────────────────────────────────────────────────────────


def test_token_round_trips_and_ciphertext_hides_it():
    ciphertext = crypto.encrypt_token(TOKEN)
    assert TOKEN not in ciphertext
    assert crypto.decrypt_token(ciphertext) == TOKEN
    assert crypto.display_prefix(TOKEN) == TOKEN[:12] + "..."


@pytest.mark.parametrize("value", ["", "REPLACE_ME", "   "])
def test_missing_key_refuses_with_actionable_error(monkeypatch, value):
    monkeypatch.setenv(crypto.KEY_ENV_VAR, value)
    with pytest.raises(crypto.WafKeyNotConfiguredError) as exc:
        crypto.encrypt_token(TOKEN)
    assert crypto.KEY_ENV_VAR in str(exc.value)
    assert exc.value.status_code == 400
    assert crypto.key_configured() is False


def test_no_fallback_to_jwt_or_totp_secret(monkeypatch):
    """The whole point of the dedicated key: no other secret can stand in for it."""
    monkeypatch.delenv(crypto.KEY_ENV_VAR, raising=False)
    monkeypatch.setenv("TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(crypto.WafKeyNotConfiguredError):
        crypto.encrypt_token(TOKEN)


def test_malformed_key_is_explained(monkeypatch):
    monkeypatch.setenv(crypto.KEY_ENV_VAR, "not-a-fernet-key")
    with pytest.raises(crypto.WafKeyMalformedError):
        crypto.encrypt_token(TOKEN)


def test_rotated_key_is_reported_as_reenter_not_auth_failure(monkeypatch):
    ciphertext = crypto.encrypt_token(TOKEN)
    monkeypatch.setenv(crypto.KEY_ENV_VAR, Fernet.generate_key().decode())
    with pytest.raises(crypto.WafTokenUndecryptableError) as exc:
        crypto.decrypt_token(ciphertext)
    assert exc.value.status_code == 409
    assert "Re-enter" in str(exc.value)


@pytest.mark.parametrize(
    "value",
    ["eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig", "waf_gatewaykey123", "wafst_", "", "   "],
)
def test_only_service_tokens_accepted(value):
    with pytest.raises(crypto.InvalidWafTokenError):
        crypto.normalize_token(value)


def test_token_whitespace_trimmed():
    assert crypto.normalize_token(f"  {TOKEN}\n") == TOKEN


# ── URL handling ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    ["https://waf:8080", "https://waf:8080/", "https://waf:8080/api/v1", "https://waf:8080/api/v1/", " https://waf:8080 "],
)
def test_api_url_variants_normalise_to_one_base(value):
    assert transport.normalize_api_url(value) == "https://waf:8080"


@pytest.mark.parametrize("value", ["waf:8080", "ftp://waf", "https://", ""])
def test_api_url_rejects_non_http(value):
    with pytest.raises(ValueError):
        transport.normalize_api_url(value)


# ── transport ──────────────────────────────────────────────────────────────


def test_sends_decrypted_bearer_to_api_path(monkeypatch):
    seen = _stub_waf(monkeypatch, lambda r: httpx.Response(200, json=[]))
    assert asyncio.run(transport.waf_get(_row(), "/sites/")) == []
    assert seen[0].url == httpx.URL("https://waf.example.com:8080/api/v1/sites/")
    assert seen[0].headers["Authorization"] == f"Bearer {TOKEN}"


@pytest.mark.parametrize(
    ("status", "body", "reason", "copilot_status"),
    [
        (401, {"detail": "Invalid, disabled or expired service token"}, "token_rejected", 502),
        (403, {"detail": "Permission denied: 'rules:write' required"}, "insufficient_role", 502),
        (404, {"detail": "Site not found"}, "not_found", 404),
        (500, None, "upstream_error", 502),
    ],
)
def test_upstream_errors_map_without_leaking_401_403(monkeypatch, status, body, reason, copilot_status):
    _stub_waf(monkeypatch, lambda r: httpx.Response(status, json=body) if body else httpx.Response(status))
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(), "/rules/custom"))
    assert exc.value.reason == reason
    assert exc.value.status_code == copilot_status
    assert exc.value.status_code not in (401, 403)


def test_insufficient_role_names_the_missing_permission(monkeypatch):
    _stub_waf(monkeypatch, lambda r: httpx.Response(403, json={"detail": "Permission denied: 'rules:write' required"}))
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(), "/rules/custom"))
    assert "rules:write" in exc.value.detail


@pytest.mark.parametrize("error", [httpx.ConnectTimeout("t"), httpx.ConnectError("refused"), httpx.ReadTimeout("t")])
def test_network_failures_are_unreachable(monkeypatch, error):
    def _raise(request):
        raise error

    _stub_waf(monkeypatch, _raise)
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(), "/logs/"))
    assert exc.value.reason == "unreachable"


def test_certificate_failure_is_tls_error(monkeypatch):
    def _raise(request):
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate")

    _stub_waf(monkeypatch, _raise)
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(), "/logs/"))
    assert exc.value.reason == "tls_error"


def test_spa_html_is_bad_response_not_a_crash(monkeypatch):
    """An api_url that reaches the admin UI's SPA answers 200 text/html."""
    _stub_waf(monkeypatch, lambda r: httpx.Response(200, text="<!doctype html><html></html>"))
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(), "/logs/"))
    assert exc.value.reason == "bad_response"


def test_disabled_instance_is_never_called(monkeypatch):
    seen = _stub_waf(monkeypatch, lambda r: httpx.Response(200, json=[]))
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(transport.waf_get(_row(enabled=False), "/logs/"))
    assert exc.value.reason == "disabled"
    assert exc.value.status_code == 409
    assert seen == []
    # ...except by the connection test, so an admin can check before enabling.
    assert asyncio.run(transport.waf_get(_row(enabled=False), "/users/me", allow_disabled=True)) == []


def test_ssl_verify_modes():
    assert transport.build_ssl_verify(False, None) is False
    assert transport.build_ssl_verify(True, None) is True


# ── token never leaks ──────────────────────────────────────────────────────


def test_token_never_logged(monkeypatch):
    records = []
    sink = logger.add(lambda m: records.append(str(m)), level="DEBUG")
    try:
        row = _row()
        for status in (200, 401, 500):
            _stub_waf(monkeypatch, lambda r, s=status: httpx.Response(s, json=[]))
            try:
                asyncio.run(transport.waf_get(row, "/logs/"))
            except transport.WafRequestError:
                pass
        _stub_waf(monkeypatch, lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused")))
        with pytest.raises(transport.WafRequestError):
            asyncio.run(transport.waf_get(row, "/logs/"))
    finally:
        logger.remove(sink)
    joined = "\n".join(records)
    assert TOKEN not in joined
    assert row.service_token_encrypted not in joined


def test_response_models_carry_no_token():
    row = _row(ca_cert_pem="-----BEGIN CERTIFICATE-----x")
    body = WafInstanceResponse(instance=svc.to_schema(row), success=True, message="ok").model_dump_json()
    assert TOKEN not in body
    assert row.service_token_encrypted not in body
    assert "service_token" not in body
    assert "BEGIN CERTIFICATE" not in body  # has_ca_cert only
    assert '"has_ca_cert":true' in body


# ── tenancy ────────────────────────────────────────────────────────────────


def test_other_customers_waf_id_is_404():
    session = _session()
    session.get = AsyncMock(return_value=_row(customer_code="VICTIM"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_instance_for_customer(session, "ACME", 7))
    assert exc.value.status_code == 404


def test_missing_waf_id_is_404():
    session = _session()
    session.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.get_instance_for_customer(session, "ACME", 7))
    assert exc.value.status_code == 404


def test_own_waf_id_resolves():
    row = _row()
    session = _session()
    session.get = AsyncMock(return_value=row)
    assert asyncio.run(svc.get_instance_for_customer(session, "ACME", 7)) is row


def _route_scopes(route):
    """Scopes demanded by a route's require_any_scope dependency, and whether it has the tenant check."""
    scopes, has_tenant_check = None, False
    for dep in route.dependant.dependencies:
        if dep.call is verify_customer_code_access:
            has_tenant_check = True
        closure = inspect.getclosurevars(dep.call).nonlocals if inspect.isfunction(dep.call) else {}
        if "required_scopes" in closure:
            scopes = set(closure["required_scopes"])
    return scopes, has_tenant_check


def test_every_route_checks_the_tenant():
    for route in customer_waf_router.routes:
        if route.path == "":
            continue  # the cross-customer list; scoped in its handler, tested below
        _, has_tenant_check = _route_scopes(route)
        assert has_tenant_check, f"{route.methods} {route.path} lacks verify_customer_code_access"


def test_only_the_cross_customer_list_lacks_a_path_customer():
    assert [r.path for r in customer_waf_router.routes if "{customer_code}" not in r.path] == [""]


@pytest.mark.parametrize(("scoped", "expect_service_call"), [(None, True), (["ACME"], True), ([], False)])
def test_cross_customer_list_is_scoped(monkeypatch, scoped, expect_service_call):
    """[] means the caller sees nothing: the service must not be called (it would read [] as 'all')."""
    import app.customer_waf.routes.customer_waf as routes

    monkeypatch.setattr(routes, "scoped_customer_codes", AsyncMock(return_value=scoped))
    service = AsyncMock(return_value=[_row()])
    monkeypatch.setattr(routes.svc, "list_all_instances", service)
    result = asyncio.run(routes.list_all_customer_wafs(session=AsyncMock(), current_user=MagicMock()))
    if expect_service_call:
        service.assert_awaited_once()
        assert service.await_args.args[1] == scoped
        assert len(result.instances) == 1
    else:
        service.assert_not_awaited()
        assert result.instances == []


def test_configuration_writes_are_admin_only():
    for route in customer_waf_router.routes:
        scopes, _ = _route_scopes(route)
        # Blocking is a response action (#1167) and open to analysts; only WAF *configuration* is admin-only.
        is_block_route = route.path.endswith("/blocks")
        writes_config = not is_block_route and (
            route.methods & {"PUT", "DELETE"} or (route.methods == {"POST"} and route.path == "/{customer_code}")
        )
        if writes_config:
            assert scopes == {"admin"}, f"{route.methods} {route.path} must be admin-only, got {scopes}"
        else:
            assert scopes == {"admin", "analyst"}, f"{route.methods} {route.path}: {scopes}"


# ── configuration ──────────────────────────────────────────────────────────


def test_update_with_blank_token_keeps_stored_token():
    row = _row(last_verified_role="viewer", last_verified_at=datetime(2026, 9, 2))
    before = (row.service_token_encrypted, row.token_prefix)
    row, changed = asyncio.run(svc.update_instance(_session(), row, WafInstanceUpdate(service_token="   ", enabled=False), 1))
    assert (row.service_token_encrypted, row.token_prefix) == before
    assert changed is False
    assert row.enabled is False
    assert row.last_verified_role == "viewer"  # nothing about the connection changed


def test_update_with_new_token_reencrypts_and_clears_cached_role():
    row = _row(last_verified_role="admin", last_verified_at=datetime(2026, 9, 2))
    new_token = "wafst_" + "B" * 43
    row, changed = asyncio.run(svc.update_instance(_session(), row, WafInstanceUpdate(service_token=new_token), 1))
    assert changed is True
    assert crypto.decrypt_token(row.service_token_encrypted) == new_token
    assert row.token_prefix == crypto.display_prefix(new_token)
    assert row.last_verified_role is None and row.last_verified_at is None


def test_duplicate_name_is_409():
    session = _session()
    customer = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = customer
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("Duplicate entry")))
    request = WafInstanceCreate(name="prod", api_url="https://waf:8080", service_token=TOKEN)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_instance(session, "ACME", request, 1))
    assert exc.value.status_code == 409
    session.rollback.assert_awaited()


def test_create_unknown_customer_is_404():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result)
    request = WafInstanceCreate(name="prod", api_url="https://waf:8080", service_token=TOKEN)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(svc.create_instance(session, "NOPE", request, 1))
    assert exc.value.status_code == 404


def test_invalid_ca_cert_rejected():
    with pytest.raises(HTTPException) as exc:
        svc._clean_ca_cert("-----BEGIN CERTIFICATE-----\nnot base64\n-----END CERTIFICATE-----")
    assert exc.value.status_code == 400
    assert svc._clean_ca_cert("   ") is None


def test_config_warnings_only_for_cleartext():
    """Unverified TLS is the default for self-signed WAFs (#1167) and is not warned about; plain http is."""
    assert len(svc.config_warnings(_row(api_url="http://waf:8000"))) == 1
    assert svc.config_warnings(_row(verify_tls=False)) == []
    assert svc.config_warnings(_row()) == []


def test_tls_verification_is_off_by_default():
    assert WafInstanceCreate(name="p", api_url="https://waf:8443", service_token=TOKEN).verify_tls is False


# ── capabilities / verify ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("roles", "read", "block", "forwarders"),
    [
        (["viewer"], True, False, False),
        (["admin"], True, True, True),
        # operator has rules:write but no sites:read — can't drive the read views
        (["operator"], False, True, False),
        (["viewer", "operator"], True, True, False),
        ([], False, False, False),
        (["someone-elses-role"], False, False, False),
    ],
)
def test_capabilities_follow_waf_role_table(roles, read, block, forwarders):
    caps = svc.capabilities_for_roles(roles)
    assert (caps.can_read, caps.can_block, caps.can_manage_forwarders) == (read, block, forwarders)


def test_verify_caches_role_and_tolerates_spa_health(monkeypatch):
    def handler(request):
        if request.url.path == "/api/v1/users/me":
            return httpx.Response(200, json={"email": "copilot@acme", "roles": [{"id": "x", "name": "viewer"}]})
        return httpx.Response(200, text="<!doctype html>")  # /health through the UI's nginx serves the SPA

    _stub_waf(monkeypatch, handler)
    row = _row()
    result = asyncio.run(svc.verify_instance(_session(), row))
    assert result.authenticated and result.reachable
    assert result.waf_user_email == "copilot@acme"
    assert result.capabilities.can_read and not result.capabilities.can_block
    assert result.health is None
    assert row.last_verified_role == "viewer"
    assert row.last_verified_at is not None


def test_verify_failure_reports_reason_and_leaves_row(monkeypatch):
    _stub_waf(monkeypatch, lambda r: httpx.Response(401, json={"detail": "nope"}))
    row = _row()
    session = _session()
    result = asyncio.run(svc.verify_instance(session, row))
    assert (result.reachable, result.authenticated, result.reason) == (True, False, "token_rejected")
    assert row.last_verified_role is None
    session.commit.assert_not_awaited()


@pytest.mark.parametrize("response", [httpx.Response(404, json={"detail": "Not Found"}), httpx.Response(200, text="<html></html>")])
def test_verify_explains_a_url_that_is_not_a_waf(monkeypatch, response):
    _stub_waf(monkeypatch, lambda r: response)
    result = asyncio.run(svc.verify_instance(_session(), _row()))
    assert (result.reachable, result.authenticated, result.reason) == (True, False, "not_a_waf")


def test_verify_works_on_disabled_waf(monkeypatch):
    _stub_waf(monkeypatch, lambda r: httpx.Response(200, json={"email": "e", "roles": []}))
    assert asyncio.run(svc.verify_instance(_session(), _row(enabled=False))).authenticated


def test_summarize_roles_fits_column():
    assert svc.summarize_roles(["viewer", "admin"]) == "admin,viewer"
    assert len(svc.summarize_roles(["r" * 30, "s" * 30])) == 50
    assert svc.summarize_roles([]) is None


# ── read projections ───────────────────────────────────────────────────────

EVENT = {
    "id": "0f8fad5b-d9cb-469f-a165-70867728950e",
    "timestamp": "2026-09-23T10:00:00Z",
    "transaction_id": "tx1",
    "site_id": None,
    "client_ip": "203.0.113.7",
    "method": "GET",
    "uri": "/?id=1 OR 1=1",
    "host": "shop.acme",
    "rule_id": "942100",
    "action": "blocked",
    "severity": "CRITICAL",
    "anomaly_score": 5,
    "matched_rules": [{"id": "942100", "msg": "SQL Injection"}],
    "raw_log": {"transaction": {"request": {"headers": {"cookie": "session=secret"}}}},
    "geoip_country_code": "NL",
    "geoip_country_name": "Netherlands",
    "geoip_city": None,
}


def test_events_drop_raw_log_and_pass_filters(monkeypatch):
    seen = _stub_waf(monkeypatch, lambda r: httpx.Response(200, json=[EVENT]))
    params = svc.build_event_params(
        action="blocked",
        severity=None,
        client_ip="203.0.113.7",
        rule_id=None,
        site_id=None,
        start_time=datetime(2026, 9, 23),
        end_time=None,
        limit=50,
        offset=0,
    )
    events = asyncio.run(svc.fetch_events(_row(), params))
    assert events[0].matched_rules[0].msg == "SQL Injection"
    dumped = events[0].model_dump_json()
    assert "raw_log" not in dumped and "session=secret" not in dumped
    query = seen[0].url.params
    assert query["action"] == "blocked" and query["client_ip"] == "203.0.113.7" and query["limit"] == "50"
    assert "severity" not in query and query["start_time"] == "2026-09-23T00:00:00+00:00"


def test_event_times_always_carry_utc_offset():
    """The WAF reads a naive timestamp in its own timezone — found live against a WAF in MDT,
    where a naive 'last hour' window matched nothing."""
    from datetime import timedelta
    from datetime import timezone as tz

    common = dict(action=None, severity=None, client_ip=None, rule_id=None, site_id=None, limit=1, offset=0)
    naive = svc.build_event_params(start_time=datetime(2026, 9, 23, 15, 0), end_time=None, **common)
    assert naive["start_time"] == "2026-09-23T15:00:00+00:00"
    mdt = tz(timedelta(hours=-6))
    aware = svc.build_event_params(start_time=None, end_time=datetime(2026, 9, 23, 9, 0, tzinfo=mdt), **common)
    assert aware["end_time"] == "2026-09-23T15:00:00+00:00"


def test_sites_hide_tls_and_auth_config(monkeypatch):
    site = {
        "id": "1b4e28ba-2fa1-11d2-883f-0016d3cca427",
        "name": "shop",
        "hostname": "shop.acme",
        "upstream_url": "http://10.0.0.5",
        "is_enabled": True,
        "detection_mode": False,
        "jwt_jwks_url": "https://idp/jwks",
        "forward_auth_url": "https://auth",
        "has_site_cert": True,
    }
    _stub_waf(monkeypatch, lambda r: httpx.Response(200, json=[site]))
    dumped = asyncio.run(svc.fetch_sites(_row()))[0].model_dump_json()
    assert "jwks" not in dumped and "forward_auth" not in dumped


def test_threat_intel_summary_and_entries(monkeypatch):
    def handler(request):
        if request.url.path.endswith("/stats"):
            return httpx.Response(
                200,
                json={"total_ips": 1, "last_run_at": None, "window_days": 7, "interval_hours": 6, "min_score": 10},
            )
        return httpx.Response(
            200,
            json=[
                {
                    "ip_address": "203.0.113.7",
                    "block_count": 40,
                    "rule_hit_count": 55,
                    "total_events": 60,
                    "threat_score": 90,
                    "top_rules": None,
                    "country_code": "NL",
                    "country_name": "Netherlands",
                    "first_seen_at": "2026-09-20T00:00:00Z",
                    "last_seen_at": "2026-09-23T00:00:00Z",
                    "is_blocked": False,
                    "updated_at": "2026-09-23T00:00:00Z",
                },
            ],
        )

    _stub_waf(monkeypatch, handler)
    summary, entries = asyncio.run(svc.fetch_threat_intel(_row()))
    assert summary.total_ips == 1 and entries[0].threat_score == 90 and entries[0].top_rules == []
