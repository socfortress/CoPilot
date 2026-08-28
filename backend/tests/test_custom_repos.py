"""Custom-repo merge + tagging in RulesCache (no GitHub/MinIO needed).

Uses asyncio.run so it works without pytest-asyncio.
"""
import asyncio

from app.integrations.copilot_searches.services import copilot_searches as cs


def test_refresh_merges_tags_and_skips_id_collisions(monkeypatch):
    cache = cs.RulesCache()
    catalog = {"id": "A", "name": "Cat A", "_provenance": "catalog", "_owner_customer_code": None, "response": {}}
    custom = {"id": "B", "name": "Cust B", "_provenance": "custom", "_owner_customer_code": "acme", "response": {}}
    dupe = {"id": "A", "name": "Dupe A", "_provenance": "custom", "_owner_customer_code": "acme", "response": {}}

    async def fake_fetch():
        return [catalog, custom, dupe]  # catalog first → wins the id-A collision

    monkeypatch.setattr(cache, "_fetch_all_rules", fake_fetch)
    n = asyncio.run(cache.refresh())

    assert n == 2  # dupe skipped
    assert cache._rules["A"]["name"] == "Cat A"  # catalog kept, custom dupe dropped
    assert "B" in cache._rules

    summary = cs.rule_to_summary(cache._rules["B"])
    assert summary.provenance == "custom"
    assert summary.owner_customer_code == "acme"

    cat_summary = cs.rule_to_summary(cache._rules["A"])
    assert cat_summary.provenance == "catalog"
    assert cat_summary.owner_customer_code is None


class _FakeResp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class _FakeClient:
    def __init__(self, text):
        self._text = text

    async def get(self, _url):
        return _FakeResp(self._text)


def test_fetch_yaml_file_tags_provenance_and_owner():
    cache = cs.RulesCache()
    yaml_text = 'id: X\nname: Test Rule\nresponse:\n  severity: high\ngraylog:\n  query: data_win_system_eventID:"1"\n'
    src = {"repo": "acme/rules", "branch": "main", "provenance": "custom", "owner": "acme"}

    rule = asyncio.run(cache._fetch_yaml_file(_FakeClient(yaml_text), src, "detections/windows/test.yaml"))

    assert rule is not None
    assert rule["id"] == "X"
    assert rule["_provenance"] == "custom"
    assert rule["_owner_customer_code"] == "acme"
    assert rule["_has_graylog"] is True
    assert rule["_file_path"] == "detections/windows/test.yaml"


def test_fetch_yaml_file_catalog_source_has_no_owner():
    cache = cs.RulesCache()
    yaml_text = "id: Y\nname: Cat\nresponse: {}\n"
    src = {"repo": cs.GITHUB_REPO, "branch": "main", "provenance": "catalog", "owner": None}
    rule = asyncio.run(cache._fetch_yaml_file(_FakeClient(yaml_text), src, "detections/x/y.yaml"))
    assert rule["_provenance"] == "catalog"
    assert rule["_owner_customer_code"] is None
