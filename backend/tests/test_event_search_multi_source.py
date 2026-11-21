"""Event Search across several sources of one customer (#1356).

``POST /siem/events/{customer_code}/search`` runs one query over the index patterns of up to five of
the customer's event sources, newest first, and every event says which source it came from.
Pinned here:

- the sources are the path's customer's, each looked up (an unknown one is a 404, a disabled one a
  400), and the caller must be allowed that customer; the Customer Portal can't reach the routes;
- they must share one time field, mapped as a date in every index: a date in one index and a
  keyword in another fails the indexer's sort, and one name holding epoch ms in one source and ISO
  text in another sorts one source after the other, so both are refused before the indexer is asked;
- one search over the patterns together, sorted on the time field, an index without it last;
- each event's ``_source_name`` is the source whose pattern names its index most literally;
- the next-page token belongs to the customer and the set of sources (in any order), and to
  nothing else: not one source, not another set; the sources are looked up again for every page;
- shards that could not answer are reported, and the fields of several sources mark the ones
  their indices type differently;
- an index pattern is read as the indexer reads it: a comma list, ``-`` removing what came before.

Run with: cd backend && python -m pytest tests/test_event_search_multi_source.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import EventSources  # noqa: E402
from app.siem.schema.events import MAX_SOURCES  # noqa: E402
from app.siem.schema.events import MultiSourceEventsQuery  # noqa: E402
from app.siem.services import events  # noqa: E402
from app.siem.utils.scroll_token import open_multi_scroll  # noqa: E402
from app.siem.utils.scroll_token import sign_multi_scroll  # noqa: E402
from app.siem.utils.scroll_token import sign_scroll  # noqa: E402

SECRET = events.AuthHandler().secret

FIREWALL = SimpleNamespace(name="Firewall", index_pattern="fortigate-acme*", time_field="timestamp")
ROUTER = SimpleNamespace(name="Router", index_pattern="mikrotik-acme*", time_field="timestamp")
CATCH_ALL = SimpleNamespace(name="Everything", index_pattern="*-acme*", time_field="timestamp")
OTHER_CLOCK = SimpleNamespace(name="Cloud", index_pattern="o365-acme*", time_field="@timestamp")


def hit(doc_id, index):
    return {"_id": doc_id, "_index": index, "_source": {"timestamp": "2026-11-20T10:00:00Z", "src_ip": "10.0.0.5"}}


class FakeIndexer:
    """The indexer, as the multi-source search talks to it."""

    def __init__(self, time_types=("date",), shards_failed=0):
        self.time_types = time_types
        self.shards_failed = shards_failed
        self.searches = []
        self.scrolled = []
        self.field_caps_calls = []

    async def field_caps(self, index=None, fields=None, **_):
        self.field_caps_calls.append({"index": index, "fields": fields})
        if fields == "*":
            return {"fields": {"src_ip": {"ip": {}, "keyword": {}}, "action": {"keyword": {}}, "timestamp": {"date": {}}}}
        return {"fields": {fields: {t: {} for t in self.time_types}}} if self.time_types else {"fields": {}}

    async def search(self, index=None, body=None, size=None, scroll=None, **_):
        self.searches.append({"index": index, "body": body, "size": size, "scroll": scroll})
        return {
            "_scroll_id": "raw-1",
            "_shards": {"total": 4, "successful": 4 - self.shards_failed, "failed": self.shards_failed},
            "hits": {"total": {"value": 9}, "hits": [hit("f1", "fortigate-acme_0"), hit("m1", "mikrotik-acme_0")]},
        }

    async def scroll(self, scroll_id, scroll):
        self.scrolled.append(scroll_id)
        return {
            "_scroll_id": "raw-2",
            "_shards": {"total": 4, "failed": 0},
            "hits": {"total": {"value": 9}, "hits": [hit("m2", "mikrotik-acme_1")]},
        }

    async def clear_scroll(self, scroll_id):
        pass

    async def close(self):
        pass


@pytest.fixture
def indexer(monkeypatch):
    fake = FakeIndexer()
    known = {s.name: s for s in (FIREWALL, ROUTER, CATCH_ALL, OTHER_CLOCK)}

    async def client(_name):
        return fake

    async def lookup(customer_code, source_name, db):
        if source_name not in known:
            raise HTTPException(status_code=404, detail="gone")
        return known[source_name]

    monkeypatch.setattr(events, "create_wazuh_indexer_client_async", client)
    monkeypatch.setattr(events, "get_event_source_by_customer_and_name", lookup)
    return fake


def search(customer="ACME", **kwargs):
    kwargs.setdefault("sources", ["Firewall", "Router"])
    return asyncio.run(events.query_events_multi(customer, MultiSourceEventsQuery(**kwargs), db=None))


# --- index patterns as the indexer reads them ---------------------------------------------------


@pytest.mark.parametrize(
    ("index_name", "pattern", "expected"),
    [
        ("fortigate-acme_0", "fortigate-acme*", True),
        ("fortigate-acme_0", "mikrotik-acme*", False),
        ("mikrotik-acme_0", "fortigate-acme*,mikrotik-acme*", True),
        ("mikrotik-acme-old_0", "mikrotik-acme*,-mikrotik-acme-old*", False),
        ("mikrotik-acme-old_0", "-mikrotik-acme-old*,mikrotik-acme*", True),  # an exclusion only removes what came before
        ("mikrotik-acme-old_0", "mikrotik-acme*,-mikrotik-acme-old*,mikrotik-acme-old_0", True),
        ("wazuh_alerts_x", "wazuh-alerts-*", False),  # a dot or dash is literal
    ],
)
def test_an_index_pattern_is_read_as_the_indexer_reads_it(index_name, pattern, expected):
    assert events.index_in_pattern(index_name, pattern) is expected


def test_the_sources_patterns_are_searched_as_one():
    assert events.combined_pattern([FIREWALL, ROUTER]) == "fortigate-acme*,mikrotik-acme*"
    assert events.combined_pattern([ROUTER, FIREWALL]) == "mikrotik-acme*,fortigate-acme*"


def test_an_exclusion_removes_only_its_own_sources_indices():
    current = SimpleNamespace(name="Current", index_pattern="fortigate-acme*,-fortigate-acme-old*", time_field="timestamp")
    pattern = events.combined_pattern([CATCH_ALL, current])
    assert pattern == "fortigate-acme*,-fortigate-acme-old*,*-acme*"
    # The catch-all covers the old index on its own, so the search together does too.
    assert events.index_in_pattern("fortigate-acme-old_0", pattern)
    assert not events.index_in_pattern("fortigate-acme-old_0", current.index_pattern)


def test_an_event_belongs_to_the_source_naming_its_index_most_literally():
    assert events.source_for_index("fortigate-acme_0", [CATCH_ALL, FIREWALL]).name == "Firewall"
    assert events.source_for_index("syslog-acme_0", [CATCH_ALL, FIREWALL]).name == "Everything"
    assert events.source_for_index("wazuh-globex_0", [CATCH_ALL, FIREWALL]) is None


# --- the request --------------------------------------------------------------------------------


def test_a_search_names_each_source_once_and_at_most_five():
    assert MultiSourceEventsQuery(sources=[" Firewall ", "Router", "Firewall"]).sources == ["Firewall", "Router"]
    with pytest.raises(ValidationError):
        MultiSourceEventsQuery(sources=[f"s{i}" for i in range(MAX_SOURCES + 1)])
    with pytest.raises(ValidationError):
        MultiSourceEventsQuery(sources=[])
    with pytest.raises(ValidationError):
        MultiSourceEventsQuery(sources=["Firewall", "  "])


# --- the search ---------------------------------------------------------------------------------


def test_one_search_runs_over_the_sources_patterns_on_their_shared_time_field(indexer):
    page = search(query="src_ip:10.0.0.5")
    (sent,) = indexer.searches
    assert sent["index"] == "fortigate-acme*,mikrotik-acme*"
    assert sent["scroll"] == "5m"
    assert sent["body"]["sort"] == [{"timestamp": {"order": "desc", "unmapped_type": "date"}}]
    assert {"query_string": {"query": "src_ip:10.0.0.5", "default_operator": "AND"}} in sent["body"]["query"]["bool"]["must"]
    assert indexer.field_caps_calls == [{"index": "fortigate-acme*,mikrotik-acme*", "fields": "timestamp"}]
    assert [(e["_id"], e["_source_name"]) for e in page.events] == [("f1", "Firewall"), ("m1", "Router")]
    assert page.total == 9 and page.warnings == []


def test_sources_on_different_time_fields_are_refused_before_the_indexer_is_asked(indexer):
    with pytest.raises(HTTPException) as refused:
        search(sources=["Firewall", "Cloud"])
    assert refused.value.status_code == 400
    assert "Firewall: timestamp" in refused.value.detail and "Cloud: @timestamp" in refused.value.detail
    assert indexer.searches == [] and indexer.field_caps_calls == []


@pytest.mark.parametrize("types", [("date", "keyword"), ("keyword",), ("date", "long")])
def test_a_time_field_that_is_not_a_date_everywhere_is_refused(indexer, types):
    indexer.time_types = types
    with pytest.raises(HTTPException) as refused:
        search()
    assert refused.value.status_code == 400
    assert "is not a date in every index" in refused.value.detail
    assert indexer.searches == []


@pytest.mark.parametrize("types", [("date",), ("date", "date_nanos"), ()])
def test_a_time_field_that_is_a_date_or_unmapped_is_searched(indexer, types):
    indexer.time_types = types
    search()
    assert len(indexer.searches) == 1


def test_an_unreadable_time_field_type_searches_nothing(indexer, monkeypatch):
    async def broken(**_):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(indexer, "field_caps", broken)
    with pytest.raises(HTTPException) as refused:
        search()
    assert refused.value.status_code == 502
    assert "connection reset" not in refused.value.detail
    assert indexer.searches == []


def test_an_unknown_source_stops_the_search(indexer):
    with pytest.raises(HTTPException) as refused:
        search(sources=["Firewall", "Gone"])
    assert refused.value.status_code == 404
    assert indexer.searches == []


def test_shards_that_could_not_answer_are_reported(indexer):
    indexer.shards_failed = 1
    assert search().warnings == ["1 of 4 shards could not answer: the results may be incomplete"]


# --- the next page ------------------------------------------------------------------------------


def test_the_next_page_continues_the_same_search_and_names_each_events_source(indexer):
    first = search()
    assert open_multi_scroll(first.scroll_id, "ACME", ["Router", "Firewall"], SECRET) == "raw-1"
    second = search(sources=["Router", "Firewall"], scroll_id=first.scroll_id)  # the set, in any order
    assert indexer.scrolled == ["raw-1"]
    assert [(e["_id"], e["_source_name"]) for e in second.events] == [("m2", "Router")]
    assert open_multi_scroll(second.scroll_id, "ACME", ["Firewall", "Router"], SECRET) == "raw-2"


@pytest.mark.parametrize(
    ("customer", "sources", "token"),
    [
        ("GLOBEX", ["Firewall", "Router"], None),  # another customer
        ("ACME", ["Firewall", "Everything"], None),  # another set of sources
        ("ACME", ["Firewall"], None),  # fewer sources
        ("ACME", ["Firewall", "Router"], "raw-1"),  # a bare scroll id
        ("ACME", ["Firewall", "Router"], sign_scroll("raw-1", "ACME", "Firewall", SECRET)),  # one source's token
    ],
)
def test_a_token_from_elsewhere_never_reaches_the_indexer(indexer, customer, sources, token):
    if token is None:
        token = sign_multi_scroll("raw-1", "ACME", ["Firewall", "Router"], SECRET)
    with pytest.raises(HTTPException) as refused:
        search(customer=customer, sources=sources, scroll_id=token)
    assert refused.value.status_code == 400
    assert refused.value.detail == events.NO_LONGER_VALID
    assert indexer.scrolled == []


def test_a_source_gone_since_the_first_page_stops_the_paging(indexer):
    token = sign_multi_scroll("raw-1", "ACME", ["Firewall", "Gone"], SECRET)
    with pytest.raises(HTTPException) as refused:
        search(sources=["Firewall", "Gone"], scroll_id=token)
    assert refused.value.status_code == 404
    assert indexer.scrolled == []


# --- the fields of several sources --------------------------------------------------------------


def test_the_fields_of_several_sources_mark_the_ones_typed_differently(indexer):
    answer = asyncio.run(events.get_field_mappings_multi("ACME", ["Firewall", "Router"], db=None))
    assert indexer.field_caps_calls == [{"index": "fortigate-acme*,mikrotik-acme*", "fields": "*"}]
    fields = {f.field: (f.type, f.conflict) for f in answer.fields}
    assert fields["src_ip"] == ("ip, keyword", True)
    assert fields["action"] == ("keyword", False)
    assert answer.index_pattern == "fortigate-acme*,mikrotik-acme*"


# --- the routes ---------------------------------------------------------------------------------


USERS = {
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
}
SCOPES = {"ana": ["analyst"], "portal": ["customer_user"]}
TABLES = ("user", "role", "user_customer_access", "customers", "event_sources")


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables[n] for n in TABLES]))
        async with self.factory() as session:
            session.add_all(
                [Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")],
            )
            await session.commit()
            session.add_all(
                [
                    UserCustomerAccess(user_id=2, customer_code="ACME"),
                    UserCustomerAccess(user_id=4, customer_code="ACME"),
                    EventSources(customer_code="ACME", name="Firewall", index_pattern="fortigate-acme*", event_type="Network Security"),
                    EventSources(customer_code="ACME", name="Router", index_pattern="mikrotik-acme*", event_type="Network Security"),
                    EventSources(customer_code="ACME", name="search", index_pattern="search-acme*", event_type="EDR"),
                    EventSources(customer_code="ACME", name="Old", index_pattern="old-acme*", event_type="EDR", enabled=False),
                    EventSources(customer_code="GLOBEX", name="Firewall", index_pattern="fortigate-globex*", event_type="Network Security"),
                ],
            )
            await session.commit()
        return self


def call(scenario):
    async def _inner():
        db = await Db().create()
        from app.routers import siem

        api = FastAPI()
        api.include_router(siem.router)

        async def _session():
            async with db.factory() as session:
                yield session

        api.dependency_overrides[get_db] = _session
        fake = FakeIndexer()

        async def client(_name):
            return fake

        async def resolve_user(self, request, username):
            return USERS.get(username)

        try:
            with patch.object(events, "create_wazuh_indexer_client_async", client), patch.object(
                AuthHandler,
                "decode_token",
                lambda self, token: (token, SCOPES.get(token, [])),
            ), patch.object(AuthHandler, "_resolve_user", resolve_user):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as http:
                    return await scenario(http, fake)
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def test_an_analyst_searches_their_customers_sources_together():
    async def scenario(http, fake):
        response = await http.post("/siem/events/ACME/search", json={"sources": ["Firewall", "Router"]}, headers=as_user("ana"))
        assert response.status_code == 200, response.text
        return response.json(), fake

    body, fake = call(scenario)
    assert fake.searches[0]["index"] == "fortigate-acme*,mikrotik-acme*"
    assert [e["_source_name"] for e in body["events"]] == ["Firewall", "Router"]


@pytest.mark.parametrize(
    ("who", "customer", "sources", "status"),
    [
        ("ana", "GLOBEX", ["Firewall"], 403),  # another customer, even with a source of the same name
        ("portal", "ACME", ["Firewall", "Router"], 403),  # the portal searches one source at a time
        ("ana", "ACME", ["Firewall", "Missing"], 404),
        ("ana", "ACME", ["Firewall", "Old"], 400),  # disabled
    ],
)
def test_refusals(who, customer, sources, status):
    async def scenario(http, fake):
        search_answer = await http.post(f"/siem/events/{customer}/search", json={"sources": sources}, headers=as_user(who))
        fields_answer = await http.post(f"/siem/events/{customer}/fields", json={"sources": sources}, headers=as_user(who))
        return search_answer, fields_answer, fake

    search_answer, fields_answer, fake = call(scenario)
    assert (search_answer.status_code, fields_answer.status_code) == (status, status)
    assert fake.searches == []


def test_a_source_called_search_still_has_its_own_routes():
    async def scenario(http, fake):
        single = await http.get("/siem/events/ACME/search", headers=as_user("ana"))
        fields = await http.get("/siem/events/ACME/search/fields", headers=as_user("ana"))
        return single, fields, fake

    single, fields, fake = call(scenario)
    assert single.status_code == 200 and fields.status_code == 200
    assert fake.searches[0]["index"] == "search-acme*"


def test_the_fields_route_answers_for_several_sources():
    async def scenario(http, fake):
        return await http.post("/siem/events/ACME/fields", json={"sources": ["Firewall", "Router"]}, headers=as_user("ana"))

    response = call(scenario)
    assert response.status_code == 200, response.text
    src_ip = next(f for f in response.json()["fields"] if f["field"] == "src_ip")
    assert src_ip == {"field": "src_ip", "type": "ip, keyword", "conflict": True}
