"""Wazuh firing stats on a cluster where the aggregation is slow (#1319).

A 30-day ``terms`` aggregation over a few hundred indices took ~29s on a real
cluster, while the shared indexer client gave up at 15s. The catalog then hid
the Activity column with no reason shown, each refresh left two abandoned
aggregations running on the cluster (``rule_id``, then the ``id`` fallback),
and a per-customer query that failed showed every rule as "No hits 30d".

These tests pin the fixes against a fake indexer client: the firing-stats
budget and its server-side twin, cancelling a search the client abandoned,
never trying another field after a timeout, field discovery before any
aggregation, no ``id`` fallback, the configurable index target, one heavy
search at a time, and per-customer slices computed in the background with
their failures reported.

Run with: cd backend && python -m pytest tests/test_wazuh_firing_stats.py
"""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import pytest  # noqa: E402
from elasticsearch7.exceptions import ConnectionTimeout  # noqa: E402
from elasticsearch7.exceptions import RequestError  # noqa: E402

from app.connectors.wazuh_indexer.utils import universal  # noqa: E402
from app.integrations.copilot_searches.services import wazuh_firing_stats_cache as fs  # noqa: E402


def _buckets(*rows):
    return {
        "timed_out": False,
        "_shards": {"total": 4, "successful": 4, "failed": 0},
        "aggregations": {
            "by_rule": {
                "buckets": [
                    {
                        "key": key,
                        "doc_count": hits,
                        "last_7d": {"doc_count": week},
                        "last_seen": {"value_as_string": "2026-10-28T10:00:00Z"},
                    }
                    for key, hits, week in rows
                ],
            },
        },
    }


class _Tasks:
    def __init__(self, client):
        self.client = client
        self.cancelled = []

    async def list(self, **kwargs):
        # The indexer reports the header under its canonical name.
        return {
            "nodes": {
                "node-a": {
                    "tasks": {f"node-a:{n}": {"headers": {"X-Opaque-Id": opaque}} for n, opaque in enumerate(self.client.opaque_ids)},
                },
            },
        }

    async def cancel(self, task_id, **kwargs):
        self.cancelled.append(task_id)


class _Cat:
    def __init__(self, client):
        self.client = client

    async def indices(self, **kwargs):
        self.client.cat_calls.append(kwargs)
        return [{"index": "wazuh-alerts-4.x-2026.10.28"}, {"index": "fortinet-acme_3"}, {"index": ".kibana"}]


class FakeIndexer:
    """Answers ``search`` per rule-ID field from ``answers`` (a response, or an exception to raise)."""

    def __init__(self, answers=None, mapped=("rule_id",), field_caps_error=None, search_delay=0.0):
        self.answers = answers or {}
        self.mapped = mapped
        self.field_caps_error = field_caps_error
        self.search_delay = search_delay
        self.searches = []
        self.opaque_ids = []
        self.cat_calls = []
        self.field_caps_calls = []
        self.tasks = _Tasks(self)
        self.cat = _Cat(self)
        self.closed = False
        self.in_flight = 0
        self.max_in_flight = 0

    async def field_caps(self, **kwargs):
        self.field_caps_calls.append(kwargs)
        if self.field_caps_error:
            raise self.field_caps_error
        return {"fields": {f: {"keyword": {"type": "keyword", "aggregatable": True}} for f in self.mapped}}

    async def search(self, index, body, **kwargs):
        field = body["aggs"]["by_rule"]["terms"]["field"]
        self.searches.append({"index": index, "body": body, "field": field, **kwargs})
        self.opaque_ids.append(kwargs.get("opaque_id"))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.search_delay:
                await asyncio.sleep(self.search_delay)
            answer = self.answers.get(field, _buckets())
            if isinstance(answer, BaseException):
                raise answer
            return answer
        finally:
            self.in_flight -= 1

    async def close(self):
        self.closed = True


@pytest.fixture
def indexer(monkeypatch):
    holder = {}

    def install(client):
        holder["client"] = client

        async def factory(*args, **kwargs):
            return client

        monkeypatch.setattr(universal, "create_wazuh_indexer_client_async", factory)
        return client

    monkeypatch.delenv("FIRING_STATS_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("FIRING_STATS_INDEX_PATTERN", raising=False)
    return install


@pytest.fixture
def cache(monkeypatch):
    fresh = fs.WazuhFiringStatsCache()
    monkeypatch.setattr(fs, "wazuh_firing_stats_cache", fresh)
    return fresh


def _timeout():
    return ConnectionTimeout("TIMEOUT", "Connection timed out", TimeoutError())


# ── the time budget ─────────────────────────────────────────────────────────


def test_the_aggregation_gets_its_own_budget_on_both_sides(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("5710", 40, 7))}))

    asyncio.run(cache.refresh())

    (search,) = client.searches
    assert search["request_timeout"] == fs.DEFAULT_TIMEOUT_SECONDS == 120
    # The indexer stops before the client does, so it answers instead of being abandoned.
    assert search["body"]["timeout"] == "115s"
    assert search["opaque_id"].startswith("copilot-firing-stats-")
    assert cache.has_stats and cache.get(5710)["hits_30d"] == 40
    assert client.closed


def test_the_budget_comes_from_the_environment_within_bounds(monkeypatch):
    monkeypatch.setenv("FIRING_STATS_TIMEOUT_SECONDS", "45")
    assert fs.firing_stats_timeout_seconds() == 45
    monkeypatch.setenv("FIRING_STATS_TIMEOUT_SECONDS", "1")
    assert fs.firing_stats_timeout_seconds() == fs.MIN_TIMEOUT_SECONDS
    monkeypatch.setenv("FIRING_STATS_TIMEOUT_SECONDS", "100000")
    assert fs.firing_stats_timeout_seconds() == fs.MAX_TIMEOUT_SECONDS
    monkeypatch.setenv("FIRING_STATS_TIMEOUT_SECONDS", "two minutes")
    assert fs.firing_stats_timeout_seconds() == fs.DEFAULT_TIMEOUT_SECONDS


def test_a_client_timeout_cancels_the_search_and_tries_nothing_else(indexer, cache):
    """The pile-up: each refresh left `rule_id` and then `id` running on the cluster."""
    client = indexer(FakeIndexer(answers={"rule.id": _timeout()}, mapped=("rule.id", "rule_id")))

    asyncio.run(cache.refresh())

    assert [s["field"] for s in client.searches] == ["rule.id"], "a timeout must not start the next field"
    assert client.tasks.cancelled == ["node-a:0"], "the abandoned search must be cancelled by its opaque id"
    assert not cache.has_stats
    assert "FIRING_STATS_TIMEOUT_SECONDS" in cache.unavailable_reason
    assert "120s" in cache.unavailable_reason


def test_a_server_side_timeout_is_a_failure_not_partial_counts(indexer, cache):
    """Partial buckets would put live rules under "Dead"."""
    partial = _buckets(("5710", 3, 1))
    partial["timed_out"] = True
    indexer(FakeIndexer(answers={"rule_id": partial}))

    asyncio.run(cache.refresh())

    assert not cache.has_stats
    assert cache.get(5710)["hits_30d"] == 0
    assert "did not finish" in cache.unavailable_reason


def test_a_failed_cancel_does_not_hide_the_timeout(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _timeout()}))

    async def refuse(**kwargs):
        raise RuntimeError("no permission to list tasks")

    client.tasks.list = refuse
    asyncio.run(cache.refresh())

    assert "did not finish" in cache.unavailable_reason


# ── which field, which indices ──────────────────────────────────────────────


def test_only_mapped_fields_are_aggregated_and_id_never(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("100", 5, 5))}, mapped=("rule_id",)))

    asyncio.run(cache.refresh())

    assert [s["field"] for s in client.searches] == ["rule_id"]
    assert client.field_caps_calls[0]["fields"] == "rule.id,rule_id"
    assert "id" not in fs.RULE_ID_FIELD_OPTIONS


def test_a_field_the_indexer_rejects_moves_on_to_the_next(indexer, cache):
    client = indexer(
        FakeIndexer(
            answers={
                "rule.id": RequestError(400, "search_phase_execution_exception", {"error": "fielddata"}),
                "rule_id": _buckets(("7", 1, 0)),
            },
            mapped=("rule.id", "rule_id"),
        ),
    )

    asyncio.run(cache.refresh())

    assert [s["field"] for s in client.searches] == ["rule.id", "rule_id"]
    assert cache.has_stats and cache._winning_field == "rule_id"


def test_the_winning_field_goes_first_next_time(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("7", 1, 0))}, mapped=("rule.id", "rule_id")))
    cache._winning_field = "rule_id"

    asyncio.run(cache.refresh())

    assert [s["field"] for s in client.searches] == ["rule_id"]


def test_no_rule_field_mapped_means_no_aggregation(indexer, cache):
    client = indexer(FakeIndexer(mapped=()))

    asyncio.run(cache.refresh())

    assert client.searches == []
    assert cache.unavailable_reason == fs.NO_RULE_FIELD_REASON


def test_unreadable_field_caps_still_tries_the_known_fields(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("7", 1, 0))}, field_caps_error=RuntimeError("forbidden")))

    asyncio.run(cache.refresh())

    assert [s["field"] for s in client.searches] == ["rule.id", "rule_id"]
    assert cache.has_stats


def test_the_index_target_is_configurable(indexer, cache, monkeypatch):
    monkeypatch.setenv("FIRING_STATS_INDEX_PATTERN", "wazuh-alerts-*,office365-*")
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("7", 1, 0))}))

    asyncio.run(cache.refresh())

    assert client.searches[0]["index"] == "wazuh-alerts-*,office365-*"
    assert client.field_caps_calls[0]["index"] == "wazuh-alerts-*,office365-*"
    assert client.cat_calls[0]["index"] == "wazuh-alerts-*,office365-*"


@pytest.mark.parametrize("value", ["", "   ", "wazuh alerts-*", ",,", "a" * 1001])
def test_an_unusable_index_target_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("FIRING_STATS_INDEX_PATTERN", value)
    assert fs.firing_stats_index_pattern() == fs.ALERT_INDEX_PATTERN


# ── loading versus unavailable ──────────────────────────────────────────────


def test_counts_are_not_shown_before_the_first_refresh(cache):
    """An empty dict before the first load read as "nothing has ever fired"."""
    assert cache.is_available
    assert not cache.is_loaded
    assert not cache.has_stats


def test_one_heavy_search_at_a_time(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("7", 1, 0))}, search_delay=0.05))

    async def scenario():
        await asyncio.gather(cache.refresh(), fs.fetch_firing_stats_for_customer("acme"), fs.fetch_firing_stats_for_customer("globex"))

    asyncio.run(scenario())

    assert len(client.searches) == 3
    assert client.max_in_flight == 1


# ── per-customer slices ─────────────────────────────────────────────────────


def test_a_customer_slice_never_waits_and_lands_in_the_background(indexer, cache):
    client = indexer(FakeIndexer(answers={"rule_id": _buckets(("5710", 9, 2))}, search_delay=0.05))

    async def scenario():
        first = cache.customer_stats("acme")
        again = cache.customer_stats("acme")
        await asyncio.sleep(0.2)
        return first, again, cache.customer_stats("acme")

    first, again, landed = asyncio.run(scenario())

    assert first.status == "loading" and again.status == "loading"
    assert len(client.searches) == 1, "a second ask while loading must not start a second aggregation"
    assert landed.status == "ready" and landed.stats[5710]["hits_30d"] == 9

    customer_filter = client.searches[0]["body"]["query"]["bool"]["filter"][-1]
    assert customer_filter == {
        "bool": {
            "should": [{"term": {"agent_labels_customer": "acme"}}, {"term": {"agent.labels.customer": "acme"}}],
            "minimum_should_match": 1,
        },
    }, "one query matches either customer field shape"


def test_a_failed_customer_slice_says_so_instead_of_zeros(indexer, cache):
    indexer(FakeIndexer(answers={"rule_id": _timeout()}))

    async def scenario():
        cache.customer_stats("acme")
        await asyncio.sleep(0.05)
        return cache.customer_stats("acme")

    landed = asyncio.run(scenario())

    assert landed.status == "error"
    assert "did not finish" in landed.error
    assert landed.stats == {}


def test_a_customer_without_alerts_is_ready_and_empty(indexer, cache):
    indexer(FakeIndexer(answers={"rule_id": _buckets()}))

    result = asyncio.run(fs.fetch_firing_stats_for_customer("quiet"))

    assert result.status == "ready" and result.stats == {}


def test_customer_slices_are_bounded(indexer, cache, monkeypatch):
    monkeypatch.setattr(fs, "CUSTOMER_CACHE_SIZE", 2)
    indexer(FakeIndexer(answers={"rule_id": _buckets(("7", 1, 0))}))

    async def scenario():
        for code in ("a", "b", "c"):
            cache.customer_stats(code)
            await asyncio.sleep(0.02)

    asyncio.run(scenario())

    assert list(cache._customer_slices) == ["b", "c"]


# ── the list envelope ───────────────────────────────────────────────────────


def test_the_envelope_tells_loading_unavailable_and_customer_states_apart(cache, monkeypatch):
    from app.integrations.copilot_searches.services import detection_catalog

    monkeypatch.setattr(detection_catalog, "wazuh_firing_stats_cache", cache)

    async def no_refresh():
        return None

    monkeypatch.setattr(cache, "ensure_fresh_nonblocking", no_refresh)
    monkeypatch.setattr(detection_catalog.wazuh_rules_cache, "ensure_fresh_nonblocking", no_refresh)
    monkeypatch.setattr(detection_catalog.wazuh_rules_cache, "get_all_rules", lambda: [{"id": 5710, "level": 10}])

    cold = asyncio.run(detection_catalog.list_wazuh_rules())
    assert cold["firing_stats_loading"] is True
    assert cold["firing_stats_available"] is False
    assert cold["customer_firing_stats_status"] is None

    cache._fail("Counting rule hits did not finish within 120s.")
    failed = asyncio.run(detection_catalog.list_wazuh_rules())
    assert failed["firing_stats_loading"] is False
    assert failed["firing_stats_available"] is False
    assert "120s" in failed["firing_stats_unavailable_reason"]

    cache._customer_slices["acme"] = fs.CustomerFiringStats(
        status="error",
        error="Wazuh indexer is not reachable.",
        fetched_at=fs.datetime.utcnow(),
    )
    scoped = asyncio.run(detection_catalog.list_wazuh_rules(customer_code="acme"))
    assert scoped["customer_firing_stats_status"] == "error"
    assert scoped["customer_firing_stats_error"] == "Wazuh indexer is not reachable."
    assert scoped["rules"][0]["hits_30d"] == 0
