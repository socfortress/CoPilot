"""Customer WAF IP blocking (#1167): target validation, rule text, idempotency, ownership.

**What this file pins:**

- The SecLang CoPilot sends is built from a parsed ``ip_network`` only — injection
  attempts are rejected before any text is produced.
- CoPilot never modifies a rule it didn't create (the WAF's own Threat Intel blocks),
  and never adds a duplicate rule for an IP something already blocks.
- Unblock disables CoPilot's rule; it never deletes, and never touches WAF-owned rules.
- A block can cite only an alert/case of the WAF's own customer.

The fake WAF below mirrors the real one's rule shapes, taken from a production-like
instance (Threat Intel blocks, a CoPilot block, and a pre-cbc7b9b bypass rule whose
stored ``action`` disagrees with its text).

Run with: cd backend && python -m pytest tests/test_customer_waf_blocks.py
"""

import asyncio
import json
import os
import re
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.customer_waf.utils.universal as transport  # noqa: E402
from app.customer_waf.services import blocks  # noqa: E402
from app.customer_waf.services import crypto  # noqa: E402
from app.customer_waf.services import customer_waf as svc  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402

TOKEN = "wafst_" + "B" * 43
REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.fixture(autouse=True)
def waf_key(monkeypatch):
    monkeypatch.setenv(crypto.KEY_ENV_VAR, Fernet.generate_key().decode())


def _row():
    return CustomerWafInstance(
        id=3,
        customer_code="ACME",
        name="prod",
        api_url="https://waf:8443",
        service_token_encrypted=crypto.encrypt_token(TOKEN),
        token_prefix=crypto.display_prefix(TOKEN),
        verify_tls=True,
        enabled=True,
    )


def _threat_intel_rule(ip, rule_id=9500000, enabled=True):
    return {
        "id": str(uuid.uuid4()),
        "rule_id": rule_id,
        "name": f"Threat Intel Block: {ip}",
        "description": "",
        "field": "REMOTE_ADDR",
        "operator": "@ipMatch",
        "value": ip,
        "action": "deny",
        "phase": 1,
        "is_enabled": enabled,
        "conf_text": f"SecRule REMOTE_ADDR \"@ipMatch {ip}\" \"id:{rule_id},phase:1,deny,status:403,log,msg:'Threat Intel Block: {ip}',tag:'threat-intel'\"",
    }


def _copilot_rule(target, rule_id=9500100, enabled=True):
    text = blocks.build_rule_text(blocks.normalize_target(target)).replace("id:AUTO", f"id:{rule_id}")
    return {
        "id": str(uuid.uuid4()),
        "rule_id": rule_id,
        "name": f"CoPilot block: {target}",
        "description": "old reason | by alice via CoPilot",
        "field": "REMOTE_ADDR",
        "operator": "@ipMatch",
        "value": target,
        "action": "deny,status:403,log,tag:'copilot-block'",
        "phase": 1,
        "is_enabled": enabled,
        "conf_text": text,
    }


# Pre-cbc7b9b rule seen on a real WAF: stored action says deny, the text is a bypass.
STALE_BYPASS = {
    "id": str(uuid.uuid4()),
    "rule_id": 9500004,
    "name": "Bypass for scanner",
    "description": "",
    "field": "REMOTE_ADDR",
    "operator": "@ipMatch",
    "value": "198.51.100.10",
    "action": "deny,status:403",
    "phase": 1,
    "is_enabled": True,
    "conf_text": 'SecRule REMOTE_ADDR "@ipMatch 198.51.100.10" "id:9500004,phase:1,pass,nolog,ctl:ruleEngine=Off"',
}


class FakeWaf:
    """Just enough of /api/v1/rules/custom, with the real WAF's parse-on-create behaviour."""

    def __init__(self, rules):
        self.rules = [dict(r) for r in rules]
        self.writes = []
        self.next_id = 9500200

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == "/api/v1/rules/custom":
            return httpx.Response(200, json=self.rules)
        body = json.loads(request.content)
        self.writes.append((request.method, path, body))
        if request.method == "POST" and path == "/api/v1/rules/custom":
            text = body["raw_conf_text"]
            m = re.match(r'SecRule (\S+) "(@\w+) ([^"]*)"', text)
            rule = {
                "id": str(uuid.uuid4()),
                "rule_id": self.next_id,
                "name": body["name"],
                "description": body.get("description", ""),
                "field": m.group(1),
                "operator": m.group(2),
                "value": m.group(3),
                "action": "deny,status:403,log,tag:'copilot-block'",
                "phase": 1,
                "is_enabled": True,
                "conf_text": text.replace("id:AUTO", f"id:{self.next_id}"),
            }
            self.next_id += 1
            self.rules.append(rule)
            return httpx.Response(201, json=rule)
        if request.method == "PUT" and path.startswith("/api/v1/rules/custom/"):
            rule = next(r for r in self.rules if r["id"] == path.rsplit("/", 1)[1])
            rule.update({k: v for k, v in body.items() if k in ("is_enabled", "description")})
            return httpx.Response(200, json=rule)
        return httpx.Response(404, json={"detail": "not found"})


def _install(monkeypatch, fake):
    def _client(**kwargs):
        kwargs.pop("verify", None)
        return REAL_ASYNC_CLIENT(transport=httpx.MockTransport(fake.handler), **kwargs)

    monkeypatch.setattr(transport.httpx, "AsyncClient", _client)
    return fake


# ── target validation / rule text ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        ("203.0.113.7", "203.0.113.7"),
        (" 203.0.113.7 ", "203.0.113.7"),
        ("203.0.113.7/32", "203.0.113.7"),
        ("203.0.113.9/24", "203.0.113.0/24"),  # host bits cleared
        ("10.20.0.0/16", "10.20.0.0/16"),  # the broadest IPv4 allowed
        ("2001:db8::1", "2001:db8::1"),
        ("2001:db8:abcd::/48", "2001:db8:abcd::/48"),
    ],
)
def test_valid_targets_normalise(value, shown):
    assert blocks.display(blocks.normalize_target(value)) == shown


@pytest.mark.parametrize(
    "value",
    [
        '203.0.113.7" "id:1,phase:1,pass,nolog,ctl:ruleEngine=Off',
        "203.0.113.7,pass",
        "203.0.113.7 ctl:ruleEngine=Off",
        "203.0.113.7\nSecRuleEngine Off",
        "203.0.113.7'",
        "example.com",
        "",
    ],
)
def test_injection_and_junk_rejected_before_any_rule_text(value):
    with pytest.raises(blocks.BlockTargetError):
        blocks.normalize_target(value)


@pytest.mark.parametrize("value", ["0.0.0.0/0", "10.0.0.0/8", "203.0.0.0/15", "::/0", "2001:db8::/47"])
def test_over_broad_ranges_refused(value):
    with pytest.raises(blocks.BlockTargetError, match="too broad"):
        blocks.normalize_target(value)


def test_rule_text_is_exactly_the_documented_shape():
    assert blocks.build_rule_text(blocks.normalize_target("203.0.113.7")) == (
        'SecRule REMOTE_ADDR "@ipMatch 203.0.113.7" '
        "\"id:AUTO,phase:1,deny,status:403,log,msg:'CoPilot block: 203.0.113.7',tag:'copilot-block'\""
    )


def test_reason_never_reaches_rule_text_only_description():
    reason = "brute force'\" ctl:ruleEngine=Off\n  from   botnet"
    description = blocks.build_description(reason, "alice", 42, None)
    assert description == "brute force'\" ctl:ruleEngine=Off from botnet | by alice via CoPilot | alert #42"
    assert "brute" not in blocks.build_rule_text(blocks.normalize_target("203.0.113.7"))


def test_warnings():
    assert blocks.target_warnings(blocks.normalize_target("203.0.113.7")) != []  # TEST-NET is reserved
    assert blocks.target_warnings(blocks.normalize_target("8.8.8.8")) == []
    assert "load balancer" in blocks.target_warnings(blocks.normalize_target("10.1.2.3"))[0]
    assert "loopback" in blocks.target_warnings(blocks.normalize_target("127.0.0.1"))[0]


# ── classifying the WAF's rules ────────────────────────────────────────────


def test_rule_classification():
    ti = _threat_intel_rule("198.51.100.1")
    mine = _copilot_rule("203.0.113.7")
    listed = _threat_intel_rule("198.51.100.2, 198.51.100.3")
    copilot, other = blocks.ip_block_rules([ti, mine, STALE_BYPASS, listed])
    assert copilot == [mine]
    assert other == [ti, listed]
    assert len(blocks.rule_networks(listed)) == 2


def test_stale_action_bypass_is_not_a_block():
    """Its stored action says deny; its text is ctl:ruleEngine=Off. Trust the text."""
    assert blocks.rule_networks(STALE_BYPASS) == []


def test_chained_rule_is_not_a_block():
    chained = {**_threat_intel_rule("198.51.100.1"), "conf_text": 'SecRule REMOTE_ADDR "@ipMatch 198.51.100.1" "id:1,phase:1,deny,chain"'}
    assert blocks.rule_networks(chained) == []


# ── block ──────────────────────────────────────────────────────────────────


def _block(monkeypatch, rules, target):
    fake = _install(monkeypatch, FakeWaf(rules))
    action, rule = asyncio.run(blocks.block(_row(), blocks.normalize_target(target), "reason | by alice via CoPilot"))
    return fake, action, rule


def test_new_target_creates_one_rule_with_built_text(monkeypatch):
    fake, action, rule = _block(monkeypatch, [_threat_intel_rule("198.51.100.1")], "203.0.113.7")
    assert action == "created"
    assert len(fake.writes) == 1
    method, path, body = fake.writes[0]
    assert (method, path) == ("POST", "/api/v1/rules/custom")
    assert body["raw_conf_text"] == blocks.build_rule_text(blocks.normalize_target("203.0.113.7"))
    assert body["name"] == "CoPilot block: 203.0.113.7"
    assert blocks.is_copilot_rule(rule)


def test_already_blocked_by_copilot_writes_nothing(monkeypatch):
    fake, action, _ = _block(monkeypatch, [_copilot_rule("203.0.113.7")], "203.0.113.7/32")
    assert action == "already_blocked" and fake.writes == []


def test_blocked_by_waf_threat_intel_rule_writes_nothing(monkeypatch):
    ti = _threat_intel_rule("203.0.113.7")
    fake, action, rule = _block(monkeypatch, [ti], "203.0.113.7")
    assert action == "blocked_by_waf_rule" and fake.writes == [] and rule["id"] == ti["id"]


def test_covered_by_broader_copilot_range_writes_nothing(monkeypatch):
    fake, action, _ = _block(monkeypatch, [_copilot_rule("203.0.113.0/24")], "203.0.113.7")
    assert action == "already_blocked" and fake.writes == []


def test_disabled_waf_rule_does_not_count(monkeypatch):
    fake, action, _ = _block(monkeypatch, [_threat_intel_rule("203.0.113.7", enabled=False)], "203.0.113.7")
    assert action == "created"


def test_reblock_reenables_copilot_rule_instead_of_duplicating(monkeypatch):
    old = _copilot_rule("203.0.113.7", enabled=False)
    fake, action, rule = _block(monkeypatch, [old], "203.0.113.7")
    assert action == "reenabled"
    assert fake.writes == [
        ("PUT", f"/api/v1/rules/custom/{old['id']}", {"is_enabled": True, "description": "reason | by alice via CoPilot"}),
    ]
    assert rule["is_enabled"] is True


def test_stale_bypass_for_same_ip_is_not_mistaken_for_a_block(monkeypatch):
    fake, action, _ = _block(monkeypatch, [STALE_BYPASS], "198.51.100.10")
    assert action == "created"


def test_viewer_token_gets_readable_insufficient_role(monkeypatch):
    class ViewerWaf(FakeWaf):
        def handler(self, request):
            if request.method != "GET":
                return httpx.Response(403, json={"detail": "Permission denied: 'rules:write' required"})
            return super().handler(request)

    _install(monkeypatch, ViewerWaf([]))
    with pytest.raises(transport.WafRequestError) as exc:
        asyncio.run(blocks.block(_row(), blocks.normalize_target("203.0.113.7"), "r"))
    assert exc.value.reason == "insufficient_role" and exc.value.status_code == 502
    assert "rules:write" in exc.value.detail


# ── unblock ────────────────────────────────────────────────────────────────


def test_unblock_disables_copilot_rule(monkeypatch):
    mine = _copilot_rule("203.0.113.7")
    fake = _install(monkeypatch, FakeWaf([mine]))
    action, rules, waf_rule = asyncio.run(blocks.unblock(_row(), blocks.normalize_target("203.0.113.7")))
    assert action == "unblocked" and waf_rule is None
    assert fake.writes == [("PUT", f"/api/v1/rules/custom/{mine['id']}", {"is_enabled": False})]
    assert all(m != "DELETE" for m, _, _ in fake.writes)


def test_unblock_never_touches_waf_owned_rule(monkeypatch):
    ti = _threat_intel_rule("203.0.113.7")
    fake = _install(monkeypatch, FakeWaf([ti]))
    action, rules, waf_rule = asyncio.run(blocks.unblock(_row(), blocks.normalize_target("203.0.113.7")))
    assert action == "already_unblocked" and rules == [] and waf_rule["id"] == ti["id"]
    assert fake.writes == []


def test_unblock_reports_waf_rule_still_blocking(monkeypatch):
    fake = _install(monkeypatch, FakeWaf([_copilot_rule("203.0.113.7"), _threat_intel_rule("203.0.113.0/24")]))
    action, _, waf_rule = asyncio.run(blocks.unblock(_row(), blocks.normalize_target("203.0.113.7")))
    assert action == "unblocked" and waf_rule is not None
    assert len(fake.writes) == 1


def test_unblock_is_exact_not_covering(monkeypatch):
    """Unblocking one IP must not lift CoPilot's block of the whole range around it."""
    rng = _copilot_rule("203.0.113.0/24")
    fake = _install(monkeypatch, FakeWaf([rng]))
    action, rules, _ = asyncio.run(blocks.unblock(_row(), blocks.normalize_target("203.0.113.7")))
    assert action == "already_unblocked" and rules == [] and fake.writes == []


# ── provenance ─────────────────────────────────────────────────────────────


def _provenance(alert_customer=None, case_customer=None):
    alert = SimpleNamespace(customer_code=alert_customer) if alert_customer else None
    case = SimpleNamespace(customer_code=case_customer) if case_customer else None
    with patch("app.incidents.services.db_operations.get_alert_by_id", AsyncMock(return_value=alert)), patch(
        "app.incidents.services.db_operations.get_case_by_id",
        AsyncMock(return_value=case),
    ), patch("app.middleware.customer_access.enforce_owned_object_access", AsyncMock()) as enforce:
        asyncio.run(
            svc.verify_block_provenance(
                AsyncMock(),
                SimpleNamespace(id=1),
                "ACME",
                1 if alert_customer else None,
                2 if case_customer else None,
            ),
        )
        return enforce


def test_alert_from_same_customer_is_accepted():
    enforce = _provenance(alert_customer="ACME")
    enforce.assert_awaited_once()


@pytest.mark.parametrize("kwargs", [{"alert_customer": "OTHER"}, {"case_customer": "OTHER"}])
def test_alert_or_case_from_another_customer_is_refused(kwargs):
    with pytest.raises(HTTPException) as exc:
        _provenance(**kwargs)
    assert exc.value.status_code == 400
