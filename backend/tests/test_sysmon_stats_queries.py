"""The indexer side of the Sysmon noise statistics (queries.py, fields.py, collector.py), against a fake indexer that
evaluates the aggregations over synthetic Sysmon alerts.

Pinned: the bodies (golden files in tests/fixtures/sysmon_stats/queries/, both shapes), aggregations only, the week's
epoch-millisecond bounds, the channel, exact label terms, the rule-level and event-ID terms, the bucket budget; each
search's budget on both sides, its opaque id, one heavy search at a time (shared with the firing-stats cache); field
discovery for flat, nested, both and neither shape, the .keyword fallback, events skipped when a key field is unmapped;
labels matched case-insensitively, ambiguous codes and unlabelled or unknown labels never attributed; pair selection;
a timed-out search, failed shards and a client timeout (cancelled) are failures, never partial counts.

Run with: cd backend && python -m pytest tests/test_sysmon_stats_queries.py
"""
import asyncio
import json
import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from elasticsearch7.exceptions import ConnectionError as IndexerConnectionError  # noqa: E402
from elasticsearch7.exceptions import ConnectionTimeout  # noqa: E402

from app.active_response.services.sysmon_stats import collector  # noqa: E402
from app.active_response.services.sysmon_stats import fields  # noqa: E402
from app.active_response.services.sysmon_stats import queries  # noqa: E402
from app.active_response.services.sysmon_stats import settings  # noqa: E402
from app.integrations.copilot_searches.services import wazuh_firing_stats_cache as fs  # noqa: E402
from tests.sysmon_stats_support import FakeIndexer  # noqa: E402
from tests.sysmon_stats_support import alert  # noqa: E402
from tests.sysmon_stats_support import field_caps  # noqa: E402
from tests.sysmon_stats_support import ms  # noqa: E402

GOLDEN = Path(__file__).parent / "fixtures" / "sysmon_stats" / "queries"


@pytest.fixture
def caplog_loguru():
    from loguru import logger

    lines = []
    sink = logger.add(lambda m: lines.append(str(m)), level="DEBUG")
    yield lines
    logger.remove(sink)


W47 = date(2026, 11, 16)
AGENT = "C:\\Program Files\\Fabrikam\\agent.exe"
NAMES = ["Image", "ImageLoaded", "SourceImage", "Signature", "SignatureStatus", "Signed", "OriginalFileName", "User", "RuleName"]


def fm_for(shape):
    doc = alert(eid=7, ts=0, agent="001", label="contoso", shape=shape, computer="WS-0142.corp.contoso.test", **{n: "x" for n in NAMES})
    return fields.discover(field_caps([doc], fields.FIELD_CAPS_FIELDS))[0]


@pytest.mark.parametrize("shape", ["flat", "nested"])
def test_the_bodies_are_the_golden_ones(shape):
    fm = fm_for(shape)
    start, end = collector.week_bounds(W47)
    assert (start, end) == (1794787200000, 1795392000000)  # 2026-11-16T00:00Z .. 2026-11-23T00:00Z
    bodies = {
        "stage0": queries.stage0_body(fm, start, end),
        "stage1": queries.stage1_body(fm, ["acme", "ACME"], start, end, 5),
        "stage2_e7": queries.stage2_body(fm, ["acme", "ACME"], start, end, 5, 7, ["C:\\\\Program Files\\\\Fabrikam\\\\agent.exe"]),
    }
    for name, body in bodies.items():
        golden = json.loads((GOLDEN / f"{name}_{shape}.json").read_text())
        assert body == golden, name
        assert body["size"] == 0 and body["track_total_hits"] is False
        filters = body["query"]["bool"]["filter"]
        assert {"range": {fm.time: {"gte": start, "lt": end, "format": "epoch_millis"}}} in filters
        assert {"term": {fm.channel: "Microsoft-Windows-Sysmon/Operational"}} in filters
    stage1 = bodies["stage1"]
    assert {"terms": {fm.label: ["acme", "ACME"]}} in stage1["query"]["bool"]["filter"]
    quiet = stage1["aggs"]["quiet"]["filter"]["bool"]["filter"]
    assert {"terms": {fm.level: [0, 1, 2, 3, 4, 5]}} in quiet
    assert {"terms": {fm.event_id: [str(e) for e in fields.EVENT_IDS]}} in quiet
    # The report's endpoints count every Sysmon event of the week, any level
    assert "cardinality" in stage1["aggs"]["endpoints"]
    text = json.dumps(bodies)
    assert "commandLine" not in text and "destinationIp" not in text and "CommandLine" not in text


def test_the_bucket_budget_halves_the_first_nested_size():
    fm = fm_for("nested")
    for name in ("DestinationHostname", "DestinationPort", "Protocol", "Initiated"):
        fm.eventdata[name] = f"data.win.eventdata.{name[0].lower() + name[1:]}"
    start, end = collector.week_bounds(W47)
    actors = [f"a{i}" for i in range(10)]
    body = queries.stage2_body(fm, ["acme"], start, end, 5, 3, actors)
    k1 = body["aggs"]["actor"]["aggs"]["k1"]
    assert k1["terms"]["size"] == 15 and k1["terms"]["missing"] == "-"
    leaf = k1["aggs"]["k2"]["aggs"]
    cost = queries.bucket_cost(10, [15, 5], queries._leaf_buckets(leaf))
    assert cost <= settings.BUCKET_BUDGET
    # A wider budget need halves k1 until it fits
    many = [f"a{i}" for i in range(40)]
    body = queries.stage2_body(fm, ["acme"], start, end, 5, 3, many)
    size = body["aggs"]["actor"]["aggs"]["k1"]["terms"]["size"]
    assert size < 15 and queries.bucket_cost(40, [size, 5], queries._leaf_buckets(leaf)) <= settings.BUCKET_BUDGET


# ── discovery ───────────────────────────────────────────────────────────────


def test_discovery_flat_nested_both_and_none():
    flat = alert(eid=1, ts=0, agent="1", label="c", shape="flat", Image="x", ParentImage="y")
    nested = alert(eid=1, ts=0, agent="1", label="c", shape="nested", Image="x", ParentImage="y")
    assert [m.shape for m in fields.discover(field_caps([flat], fields.FIELD_CAPS_FIELDS))] == ["flat"]
    assert [m.shape for m in fields.discover(field_caps([nested], fields.FIELD_CAPS_FIELDS))] == ["nested"]
    both = fields.discover(field_caps([flat, nested], fields.FIELD_CAPS_FIELDS))
    assert [m.shape for m in both] == ["flat", "nested"]
    assert both[0].ed("Image") == "data_win_eventdata_image" and both[1].ed("ParentImage") == "data.win.eventdata.parentImage"
    no_label = {k: v for k, v in nested.items() if k != "agent.labels.customer"}
    assert fields.discover(field_caps([no_label], fields.FIELD_CAPS_FIELDS)) == []


def test_a_text_field_falls_back_to_its_keyword_subfield():
    doc = alert(eid=1, ts=0, agent="1", label="c", Image="x", ParentImage="y")
    caps = field_caps([doc], fields.FIELD_CAPS_FIELDS)
    caps["fields"]["data.win.eventdata.image"] = {"text": {"type": "text", "searchable": True, "aggregatable": False}}
    caps["fields"]["data.win.eventdata.image.keyword"] = {"keyword": {"type": "keyword", "searchable": True, "aggregatable": True}}
    (fm,) = fields.discover(caps)
    assert fm.ed("Image") == "data.win.eventdata.image.keyword"
    # Mixed: text in one index fails its shards, so the field is not used as is
    caps["fields"]["data.win.eventdata.parentImage"] = {
        "keyword": {"type": "keyword", "aggregatable": True},
        "text": {"type": "text", "aggregatable": False},
    }
    (fm,) = fields.discover(caps)
    assert fm.ed("ParentImage") is None and not fm.plan_mapped(1)


def test_an_event_whose_key_field_is_unmapped_is_skipped():
    docs = [alert(eid=22, ts=ms("2026-11-17T10:00:00"), agent=f"{i}", label="contoso", Image=AGENT) for i in range(5)]
    fi = FakeIndexer(docs)

    async def scenario():
        maps = (await collector.discover_fields(fi, "wazuh-*")).maps
        return await collector.collect_customer(fi, "wazuh-*", maps, {"nested": ["contoso"]}, W47, 5, 3, 60)

    result = asyncio.run(scenario())
    assert result.unavailable_events == [22] and result.patterns == []
    assert [s["stage"] for s in fi.searches] == ["quiet"]


def test_an_unavailable_event_is_said_never_silently_left_out(caplog_loguru):
    """An event whose key field one index maps as text: its patterns are left out, logged by field name (no value), and
    the report says it is truncated (review: unavailable_events was counted and never read)."""
    from app.active_response.services.sysmon_stats.redaction import build_context
    from app.active_response.services.sysmon_stats.report import build_report

    docs = []
    for i in range(5):
        for day in range(7):
            ts = ms("2026-11-16T09:00:00") + day * 86_400_000 + i
            docs.append(
                alert(
                    eid=11,
                    ts=ts,
                    agent=f"{i}",
                    label="contoso",
                    Image=AGENT,
                    TargetFilename="C:\\ProgramData\\Fabrikam\\cache\\state.json",
                ),
            )
            docs.append(alert(eid=22, ts=ts, agent=f"{i}", label="contoso", Image=AGENT, QueryName="t.fabrikam-example.com"))
    mixed = {"keyword": {"type": "keyword", "aggregatable": True}, "text": {"type": "text", "aggregatable": False}}
    fi = FakeIndexer(docs, caps_overrides={"data.win.eventdata.targetFilename": mixed})
    result = _collect(fi)
    assert result.unavailable_events == [11]
    assert any("event 11" in line and "TargetFilename" in line and "truncated" in line for line in caplog_loguru)
    assert not any("ProgramData" in line for line in caplog_loguru)
    built = build_report(
        customer="cust_" + "0" * 32,
        week="2026-W47",
        config="unknown",
        endpoints=result.endpoints,
        raw_patterns=result.patterns,
        ctx=build_context(customer_code="contoso", customer_name=None),
        min_endpoints=3,
        unavailable_events=result.unavailable_events,
    )
    assert built.doc["truncated"] is True and built.stats.unavailable_events == [11]
    assert [p["event_id"] for p in built.doc["patterns"]] == [22]


def test_discovery_asks_only_the_weeks_indices_and_the_searches_target_them():
    """An index outside the week that mapped a field as text no longer hides it: discovery is asked with an index_filter
    for the week, and the week's searches go to exactly the indices it names."""
    docs = [
        alert(
            eid=11,
            ts=ms("2026-11-17T09:00:00") + i,
            agent=f"{i}",
            label="contoso",
            Image=AGENT,
            TargetFilename="C:\\ProgramData\\Fabrikam\\x.json",
        )
        for i in range(5)
    ]
    old_text = {"keyword": {"type": "keyword", "aggregatable": True}, "text": {"type": "text", "aggregatable": False}}
    fi = FakeIndexer(
        docs,
        history_caps={"data.win.eventdata.targetFilename": old_text},
        week_indices=["wazuh-alerts-4.x-2026.11.17", "wazuh-alerts-4.x-2026.11.16"],
    )

    async def scenario():
        discovery = await collector.discover_fields(fi, "wazuh-*", W47)
        result = await collector.collect_customer(fi, discovery.index, discovery.maps, {"nested": ["contoso"]}, W47, 5, 3, 60)
        return discovery, result

    discovery, result = asyncio.run(scenario())
    (call,) = fi.field_caps_calls
    start, end = collector.week_bounds(W47)
    assert call["body"] == {"index_filter": {"range": {"timestamp": {"gte": start, "lt": end, "format": "epoch_millis"}}}}
    assert discovery.index == "wazuh-alerts-4.x-2026.11.16,wazuh-alerts-4.x-2026.11.17"
    assert {s["index"] for s in fi.searches} == {discovery.index}
    assert result.unavailable_events == [] and [p.eid for p in result.patterns] == [11]
    # Without the week (or when the indexer names no index), the whole pattern: the old index's text mapping counts
    plain = asyncio.run(collector.discover_fields(fi, "wazuh-*"))
    assert plain.index == "wazuh-*" and plain.maps[0].ed("TargetFilename") is None
    fi.week_indices = []
    fallback = asyncio.run(collector.discover_fields(fi, "wazuh-*", W47))
    assert fallback.index == "wazuh-*" and "body" not in fi.field_caps_calls[-1]


def test_an_indexer_that_cannot_filter_field_discovery_is_asked_the_old_way():
    from elasticsearch7.exceptions import RequestError

    docs = [alert(eid=22, ts=ms("2026-11-17T09:00:00"), agent="1", label="contoso", Image=AGENT, QueryName="t.fabrikam-example.com")]
    fi = FakeIndexer(docs)
    real = fi.field_caps

    async def field_caps(**kwargs):
        if "body" in kwargs:
            raise RequestError(400, "illegal_argument_exception", {})
        return await real(**kwargs)

    fi.field_caps = field_caps
    discovery = asyncio.run(collector.discover_fields(fi, "wazuh-*", W47))
    assert discovery.index == "wazuh-*" and [m.shape for m in discovery.maps] == ["nested"]


def test_counts_in_both_shapes_are_never_added():
    """Review: a customer whose pipeline moves from the flat shape to the nested one mid-week has the same agents in
    both. Endpoints are the larger of the two shapes', never their sum: a pattern seen on 2 endpoints is not sent as 4."""
    from app.active_response.services.sysmon_stats.redaction import build_context
    from app.active_response.services.sysmon_stats.report import build_report

    docs = []
    start = ms("2026-11-16T09:00:00")
    for day in range(7):
        shape = "flat" if day < 3 else "nested"
        for i in range(3):
            ts = start + day * 86_400_000 + i * 1000
            docs.append(alert(eid=22, ts=ts, agent=f"00{i}", label="acme", shape=shape, Image=AGENT, QueryName="x.fabrikam-example.com"))
            if i < 2:
                docs.append(
                    alert(eid=22, ts=ts, agent=f"00{i}", label="acme", shape=shape, Image=AGENT, QueryName="y.fabrikam-example.com"),
                )
    fi = FakeIndexer(docs)

    async def scenario():
        maps = (await collector.discover_fields(fi, "wazuh-*")).maps
        labels, _ = await collector.stage0(fi, "wazuh-*", maps, W47, 60)
        mapped = collector.map_labels(labels, ["acme"])
        return await collector.collect_customer(fi, "wazuh-*", maps, mapped.by_customer["acme"], W47, 5, 3, 60)

    result = asyncio.run(scenario())
    assert result.endpoints == 3
    by_name = {p.key["QueryName"]: p for p in result.patterns}
    assert by_name["x.fabrikam-example.com"].endpoints == 3 and by_name["y.fabrikam-example.com"].endpoints == 2
    assert by_name["x.fabrikam-example.com"].days == 0b1111111
    built = build_report(
        customer="cust_" + "0" * 32,
        week="2026-W47",
        config="unknown",
        endpoints=result.endpoints,
        raw_patterns=result.patterns,
        ctx=build_context(customer_code="acme", customer_name=None),
        min_endpoints=3,
    )
    assert built.doc["endpoints"] == 3
    assert [p["fields"]["QueryName"] for p in built.doc["patterns"]] == ["x.fabrikam-example.com"]
    assert built.stats.dropped_by_reason == {"below-min-endpoints": 1}


def test_merge_shapes_keeps_the_larger_count():
    a = queries.RawPattern(22, {"Image": "a", "QueryName": "q"}, events=10, endpoints=2, days=0b11, details={"User": ["x"]})
    b = queries.RawPattern(22, {"Image": "a", "QueryName": "q"}, events=7, endpoints=3, days=0b1100, details={"User": ["y"]})
    (m,) = queries.merge_shapes([a, b])
    assert (m.events, m.endpoints, m.days, m.details["User"]) == (10, 3, 0b1111, ["x", "y"])


def test_the_customers_computers_are_read_in_stage_1_never_from_another_customer():
    docs = [
        alert(
            eid=22,
            ts=ms("2026-11-17T09:00:00") + i,
            agent=f"{i}",
            label="contoso",
            computer=f"WS-{i:04d}.aw-corp.example",
            Image=AGENT,
            QueryName="t.fabrikam-example.com",
        )
        for i in range(4)
    ]
    docs.append(
        alert(
            eid=22,
            ts=ms("2026-11-17T09:00:00"),
            agent="9",
            label="northwind",
            computer="NW-01.northwind.example",
            Image=AGENT,
            QueryName="t.fabrikam-example.com",
        ),
    )
    result = _collect(FakeIndexer(docs))
    assert sorted(result.computers) == [f"WS-{i:04d}.aw-corp.example" for i in range(4)]


# ── labels ──────────────────────────────────────────────────────────────────


def test_labels_are_matched_case_insensitively_and_never_guessed():
    labels = {"nested": {"Contoso": 10, " contoso ": 3, "fabrikam": 4, "unknown-co": 9}, "flat": {"CONTOSO": 2}}
    mapped = collector.map_labels(labels, ["contoso", "Fabrikam", "northwind"])
    assert mapped.by_customer["contoso"] == {"nested": ["Contoso", " contoso "], "flat": ["CONTOSO"]}
    assert mapped.by_customer["Fabrikam"] == {"nested": ["fabrikam"]}
    assert "northwind" not in mapped.by_customer
    assert all("unknown-co" not in v for c in mapped.by_customer.values() for v in c.values())


def test_codes_equal_but_for_case_are_ambiguous_and_skipped():
    mapped = collector.map_labels({"nested": {"acme": 5}}, ["acme", "ACME"])
    assert mapped.ambiguous == {"acme", "ACME"} and mapped.by_customer == {}


def test_unlabelled_events_are_never_attributed():
    docs = [
        alert(eid=22, ts=ms("2026-11-17T10:00:00"), agent=f"{i}", label=None, Image=AGENT, QueryName="t.fabrikam-example.com")
        for i in range(5)
    ]
    docs += [
        alert(eid=22, ts=ms("2026-11-17T10:00:00"), agent=f"{i}", label="someone-else", Image=AGENT, QueryName="t.fabrikam-example.com")
        for i in range(5)
    ]
    fi = FakeIndexer(docs)

    async def scenario():
        maps = (await collector.discover_fields(fi, "wazuh-*")).maps
        labels, _ = await collector.stage0(fi, "wazuh-*", maps, W47, 60)
        return collector.map_labels(labels, ["contoso"])

    assert asyncio.run(scenario()).by_customer == {}


# ── pairs ───────────────────────────────────────────────────────────────────


def test_pair_selection_threshold_per_event_and_total():
    pairs = [queries.Pair(22, f"a{i}", 1000 - i, 5) for i in range(15)]
    pairs += [queries.Pair(11, f"b{i}", 500 - i, 5) for i in range(15)]
    pairs += [queries.Pair(13, f"c{i}", 400 - i, 5) for i in range(15)]
    pairs += [queries.Pair(7, f"d{i}", 300 - i, 5) for i in range(15)]
    pairs += [queries.Pair(1, "small", 10**6, 2)]
    chosen, left_out = queries.select_pairs(pairs, 3)
    assert left_out and len(chosen) == settings.PAIRS_TOTAL
    assert all(p.actor != "small" for p in chosen)
    per = {}
    for p in chosen:
        per[p.eid] = per.get(p.eid, 0) + 1
    assert max(per.values()) <= settings.PAIRS_PER_EVENT
    assert queries.select_pairs([queries.Pair(22, "x", 5, 3)], 3) == ([queries.Pair(22, "x", 5, 3)], False)


# ── failures ────────────────────────────────────────────────────────────────


def _collect(fi):
    async def scenario():
        maps = (await collector.discover_fields(fi, "wazuh-*")).maps
        return await collector.collect_customer(fi, "wazuh-*", maps, {"nested": ["contoso"]}, W47, 5, 3, 60)

    return asyncio.run(scenario())


def _docs():
    return [
        alert(
            eid=22,
            ts=ms("2026-11-17T10:00:00"),
            agent=f"{i}",
            label="contoso",
            Image=AGENT,
            QueryName="t.fabrikam-example.com",
            User="NT AUTHORITY\\SYSTEM",
        )
        for i in range(5)
    ]


def test_a_search_gets_its_own_budget_and_an_opaque_id():
    fi = FakeIndexer(_docs())
    _collect(fi)
    for s in fi.searches:
        assert s["request_timeout"] == 60 and s["body"]["timeout"] == "55s"
        assert s["opaque_id"].startswith("copilot-sysmon-stats-")
        assert s["ignore_unavailable"] is True and s["allow_no_indices"] is True and s["request_cache"] is True


def test_timed_out_and_failed_shards_are_failures_not_partial_counts():
    timed_out = {"timed_out": True, "_shards": {"failed": 0}, "aggregations": {}}
    with pytest.raises(collector.IndexerTimeout):
        _collect(FakeIndexer(_docs(), answers={"quiet": timed_out}))
    failed = {"timed_out": False, "_shards": {"total": 3, "failed": 1}, "aggregations": {}}
    with pytest.raises(collector.IndexerFailure):
        _collect(FakeIndexer(_docs(), answers={"actor22": failed}))


def test_a_client_timeout_cancels_the_search():
    fi = FakeIndexer(_docs(), answers={"quiet": ConnectionTimeout("TIMEOUT", "timed out", TimeoutError())})
    with pytest.raises(collector.IndexerTimeout):
        _collect(fi)
    assert fi.tasks.cancelled, "the abandoned search must be cancelled by its opaque id"


def test_an_unreachable_indexer_is_its_own_failure():
    fi = FakeIndexer(_docs(), answers={"quiet": IndexerConnectionError("N/A", "refused", None)})
    with pytest.raises(collector.IndexerUnreachable):
        _collect(fi)


def test_one_heavy_search_at_a_time_shared_with_the_firing_stats(monkeypatch):
    fi = FakeIndexer(_docs(), delay=0.02)

    async def firing_search():
        async with fs._heavy_query_slot():
            fi.in_flight += 1
            fi.max_in_flight = max(fi.max_in_flight, fi.in_flight)
            await asyncio.sleep(0.02)
            fi.in_flight -= 1

    async def scenario():
        maps = (await collector.discover_fields(fi, "wazuh-*")).maps
        await asyncio.gather(
            collector.collect_customer(fi, "wazuh-*", maps, {"nested": ["contoso"]}, W47, 5, 3, 60),
            collector.collect_customer(fi, "wazuh-*", maps, {"nested": ["contoso"]}, W47, 5, 3, 60),
            firing_search(),
            firing_search(),
        )

    asyncio.run(scenario())
    assert fi.max_in_flight == 1


def test_a_leaf_parses_into_a_raw_pattern():
    docs = []
    for i in range(4):
        for day in (0, 2):
            docs.append(
                alert(
                    eid=7,
                    ts=ms("2026-11-16T08:00:00") + day * 86_400_000,
                    agent=f"{i}",
                    label="contoso",
                    Image=AGENT,
                    ImageLoaded="C:\\Program Files\\Fabrikam\\hook.dll",
                    Signature="Fabrikam, Inc.",
                    SignatureStatus="Valid",
                    Signed="true",
                    User="NT AUTHORITY\\SYSTEM",
                    RuleName="-",
                ),
            )
    # One event without a Signature: Sysmon's "-" bucket
    docs.append(
        alert(
            eid=7,
            ts=ms("2026-11-18T08:00:00"),
            agent="9",
            label="contoso",
            Image=AGENT,
            ImageLoaded="C:\\Program Files\\Fabrikam\\hook.dll",
        ),
    )
    result = _collect(FakeIndexer(docs))
    signed = next(p for p in result.patterns if p.key["Signature"] == "Fabrikam, Inc.")
    assert signed.events == 8 and signed.endpoints == 4 and signed.days == 0b101
    assert signed.details["SignatureStatus"] == ["Valid"] and signed.details["User"] == ["NT AUTHORITY\\\\SYSTEM"]
    assert signed.rule_names == ["-"]
    unsigned = next(p for p in result.patterns if p.key["Signature"] == "-")
    assert unsigned.events == 1 and unsigned.details["User"] is None
