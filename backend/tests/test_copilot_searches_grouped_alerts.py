"""Grouped (aggregation) CoPilot Searches events become CoPilot alerts (app/integrations/copilot_searches/services/
grouped_alerts.py). No database, no indexer, no Graylog: CoPilot's alert services are replaced by recorders."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

# Imported at module level, as the other incident tests do: importing it inside a running test trips the
# Velociraptor connector's module-level anyio limiter (sniffio: "not in async context").
from app.incidents.services import incident_alert as ia
from app.incidents.services import threshold_alert as ta
from app.integrations.copilot_searches.schema.copilot_searches import AggregationConfig
from app.integrations.copilot_searches.services import copilot_searches as cs
from app.integrations.copilot_searches.services import grouped_alerts as ga


def run(coro):
    return asyncio.run(coro)


def grouped_hit(**over):
    source = {
        "event_definition_type": "aggregation-v1",
        "event_definition_id": "def-1",
        "origin_context": None,
        "timestamp": "2026-08-23 00:05:47.714",
        "timerange_start": "2026-08-22 14:05:47.714",
        "timerange_end": "2026-08-23 00:05:47.714",
        "message": "SOPHOS - REPEATED - UPDATE - FAILURE: WS-0042, acme - count()=7.0",
        "key": "",
        "key_tuple": [],
        "group_by_fields": {"sophos_endpoint_name": "WS-0042", "customer_code": "acme"},
        "source_streams": ["stream-1"],
        "replay_info": {
            "query": "sophos_event:update_failed",
            "timerange_start": "2026-08-22T14:05:47.714Z",
            "timerange_end": "2026-08-23T00:05:47.714Z",
            "streams": ["stream-1"],
        },
        "fields": {"ALERT_ID": "", "ALERT_SOURCE": "SOPHOS", "RULE_ID": "Sophos_Update_Failure", "COPILOT_ALERT_ID": "GROUPED"},
    }
    source.update(over)
    return {"_index": "gl-events_44", "_id": "ev-1", "_seq_no": 5, "_primary_term": 1, "_source": source}


# --- what an event says -----------------------------------------------------------------------------------------------


def test_the_title_is_the_search_without_its_group_values_and_count():
    title = ga.grouped_alert_title
    assert title("M365 - MASS - FILE - DOWNLOAD: carlos@x.com - count()=26.0", {"data_office365_UserId": "carlos@x.com"}) == (
        "M365 - MASS - FILE - DOWNLOAD"
    )
    assert title("SOPHOS - FAIL: WS-0042, acme - count()=7.0", {"a": "WS-0042", "b": "acme"}) == "SOPHOS - FAIL"
    # A title with its own ": " keeps it; only the part holding every group value is cut.
    assert title("AD: LOCKOUT: jdoe - count()=9", {"user": "jdoe"}) == "AD: LOCKOUT"
    # Several series, no group-by, an unknown shape.
    assert title("BRUTE - FORCE - count()=30, card(src)=4", {}) == "BRUTE - FORCE"
    assert title("Just a message", {"user": "x"}) == "Just a message"
    assert ga.series_text("X: y - count()=26.0") == "count()=26.0"
    assert ga.series_text("no series") is None


def test_the_queue_is_grouped_events_and_stale_claims_only():
    query = ga.queue_query(now=2_000_000_000)
    should = query["query"]["bool"]["should"]
    assert should[0] == {"term": {"fields.COPILOT_ALERT_ID": "GROUPED"}}
    legacy = should[1]["bool"]
    assert {"term": {"fields.COPILOT_ALERT_ID": "NONE"}} in legacy["filter"]
    assert {"exists": {"field": "fields.RULE_ID"}} in legacy["filter"]  # CoPilot Searches events only
    assert legacy["must_not"] == [{"exists": {"field": "origin_context"}}]  # single-event events stay with CoPilot
    claim = should[2]["range"]["fields.COPILOT_ALERT_ID"]
    assert claim["lt"] == f"PROCESSING:{2_000_000_000 - ga.CLAIM_STALE_SECONDS:010d}"
    assert query["sort"] == [{"timestamp": {"order": "asc"}}]


def test_the_log_query_replays_the_search_with_the_group_values():
    source = grouped_hit()["_source"]
    body = ga.log_query(source, ga.group_values(source), ["stream-1"])
    filters = body["query"]["bool"]["filter"]
    assert filters[0]["query_string"]["query"] == "sophos_event:update_failed"
    assert filters[1]["range"]["timestamp"]["gte"] == "2026-08-22T14:05:47.714Z"
    assert {"match_phrase": {"sophos_endpoint_name": "WS-0042"}} in filters
    assert {"terms": {"streams": ["stream-1"]}} in filters
    assert ga.log_query({"replay_info": {}}, {}, None) is None  # no window, no search


# --- failures ---------------------------------------------------------------------------------------------------------


def test_failures_are_final_retried_or_counted(monkeypatch):
    ga._ATTEMPTS.clear()
    assert ga.failure_outcome("i", "a", ga.GroupedEventUnresolvable("no customer")) == "FAILED"

    class ConnectionTimeout(Exception):
        pass

    for _ in range(10):  # an outage never counts
        assert ga.failure_outcome("i", "b", ConnectionTimeout("indexer down")) == "retry"
    wrapped = RuntimeError("wrapped")
    wrapped.__cause__ = ConnectionTimeout("down")
    assert ga.looks_transient(wrapped)
    outcomes = [ga.failure_outcome("i", "c", ValueError("odd")) for _ in range(ga.MAX_ATTEMPTS)]
    assert outcomes == ["retry"] * (ga.MAX_ATTEMPTS - 1) + ["FAILED"]


# --- building the alert -----------------------------------------------------------------------------------------------


class Recorder:
    def __init__(self, open_alert=None, log=None, log_customer=None):
        self.calls = []
        self.open_alert = open_alert
        self.log = log
        self.log_customer = log_customer


@pytest.fixture
def services(monkeypatch):
    rec = Recorder()

    async def resolve_customer_code(details, session=None):
        for key in ("customer_code", "agent_labels_customer", "syslog_customer"):
            if details.get(key):
                return details[key]
        return None

    async def is_customer_code_valid(customer_code, session):
        rec.calls.append(("valid", customer_code))

    async def get_single_alert_details(alert_details):
        if rec.log is None:
            raise HTTPException(status_code=400, detail="gone")
        return SimpleNamespace(
            syslog_type="wazuh",
            index=alert_details.index_name,
            id=alert_details.alert_id,
            source=SimpleNamespace(to_dict=lambda: dict(rec.log)),
        )

    async def validate_syslog_type_source(source, session):
        return True

    async def get_all_field_names(syslog_type, session):
        return SimpleNamespace(asset_name="agent_name", ioc_field_names=[], field_names=[])

    async def build_alert_context_payload(alert_payload, field_names):
        return {"rule_description": alert_payload.get("rule_description")}

    async def build_ioc_payload(alert_payload, field_names):
        return None

    async def open_alert_exists(payload, customer_code, session):
        rec.calls.append(("open?", payload.alert_title_payload, customer_code))
        return rec.open_alert

    async def create_alert_full(payload, customer_code, session, threshold_alert=False, velo_sigma_alert=False):
        rec.calls.append(("create", payload, customer_code, threshold_alert))
        return 77

    async def update_alert_creation_time(alert_id, timefield, session):
        rec.calls.append(("touch", alert_id))

    async def add_asset_to_copilot_alert(payload, alert_id, customer_code, session):
        rec.calls.append(("asset", alert_id, payload.asset_payload))

    async def add_ioc_to_copilot_alert(*a, **k):
        rec.calls.append(("ioc",))

    async def add_alert_to_document(request, alert_id):
        rec.calls.append(("doc", request.index_name, request.alert_id, alert_id))

    async def save_threshold_metadata(**kwargs):
        rec.calls.append(("timeline", kwargs["resolved_index_id"]))

    for name, fn in locals().copy().items():
        if callable(fn) and name != "rec" and hasattr(ia, name) and getattr(fn, "__module__", "") == __name__:
            monkeypatch.setattr(ia, name, fn)
    monkeypatch.setattr(ta, "save_threshold_metadata", save_threshold_metadata)

    async def all_asset_fields(session):
        return ["agent_name", "sophos_endpoint_name"]

    monkeypatch.setattr(ga, "_all_asset_fields", all_asset_fields)

    async def find_log(es, source, group):
        return ("wazuh-alerts_1", "log-9") if rec.log is not None else None

    monkeypatch.setattr(ga, "find_contributing_log", find_log)
    return rec


def test_a_grouped_event_with_no_log_becomes_an_alert_from_the_event(services):
    alert_id = run(ga.create_alert_from_grouped_event(None, grouped_hit(), session=None))
    assert alert_id == 77
    (_, payload, customer, threshold) = next(c for c in services.calls if c[0] == "create")
    assert customer == "acme" and threshold is True  # no write to a source document that doesn't exist
    assert payload.alert_title_payload == "SOPHOS - REPEATED - UPDATE - FAILURE"
    assert payload.asset_payload == "WS-0042"  # a group-by field that is a configured asset field
    assert payload.index_name == "gl-events_44" and payload.index_id == "ev-1"
    ctx = payload.alert_context_payload[ga.CONTEXT_KEY]
    assert ctx["group_by_fields"] == {"sophos_endpoint_name": "WS-0042", "customer_code": "acme"}
    assert ctx["series"] == "count()=7.0" and ctx["rule_id"] == "Sophos_Update_Failure"
    assert ("valid", "acme") in services.calls


def test_an_event_with_no_asset_still_becomes_an_alert(services):
    hit = grouped_hit(group_by_fields={"customer_code": "acme", "user": "jdoe"}, message="AD - LOCKOUT: acme, jdoe - count()=9")
    run(ga.create_alert_from_grouped_event(None, hit, session=None))
    (_, payload, _, _) = next(c for c in services.calls if c[0] == "create")
    assert payload.asset_payload == ga.NO_ASSET


def test_the_customer_and_asset_come_from_the_contributing_log(services):
    services.log = {"agent_labels_customer": "bravo", "agent_name": "SRV-7", "rule_description": "x"}
    hit = grouped_hit(group_by_fields={"data_office365_UserId": "carlos@x.com"}, message="M365 - DL: carlos@x.com - count()=26.0")
    run(ga.create_alert_from_grouped_event(None, hit, session=None))
    (_, payload, customer, _) = next(c for c in services.calls if c[0] == "create")
    assert customer == "bravo" and payload.asset_payload == "SRV-7" and payload.source == "wazuh"
    assert payload.index_name == "wazuh-alerts_1" and payload.index_id == "log-9"
    assert ("doc", "wazuh-alerts_1", "log-9", 77) in services.calls
    assert ("timeline", "log-9") in services.calls


def test_no_customer_anywhere_is_unresolvable(services):
    hit = grouped_hit(group_by_fields={"user": "jdoe"}, message="AD - LOCKOUT: jdoe - count()=9")
    hit["_source"]["fields"].pop("CUSTOMER_CODE", None)
    with pytest.raises(ga.GroupedEventUnresolvable):
        run(ga.create_alert_from_grouped_event(None, hit, session=None))
    assert not any(c[0] == "create" for c in services.calls)


def test_a_repeat_firing_adds_to_the_open_alert(services):
    services.open_alert = 12
    assert run(ga.create_alert_from_grouped_event(None, grouped_hit(), session=None)) == 12
    assert ("touch", 12) in services.calls and ("asset", 12, "WS-0042") in services.calls
    assert not any(c[0] == "create" for c in services.calls)


# --- stamping and claiming --------------------------------------------------------------------------------------------


@pytest.fixture
def stamps(monkeypatch):
    written = []

    async def stamp(index, doc_id, value):
        written.append((index, doc_id, value))

    class Session:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *exc):
            return False

    import app.db.db_session as db

    monkeypatch.setattr(ga, "_stamp", stamp)
    monkeypatch.setattr(db, "get_db_session", lambda: Session())
    ga._ATTEMPTS.clear()
    return written


def test_the_event_is_stamped_with_the_alert_or_failed_or_requeued(monkeypatch, stamps):
    async def ok(es, hit, session):
        return 77

    monkeypatch.setattr(ga, "create_alert_from_grouped_event", ok)
    assert run(ga.handle_event(None, grouped_hit())) == "77"

    async def unresolvable(es, hit, session):
        raise ga.GroupedEventUnresolvable("no customer")

    monkeypatch.setattr(ga, "create_alert_from_grouped_event", unresolvable)
    assert run(ga.handle_event(None, grouped_hit())) == "FAILED"

    class OperationalError(Exception):
        pass

    async def outage(es, hit, session):
        raise OperationalError("database gone")

    monkeypatch.setattr(ga, "create_alert_from_grouped_event", outage)
    legacy = grouped_hit()
    legacy["_source"]["fields"]["COPILOT_ALERT_ID"] = "NONE"
    assert run(ga.handle_event(None, legacy)) == "GROUPED"  # requeued in this module's queue, never back to NONE
    assert stamps == [("gl-events_44", "ev-1", "77"), ("gl-events_44", "ev-1", "FAILED"), ("gl-events_44", "ev-1", "GROUPED")]


class FakeIndexer:
    def __init__(self, hits, conflict_ids=()):
        self.hits = hits
        self.conflict_ids = set(conflict_ids)
        self.searches = []
        self.updates = []

    async def search(self, **kw):
        self.searches.append(kw)
        return {"hits": {"hits": list(self.hits) if len(self.searches) == 1 else []}}

    async def update(self, **kw):
        self.updates.append(kw)
        if kw["id"] in self.conflict_ids:
            raise type("ConflictError", (Exception,), {})("version conflict")

    async def close(self):
        pass


def test_one_run_claims_each_event_and_skips_one_taken_elsewhere(monkeypatch):
    import app.connectors.wazuh_indexer.utils.universal as uni

    one, two = grouped_hit(), grouped_hit()
    two["_id"] = "ev-2"
    fake = FakeIndexer([one, two], conflict_ids={"ev-2"})

    async def client(name):
        return fake

    async def indices():
        return ["gl-events_44", "gl-events_45"]

    handled = []

    async def handle(es, hit):
        handled.append(hit["_id"])
        return "77"

    monkeypatch.setattr(uni, "create_wazuh_indexer_client_async", client)
    monkeypatch.setattr(uni, "return_graylog_events_index_names", indices)
    monkeypatch.setattr(ga, "handle_event", handle)
    assert run(ga.collect_grouped_alerts_once()) == 1
    assert handled == ["ev-1"]
    assert fake.searches[0]["seq_no_primary_term"] is True and fake.searches[0]["index"] == "gl-events_44,gl-events_45"
    claim = fake.updates[0]
    assert claim["if_seq_no"] == 5 and claim["if_primary_term"] == 1
    assert claim["body"]["doc"]["fields"]["COPILOT_ALERT_ID"].startswith("PROCESSING:")


# --- provisioning and start -------------------------------------------------------------------------------------------


def test_only_a_rule_grouped_by_fields_is_provisioned_into_the_grouped_queue():
    assert cs._copilot_alert_id_marker(None) == "NONE"
    assert cs._copilot_alert_id_marker(AggregationConfig(enabled=True, group_by=[])) == "NONE"  # Graylog sets origin_context
    assert cs._copilot_alert_id_marker(AggregationConfig(enabled=True, group_by=["sophos_endpoint_name"])) == "GROUPED"


def test_the_collector_never_starts_under_tests_or_when_turned_off(monkeypatch):
    assert ga.start_grouped_alert_collector() is False  # pytest
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("COPILOT_SEARCHES_GROUPED_ALERTS", "false")
    assert ga.start_grouped_alert_collector() is False
