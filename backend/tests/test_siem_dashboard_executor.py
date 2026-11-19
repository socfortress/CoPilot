"""The SIEM dashboard panel executor's stat panels report exact counts.

The indexer stops counting at 10,000 hits unless the search asks for the exact total, so a stat panel
used to read 10,000 for any busier source (a firewall gets there within minutes). Built-in and custom
dashboards share `execute_panels`, so this covers both.

No DB, no network: the indexer client is a recorder.

Run with: cd backend && python -m pytest tests/test_siem_dashboard_executor.py
"""

import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.siem.services import dashboards  # noqa: E402


class RecordingIndexer:
    def __init__(self, total):
        self.total = total
        self.bodies = []
        self.closed = False

    async def search(self, index, body):
        self.bodies.append(body)
        return {"hits": {"total": {"value": self.total, "relation": "eq"}, "hits": []}, "aggregations": {}}

    async def close(self):
        self.closed = True


def run_panels(monkeypatch, panels, total):
    indexer = RecordingIndexer(total)

    async def client(_name):
        return indexer

    monkeypatch.setattr(dashboards, "create_wazuh_indexer_client_async", client)
    results = asyncio.run(dashboards.execute_panels(panels, "sonicwall-example01*", "timestamp", "24h"))
    return results, indexer


def test_a_stat_panel_asks_for_the_exact_total(monkeypatch):
    panel = {"id": "events", "title": "Events", "type": "stat", "w": 3, "h": 100, "lucene": "syslog_type:sonicwall"}

    results, indexer = run_panels(monkeypatch, [panel], total=123_456)

    [body] = indexer.bodies
    assert body["track_total_hits"] is True
    assert body["size"] == 0
    assert results["events"].value == 123_456
    assert indexer.closed


def test_aggregation_panels_are_unchanged(monkeypatch):
    """Histograms and terms panels count through their buckets; they never needed the total."""
    panel = {"id": "over_time", "title": "Over Time", "type": "histogram", "w": 12, "h": 200, "lucene": "*"}

    async def search(index, body):
        indexer.bodies.append(body)
        return {"hits": {"total": {"value": 0, "relation": "eq"}, "hits": []}, "aggregations": {"over_time": {"buckets": []}}}

    indexer = RecordingIndexer(0)
    indexer.search = search

    async def client(_name):
        return indexer

    monkeypatch.setattr(dashboards, "create_wazuh_indexer_client_async", client)
    asyncio.run(dashboards.execute_panels([panel], "sonicwall-example01*", "timestamp", "24h"))

    [body] = indexer.bodies
    assert "track_total_hits" not in body
