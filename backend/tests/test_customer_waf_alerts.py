"""WAF alerts (#1169 phase 4b): event definitions, the threshold webhook, and the 'waf' source.

**What this file pins:**

- Both definitions are titled exactly as the Monitoring Alerts route derives from the
  catalog name (``alert_name.replace("_", " ")``) — otherwise its duplicate check never fires.
- BLOCKED rides the per-event collector: ``COPILOT_ALERT_ID=NONE``, ``ALERT_ID=${source._id}``,
  customer from ``syslog_customer``.
- BRUTE FORCE is a real threshold: ``count() >= 30`` grouped by customer + IP over 5 min,
  delivered to the threshold route with the ``graylog`` header — and it must NOT carry
  ``COPILOT_ALERT_ID`` (the collector would double-process it). Its field spec is exactly
  the four fields the threshold route requires.
- Missing ALERT_FORWARDING_IP / GRAYLOG_API_HEADER_VALUE fails before anything is created.
- The rule-message extractor yields a usable alert title from the raw WAF payload.

No network, no database.
"""

import asyncio
import os
import re
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.active_response.schema.graylog import GraylogThresholdEventFields  # noqa: E402
from app.customer_waf.services import alerts  # noqa: E402
from app.customer_waf.services.forwarding import extractor_payloads  # noqa: E402
from app.integrations.monitoring_alert.routes.provision import (  # noqa: E402
    PROVISION_FUNCTIONS,
)
from app.integrations.monitoring_alert.schema.provision import (  # noqa: E402
    AvailableMonitoringAlerts,
)

PAYLOAD = (
    '{"source":"socfortress-waf","event_id":"e1","timestamp":"2026-09-23T21:19:53.243267+00:00","transaction_id":"t1",'
    '"client_ip":"203.0.113.9","method":"GET","uri":"/?id=1","host":"crm.example.com","action":"blocked",'
    '"rule_id":"942100","severity":"CRITICAL","anomaly_score":5,'
    '"matched_rules":[{"id":"942100","msg":"SQL Injection Attack Detected via libinjection"},{"id":"949110","msg":"Inbound Anomaly"}]}'
)


# ── catalog wiring ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "title"),
    [("SOCFORTRESS_WAF_BLOCKED", alerts.BLOCKED_TITLE), ("SOCFORTRESS_WAF_BRUTE_FORCE", alerts.BRUTE_FORCE_TITLE)],
)
def test_catalog_entry_title_matches_what_the_route_checks(name, title):
    assert name in AvailableMonitoringAlerts.__members__
    assert name in PROVISION_FUNCTIONS
    # provision_monitoring_alert_route checks existence by alert_name.replace("_", " ")
    assert name.replace("_", " ") == title


# ── BLOCKED (per event) ────────────────────────────────────────────────────


def test_blocked_definition_rides_the_per_event_collector():
    d = alerts.blocked_definition(execute_every_ms=60000, search_within_ms=60000)
    assert d["config"]["query"] == "syslog_type:waf AND waf_action:blocked"
    assert d["config"]["series"] == [] and d["config"]["group_by"] == [] and d["config"]["conditions"] == {"expression": None}
    spec = {k: v["providers"][0]["template"] for k, v in d["field_spec"].items()}
    assert spec["COPILOT_ALERT_ID"] == "NONE"
    assert spec["ALERT_ID"] == "${source._id}"
    assert spec["CUSTOMER_CODE"] == "${source.syslog_customer}"
    assert d["notifications"] == []


# ── BRUTE FORCE (threshold) ────────────────────────────────────────────────


def test_brute_force_is_a_real_threshold():
    d = alerts.brute_force_definition("notif-1")
    cfg = d["config"]
    assert cfg["group_by"] == ["syslog_customer", "waf_client_ip"]
    assert cfg["series"] == [{"id": "waf-blocks-count", "type": "count", "field": None}]
    cond = cfg["conditions"]["expression"]
    assert (cond["expr"], cond["left"]["ref"], cond["right"]) == (">=", "waf-blocks-count", {"expr": "number", "value": 30})
    assert cfg["search_within_ms"] == 300000 and cfg["execute_every_ms"] == 60000
    assert d["notifications"] == [{"notification_id": "notif-1", "notification_parameters": None}]


def test_brute_force_fields_are_exactly_what_the_threshold_route_needs():
    d = alerts.brute_force_definition("n")
    assert set(d["field_spec"]) == {"CUSTOMER_CODE", "SOURCE", "ALERT_DESCRIPTION", "ASSET_NAME"}
    assert "COPILOT_ALERT_ID" not in d["field_spec"]  # would be double-processed by the collector
    # ...and each is a field the route's schema actually reads.
    assert set(d["field_spec"]) <= set(GraylogThresholdEventFields.model_fields)
    assert d["field_spec"]["SOURCE"]["providers"][0]["template"] == "waf"  # threshold index fallback -> waf-*


def test_notification_sends_the_graylog_header():
    cfg = alerts.notification_payload("http://10.0.0.5:5000/api/incidents/alerts/create/threshold", "s3cret")["config"]
    assert cfg["type"] == "http-notification-v1" and cfg["api_key_as_header"] is True
    assert cfg["api_key"] == "graylog" and cfg["api_secret"] == {"set_value": "s3cret"}


@pytest.mark.parametrize(("ip", "header"), [("", "x"), ("0.0.0.0", "x"), ("10.0.0.5", "")])
def test_missing_webhook_settings_fail_before_anything_is_created(monkeypatch, ip, header):
    monkeypatch.setenv("ALERT_FORWARDING_IP", ip)
    monkeypatch.setenv("GRAYLOG_API_HEADER_VALUE", header)
    created = AsyncMock()
    monkeypatch.setattr(alerts, "send_post_request_create_entity", created)
    monkeypatch.setattr(alerts, "send_get_request", AsyncMock(return_value={"data": {"notifications": []}}))
    monkeypatch.setattr(alerts, "ensure_waf_alert_source", AsyncMock())
    with pytest.raises(Exception) as exc:
        asyncio.run(alerts.provision_brute_force_alert())
    assert getattr(exc.value, "status_code", None) == 400
    created.assert_not_awaited()
    alerts.ensure_waf_alert_source.assert_not_awaited()


def _graylog(monkeypatch, notifications=(), allowlist=None):
    calls = {"created": [], "put": []}

    async def get(endpoint, params=None, connector_name=None):
        if endpoint == "/api/events/notifications":
            return {"data": {"notifications": list(notifications)}}
        if endpoint == "/api/system/urlallowlist":
            return {"data": allowlist or {"entries": [], "disabled": False}}
        raise AssertionError(endpoint)

    async def create(endpoint, entity, share_request=None, connector_name=None):
        calls["created"].append((endpoint, entity))
        return {"data": {"id": "new-notif"}}

    async def put(endpoint, data=None, connector_name=None):
        calls["put"].append((endpoint, data))
        return {"success": True}

    monkeypatch.setattr(alerts, "send_get_request", get)
    monkeypatch.setattr(alerts, "send_post_request_create_entity", create)
    monkeypatch.setattr(alerts, "send_put_request", put)
    monkeypatch.setattr(alerts, "ensure_waf_alert_source", AsyncMock())
    monkeypatch.setenv("ALERT_FORWARDING_IP", "10.0.0.5")
    monkeypatch.setenv("GRAYLOG_API_HEADER_VALUE", "s3cret")
    return calls


def test_brute_force_creates_allowlisted_notification_then_definition(monkeypatch):
    calls = _graylog(monkeypatch)
    asyncio.run(alerts.provision_brute_force_alert())
    url = "http://10.0.0.5:5000/api/incidents/alerts/create/threshold"
    assert calls["put"][0][0] == "/api/system/urlallowlist"
    assert any(e["value"] == url for e in calls["put"][0][1]["entries"])
    (n_endpoint, n_entity), (d_endpoint, d_entity) = calls["created"]
    assert n_endpoint == "/api/events/notifications" and n_entity["config"]["url"] == url
    assert d_endpoint == "/api/events/definitions" and d_entity["notifications"][0]["notification_id"] == "new-notif"


def test_existing_notification_and_allowlist_entry_are_reused(monkeypatch):
    calls = _graylog(monkeypatch, notifications=[{"id": "existing", "title": alerts.THRESHOLD_NOTIFICATION_TITLE}])
    asyncio.run(alerts.provision_brute_force_alert())
    assert calls["put"] == []
    [(endpoint, entity)] = calls["created"]
    assert endpoint == "/api/events/definitions" and entity["notifications"][0]["notification_id"] == "existing"


# ── the 'waf' alert source ─────────────────────────────────────────────────


def test_waf_source_registration(monkeypatch):
    added = []

    def rec(kind):
        async def _add(source, name, session):
            added.append((kind, source, name))

        return _add

    for kind in ("field", "asset", "timefield", "alert_title", "ioc"):
        monkeypatch.setattr(alerts, f"add_{kind}_name", rec(kind))

    class _Session:
        async def __aenter__(self):
            self.commit = AsyncMock()
            return self

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(alerts, "get_db_session", lambda: _Session())
    asyncio.run(alerts.ensure_waf_alert_source())
    assert all(source == "waf" for _, source, _ in added)
    assert ("asset", "waf", "waf_host") in added and ("ioc", "waf", "waf_client_ip") in added
    assert ("alert_title", "waf", "waf_rule_msg") in added and ("timefield", "waf", "timestamp") in added
    assert {n for k, _, n in added if k == "field"} >= {"waf_client_ip", "waf_uri", "waf_rule_msg", "waf_action"}


# ── rule-message extractor ─────────────────────────────────────────────────


def _rule_msg_extractor():
    return next(e for e in extractor_payloads() if e["target_field"] == "waf_rule_msg")


def test_rule_message_extractor_titles_the_alert():
    ex = _rule_msg_extractor()
    assert ex["source_field"] == "waf_json" and ex["order"] > 1  # after the JSON extractor
    assert ex["condition_value"] in PAYLOAD
    m = re.search(ex["extractor_config"]["regex_value"], PAYLOAD)
    assert m and m.group(1) == "SQL Injection Attack Detected via libinjection"


def test_rule_message_extractor_handles_escaped_quotes_and_no_match():
    regex = _rule_msg_extractor()["extractor_config"]["regex_value"]
    escaped = '"matched_rules":[{"id":"1","msg":"Found \\"union select\\" in ARGS"}]'
    assert re.search(regex, escaped).group(1) == 'Found \\"union select\\" in ARGS'
    assert re.search(regex, '"matched_rules":[]') is None


# ── pinned to the default Graylog ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("alert_name", "requested", "expected"),
    [
        ("SOCFORTRESS_WAF_BLOCKED", "network", "WAZUH"),
        ("SOCFORTRESS_WAF_BRUTE_FORCE", "network", "WAZUH"),
        ("SOCFORTRESS_WAF_BLOCKED", "default", "WAZUH"),
        ("FORTINET_SYSTEM", "network", "NETWORK"),  # everything else still honours the request
    ],
)
def test_waf_alerts_always_go_to_the_default_graylog(monkeypatch, alert_name, requested, expected):
    """The duplicate check and the creation both run under the context the route sets first."""
    import app.integrations.monitoring_alert.routes.provision as route
    from app.integrations.monitoring_alert.schema.provision import GraylogInstance
    from app.integrations.monitoring_alert.schema.provision import (
        ProvisionMonitoringAlertRequest,
    )

    contexts = []
    monkeypatch.setattr(route, "set_graylog_context", lambda ctx: contexts.append(ctx.name))
    monkeypatch.setattr(route, "clear_graylog_context", lambda: None)
    monkeypatch.setattr(route, "check_if_event_definition_exists", AsyncMock(return_value=False))
    monkeypatch.setitem(route.PROVISION_FUNCTIONS, alert_name, AsyncMock())
    request = ProvisionMonitoringAlertRequest(
        search_within_last=60,
        execute_every=60,
        alert_name=alert_name,
        graylog_instance=GraylogInstance(requested),
    )
    asyncio.run(route.provision_monitoring_alert_route(request))
    assert contexts == [expected]
    route.PROVISION_FUNCTIONS[alert_name].assert_awaited_once()
