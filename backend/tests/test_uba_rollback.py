"""Rolling SOCFortress UBA back for one customer (connectors/uba/services/rollback.py, #1241).

**The traps this file exists for:**

- Routing is disconnected before anything it routes to is removed: a pipeline left
  connected while its feed stream is deleted routes to nothing, and an output removed
  last leaves Graylog sending to an unreachable UBA meanwhile.
- Only what is provably the customer's UBA goes: a pipeline that also runs someone
  else's rule, a stream an event definition reads, another customer's objects, the
  customer's own streams and the shared Wazuh rules are never touched.
- The shared UBA ALERTS input goes only with the last customer's alerts stream.
- The customer's source streams keep every other pipeline, and the event definitions
  are unchanged: the rollback checks both and says so.
- UBA being down does not stop the Graylog side, which is what protects Graylog.
- A failed step leaves what depends on it in place, and running it again finishes.

Graylog, UBA and the database are fakes; no network.

Run with: cd backend && python -m pytest tests/test_uba_rollback.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.uba.services import ownership  # noqa: E402
from app.connectors.uba.services import provision  # noqa: E402
from app.connectors.uba.services import rollback  # noqa: E402
from app.connectors.uba.utils.universal import UbaRequestError  # noqa: E402

GELF_OUTPUT = "org.graylog2.outputs.GelfOutput"
GELF_TCP = "org.graylog2.inputs.gelf.tcp.GELFTCPInput"


def _rule(feed, selector):
    return {
        "title": f"{feed} - {selector}",
        "source": f'rule "{feed} - {selector}"\nwhen true\nthen\n  set_field("uba_feed", "behavior");\n  route_to_stream(name: "{feed}");\nend',
    }


def _pipeline(title, rules):
    return {
        "title": title,
        "source": f'pipeline "{title}"\nstage 10 match either\n' + "".join(f'rule "{r}"\n' for r in rules) + "end",
        "stages": [{"stage": 10, "match": "EITHER", "rules": list(rules)}],
    }


class FakeGraylog:
    """Graylog as UBA setup leaves it for ``codes``, next to each customer's own Wazuh stream and pipeline."""

    def __init__(self, codes=("acme",)):
        self.streams, self.pipelines, self.rules, self.outputs, self.inputs = {}, {}, {}, {}, {}
        self.connections = {}  # stream id -> pipeline ids
        self.definitions = [{"id": "ed1", "title": "WAZUH - HIGH", "state": "ENABLED", "config": {"streams": []}}]
        self.calls, self.fail = [], set()
        self.inputs["in-uba"] = {"id": "in-uba", "title": "UBA ALERTS", "type": GELF_TCP}
        for code in codes:
            self.add_customer(code)

    def add_customer(self, code):
        src = f"wazuh-{code}"
        self.streams[src] = {"id": src, "title": f"{code.upper()} - Wazuh", "rules": [{"field": "agent_labels_customer"}], "outputs": []}
        self.pipelines[f"proc-{code}"] = _pipeline("WAZUH PROCESSING", ["WAZUH ENRICH"])
        self.pipelines[f"proc-{code}"]["id"] = f"proc-{code}"
        feed = f"UBA FEED - WAZUH - {code}"
        self.streams[f"feed-{code}"] = {"id": f"feed-{code}", "title": feed, "rules": [], "outputs": [{"id": f"out-{code}"}]}
        titles = []
        for i, selector in enumerate(("WINDOWS AUTH", "PROCESS")):
            rid = f"rule-{code}-{i}"
            self.rules[rid] = {"id": rid, **_rule(feed, selector)}
            titles.append(self.rules[rid]["title"])
        self.pipelines[f"route-{code}"] = {"id": f"route-{code}", **_pipeline(f"UBA ROUTING - WAZUH - {code}", titles)}
        self.connections[src] = [f"proc-{code}", f"route-{code}"]
        self.outputs[f"out-{code}"] = {
            "id": f"out-{code}",
            "title": f"UBA GELF - {code}",
            "type": GELF_OUTPUT,
            "configuration": {"hostname": "127.0.0.1", "port": 12203},
        }
        self.streams[f"alerts-{code}"] = {
            "id": f"alerts-{code}",
            "title": f"UBA ALERTS - {code}",
            "rules": [{"field": "syslog_type", "value": "uba"}, {"field": "agent_labels_customer", "value": code}],
            "outputs": [],
        }

    def _check(self, method, endpoint):
        self.calls.append((method, endpoint))
        for f in self.fail:
            if f == (method, endpoint):
                raise HTTPException(status_code=500, detail=f"Graylog refused {method} {endpoint}")

    async def get(self, endpoint, params=None, **_):
        self._check("GET", endpoint)
        lists = {
            "/api/streams": {"streams": list(self.streams.values())},
            "/api/system/pipelines/pipeline": list(self.pipelines.values()),
            "/api/system/pipelines/rule": list(self.rules.values()),
            "/api/system/outputs": {"outputs": list(self.outputs.values())},
            "/api/system/inputs": {"inputs": list(self.inputs.values())},
            "/api/system/pipelines/connections": [{"stream_id": s, "pipeline_ids": list(p)} for s, p in self.connections.items()],
            "/api/events/definitions": {"event_definitions": list(self.definitions), "total": len(self.definitions)},
        }
        if endpoint in lists:
            return {"data": lists[endpoint], "success": True}
        for prefix, store in (
            ("/api/streams/", self.streams),
            ("/api/system/pipelines/pipeline/", self.pipelines),
            ("/api/system/pipelines/rule/", self.rules),
            ("/api/system/outputs/", self.outputs),
            ("/api/system/inputs/", self.inputs),
        ):
            if endpoint.startswith(prefix) and endpoint[len(prefix) :] in store:
                return {"data": store[endpoint[len(prefix) :]], "success": True}
        raise HTTPException(status_code=404, detail=f"Failed to send GET request to {endpoint}")

    async def post(self, endpoint, data=None, **_):
        self._check("POST", endpoint)
        assert endpoint == "/api/system/pipelines/connections/to_pipeline", endpoint
        for stream_id, pipelines in self.connections.items():
            if data["pipeline_id"] in pipelines:
                pipelines.remove(data["pipeline_id"])
        for stream_id in data["stream_ids"]:
            self.connections.setdefault(stream_id, []).append(data["pipeline_id"])
        return {"data": None, "success": True}

    async def delete(self, endpoint, **_):
        self._check("DELETE", endpoint)
        parts = endpoint.split("/")
        if endpoint.startswith("/api/streams/") and "/outputs/" in endpoint:
            stream = self.streams.get(parts[3])
            if stream is None:
                raise HTTPException(status_code=404, detail="not found")
            stream["outputs"] = [o for o in stream["outputs"] if o["id"] != parts[5]]
            return {"success": True}
        for prefix, store in (
            ("/api/streams/", self.streams),
            ("/api/system/pipelines/pipeline/", self.pipelines),
            ("/api/system/pipelines/rule/", self.rules),
            ("/api/system/outputs/", self.outputs),
            ("/api/system/inputs/", self.inputs),
        ):
            if endpoint.startswith(prefix):
                key = endpoint[len(prefix) :]
                if key not in store:
                    raise HTTPException(status_code=404, detail="not found")
                if prefix == "/api/system/pipelines/pipeline/" and any(key in p for p in self.connections.values()):
                    raise HTTPException(status_code=404, detail="pipeline is still connected")
                del store[key]
                if prefix == "/api/streams/":
                    self.connections.pop(key, None)
                if prefix == "/api/system/outputs/":
                    for s in self.streams.values():
                        s["outputs"] = [o for o in s["outputs"] if o["id"] != key]
                return {"success": True}
        raise AssertionError(endpoint)


class FakeUba:
    def __init__(self, active=True, down=False, log=None):
        self.active, self.down, self.calls = active, down, []
        self.log = log

    async def __call__(self, method, path, *, params=None, json=None, **_):
        self.calls.append((method, path, json))
        if self.log is not None:
            self.log.append(("UBA " + method, path))
        if self.down:
            raise UbaRequestError("unreachable", "SOCFortress UBA is unreachable", 502)
        if path == "/v1/provisioning":
            return {"graylog": dict(rollback.DEFAULT_NAMES, pipeline_stage=10)}
        if path.endswith("/onboarding"):
            if self.active is None:
                raise UbaRequestError("not_found", "unknown tenant", 404)
            return {"tenant": "acme", "active": self.active, "status": "live" if self.active else "inactive"}
        if method == "PUT":
            self.active = json.get("active", self.active)
            return {"tenant": path.rsplit("/", 1)[1], "active": self.active, "mode": json.get("mode", "active")}
        raise AssertionError(path)


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        obj.id = obj.id or 7

    async def execute(self, query):
        return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None, all=lambda: []))


class Ownership:
    """uba_provisioned_resource in memory."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.removed = []

    async def active(self, session, customer_code=None):
        return [r for r in self.rows if customer_code is None or r.customer_code == customer_code]

    async def mark_removed(self, session, customer_code, items, rollback_id):
        self.removed.extend((i.kind, i.graylog_id, i.origin) for i in items)


def _row(code, kind, graylog_id, title, source=None, shared=False):
    return SimpleNamespace(customer_code=code, kind=kind, graylog_id=graylog_id, title=title, source=source, shared=shared)


def _patches(graylog, uba, owned, sources):
    async def source_ids(code, session):
        return sources.get(code, [])

    return [
        patch.object(rollback, "send_get_request", graylog.get),
        patch.object(rollback, "send_post_request", graylog.post),
        patch.object(rollback, "send_delete_request", graylog.delete),
        patch.object(rollback, "uba_request", uba),
        patch.object(rollback.ownership, "active", owned.active),
        patch.object(rollback.ownership, "mark_removed", owned.mark_removed),
        patch.object(rollback, "_source_stream_ids", source_ids),
    ]


def _run(coro_factory, graylog, uba=None, owned=None, sources=None):
    uba = uba or FakeUba()
    owned = owned or Ownership()
    sources = sources or {code: [f"wazuh-{code}"] for code in ("acme", "globex")}
    patches = _patches(graylog, uba, owned, sources)
    for p in patches:
        p.start()
    try:
        return asyncio.run(coro_factory())
    finally:
        for p in reversed(patches):
            p.stop()


def _roll_back(graylog, uba=None, owned=None, sources=None, code="acme"):
    return _run(lambda: rollback.roll_back(code, FakeSession(), 1, "admin"), graylog, uba, owned, sources)


def _plan(graylog, uba=None, owned=None, code="acme"):
    return _run(lambda: rollback.get_rollback_plan(code, FakeSession()), graylog, uba, owned)


def _writes(graylog):
    return [c for c in graylog.calls if c[0] not in ("GET", "UBA GET")]


# -- the whole rollback ---------------------------------------------------------------------------


def test_routing_goes_first_then_the_output_then_what_it_routed_to_and_uba_last():
    graylog = FakeGraylog()
    uba = FakeUba(log=graylog.calls)
    report = _roll_back(graylog, uba)

    writes = _writes(graylog)
    assert writes[0] == ("POST", "/api/system/pipelines/connections/to_pipeline")
    order = [c[1] for c in writes]
    assert order.index("/api/streams/feed-acme/outputs/out-acme") < order.index("/api/system/outputs/out-acme")
    assert order.index("/api/system/outputs/out-acme") < order.index("/api/streams/feed-acme")
    assert order.index("/api/system/pipelines/pipeline/route-acme") < order.index("/api/system/pipelines/rule/rule-acme-0")
    assert writes[-1] == ("UBA PUT", "/v1/tenants/acme") and uba.calls[-2][2] == {"active": False}

    assert set(graylog.streams) == {"wazuh-acme"}
    assert graylog.connections["wazuh-acme"] == ["proc-acme"]  # the customer's own processing stays
    assert set(graylog.pipelines) == {"proc-acme"} and not graylog.rules and not graylog.outputs
    assert not graylog.inputs  # the last customer with UBA: the shared input goes too
    assert report.status == "completed", report.steps
    checks = {c.check: c for c in report.verification}
    assert checks["stream ACME - Wazuh"].ok and checks["pipelines of ACME - Wazuh"].ok
    assert "WAZUH PROCESSING" in checks["pipelines of ACME - Wazuh"].detail
    assert checks["event definitions"].ok and checks["UBA routing"].ok and checks["output to UBA"].ok
    assert checks["UBA tenant"].ok
    # The snapshot was taken before anything changed.
    before = {o["object"]["id"] for o in report.snapshot["objects"]}
    assert {"feed-acme", "route-acme", "out-acme", "alerts-acme", "rule-acme-0", "in-uba"} <= before
    assert report.snapshot["connections"] == {"route-acme": ["wazuh-acme"]}


def test_objects_found_by_title_are_adopted_and_recorded_ones_marked_removed():
    graylog = FakeGraylog()
    owned = Ownership([_row("acme", ownership.OUTPUT, "out-acme", "UBA GELF - acme")])
    _roll_back(graylog, owned=owned)
    origins = {(kind, gid): origin for kind, gid, origin in owned.removed}
    assert origins[(ownership.OUTPUT, "out-acme")] == "found"  # recorded by setup
    assert origins[(ownership.FEED_STREAM, "feed-acme")] == "adopted"  # set up before the table existed


def test_another_customers_uba_and_the_shared_input_stay():
    graylog = FakeGraylog(codes=("acme", "globex"))
    report = _roll_back(graylog)
    assert {"feed-globex", "alerts-globex", "wazuh-globex"} <= set(graylog.streams)
    assert "route-globex" in graylog.connections["wazuh-globex"] and "out-globex" in graylog.outputs
    assert "in-uba" in graylog.inputs
    [kept] = [s for s in report.steps if s.step == "input UBA ALERTS"]
    assert kept.status == "kept" and "UBA ALERTS - globex" in kept.detail
    assert report.status == "completed"


def test_the_preview_changes_nothing_and_lists_the_order():
    graylog = FakeGraylog(codes=("acme", "globex"))
    plan = _plan(graylog)
    assert not _writes(graylog)
    assert [i.kind for i in plan.remove] == [
        "routing_pipeline",
        "output",
        "routing_rule",
        "routing_rule",
        "feed_stream",
        "alerts_stream",
        "uba_tenant",
    ]
    assert [i.title for i in plan.keep] == ["UBA ALERTS"]
    assert plan.source_streams == [
        {"id": "wazuh-acme", "title": "ACME - Wazuh", "exists": True, "pipelines": ["WAZUH PROCESSING", "UBA ROUTING - WAZUH - acme"]},
    ]


# -- what is never touched ------------------------------------------------------------------------


def test_a_pipeline_running_someone_elses_rule_is_left_and_so_is_what_it_routes_to():
    graylog = FakeGraylog()
    graylog.pipelines["route-acme"]["stages"][0]["rules"].append("HAND MADE ENRICHMENT")
    report = _roll_back(graylog)
    assert "route-acme" in graylog.pipelines and "route-acme" in graylog.connections["wazuh-acme"]
    assert "feed-acme" in graylog.streams and {"rule-acme-0", "rule-acme-1"} <= set(graylog.rules)
    statuses = {s.step: s.status for s in report.steps}
    assert statuses["routing_pipeline UBA ROUTING - WAZUH - acme"] == "conflict"
    assert statuses["feed_stream UBA FEED - WAZUH - acme"] == "conflict"
    assert "out-acme" not in graylog.outputs  # the output to UBA goes regardless: nothing sends to UBA


def test_a_stream_an_event_definition_reads_is_kept_and_the_input_with_it():
    graylog = FakeGraylog()
    graylog.definitions.append({"id": "ed2", "title": "UBA HIGH RISK", "state": "ENABLED", "config": {"streams": ["alerts-acme"]}})
    report = _roll_back(graylog)
    assert "alerts-acme" in graylog.streams and "in-uba" in graylog.inputs
    [conflict] = [s for s in report.steps if s.step == "alerts_stream UBA ALERTS - acme"]
    assert conflict.status == "conflict" and "UBA HIGH RISK" in conflict.detail
    assert {c.check: c.ok for c in report.verification}["event definitions"]


def test_the_customers_own_stream_is_never_removed_even_if_recorded():
    graylog = FakeGraylog()
    owned = Ownership([_row("acme", ownership.FEED_STREAM, "wazuh-acme", "ACME - Wazuh", "WAZUH")])
    _roll_back(graylog, owned=owned)
    assert "wazuh-acme" in graylog.streams and ("DELETE", "/api/streams/wazuh-acme") not in graylog.calls


def test_wazuh_rules_are_kept():
    graylog = FakeGraylog()
    owned = Ownership([_row("acme", ownership.WAZUH_RULES, "0950-uba.xml", "0950-uba.xml", shared=True)])
    report = _roll_back(graylog, owned=owned)
    [step] = [s for s in report.steps if s.step.startswith("Wazuh rules")]
    assert step.status == "kept" and "manager restart" in step.detail


def test_an_output_also_attached_elsewhere_is_only_detached():
    graylog = FakeGraylog()
    graylog.streams["wazuh-acme"]["outputs"].append({"id": "out-acme"})  # someone forwards the raw stream to UBA too
    _roll_back(graylog)
    assert "out-acme" in graylog.outputs and graylog.streams["wazuh-acme"]["outputs"] == [{"id": "out-acme"}]
    assert "feed-acme" not in graylog.streams


# -- failures --------------------------------------------------------------------------------------


def test_uba_down_does_not_stop_the_graylog_side():
    graylog = FakeGraylog()
    report = _roll_back(graylog, FakeUba(down=True))
    assert set(graylog.streams) == {"wazuh-acme"} and not graylog.outputs
    [tenant] = [s for s in report.steps if s.step == "UBA tenant"]
    assert tenant.status == "failed" and "roll back again" in tenant.detail
    assert report.status == "partial"


def test_a_pipeline_that_cannot_be_disconnected_keeps_its_feed_stream_and_rules():
    graylog = FakeGraylog()
    graylog.fail.add(("POST", "/api/system/pipelines/connections/to_pipeline"))
    report = _roll_back(graylog)
    assert "feed-acme" in graylog.streams and "route-acme" in graylog.pipelines and len(graylog.rules) == 2
    assert report.status == "partial"
    statuses = {s.step: s.status for s in report.steps}
    assert statuses["stream UBA FEED - WAZUH - acme"] == "skipped"

    graylog.fail.clear()  # running it again finishes
    again = _roll_back(graylog, FakeUba(active=False))
    assert again.status == "completed" and set(graylog.streams) == {"wazuh-acme"}


def test_nothing_to_roll_back_is_a_409():
    graylog = FakeGraylog(codes=())
    with pytest.raises(HTTPException) as e:
        _roll_back(graylog, FakeUba(active=False))
    assert e.value.status_code == 409


def test_a_check_that_fails_makes_the_rollback_partial():
    graylog = FakeGraylog()
    real = graylog.post

    async def also_disconnect_processing(endpoint, data=None, **kw):
        await real(endpoint, data)
        graylog.connections["wazuh-acme"] = []  # e.g. someone else's change at the same moment

    graylog.post = also_disconnect_processing
    report = _roll_back(graylog)
    checks = {c.check: c for c in report.verification}
    assert checks["pipelines of ACME - Wazuh"].ok is False and report.status == "partial"


# -- mode ------------------------------------------------------------------------------------------


def test_learning_mode_is_sent_with_active_and_refused_for_a_rolled_back_customer():
    uba = FakeUba()
    with patch.object(provision, "uba_request", uba):
        out = asyncio.run(provision.set_mode("acme", "learning"))
    assert out.onboarding["mode"] == "learning" and uba.calls[-1] == ("PUT", "/v1/tenants/acme", {"active": True, "mode": "learning"})

    with patch.object(provision, "uba_request", FakeUba(active=False)), pytest.raises(UbaRequestError) as e:
        asyncio.run(provision.set_mode("acme", "learning"))
    assert e.value.status_code == 409


def test_a_uba_without_modes_is_reported_not_silently_ignored():
    class OldUba(FakeUba):
        async def __call__(self, method, path, **kw):
            out = await super().__call__(method, path, **kw)
            return {k: v for k, v in out.items() if k != "mode"}

    with patch.object(provision, "uba_request", OldUba()), pytest.raises(UbaRequestError) as e:
        asyncio.run(provision.set_mode("acme", "learning"))
    assert e.value.reason == "unsupported"


# -- routes ----------------------------------------------------------------------------------------


def test_rollback_and_mode_routes_are_admin_only():
    from app.connectors.uba.routes import uba as routes

    paths = {"/{customer_code}/mode", "/{customer_code}/rollback", "/{customer_code}/rollbacks", "/{customer_code}/rollbacks/{rollback_id}"}
    found = [r for r in routes.uba_router.routes if r.path in paths]
    assert len(found) == 5 and all(r.dependencies == routes._ADMIN for r in found)
