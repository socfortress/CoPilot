"""Connector credentials, read once instead of 3.4 times per request (#1072, level 4).

Level 2 measured a fixed ~135ms per statement on this deployment, which makes the
*count* of round-trips the only lever worth pulling. With the per-request user
lookup fixed in level 3, the biggest remaining consumer was
`get_connector_info_from_db` — 244 queries in one session, 3.4 per request, from
89 call sites — and it costs two statements per call, not one, because
`Connectors.history_logs` is `lazy="selectin"` and nothing reads it.

Connector rows are deployment-wide and change only when an operator changes them,
so they cache well. What makes that *safe* rather than merely fast is the
invalidation, and most of what follows tests exactly that: a rotated credential
must never be served from cache, not even for a moment.

Run with: cd backend && python -m pytest tests/test_connector_cache.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors import cache as connector_cache  # noqa: E402
from app.connectors.models import Connectors  # noqa: E402
from app.connectors.utils import get_connector_info_from_db  # noqa: E402
from app.connectors.utils import is_connector_verified  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_cache():
    """The cache is module state; every test starts from empty."""
    connector_cache.invalidate_all()
    connector_cache.reset_stats()
    yield
    connector_cache.invalidate_all()
    connector_cache.reset_stats()


def _connector(name="Wazuh-Indexer", api_key="key-one", verified=True):
    return Connectors(
        id=1,
        connector_name=name,
        connector_type="4.4.1",
        connector_url="https://indexer.local:9200",
        connector_last_updated=datetime(2026, 8, 14, 12, 0, 0),
        connector_api_key=api_key,
        connector_configured=True,
        connector_verified=verified,
        connector_enabled=True,
    )


class _Session:
    """Records every statement, so the tests count round-trips rather than mock them away."""

    def __init__(self, row=None):
        self.row = row
        self.executed = []

    async def execute(self, statement):
        self.executed.append(statement)
        row = self.row

        class _Result:
            def scalars(self):
                return SimpleNamespace(first=lambda: row)

        return _Result()


# ── the point of the exercise: fewer round-trips ────────────────────────────


def test_the_second_read_does_not_touch_the_database():
    session = _Session(_connector())

    async def scenario():
        return [await get_connector_info_from_db("Wazuh-Indexer", session) for _ in range(5)]

    results = asyncio.run(scenario())

    assert len(session.executed) == 1, f"expected one query, got {len(session.executed)}"
    assert all(r["connector_api_key"] == "key-one" for r in results)


def test_each_connector_is_cached_separately():
    """One shared entry would hand Graylog's URL to the Velociraptor client."""

    async def scenario():
        graylog = await get_connector_info_from_db("Graylog", _Session(_connector("Graylog", "graylog-key")))
        velo = await get_connector_info_from_db("Velociraptor", _Session(_connector("Velociraptor", "velo-key")))
        return graylog, velo

    graylog, velo = asyncio.run(scenario())

    assert graylog["connector_api_key"] == "graylog-key"
    assert velo["connector_api_key"] == "velo-key"


def test_is_connector_verified_reads_through_the_same_cache():
    """It asks about the same row, and its callers fetch that row moments later."""
    session = _Session(_connector(verified=True))

    async def scenario():
        await get_connector_info_from_db("Wazuh-Indexer", session)
        return await is_connector_verified("Wazuh-Indexer", session)

    verified = asyncio.run(scenario())

    assert verified is True
    assert len(session.executed) == 1, "the verification check issued its own query"


def test_a_missing_connector_is_not_remembered():
    """Caching a None would hide a newly-created connector for a whole TTL."""
    session = _Session(None)

    async def scenario():
        return [await get_connector_info_from_db("Not-Yet-Created", session) for _ in range(2)]

    results = asyncio.run(scenario())

    assert results == [None, None]
    assert len(session.executed) == 2, "a missing row must be re-checked, not cached"


def test_concurrent_cold_reads_issue_one_query():
    """`/status/sidebar` fans out 14 builders; several want the same connector.

    Without a per-name lock a cold cache turns that fan-out into 14 identical
    queries — the stampede the earlier parallelisation work made possible.
    """
    session = _Session(_connector())
    started = asyncio.Event()

    original_execute = session.execute

    async def slow_execute(statement):
        started.set()
        await asyncio.sleep(0.01)  # long enough for the others to pile up
        return await original_execute(statement)

    session.execute = slow_execute

    async def scenario():
        return await asyncio.gather(*(get_connector_info_from_db("Wazuh-Indexer", session) for _ in range(10)))

    results = asyncio.run(scenario())

    assert len(session.executed) == 1, f"stampede: {len(session.executed)} concurrent queries"
    assert all(r["connector_url"] == "https://indexer.local:9200" for r in results)


def test_different_connectors_do_not_share_a_lock():
    """A slow Velociraptor lookup must not block a Graylog one."""
    assert connector_cache.lock_for("Graylog") is not connector_cache.lock_for("Velociraptor")
    assert connector_cache.lock_for("Graylog") is connector_cache.lock_for("Graylog")


# ── what makes it safe: the credential must never be stale ──────────────────


def test_invalidation_forces_the_next_read_back_to_the_database():
    """The rotated-key scenario, end to end."""
    old = _Session(_connector(api_key="key-one"))
    new = _Session(_connector(api_key="key-two"))

    async def scenario():
        first = await get_connector_info_from_db("Wazuh-Indexer", old)
        # An operator saves a new API key; the write path invalidates.
        connector_cache.invalidate("Wazuh-Indexer")
        second = await get_connector_info_from_db("Wazuh-Indexer", new)
        return first, second

    first, second = asyncio.run(scenario())

    assert first["connector_api_key"] == "key-one"
    assert second["connector_api_key"] == "key-two", "outbound calls would keep using the old credential"


def test_updating_a_connector_invalidates_it_and_only_after_committing():
    """Order matters: a read racing an uncommitted write would re-cache the old row.

    Asserted on the real service method rather than on its source, because the
    property under test is a *sequence* — commit, then invalidate.
    """
    from app.connectors.schema import ConnectorResponse
    from app.connectors.services import ConnectorServices

    record = _connector(api_key="key-one")
    events = []

    class _WriteSession:
        async def execute(self, statement):
            class _Result:
                def scalars(self_inner):
                    return SimpleNamespace(first=lambda: record)

            return _Result()

        def add(self, obj):
            events.append("add")

        async def commit(self):
            events.append("commit")

    original_invalidate = connector_cache.invalidate

    def tracking_invalidate(name):
        events.append(f"invalidate:{name}")
        original_invalidate(name)

    connector_cache.invalidate = tracking_invalidate
    try:
        payload = ConnectorResponse(
            connector_name="Wazuh-Indexer",
            connector_type="4.4.1",
            connector_url="https://indexer.local:9200",
            connector_last_updated=datetime(2026, 8, 14, 12, 0, 0),
            connector_api_key="key-two",
            connector_configured=True,
            connector_verified=True,
            connector_enabled=True,
            connector_accepts_host_only=False,
            connector_accepts_api_key=True,
            connector_accepts_username_password=False,
            connector_accepts_file=False,
            connector_accepts_extra_data=False,
        )
        asyncio.run(ConnectorServices.update_connector_by_id(1, payload, _WriteSession()))
    finally:
        connector_cache.invalidate = original_invalidate

    assert "invalidate:Wazuh-Indexer" in events, "the update path left the cache stale"
    assert events.index("commit") < events.index(
        "invalidate:Wazuh-Indexer",
    ), "invalidating before the commit lets a concurrent read re-cache the old row"


@pytest.mark.parametrize("method", ["verify_connector_by_id", "update_connector_by_id", "save_file"])
def test_every_write_path_invalidates(method):
    """A new write path added without an invalidation is the failure mode here."""
    import inspect

    from app.connectors.services import ConnectorServices

    source = inspect.getsource(getattr(ConnectorServices, method))

    assert "connector_cache.invalidate(" in source, f"{method} commits without invalidating the cache"


def test_a_caller_mutating_its_result_cannot_corrupt_the_cache():
    """Callers only read today; this keeps a future one from poisoning everybody.

    Both reads are mutated on purpose. The first returns the freshly loaded
    payload and the second is served from the stored entry, and only the second
    catches a `_peek` that hands out the stored dict itself — the first would
    pass anyway, because the store path copies for its own reasons.
    """
    session = _Session(_connector())

    async def scenario():
        after_miss = await get_connector_info_from_db("Wazuh-Indexer", session)
        after_miss["connector_url"] = "https://attacker.example"

        after_hit = await get_connector_info_from_db("Wazuh-Indexer", session)
        assert after_hit["connector_url"] == "https://indexer.local:9200"
        after_hit["connector_url"] = "https://attacker.example"

        return await get_connector_info_from_db("Wazuh-Indexer", session)

    third = asyncio.run(scenario())

    assert third["connector_url"] == "https://indexer.local:9200"


# ── the second funnel: get_connector_attribute ──────────────────────────────
#
# Caching only `get_connector_info_from_db` left about a quarter of the connector
# reads still hitting the database, because `app/utils.py:get_connector_attribute`
# reads the same table from 88 further call sites. The first measured session
# after the cache landed showed it: 54 connector statements where the cache had
# only accounted for 5 loads.


def test_reading_an_attribute_by_name_goes_through_the_cache():
    from app.utils import get_connector_attribute

    session = _Session(_connector())

    async def scenario():
        url = await get_connector_attribute(column_name="connector_url", connector_name="Wazuh-Indexer", session=session)
        key = await get_connector_attribute(column_name="connector_api_key", connector_name="Wazuh-Indexer", session=session)
        return url, key

    url, key = asyncio.run(scenario())

    assert url == "https://indexer.local:9200"
    assert key == "key-one"
    assert len(session.executed) == 1, f"two attribute reads cost {len(session.executed)} queries"


def test_an_attribute_read_shares_the_cache_with_the_credential_read():
    """The two funnels must not each keep their own copy of the same row."""
    from app.utils import get_connector_attribute

    session = _Session(_connector())

    async def scenario():
        await get_connector_info_from_db("Wazuh-Indexer", session)
        return await get_connector_attribute(column_name="connector_url", connector_name="Wazuh-Indexer", session=session)

    url = asyncio.run(scenario())

    assert url == "https://indexer.local:9200"
    assert len(session.executed) == 1


def test_reading_an_attribute_by_id_costs_one_query_then_none():
    """A handful of call sites address a connector by id (`connector_id=10`)."""
    from app.utils import get_connector_attribute

    session = _Session(_connector())

    async def scenario():
        first = await get_connector_attribute(column_name="connector_url", connector_id=1, session=session)
        second = await get_connector_attribute(column_name="connector_api_key", connector_id=1, session=session)
        # …and the name path must now hit too, having learned the mapping.
        third = await get_connector_attribute(column_name="connector_url", connector_name="Wazuh-Indexer", session=session)
        return first, second, third

    first, second, third = asyncio.run(scenario())

    assert (first, second, third) == ("https://indexer.local:9200", "key-one", "https://indexer.local:9200")
    assert len(session.executed) == 1, f"the id path cost {len(session.executed)} queries"


def test_a_row_loaded_by_name_can_then_be_read_by_id():
    """The mapping has to be learned on the *load*, not only on the id path.

    This is the ordering the app actually produces: something asks for the
    credentials by name early in a request, and a provisioning helper later asks
    for one column by id. Without the id being recorded when the row is loaded,
    that second read falls through to a query even though the row is cached.
    """
    from app.utils import get_connector_attribute

    session = _Session(_connector())

    async def scenario():
        await get_connector_info_from_db("Wazuh-Indexer", session)
        return await get_connector_attribute(column_name="connector_url", connector_id=1, session=session)

    url = asyncio.run(scenario())

    assert url == "https://indexer.local:9200"
    assert len(session.executed) == 1, "the id read did not recognise the already-cached row"


def test_a_rotated_credential_is_not_served_to_the_attribute_path_either():
    from app.utils import get_connector_attribute

    old = _Session(_connector(api_key="key-one"))
    new = _Session(_connector(api_key="key-two"))

    async def scenario():
        first = await get_connector_attribute(column_name="connector_api_key", connector_name="Wazuh-Indexer", session=old)
        connector_cache.invalidate("Wazuh-Indexer")
        second = await get_connector_attribute(column_name="connector_api_key", connector_name="Wazuh-Indexer", session=new)
        return first, second

    first, second = asyncio.run(scenario())

    assert (first, second) == ("key-one", "key-two")


def test_the_attribute_path_keeps_its_previous_contract():
    """Unknown column, unknown connector, and neither argument — all unchanged."""
    from app.utils import get_connector_attribute

    async def scenario():
        unknown_column = await get_connector_attribute(
            column_name="no_such_column",
            connector_name="Wazuh-Indexer",
            session=_Session(_connector()),
        )
        missing = await get_connector_attribute(
            column_name="connector_url",
            connector_name="Nope",
            session=_Session(None),
        )
        missing_by_id = await get_connector_attribute(
            column_name="connector_url",
            connector_id=999,
            session=_Session(None),
        )
        return unknown_column, missing, missing_by_id

    assert asyncio.run(scenario()) == (None, None, None)

    with pytest.raises(ValueError):
        asyncio.run(get_connector_attribute(column_name="connector_url", session=_Session(None)))


def test_the_id_map_is_cleared_when_everything_is():
    """A startup sync can delete and recreate rows, so ids can change meaning."""
    connector_cache.remember_id(1, "Wazuh-Indexer")
    assert connector_cache.name_for_id(1) == "Wazuh-Indexer"

    connector_cache.invalidate_all()

    assert connector_cache.name_for_id(1) is None


# ── expiry and the off switch ───────────────────────────────────────────────


def test_an_expired_entry_is_re_read(monkeypatch):
    """The TTL is the backstop for edits made outside the app."""
    clock = {"t": 1000.0}
    monkeypatch.setattr(connector_cache.time, "monotonic", lambda: clock["t"])

    old = _Session(_connector(api_key="key-one"))
    new = _Session(_connector(api_key="key-two"))

    async def scenario():
        first = await get_connector_info_from_db("Wazuh-Indexer", old)
        clock["t"] += connector_cache.TTL_SECONDS + 1
        second = await get_connector_info_from_db("Wazuh-Indexer", new)
        return first, second

    first, second = asyncio.run(scenario())

    assert first["connector_api_key"] == "key-one"
    assert second["connector_api_key"] == "key-two"


def test_a_fresh_entry_is_not_re_read(monkeypatch):
    """The other half of the boundary — otherwise the TTL check is inverted."""
    clock = {"t": 1000.0}
    monkeypatch.setattr(connector_cache.time, "monotonic", lambda: clock["t"])
    session = _Session(_connector())

    async def scenario():
        await get_connector_info_from_db("Wazuh-Indexer", session)
        clock["t"] += connector_cache.TTL_SECONDS - 1
        await get_connector_info_from_db("Wazuh-Indexer", session)

    asyncio.run(scenario())

    assert len(session.executed) == 1


def test_the_cache_can_be_turned_off(monkeypatch):
    """`CONNECTOR_CACHE_TTL_SECONDS=0` restores the pre-#1072 behaviour exactly."""
    monkeypatch.setattr(connector_cache, "TTL_SECONDS", 0)
    session = _Session(_connector())

    async def scenario():
        for _ in range(3):
            await get_connector_info_from_db("Wazuh-Indexer", session)

    asyncio.run(scenario())

    assert len(session.executed) == 3


# ── measurement, so the next session can see the effect ─────────────────────


def test_the_hit_ratio_is_reported():
    """The whole project has been measure-first; this is how level 4 gets measured."""
    session = _Session(_connector())

    async def scenario():
        for _ in range(4):
            await get_connector_info_from_db("Wazuh-Indexer", session)

    asyncio.run(scenario())
    stats = connector_cache.stats()

    assert stats["hits"] == 3
    assert stats["entries"] == 1
    assert stats["hit_ratio"] == pytest.approx(0.75, abs=0.01)


def test_the_session_log_carries_the_connector_cache():
    import inspect

    from app.performance.services import session_log

    source = inspect.getsource(session_log.PerformanceSessionLog._summary)

    assert "connector_cache" in source, "level 4 would be invisible in the next session's log"
