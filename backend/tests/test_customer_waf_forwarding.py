"""WAF event forwarding (#1169): what gets provisioned, reuse, rollback and teardown.

**What this file pins:**

- The input carries ``syslog_type=waf`` / ``syslog_customer=<code>`` / ``waf_name`` — the
  fields CoPilot's alert pipeline reads — and the JSON extractor uses the ``waf_``
  prefix, so the payload's ``timestamp``/``source`` can't overwrite Graylog's own.
- Index set: ``waf-<code>``, 30 daily indices (30-day retention), 1 shard. The stream
  routes on the static fields and is created through the Graylog 6/7-aware helper.
- A failure unwinds everything this run created, newest first — and never a sibling
  WAF's stream or index set that was reused.
- Teardown removes the per-WAF input and forwarder, the stream only with the customer's
  last forwarding WAF, and never the index set (stored events are kept).

Fake Graylog + fake WAF — no network, no database.

Run with: cd backend && python -m pytest tests/test_customer_waf_forwarding.py
"""

import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.customer_waf.services import crypto  # noqa: E402
from app.customer_waf.services import forwarding as fwd  # noqa: E402
from app.customer_waf.utils.universal import WafRequestError  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402

TOKEN = "wafst_" + "F" * 43


class FakeGraylog:
    def __init__(self, used_ports=(5600,), index_sets=(), streams=(), fail_on=None):
        self.used_ports = list(used_ports)
        self.index_sets = [dict(s) for s in index_sets]
        self.streams = [dict(s) for s in streams]
        self.calls = []  # (method, endpoint, body)
        self.fail_on = fail_on
        self.next = 0

    def _id(self, kind):
        self.next += 1
        return f"{kind}-{self.next}"

    async def get(self, endpoint, params=None, connector_name=None):
        self.calls.append(("GET", endpoint, params))
        if endpoint == "/api/system/inputs":
            return {"data": {"inputs": [{"id": f"x{p}", "attributes": {"port": p}} for p in self.used_ports]}, "success": True}
        if endpoint == "/api/system/indices/index_sets":
            return {"data": {"index_sets": self.index_sets}, "success": True}
        if endpoint == "/api/streams":
            return {"data": {"streams": self.streams}, "success": True}
        raise AssertionError(endpoint)

    async def post(self, endpoint, data=None, connector_name=None):
        self.calls.append(("POST", endpoint, data))
        if self.fail_on and self.fail_on in endpoint:
            raise HTTPException(status_code=500, detail=f"boom on {endpoint}")
        if endpoint == "/api/system/inputs":
            return {"data": {"id": self._id("input")}, "success": True}
        if endpoint == "/api/system/indices/index_sets":
            return {"data": {"id": self._id("indexset")}, "success": True}
        return {"data": None, "success": True}

    async def create_entity(self, endpoint, entity, share_request=None, connector_name=None):
        self.calls.append(("CREATE_ENTITY", endpoint, entity))
        return {"data": {"stream_id": self._id("stream")}, "success": True}

    async def delete(self, endpoint, params=None, connector_name=None):
        self.calls.append(("DELETE", endpoint, params))
        return {"data": "No content returned", "success": True}

    def by(self, method, endpoint_part):
        return [c for c in self.calls if c[0] == method and endpoint_part in c[1]]


class FakeWaf:
    def __init__(self, roles=("admin",), fail_forwarder=False, test_ok=True):
        self.roles = roles
        self.fail_forwarder = fail_forwarder
        self.test_ok = test_ok
        self.calls = []

    async def __call__(self, instance, method, path, *, json=None, **kwargs):
        self.calls.append((method, path, json))
        if path == "/users/me":
            return {"email": "copilot@acme", "roles": [{"name": r} for r in self.roles]}
        if method == "POST" and path == "/forwarders/":
            if self.fail_forwarder:
                raise WafRequestError("insufficient_role", "Permission denied: 'config:write' required")
            return {"id": "fwd-77"}
        if path.endswith("/test"):
            return {"success": self.test_ok, "message": "sent" if self.test_ok else "connection refused"}
        if method == "DELETE":
            return None
        raise AssertionError((method, path))


@pytest.fixture(autouse=True)
def waf_key(monkeypatch):
    monkeypatch.setenv(crypto.KEY_ENV_VAR, Fernet.generate_key().decode())
    monkeypatch.delenv("WAF_SYSLOG_PORT_RANGE", raising=False)


def _install(monkeypatch, graylog: FakeGraylog, waf: FakeWaf):
    monkeypatch.setattr(fwd, "send_get_request", graylog.get)
    monkeypatch.setattr(fwd, "send_post_request", graylog.post)
    monkeypatch.setattr(fwd, "send_post_request_create_entity", graylog.create_entity)
    monkeypatch.setattr(fwd, "send_delete_request", graylog.delete)
    monkeypatch.setattr(fwd, "waf_request", waf)
    monkeypatch.setattr(fwd, "_customer_name", AsyncMock(return_value="Acme Corp"))


def _row(**over):
    row = CustomerWafInstance(
        id=5,
        customer_code="ACME",
        name="prod-eu",
        api_url="https://waf:8443",
        service_token_encrypted=crypto.encrypt_token(TOKEN),
        token_prefix=crypto.display_prefix(TOKEN),
        verify_tls=False,
        enabled=True,
    )
    for k, v in over.items():
        setattr(row, k, v)
    return row


def _session(siblings=()):
    s = AsyncMock()
    s.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(siblings)
    s.execute = AsyncMock(return_value=result)
    return s


# ── provisioning ───────────────────────────────────────────────────────────


def test_provisions_everything_with_the_agreed_shapes(monkeypatch):
    gl, waf = FakeGraylog(used_ports=(5600, 5601, 12201)), FakeWaf()
    _install(monkeypatch, gl, waf)
    row = _row()
    result = asyncio.run(fwd.provision(_session(), row, "graylog.example.com"))

    # Input: next free port in range, Syslog TCP, no TLS, global.
    [inp] = [c[2] for c in gl.calls if c[:2] == ("POST", "/api/system/inputs")]
    assert inp["type"] == "org.graylog2.inputs.syslog.tcp.SyslogTCPInput" and inp["global"] is True
    assert inp["configuration"]["port"] == 5602 and inp["configuration"]["tls_enable"] is False
    assert inp["title"] == "SOCFORTRESS WAF - ACME - prod-eu"

    # Static fields: the alert pipeline's source + customer keys, and the WAF's name.
    fields = {c[2]["key"]: c[2]["value"] for c in gl.by("POST", "/staticfields")}
    assert fields == {"syslog_type": "waf", "syslog_customer": "ACME", "waf_name": "prod-eu"}

    # Extractors: regex copy into waf_json, then JSON flattened with the waf_ prefix.
    regex, js = (c[2] for c in gl.by("POST", "/extractors"))
    assert regex["extractor_type"] == "regex" and regex["target_field"] == "waf_json"
    assert regex["extractor_config"]["regex_value"] == r"^\S+ - (\{.*\})$" and regex["cursor_strategy"] == "copy"
    assert js["extractor_type"] == "json" and js["source_field"] == "waf_json"
    assert js["extractor_config"]["key_prefix"] == "waf_" and js["extractor_config"]["flatten"] is True

    # Index set: waf-<code>, 30-day retention, 1 shard.
    ((_, _, ix),) = [c for c in gl.calls if c[:2] == ("POST", "/api/system/indices/index_sets")]
    assert ix["index_prefix"] == "waf-acme" and ix["shards"] == 1
    assert ix["retention_strategy"]["max_number_of_indices"] == 30 and ix["rotation_strategy"]["rotation_period"] == "P1D"

    # Stream: via the 6/7-aware helper, bound to the index set, routed on static fields, then resumed.
    ((_, _, stream),) = gl.by("CREATE_ENTITY", "/api/streams")
    assert stream["index_set_id"] == "indexset-2" and stream["title"] == "SOCFORTRESS WAF - ACME"
    assert {(r["field"], r["value"]) for r in stream["rules"]} == {("syslog_type", "waf"), ("syslog_customer", "ACME")}
    assert gl.by("POST", "/resume")

    # WAF forwarder: syslog over TCP, no TLS, to the given host and the input's port; then tested.
    ((_, _, forwarder),) = [c for c in waf.calls if c[:2] == ("POST", "/forwarders/")]
    assert forwarder == {
        "name": "CoPilot SIEM (ACME)",
        "type": "syslog",
        "is_enabled": True,
        "syslog_host": "graylog.example.com",
        "syslog_port": 5602,
        "syslog_tls": False,
        "syslog_app_name": "waf-platform",
    }
    assert result.test_success is True and result.reused == []
    assert (row.syslog_port, row.graylog_input_id, row.graylog_stream_id, row.waf_forwarder_id) == (5602, "input-1", "stream-3", "fwd-77")
    assert row.forwarding_provisioned_at is not None


def test_sibling_wafs_share_the_customers_index_set_and_stream(monkeypatch):
    gl = FakeGraylog(
        index_sets=[{"id": "ix-existing", "index_prefix": "waf-acme"}],
        streams=[{"id": "st-existing", "title": "SOCFORTRESS WAF - ACME"}],
    )
    _install(monkeypatch, gl, FakeWaf())
    row = _row()
    result = asyncio.run(fwd.provision(_session(), row, "graylog.example.com"))
    assert not gl.by("POST", "/index_sets") and not gl.by("CREATE_ENTITY", "/api/streams")
    assert (row.graylog_index_set_id, row.graylog_stream_id) == ("ix-existing", "st-existing")
    assert len(result.reused) == 2


def test_token_without_forwarder_rights_is_refused_before_touching_graylog(monkeypatch):
    gl = FakeGraylog()
    _install(monkeypatch, gl, FakeWaf(roles=("viewer",)))
    with pytest.raises(fwd.ForwardingError) as exc:
        asyncio.run(fwd.provision(_session(), _row(), "graylog.example.com"))
    assert exc.value.status_code == 400 and "admin" in exc.value.detail
    assert gl.calls == []


def test_failure_unwinds_newest_first(monkeypatch):
    gl = FakeGraylog()
    _install(monkeypatch, gl, FakeWaf(fail_forwarder=True))
    row = _row()
    with pytest.raises(fwd.ForwardingError):
        asyncio.run(fwd.provision(_session(), row, "graylog.example.com"))
    deletes = [c[1] for c in gl.by("DELETE", "")]
    assert deletes == ["/api/streams/stream-3", "/api/system/indices/index_sets/indexset-2", "/api/system/inputs/input-1"]
    assert row.forwarding_provisioned_at is None and row.graylog_input_id is None


def test_rollback_never_removes_reused_sibling_objects(monkeypatch):
    gl = FakeGraylog(
        index_sets=[{"id": "ix-existing", "index_prefix": "waf-acme"}],
        streams=[{"id": "st-existing", "title": "SOCFORTRESS WAF - ACME"}],
    )
    _install(monkeypatch, gl, FakeWaf(fail_forwarder=True))
    with pytest.raises(fwd.ForwardingError):
        asyncio.run(fwd.provision(_session(), _row(), "graylog.example.com"))
    assert [c[1] for c in gl.by("DELETE", "")] == ["/api/system/inputs/input-1"]


def test_graylog_failure_midway_unwinds_the_input(monkeypatch):
    gl = FakeGraylog(fail_on="/extractors")
    _install(monkeypatch, gl, FakeWaf())
    with pytest.raises(fwd.ForwardingError) as exc:
        asyncio.run(fwd.provision(_session(), _row(), "graylog.example.com"))
    assert "boom" in exc.value.detail
    assert [c[1] for c in gl.by("DELETE", "")] == ["/api/system/inputs/input-1"]


def test_failed_test_event_is_reported_not_fatal(monkeypatch):
    _install(monkeypatch, FakeGraylog(), FakeWaf(test_ok=False))
    row = _row()
    result = asyncio.run(fwd.provision(_session(), row, "graylog.example.com"))
    assert result.test_success is False and "refused" in result.test_message
    assert row.forwarding_provisioned_at is not None


def test_already_provisioned_is_409(monkeypatch):
    _install(monkeypatch, FakeGraylog(), FakeWaf())
    with pytest.raises(fwd.ForwardingError) as exc:
        asyncio.run(fwd.provision(_session(), _row(forwarding_provisioned_at=datetime(2026, 9, 1)), "h"))
    assert exc.value.status_code == 409


def test_port_range_exhausted(monkeypatch):
    monkeypatch.setenv("WAF_SYSLOG_PORT_RANGE", "5600-5601")
    gl = FakeGraylog(used_ports=(5600, 5601))
    _install(monkeypatch, gl, FakeWaf())
    with pytest.raises(fwd.ForwardingError) as exc:
        asyncio.run(fwd.provision(_session(), _row(), "h"))
    assert exc.value.status_code == 409
    assert not gl.by("POST", "/api/system/inputs")


@pytest.mark.parametrize("raw", ["nope", "70000-70010", "5700-5600", "80-90"])
def test_bad_port_range_is_explained(monkeypatch, raw):
    monkeypatch.setenv("WAF_SYSLOG_PORT_RANGE", raw)
    with pytest.raises(fwd.ForwardingError) as exc:
        fwd.port_range()
    assert exc.value.status_code == 400


# ── teardown ───────────────────────────────────────────────────────────────


def _provisioned(**over):
    return _row(
        syslog_host="graylog.example.com",
        syslog_port=5602,
        graylog_input_id="input-1",
        graylog_stream_id="stream-3",
        graylog_index_set_id="indexset-2",
        waf_forwarder_id="fwd-77",
        forwarding_provisioned_at=datetime(2026, 9, 1),
        **over,
    )


def test_teardown_of_last_forwarding_waf_removes_stream_but_keeps_index_set(monkeypatch):
    gl, waf = FakeGraylog(), FakeWaf()
    _install(monkeypatch, gl, waf)
    row = _provisioned()
    warnings = asyncio.run(fwd.deprovision(_session(siblings=[]), row))
    assert warnings == []
    assert ("DELETE", "/forwarders/fwd-77", None) in waf.calls
    assert [c[1] for c in gl.by("DELETE", "")] == ["/api/system/inputs/input-1", "/api/streams/stream-3"]
    assert not gl.by("DELETE", "index_sets")
    assert row.forwarding_provisioned_at is None and row.graylog_input_id is None and row.syslog_port is None


def test_teardown_keeps_stream_while_a_sibling_still_forwards(monkeypatch):
    gl = FakeGraylog()
    _install(monkeypatch, gl, FakeWaf())
    asyncio.run(fwd.deprovision(_session(siblings=[_provisioned(id=6, name="prod-us")]), _provisioned()))
    assert [c[1] for c in gl.by("DELETE", "")] == ["/api/system/inputs/input-1"]


def test_teardown_with_unreachable_waf_still_cleans_graylog_and_warns(monkeypatch):
    class DownWaf(FakeWaf):
        async def __call__(self, instance, method, path, **kwargs):
            raise WafRequestError("unreachable", "WAF did not respond")

    gl = FakeGraylog()
    _install(monkeypatch, gl, DownWaf())
    row = _provisioned()
    warnings = asyncio.run(fwd.deprovision(_session(), row))
    assert any("Remove it in the WAF UI" in w for w in warnings)
    assert gl.by("DELETE", "/api/system/inputs/input-1")
    assert row.forwarding_provisioned_at is None
