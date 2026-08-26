"""Publish-to-GitHub logic (mocked GitHub Contents API, config, and linter)."""
import asyncio

from app.integrations.copilot_searches.services import publish as pub

VALID_YAML = 'name: My Rule\nid: 11111111-1111-1111-1111-111111111111\nversion: 1\nschema_version: "1.0"\ngraylog:\n  query: a:1\n'


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or {}
        self.text = str(self._data)

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, get_resp, put_resp):
        self._get = get_resp
        self._put = put_resp
        self.put_body = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        return self._get

    async def put(self, url, json=None):
        self.put_body = json
        return self._put


class _FakeCache:
    def __init__(self, existing=None):
        self._existing = existing

    async def ensure_loaded(self):
        pass

    def get_rule_by_id(self, _rule_id):
        return self._existing


def _patch(monkeypatch, cfg, get_resp, put_resp, valid=True, existing=None):
    async def fake_get_repo(_code):
        return cfg

    monkeypatch.setattr(pub, "get_custom_repo", fake_get_repo)
    monkeypatch.setattr(pub, "lint_result", lambda _y: {"valid": valid, "error_count": 0 if valid else 2, "findings": []})
    monkeypatch.setattr(pub, "rules_cache", _FakeCache(existing))
    client = _FakeClient(get_resp, put_resp)
    monkeypatch.setattr(pub.httpx, "AsyncClient", lambda **kw: client)
    return client


CFG = {"customer_code": "acme", "repo": "acme/rules", "branch": "main", "token": "ghp_x", "enabled": True}


def test_publish_creates_new_file(monkeypatch):
    client = _patch(
        monkeypatch,
        CFG,
        _Resp(404),
        _Resp(201, {"commit": {"html_url": "http://c/1"}, "content": {"html_url": "http://f/1"}}),
    )
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme"))
    assert r["success"] and r["action"] == "created"
    assert r["path"] == "detections/custom/my-rule.yaml"
    assert "sha" not in client.put_body  # create → no sha
    assert r["commit_url"] == "http://c/1"


def test_publish_updates_existing_file(monkeypatch):
    client = _patch(
        monkeypatch,
        CFG,
        _Resp(200, {"sha": "abc123"}),
        _Resp(200, {"commit": {"html_url": "http://c/2"}, "content": {"html_url": "http://f/2"}}),
    )
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme", path="detections/custom/x.yaml"))
    assert r["success"] and r["action"] == "updated"
    assert client.put_body["sha"] == "abc123"  # update → sha carried


def test_publish_rejects_when_no_repo(monkeypatch):
    _patch(monkeypatch, None, _Resp(404), _Resp(201))
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme"))
    assert not r["success"] and "no custom repository" in r["error"].lower()


def test_publish_rejects_when_no_token(monkeypatch):
    cfg = {**CFG, "token": None}
    _patch(monkeypatch, cfg, _Resp(404), _Resp(201))
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme"))
    assert not r["success"] and "write token" in r["error"].lower()


def test_publish_rejects_invalid_rule(monkeypatch):
    _patch(monkeypatch, CFG, _Resp(404), _Resp(201), valid=False)
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme"))
    assert not r["success"] and "validation error" in r["error"].lower()


def test_publish_rejects_paths_outside_detections(monkeypatch):
    _patch(monkeypatch, CFG, _Resp(404), _Resp(201))
    for bad in ["README.md", ".github/workflows/x.yml", "detections/../README.md", "detections\\x.yaml", "/detections/x.yaml", "detections/x.txt"]:
        r = asyncio.run(pub.publish_rule(VALID_YAML, "acme", path=bad))
        assert not r["success"], f"path {bad!r} should be rejected"
        assert "detections/" in r["error"]


def test_publish_rejects_id_collision_with_catalog(monkeypatch):
    existing = {"id": "11111111-1111-1111-1111-111111111111", "name": "Catalog Rule", "_provenance": "catalog", "_file_path": "detections/windows/x.yaml", "_owner_customer_code": None}
    _patch(monkeypatch, CFG, _Resp(404), _Resp(201), existing=existing)
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme"))
    assert not r["success"] and "already used" in r["error"] and "catalog" in r["error"]


def test_publish_rejects_id_collision_with_other_custom_file(monkeypatch):
    existing = {"id": "11111111-1111-1111-1111-111111111111", "name": "Other Rule", "_provenance": "custom", "_file_path": "detections/custom/other.yaml", "_owner_customer_code": "acme"}
    _patch(monkeypatch, CFG, _Resp(404), _Resp(201), existing=existing)
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme", path="detections/custom/my-rule.yaml"))
    assert not r["success"] and "already used" in r["error"]


def test_publish_allows_republish_of_same_file(monkeypatch):
    existing = {"id": "11111111-1111-1111-1111-111111111111", "name": "My Rule", "_provenance": "custom", "_file_path": "detections/custom/my-rule.yaml", "_owner_customer_code": "acme"}
    _patch(
        monkeypatch,
        CFG,
        _Resp(200, {"sha": "abc"}),
        _Resp(200, {"commit": {"html_url": "c"}, "content": {"html_url": "f"}}),
        existing=existing,
    )
    r = asyncio.run(pub.publish_rule(VALID_YAML, "acme", path="detections/custom/my-rule.yaml"))
    assert r["success"] and r["action"] == "updated"
