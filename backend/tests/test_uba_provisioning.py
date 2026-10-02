"""Setting SOCFortress UBA up for a customer (connectors/uba/services/provision.py).

**The traps this file exists for:**

- The customer is registered with UBA *before* Graylog routes anything to it:
  events reaching UBA first would be processed without the history replay.
- Feed streams live in their source stream's index set (else every routed message
  is indexed twice), and pipelines are connected with ``to_pipeline`` (``to_stream``
  would replace the source stream's own Wazuh / Office365 processing pipelines).
- Running it again repairs, never duplicates.
- Without UBA's GELF endpoints nothing is created.

Graylog and UBA are fakes; no network, no database.

Run with: cd backend && python -m pytest tests/test_uba_provisioning.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.uba.schema.provision import UbaProvisionRequest  # noqa: E402
from app.connectors.uba.schema.provision import UbaSourceStream  # noqa: E402
from app.connectors.uba.services import provision  # noqa: E402
from app.connectors.uba.utils.universal import UbaRequestError  # noqa: E402

ORG = "aaaaaaaa-0000-4000-8000-000000000001"
NAMES = {
    "sources": {"WAZUH": "wazuh", "O365": "office365"},
    "feed_stream": "UBA FEED - {source} - {tenant}",
    "routing_pipeline": "UBA ROUTING - {source} - {tenant}",
    "pipeline_stage": 10,
    "output": "UBA GELF - {tenant}",
    "alerts_input": "UBA ALERTS",
    "alerts_stream": "UBA ALERTS - {tenant}",
    "alerts_stream_rules": {"syslog_type": "uba", "agent_labels_customer": "{tenant}"},
}


class FakeGraylog:
    def __init__(self, prefixes):
        self.index_sets = {k: {"index_prefix": v} for k, v in prefixes.items()}
        self.streams, self.rules, self.pipelines, self.outputs, self.inputs = {}, {}, {}, {}, {}
        self.connections, self.attached, self.calls = {}, {}, []
        self.next_id = 0

    def _id(self):
        self.next_id += 1
        return f"id{self.next_id}"

    async def get(self, endpoint, params=None):
        self.calls.append(("GET", endpoint))
        if endpoint.startswith("/api/system/indices/index_sets/"):
            return {"data": self.index_sets[endpoint.rsplit("/", 1)[1]]}
        data = {
            "/api/streams": {"streams": list(self.streams.values())},
            "/api/system/pipelines/rule": list(self.rules.values()),
            "/api/system/pipelines/pipeline": list(self.pipelines.values()),
            "/api/system/outputs": {"outputs": list(self.outputs.values())},
            "/api/system/inputs": {"inputs": list(self.inputs.values())},
        }[endpoint]
        return {"data": data}

    async def post(self, endpoint, data=None):
        self.calls.append(("POST", endpoint))
        if endpoint == "/api/system/pipelines/rule":
            i = self._id()
            self.rules[i] = {"id": i, **data}
            return {"data": self.rules[i]}
        if endpoint == "/api/system/pipelines/pipeline":
            i = self._id()
            self.pipelines[i] = {"id": i, **data}
            return {"data": self.pipelines[i]}
        if endpoint == "/api/system/pipelines/connections/to_pipeline":
            self.connections[data["pipeline_id"]] = data["stream_ids"]
            return {"data": None}
        if endpoint == "/api/system/outputs":
            i = self._id()
            self.outputs[i] = {"id": i, "title": data["title"], "configuration": data["configuration"]}
            return {"data": {"id": i}}
        if endpoint == "/api/system/inputs":
            i = self._id()
            self.inputs[i] = {"id": i, "title": data["title"], "attributes": data["configuration"]}
            return {"data": {"id": i}}
        if endpoint.endswith("/outputs"):
            self.attached.setdefault(endpoint.split("/")[3], set()).update(data["outputs"])
            return {"data": None}
        if endpoint.endswith("/resume"):
            return {"data": None}
        raise AssertionError(endpoint)

    async def create_entity(self, endpoint, entity, share_request=None, connector_name=None):
        self.calls.append(("POST", endpoint))
        i = self._id()
        self.streams[i] = {"id": i, **entity}
        return {"data": {"stream_id": i}}

    async def put(self, endpoint, data=None):
        self.calls.append(("PUT", endpoint))
        i = endpoint.rsplit("/", 1)[1]
        if "/rule/" in endpoint:
            self.rules[i].update(data)
        elif "/pipeline/" in endpoint:
            self.pipelines[i].update(data)
        elif "/outputs/" in endpoint:
            self.outputs[i].update(title=data["title"], configuration=data["configuration"])
        return {"data": None}


class FakeUba:
    def __init__(self, feed_host="127.0.0.1", log=None):
        self.info = {
            "graylog": NAMES,
            "feed_output": {"host": feed_host, "port": 12203} if feed_host else None,
            "alerts_input": {"bind_address": "172.17.0.1", "port": 12204},
            "wazuh_rules": [{"filename": "0950-uba_windows_account_rules.xml", "content": "<group/>"}],
        }
        self.calls = []
        self.log = log if log is not None else []  # shared with FakeGraylog.calls: the order of writes

    async def __call__(self, method, path, *, params=None, json=None, **_):
        self.calls.append((method, path, json))
        self.log.append(("UBA " + method, path))
        if path == "/v1/provisioning":
            return self.info
        if path.endswith("/graylog-rules"):
            source = "OFFICE365" if "office365" in path else "WINDOWS AUTH"
            return {
                "rules": [f'rule "{params["stream"]} - {source}"\nwhen true\nthen\n  route_to_stream(name: "{params["stream"]}");\nend'],
            }
        if method == "PUT" and path.startswith("/v1/tenants/"):
            return {"tenant": path.rsplit("/", 1)[1], "status": "pending", "active": True}
        raise AssertionError(path)


def _run(graylog, uba, request=None, sources=None):
    sources = sources or {
        "WAZUH": [UbaSourceStream(stream_id="wazuh-src", index_set_id="wazuh-set")],
        "O365": [
            UbaSourceStream(stream_id="o365-a", index_set_id="o365-set"),
            UbaSourceStream(stream_id="o365-b", index_set_id="o365-set", instance="second"),
        ],
    }
    meta = SimpleNamespace(customer_name="Acme Corp", customer_meta_graylog_index="wazuh-set", customer_meta_graylog_stream="wazuh-src")

    async def source_streams(code, session):
        return sources

    async def customer_meta(code, session):
        return meta

    async def tenant_ids(code, session):
        return [ORG]

    with patch.object(provision, "send_get_request", graylog.get), patch.object(provision, "send_post_request", graylog.post), patch.object(
        provision,
        "send_put_request",
        graylog.put,
    ), patch.object(provision, "send_post_request_create_entity", graylog.create_entity), patch.object(
        provision,
        "uba_request",
        uba,
    ), patch.object(
        provision,
        "_source_streams",
        source_streams,
    ), patch.object(
        provision,
        "_customer_meta",
        customer_meta,
    ), patch.object(
        provision,
        "_office365_tenant_ids",
        tenant_ids,
    ):
        return asyncio.run(provision.provision_uba("acme", request or UbaProvisionRequest(), session=None))


def _by_title(objects):
    return {o["title"]: o for o in objects.values()}


def test_a_customer_is_registered_first_then_routed_next_to_its_streams():
    graylog = FakeGraylog({"wazuh-set": "wazuh-acme", "o365-set": "office365-acme"})
    uba = FakeUba(log=graylog.calls)
    out = _run(graylog, uba)

    [register] = [c for c in uba.calls if c[0] == "PUT"]
    assert register[1] == "/v1/tenants/acme"
    assert register[2] == {
        "name": "Acme Corp",
        "active": True,
        "bootstrap_days": 14,
        "office365_organization_ids": [ORG],
        "indices": None,  # wazuh-acme_* / office365-acme_*: UBA's defaults
    }
    writes = [c for c in graylog.calls if c[0] in ("POST", "PUT", "UBA PUT")]
    assert writes[0] == ("UBA PUT", "/v1/tenants/acme") and out.steps[0].step == "UBA tenant"

    streams = _by_title(graylog.streams)
    assert streams["UBA FEED - WAZUH - acme"]["index_set_id"] == "wazuh-set"
    assert streams["UBA FEED - O365 - acme"]["index_set_id"] == "o365-set"
    pipelines = _by_title(graylog.pipelines)
    assert graylog.connections[pipelines["UBA ROUTING - WAZUH - acme"]["id"]] == ["wazuh-src"]
    assert graylog.connections[pipelines["UBA ROUTING - O365 - acme"]["id"]] == ["o365-a", "o365-b"]
    assert 'stage 10 match either\nrule "UBA FEED - O365 - acme - OFFICE365"' in pipelines["UBA ROUTING - O365 - acme"]["source"]
    assert not any(c[1].endswith("/connections/to_stream") for c in graylog.calls)  # would drop the source's pipelines

    [output] = graylog.outputs.values()
    assert output["title"] == "UBA GELF - acme" and (output["configuration"]["hostname"], output["configuration"]["port"]) == (
        "127.0.0.1",
        12203,
    )
    feeds = {streams["UBA FEED - WAZUH - acme"]["id"], streams["UBA FEED - O365 - acme"]["id"]}
    assert {s for s, outs in graylog.attached.items() if output["id"] in outs} == feeds

    [alerts_input] = graylog.inputs.values()
    assert alerts_input["title"] == "UBA ALERTS" and alerts_input["attributes"]["bind_address"] == "172.17.0.1"
    alerts = streams["UBA ALERTS - acme"]
    assert alerts["index_set_id"] == "wazuh-set"
    assert {(r["field"], r["value"]) for r in alerts["rules"]} == {("syslog_type", "uba"), ("agent_labels_customer", "acme")}
    assert alerts["id"] not in graylog.connections.values()  # loop guard: no pipeline reads UBA's own alerts
    assert out.steps[-1].step == "Wazuh rules" and out.steps[-1].status == "skipped"


def test_running_it_again_repairs_and_never_duplicates():
    graylog = FakeGraylog({"wazuh-set": "wazuh-acme", "o365-set": "office365-acme"})
    _run(graylog, FakeUba())
    counts = (len(graylog.streams), len(graylog.rules), len(graylog.pipelines), len(graylog.outputs), len(graylog.inputs))
    out = _run(graylog, FakeUba(feed_host="10.0.0.5"))  # UBA moved
    assert (len(graylog.streams), len(graylog.rules), len(graylog.pipelines), len(graylog.outputs), len(graylog.inputs)) == counts
    statuses = {s.step: s.status for s in out.steps}
    assert statuses["stream UBA FEED - WAZUH - acme"] == "exists" and statuses["rule UBA FEED - WAZUH - acme - WINDOWS AUTH"] == "exists"
    assert statuses["output UBA GELF - acme"] == "attached"
    assert [s.status for s in out.steps if s.step == "output UBA GELF - acme"][0] == "updated"
    [output] = graylog.outputs.values()
    assert output["configuration"]["hostname"] == "10.0.0.5"


def test_index_sets_that_differ_from_ubas_defaults_are_registered():
    graylog = FakeGraylog({"wazuh-set": "acme-wazuh", "o365-set": "office365-acme"})
    uba = FakeUba()
    _run(graylog, uba)
    [register] = [c for c in uba.calls if c[0] == "PUT"]
    assert register[2]["indices"] == {"wazuh": "acme-wazuh_*"}


def test_without_ubas_gelf_endpoints_nothing_is_created():
    graylog = FakeGraylog({"wazuh-set": "wazuh-acme", "o365-set": "office365-acme"})
    uba = FakeUba(feed_host=None)
    with pytest.raises(UbaRequestError) as e:
        _run(graylog, uba)
    assert e.value.status_code == 409 and "UBA_PROVISION_FEED_HOST" in e.value.detail
    assert not [c for c in uba.calls if c[0] == "PUT"] and not [c for c in graylog.calls if c[0] != "GET"]


def test_a_feed_stream_in_another_index_set_is_refused():
    graylog = FakeGraylog({"wazuh-set": "wazuh-acme", "o365-set": "office365-acme"})
    graylog.streams["x"] = {"id": "x", "title": "UBA FEED - WAZUH - acme", "index_set_id": "elsewhere"}
    with pytest.raises(HTTPException) as e:
        _run(graylog, FakeUba())
    assert e.value.status_code == 409 and "indexed twice" in e.value.detail


def test_wazuh_rules_are_uploaded_and_the_manager_restarted_only_on_request():
    graylog = FakeGraylog({"wazuh-set": "wazuh-acme"})
    uploads, restarts = [], []

    async def upload(filename, content, overwrite=False, **_):
        uploads.append((filename, content, overwrite))

    async def restart(endpoint, data=None, **_):
        restarts.append(endpoint)

    with patch("app.connectors.wazuh_manager.services.rules.update_wazuh_rule_file", upload), patch(
        "app.connectors.wazuh_manager.utils.universal.send_put_request",
        restart,
    ):
        out = _run(
            graylog,
            FakeUba(),
            UbaProvisionRequest(bootstrap_days=7, deploy_wazuh_rules=True),
            sources={"WAZUH": [UbaSourceStream(stream_id="wazuh-src", index_set_id="wazuh-set")]},
        )
    assert uploads == [("0950-uba_windows_account_rules.xml", b"<group/>", True)] and restarts == ["/manager/restart"]
    assert [s.status for s in out.steps[-2:]] == ["uploaded", "restarted"]


def test_provisioning_routes_are_admin_only():
    from app.connectors.uba.routes import uba as routes

    by_path = {(r.path, tuple(sorted(r.methods))): r for r in routes.uba_router.routes}
    assert by_path[("/{customer_code}/provision", ("POST",))].dependencies == routes._ADMIN
    assert by_path[("/{customer_code}/provisioning", ("GET",))].dependencies == routes._ADMIN
