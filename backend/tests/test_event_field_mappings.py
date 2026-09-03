"""Event Search field discovery spans every index matching the source pattern.

An event source's `index_pattern` routinely resolves to many indices whose mappings
diverge -- a quiet period or a dynamically-mapped field means one index can be missing
fields another has. The old implementation read `_mapping` and used only the first index
in the response, so fields that existed in a sibling index were absent from the column
selector even though events displayed them fine (#1114).

Discovery now asks `_field_caps`, which returns the union over all matching indices in
one response. These tests pin that (the call shape, and the projection of the response),
plus the noise filtering a column picker needs.

No DB, no network -- the indexer client and the event-source lookup are faked.

Run with: cd backend && python -m pytest tests/test_event_field_mappings.py
"""

import asyncio
import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.siem.services import events  # noqa: E402


def _leaf(field_type: str, **extra) -> dict:
    return {"type": field_type, "searchable": True, "aggregatable": True, **extra}


class FakeIndexerClient:
    """Records the `field_caps` call and replays a canned response."""

    def __init__(self, response: dict):
        self._response = response
        self.field_caps_calls = []
        self.closed = False

    async def field_caps(self, **kwargs):
        self.field_caps_calls.append(kwargs)
        return self._response

    async def close(self):
        self.closed = True


class FakeEventSource:
    def __init__(self, index_pattern: str):
        self.index_pattern = index_pattern
        self.time_field = "timestamp"


def _run_get_field_mappings(monkeypatch, response: dict, index_pattern: str = "office365-abc-*"):
    client = FakeIndexerClient(response)

    async def fake_client(_connector_name):
        return client

    async def fake_lookup(customer_code, source_name, db):
        return FakeEventSource(index_pattern)

    monkeypatch.setattr(events, "create_wazuh_indexer_client_async", fake_client)
    monkeypatch.setattr(events, "get_event_source_by_customer_and_name", fake_lookup)

    result = asyncio.run(events.get_field_mappings("ABC", "Office365", db=None))
    return result, client


def test_fields_are_unioned_across_indices_in_the_pattern(monkeypatch):
    """A field mapped in only one index of the pattern is still offered."""
    # `_field_caps` reports, per field, which indices carry it when the coverage is
    # partial -- the shape a quiet or newly-rolled index produces.
    response = {
        "indices": ["office365-abc-000001", "office365-abc-000002"],
        "fields": {
            "timestamp": {"date": _leaf("date")},
            # present in both
            "syslog_level": {"keyword": _leaf("keyword")},
            # only in the older index
            "data_office365_UserId": {"keyword": _leaf("keyword", indices=["office365-abc-000001"])},
            # only in the newer index -- the field the old first-index-only read lost
            "data_office365_ClientIP": {"keyword": _leaf("keyword", indices=["office365-abc-000002"])},
        },
    }

    result, client = _run_get_field_mappings(monkeypatch, response)

    assert [f.field for f in result.fields] == [
        "data_office365_ClientIP",
        "data_office365_UserId",
        "syslog_level",
        "timestamp",
    ]
    assert result.total == 4
    assert result.index_pattern == "office365-abc-*"
    assert result.success is True


def test_field_caps_is_queried_for_the_whole_pattern(monkeypatch):
    """The pattern is resolved server-side, tolerating unavailable and empty matches."""
    _, client = _run_get_field_mappings(monkeypatch, {"fields": {"timestamp": {"date": _leaf("date")}}})

    assert len(client.field_caps_calls) == 1
    call = client.field_caps_calls[0]
    assert call["index"] == "office365-abc-*"
    assert call["fields"] == "*"
    # One inaccessible or closed index must not fail discovery for the whole source.
    assert call["ignore_unavailable"] is True
    assert call["allow_no_indices"] is True
    assert client.closed is True


def test_multifield_subfields_are_suppressed_but_only_under_a_leaf_parent(monkeypatch):
    """`full_log.keyword` is noise next to `full_log`; an object's children are not."""
    response = {
        "fields": {
            "full_log": {"text": _leaf("text", aggregatable=False)},
            "full_log.keyword": {"keyword": _leaf("keyword")},
            # A container plus its child: the child must survive.
            "agent": {"object": {"type": "object", "searchable": False, "aggregatable": False}},
            "agent.name": {"keyword": _leaf("keyword")},
            # A dotted name whose parent is not a field at all.
            "orphan.subfield": {"keyword": _leaf("keyword")},
        },
    }

    result, _ = _run_get_field_mappings(monkeypatch, response)

    fields = [f.field for f in result.fields]
    assert "full_log" in fields
    assert "full_log.keyword" not in fields
    # Containers hold no value of their own, so they are not selectable columns.
    assert "agent" not in fields
    assert "agent.name" in fields
    assert "orphan.subfield" in fields


def test_metadata_fields_are_excluded(monkeypatch):
    response = {
        "fields": {
            "_id": {"_id": _leaf("_id", metadata_field=True, aggregatable=False)},
            "_index": {"_index": _leaf("_index", metadata_field=True)},
            "syslog_level": {"keyword": _leaf("keyword")},
        },
    }

    result, _ = _run_get_field_mappings(monkeypatch, response)

    assert [f.field for f in result.fields] == ["syslog_level"]


def test_conflicting_types_across_indices_are_all_reported(monkeypatch):
    """A field remapped between indices reports both types rather than picking one."""
    response = {
        "fields": {
            "data_status": {
                "keyword": _leaf("keyword", indices=["office365-abc-000002"]),
                "long": _leaf("long", indices=["office365-abc-000001"]),
            },
        },
    }

    result, _ = _run_get_field_mappings(monkeypatch, response)

    assert len(result.fields) == 1
    assert result.fields[0].field == "data_status"
    assert result.fields[0].type == "keyword, long"


def test_empty_field_caps_response_is_not_an_error(monkeypatch):
    """A pattern matching no index (or an index with no mapping yet) yields no fields."""
    result, _ = _run_get_field_mappings(monkeypatch, {"indices": [], "fields": {}})

    assert result.fields == []
    assert result.total == 0
    assert result.success is True


def test_indexer_failure_surfaces_as_a_500(monkeypatch):
    from fastapi import HTTPException

    class FailingClient(FakeIndexerClient):
        async def field_caps(self, **kwargs):
            raise RuntimeError("indexer unreachable")

    client = FailingClient({})

    async def fake_client(_connector_name):
        return client

    async def fake_lookup(customer_code, source_name, db):
        return FakeEventSource("office365-abc-*")

    monkeypatch.setattr(events, "create_wazuh_indexer_client_async", fake_client)
    monkeypatch.setattr(events, "get_event_source_by_customer_and_name", fake_lookup)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(events.get_field_mappings("ABC", "Office365", db=None))

    assert exc.value.status_code == 500
    # The client is still released on the failure path.
    assert client.closed is True
