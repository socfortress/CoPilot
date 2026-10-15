"""Event search's next-page token is bound to the customer and source it was opened for (#1258).

`GET /siem/events/{customer_code}/{source_name}?scroll_id=…` used to hand the scroll id
straight to the indexer: the route checked only that the caller may see the customer in the
path, and a scroll id names a search context, not a tenant. So a portal user of customer A
could read the next page of a search run for customer B by presenting its scroll id, which
travels in a query string (proxy and access logs) and is built from per-node counters.

The API now returns the scroll id signed with the customer and the source, and continues
only a token issued for the same pair. No DB, no network: the indexer and the event-source
lookup are faked.

Run with: cd backend && python -m pytest tests/test_event_scroll_scoping.py
"""

import asyncio
import os

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.siem.schema.events import EventsQueryParams  # noqa: E402
from app.siem.services import events  # noqa: E402
from app.siem.utils.scroll_token import open_scroll  # noqa: E402
from app.siem.utils.scroll_token import sign_scroll  # noqa: E402

SECRET = "s3cret"
RAW = "FGluY2x1ZGVfY29udGV4dF91dWlkDXF1ZXJ5QW5kRmV0Y2gBFkx6Q0Rn=="


class TestToken:
    def test_round_trip(self):
        token = sign_scroll(RAW, "A", "Wazuh", SECRET)
        assert token.startswith(RAW + ".")
        assert open_scroll(token, "A", "Wazuh", SECRET) == RAW

    @pytest.mark.parametrize(
        ("customer", "source", "secret"),
        [("B", "Wazuh", SECRET), ("A", "Office", SECRET), ("A", "Wazuh", "another secret")],
    )
    def test_another_customer_source_or_key_does_not_open_it(self, customer, source, secret):
        assert open_scroll(sign_scroll(RAW, "A", "Wazuh", SECRET), customer, source, secret) is None

    def test_the_customer_and_source_cannot_be_shifted_into_each_other(self):
        # "A" + "BWazuh" must not sign like "AB" + "Wazuh".
        assert open_scroll(sign_scroll(RAW, "A", "BWazuh", SECRET), "AB", "Wazuh", SECRET) is None

    @pytest.mark.parametrize("token", [RAW, "", ".", f".{'0' * 64}", f"{RAW}.", f"{RAW}.nothex", f"other.{'0' * 64}"])
    def test_a_bare_or_tampered_scroll_id_is_refused(self, token):
        assert open_scroll(token, "A", "Wazuh", SECRET) is None

    def test_a_tampered_scroll_id_with_a_valid_mac_is_refused(self):
        mac = sign_scroll(RAW, "A", "Wazuh", SECRET).rpartition(".")[2]
        assert open_scroll(f"{RAW}x.{mac}", "A", "Wazuh", SECRET) is None

    def test_no_next_page_stays_none(self):
        assert sign_scroll(None, "A", "Wazuh", SECRET) is None
        assert sign_scroll("", "A", "Wazuh", SECRET) is None


class FakeIndexer:
    def __init__(self):
        self.scrolled: list[str] = []
        self.closed = 0

    async def search(self, **kwargs):
        return {"_scroll_id": "raw-1", "hits": {"total": {"value": 3}, "hits": [_hit(0)]}}

    async def scroll(self, scroll_id, scroll):
        self.scrolled.append(scroll_id)
        return {"_scroll_id": "raw-2", "hits": {"total": {"value": 3}, "hits": [_hit(1)]}}

    async def clear_scroll(self, scroll_id):
        pass

    async def close(self):
        self.closed += 1


def _hit(n):
    return {"_id": f"e{n}", "_index": "wazuh-a-1", "_source": {"n": n}}


class FakeSource:
    index_pattern = "wazuh-a-*"
    time_field = "timestamp"


@pytest.fixture
def indexer(monkeypatch):
    client = FakeIndexer()
    looked_up = []

    async def fake_client(_name):
        return client

    async def fake_lookup(customer_code, source_name, db):
        looked_up.append((customer_code, source_name))
        if source_name == "Gone":
            raise HTTPException(status_code=404, detail="gone")
        return FakeSource()

    monkeypatch.setattr(events, "create_wazuh_indexer_client_async", fake_client)
    monkeypatch.setattr(events, "get_event_source_by_customer_and_name", fake_lookup)
    client.looked_up = looked_up
    return client


def _query(customer, source, **params):
    return asyncio.run(events.query_events(customer, source, EventsQueryParams(**params), db=None))


def test_the_first_page_hands_out_a_token_for_its_customer_and_source(indexer):
    page = _query("A", "Wazuh")
    assert page.scroll_id != "raw-1"
    assert open_scroll(page.scroll_id, "A", "Wazuh", events.AuthHandler().secret) == "raw-1"


def test_the_next_page_continues_the_same_search_and_hands_out_a_new_token(indexer):
    first = _query("A", "Wazuh")
    second = _query("A", "Wazuh", scroll_id=first.scroll_id)
    assert indexer.scrolled == ["raw-1"]
    assert [e["_id"] for e in second.events] == ["e1"]
    assert open_scroll(second.scroll_id, "A", "Wazuh", events.AuthHandler().secret) == "raw-2"


@pytest.mark.parametrize(
    ("customer", "source", "token"),
    [
        ("B", "Wazuh", None),  # another customer's token
        ("A", "Office", None),  # another source's token
        ("A", "Wazuh", "raw-1"),  # a bare scroll id
    ],
)
def test_a_token_from_elsewhere_never_reaches_the_indexer(indexer, customer, source, token):
    if token is None:
        token = _query("A", "Wazuh").scroll_id
    with pytest.raises(HTTPException) as refused:
        _query(customer, source, scroll_id=token)
    assert refused.value.status_code == 400
    assert indexer.scrolled == []


def test_a_source_removed_since_the_first_page_stops_there(indexer):
    token = sign_scroll("raw-1", "A", "Gone", events.AuthHandler().secret)
    with pytest.raises(HTTPException) as refused:
        _query("A", "Gone", scroll_id=token)
    assert refused.value.status_code == 404
    assert indexer.scrolled == []
