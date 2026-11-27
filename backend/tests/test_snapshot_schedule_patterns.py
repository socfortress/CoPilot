"""Snapshot schedules whose index pattern has commas or exclusions.

A schedule's pattern was turned into one regex (``*`` became ``.*``), so ``fortinet-*,palo_alto-*``
became ``^fortinet-.*,palo_alto-.*$``, which no index name matches. Such a schedule ran, matched
nothing, recorded "SKIPPED: No new indices to snapshot", advanced last_execution_time and waited
interval_days, and the next poll replaced its status with "DEFERRED: …": it never snapshotted
anything, and nothing on screen said so. What this pins:

- the pattern is read as OpenSearch's multi-target syntax (``resolve_index_pattern``): comma
  parts, whitespace around them ignored, ``-`` exclusions wherever they stand, ``*`` the only
  wildcard (``.`` matches a dot);
- a run whose pattern matches nothing records NO_MATCH, is not a success, and leaves
  last_execution_time alone, so the next poll tries again; a deferred poll leaves NO_MATCH (and
  FAILED) on screen; an indexer that can't be asked is FAILED, never NO_MATCH;
- indices matched but none new stays a normal run (SKIPPED, time advanced), and a snapshot's name
  is unchanged, so an existing schedule still finds what it snapshotted before;
- a pattern with nothing to include is a 422 on create and on update, and both answer how many
  indices a new pattern matches right now;
- a manual snapshot's write-index filter reads its index list the same way.

No indexer and no MySQL: a fake indexer client and in-memory SQLite.
Run with: cd backend && python -m pytest tests/test_snapshot_schedule_patterns.py
"""

import asyncio
import fnmatch
import itertools
import os
import time
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.wazuh_indexer.models.snapshot_and_restore import (  # noqa: E402
    SnapshotSchedule,
)
from app.connectors.wazuh_indexer.routes.snapshot_and_restore import (  # noqa: E402
    wazuh_indexer_snapshots_router,
)
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import (  # noqa: E402
    SnapshotScheduleCreate,
)
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import (  # noqa: E402
    SnapshotScheduleUpdate,
)
from app.connectors.wazuh_indexer.services import snapshot_and_restore as snapshots  # noqa: E402
from app.connectors.wazuh_indexer.utils.index_patterns import (  # noqa: E402
    expand_requested_indices,
)
from app.connectors.wazuh_indexer.utils.index_patterns import glob_matches  # noqa: E402
from app.connectors.wazuh_indexer.utils.index_patterns import (  # noqa: E402
    index_pattern_problem,
)
from app.connectors.wazuh_indexer.utils.index_patterns import (  # noqa: E402
    resolve_index_pattern,
)
from app.db.db_session import get_db  # noqa: E402

CLUSTER = [
    "fortinet-acme_12",
    "fortinet-poc_3",
    "palo_alto-globex_4",
    "wazuh-acme_30",
    "wazuh-monitoring-2026.48w",
    "wazuh-statistics-2026.1w",
    "wazuh-states-vulnerabilities-acme",
    "wazuh-poc_0",
    "suricata-acme_5",
    "gl-events_2",
]

# Every tenant's index sets, Wazuh's own indices and proof-of-concept tenants left out.
FULL_PATTERN = (
    "fortinet-*,palo_alto-*,pfsense-*,office365-*,cloudflare-*,sophos-central-*,wazuh-*,"
    "-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*,-*-poc_*"
)
SCHEDULE_PREFIX = "scheduled_daily_cold_storage_"


# --- reading a pattern -------------------------------------------------------------------------


def test_a_single_pattern_selects_what_it_always_did():
    assert resolve_index_pattern("fortinet-*", CLUSTER) == ["fortinet-acme_12", "fortinet-poc_3"]
    assert resolve_index_pattern("*", CLUSTER) == CLUSTER


def test_a_name_without_a_wildcard_selects_that_index_only_when_it_exists():
    assert resolve_index_pattern("gl-events_2", CLUSTER) == ["gl-events_2"]
    assert resolve_index_pattern("gl-events_3", CLUSTER) == []


def test_each_inclusion_adds_its_indices():
    assert resolve_index_pattern("fortinet-*,palo_alto-*", CLUSTER) == ["fortinet-acme_12", "fortinet-poc_3", "palo_alto-globex_4"]


def test_whitespace_around_parts_and_empty_parts_are_ignored():
    expected = ["fortinet-acme_12", "fortinet-poc_3", "palo_alto-globex_4"]
    assert resolve_index_pattern("fortinet-*, palo_alto-*", CLUSTER) == expected
    assert resolve_index_pattern(" fortinet-* ,,palo_alto-*, ", CLUSTER) == expected


def test_exclusions_remove_what_the_inclusions_matched():
    pattern = "wazuh-*,-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*"
    assert resolve_index_pattern(pattern, CLUSTER) == ["wazuh-acme_30", "wazuh-poc_0"]


def test_an_exclusion_applies_wherever_it_stands():
    # Before the first inclusion: OpenSearch would read it as a name matching nothing.
    assert resolve_index_pattern("-wazuh-monitoring-*,wazuh-*,-wazuh-statistics-*,-wazuh-states-*", CLUSTER) == [
        "wazuh-acme_30",
        "wazuh-poc_0",
    ]
    # A later inclusion doesn't bring an excluded index back.
    assert resolve_index_pattern("wazuh-*,-wazuh-states-*,wazuh-states-vulnerabilities-acme", CLUSTER) == [
        "wazuh-acme_30",
        "wazuh-monitoring-2026.48w",
        "wazuh-statistics-2026.1w",
        "wazuh-poc_0",
    ]


def test_an_exclusion_with_a_wildcard_at_both_ends():
    assert resolve_index_pattern("fortinet-*,wazuh-*,-*-poc_*", CLUSTER) == [
        "fortinet-acme_12",
        "wazuh-acme_30",
        "wazuh-monitoring-2026.48w",
        "wazuh-statistics-2026.1w",
        "wazuh-states-vulnerabilities-acme",
    ]


def test_only_the_star_is_a_wildcard():
    indices = ["wazuh-monitoring-2026.48w", "wazuh-monitoring-2026x48w", "archive(old)-1", "archiveold-1"]
    assert resolve_index_pattern("wazuh-monitoring-2026.48*", indices) == ["wazuh-monitoring-2026.48w"]
    assert resolve_index_pattern("archive(old)-*", indices) == ["archive(old)-1"]


def test_only_exclusions_select_nothing_and_cannot_be_saved():
    pattern = "-wazuh-monitoring-*,-*-poc_*"
    assert resolve_index_pattern(pattern, CLUSTER) == []
    assert "only excludes" in index_pattern_problem(pattern)
    with pytest.raises(ValidationError, match="only excludes"):
        SnapshotScheduleCreate(name="Daily cold storage", index_pattern=pattern, repository="cold")


def test_the_full_schedule_pattern():
    assert resolve_index_pattern(FULL_PATTERN, CLUSTER) == ["fortinet-acme_12", "palo_alto-globex_4", "wazuh-acme_30"]


@pytest.mark.parametrize(
    ("name", "part", "matches"),
    [
        ("a", "a*a", False),
        ("aa", "a*a", True),
        ("a-b-a", "a*a", True),
        ("", "*", True),
        ("abc", "**", True),
        ("ab", "ab*b", False),
        ("abb", "ab*b", True),
        # The pieces between the stars may not overlap each other or the ends.
        ("aba", "*ab*ba*", False),
        ("abba", "*ab*ba*", True),
        ("fortinet-poc_3", "*-poc_*", True),
        ("fortinet-acme_12", "*-poc_*", False),
    ],
)
def test_the_star_matcher(name, part, matches):
    assert glob_matches(name, part) is matches


def test_the_star_matcher_agrees_with_fnmatch_on_every_short_name_and_pattern():
    # fnmatch reads "?" and "[" too; with only letters and stars the two must agree.
    names = ["".join(chars) for size in range(6) for chars in itertools.product("ab", repeat=size)]
    parts = ["".join(chars) for size in range(1, 6) for chars in itertools.product("ab*", repeat=size)]
    for name, part in itertools.product(names, parts):
        assert glob_matches(name, part) == fnmatch.fnmatchcase(name, part), (name, part)


def test_no_pattern_makes_matching_slow():
    # As a backtracking regex (".*a.*a…b"), this pattern against this name takes longer than a run.
    started = time.perf_counter()
    assert resolve_index_pattern("*a*a*a*a*a*a*a*a*a*a*a*a*b", ["a" * 255] * 50) == []
    assert time.perf_counter() - started < 1


# --- validation --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pattern", "problem"),
    [
        ("", "Enter an index pattern"),
        (" , ,", "Enter an index pattern"),
        ("-", "must be followed by the pattern to exclude"),
        ("wazuh-*, - ", "must be followed by the pattern to exclude"),
        ("-wazuh-monitoring-*", "only excludes"),
    ],
)
def test_a_pattern_that_can_never_match_is_refused_on_create_and_update(pattern, problem):
    with pytest.raises(ValidationError, match=problem):
        SnapshotScheduleCreate(name="Daily cold storage", index_pattern=pattern, repository="cold")
    with pytest.raises(ValidationError, match=problem):
        SnapshotScheduleUpdate(index_pattern=pattern)


def test_a_pattern_is_stored_as_written():
    assert (
        SnapshotScheduleCreate(name="n", index_pattern="fortinet-*, palo_alto-*", repository="r").index_pattern == "fortinet-*, palo_alto-*"
    )
    assert SnapshotScheduleCreate(name="n", index_pattern=FULL_PATTERN, repository="r").index_pattern == FULL_PATTERN


def test_an_update_without_a_pattern_keeps_the_stored_one():
    assert SnapshotScheduleUpdate(enabled=False).index_pattern is None
    assert SnapshotScheduleUpdate(index_pattern=None).index_pattern is None


# --- a fake indexer and a database --------------------------------------------------------------


class FakeIndexer:
    """The calls the snapshot service makes, on a fixed cluster."""

    def __init__(self, names, existing_snapshots=(), unreachable=False):
        self.names = list(names)
        self.existing_snapshots = list(existing_snapshots)
        self.unreachable = unreachable
        self.listings = 0
        self.created = []
        self.indices = SimpleNamespace(get_alias=self._get_alias)
        self.snapshot = SimpleNamespace(get=self._get_snapshots, create=self._create)

    def _get_alias(self, index):
        self.listings += 1
        if self.unreachable:
            raise ConnectionError("indexer unreachable")
        assert index == "*"
        return {name: {"aliases": {}} for name in self.names}

    def _get_snapshots(self, repository, snapshot, ignore_unavailable):
        return {"snapshots": self.existing_snapshots}

    def _create(self, repository, snapshot, body, wait_for_completion):
        self.created.append({"repository": repository, "snapshot": snapshot, "body": body})
        return {"accepted": True}


def indexer_client(fake):
    async def create(name):
        assert name == "Wazuh-Indexer"
        return fake

    return patch.object(snapshots, "create_wazuh_indexer_client", create)


class Db:
    async def create(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        table = SQLModel.metadata.tables["index_snapshot_schedules"]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[table]))
        # As the application's sessions: attributes stay readable after a commit.
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        return self

    async def add(self, **fields) -> int:
        async with self.factory() as session:
            schedule = SnapshotSchedule(**fields)
            session.add(schedule)
            await session.commit()
            return schedule.id

    async def get(self, schedule_id) -> SnapshotSchedule:
        async with self.factory() as session:
            return await session.get(SnapshotSchedule, schedule_id)

    async def count(self) -> int:
        async with self.factory() as session:
            return (await session.execute(select(func.count()).select_from(SnapshotSchedule))).scalar_one()


def a_while_ago():
    """A last run old enough for an interval_days=1 schedule to be due (whole seconds, as MySQL keeps)."""
    return (datetime.utcnow() - timedelta(days=2)).replace(microsecond=0)


def schedule_fields(**overrides):
    fields = dict(
        name="Daily cold storage",
        index_pattern=FULL_PATTERN,
        repository="cold",
        snapshot_prefix="scheduled",
        skip_write_indices=True,
        interval_days=1,
    )
    fields.update(overrides)
    return fields


def run_schedule(fake, polls=1, **overrides):
    """Store a schedule, run it ``polls`` times as the scheduler would, and read it back."""

    async def _inner():
        db = await Db().create()
        try:
            schedule_id = await db.add(**schedule_fields(**overrides))
            results = []
            with indexer_client(fake):
                for _ in range(polls):
                    async with db.factory() as session:
                        schedule = await session.get(SnapshotSchedule, schedule_id)
                        results.append(await snapshots.execute_snapshot_schedule(schedule, session))
            return results, await db.get(schedule_id)
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())


# --- running a schedule ------------------------------------------------------------------------


@pytest.mark.parametrize("last_run", [a_while_ago(), None])
def test_a_pattern_that_matches_nothing_is_no_match_and_is_tried_again_at_the_next_poll(last_run):
    fake = FakeIndexer(CLUSTER)
    previous_snapshot = f"{SCHEDULE_PREFIX}20261120_000511"

    results, stored = run_schedule(
        fake,
        polls=2,
        index_pattern="pfsense-*,office365-*",
        last_execution_time=last_run,
        last_snapshot_name=previous_snapshot,
        last_execution_status="SUCCESS",
    )

    # Two polls in a row both ran (the second wasn't deferred by interval_days), neither a success.
    assert [r.success for r in results] == [False, False]
    assert [r.message for r in results] == [snapshots.NO_MATCH_STATUS] * 2
    assert stored.last_execution_status == "NO_MATCH: pattern matched 0 indices"
    assert stored.last_execution_time == last_run
    assert stored.last_snapshot_name == previous_snapshot
    assert fake.created == []


def test_the_full_pattern_snapshots_its_new_indices_under_the_same_name_as_before():
    fake = FakeIndexer(
        CLUSTER + ["fortinet-acme_11", "wazuh-acme_29"],
        existing_snapshots=[
            # This schedule's earlier snapshot: wazuh-acme_29 is already in cold storage.
            {"snapshot": f"{SCHEDULE_PREFIX}20261126_000511", "indices": ["wazuh-acme_29"]},
            # Another schedule's snapshot counts for nothing here.
            {"snapshot": "scheduled_other_schedule_20261126_000511", "indices": ["fortinet-acme_11"]},
        ],
    )
    last_run = a_while_ago()

    [result], stored = run_schedule(fake, last_execution_time=last_run)

    assert result.success is True
    assert result.indices_snapshotted == ["fortinet-acme_11"]
    # The newest index of each index set is still being written to.
    assert result.skipped_write_indices == ["fortinet-acme_12", "palo_alto-globex_4", "wazuh-acme_30"]
    [created] = fake.created
    assert created["repository"] == "cold"
    assert created["body"]["indices"] == "fortinet-acme_11"
    assert created["snapshot"].startswith(SCHEDULE_PREFIX)
    assert stored.last_snapshot_name == created["snapshot"]
    assert stored.last_execution_status == "SUCCESS"
    assert stored.last_execution_time > last_run


def test_indices_matched_but_none_new_is_still_a_normal_run():
    fake = FakeIndexer(
        CLUSTER + ["fortinet-acme_11"],
        existing_snapshots=[{"snapshot": f"{SCHEDULE_PREFIX}20261126_000511", "indices": ["fortinet-acme_11"]}],
    )
    last_run = a_while_ago()

    [result], stored = run_schedule(fake, last_execution_time=last_run)

    assert result.success is True
    assert fake.created == []
    assert stored.last_execution_status == "SKIPPED: No new indices to snapshot (3 write indices skipped) (1 already snapshotted)"
    assert stored.last_execution_time > last_run


@pytest.mark.parametrize(
    ("status", "kept"),
    [
        (snapshots.NO_MATCH_STATUS, True),
        ("FAILED: Failed to create snapshot: repository_missing_exception", True),
        ("SUCCESS", False),
        ("SKIPPED: No new indices to snapshot (3 write indices skipped)", False),
    ],
)
def test_a_deferred_poll_leaves_a_problem_on_screen(status, kept):
    fake = FakeIndexer(CLUSTER)

    # Ran today already: interval_days=1 defers this poll.
    [result], stored = run_schedule(fake, last_execution_time=datetime.utcnow(), last_execution_status=status)

    assert result.message.startswith("DEFERRED: interval_days=1")
    assert fake.listings == 0
    if kept:
        assert stored.last_execution_status == status
    else:
        assert stored.last_execution_status == result.message


def test_an_indexer_that_cannot_be_asked_is_a_failed_run_not_a_pattern_without_matches():
    fake = FakeIndexer(CLUSTER, unreachable=True)

    [result], stored = run_schedule(fake, last_execution_time=a_while_ago())

    assert result.success is False
    assert stored.last_execution_status.startswith("FAILED: ")
    assert "indexer unreachable" in stored.last_execution_status
    assert fake.created == []


# --- creating and updating a schedule ----------------------------------------------------------

ADMIN = SimpleNamespace(id=1, username="admin", role_id=1)


def call_api(fake, scenario):
    async def _inner():
        db = await Db().create()
        api = FastAPI()
        api.include_router(wazuh_indexer_snapshots_router, prefix="/snapshots")

        async def _session():
            async with db.factory() as session:
                yield session

        async def resolve_user(self, request, username):
            return ADMIN if username == "admin" else None

        api.dependency_overrides[get_db] = _session
        try:
            with indexer_client(fake), patch.object(AuthHandler, "decode_token", lambda self, token: (token, ["admin"])), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=api),
                    base_url="http://test",
                    headers={"Authorization": "Bearer admin"},
                ) as http:
                    return await scenario(http, db)
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())


NEW_SCHEDULE = {"name": "Daily cold storage", "index_pattern": FULL_PATTERN, "repository": "cold", "interval_days": 1}


def test_creating_a_schedule_answers_how_many_indices_its_pattern_matches():
    async def scenario(http, db):
        response = await http.post("/snapshots/schedules", json=NEW_SCHEDULE)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["matching_index_count"] == 3
        assert "matches 3 indices right now" in body["message"]
        assert body["schedule"]["index_pattern"] == FULL_PATTERN

        response = await http.post("/snapshots/schedules", json={**NEW_SCHEDULE, "name": "Nothing yet", "index_pattern": "pfsense-*"})
        assert response.status_code == 200, response.text
        assert response.json()["matching_index_count"] == 0
        assert "matches no index right now" in response.json()["message"]

    call_api(FakeIndexer(CLUSTER), scenario)


def test_updating_a_pattern_answers_its_count_and_other_updates_ask_the_indexer_nothing():
    fake = FakeIndexer(CLUSTER)

    async def scenario(http, db):
        schedule_id = (await http.post("/snapshots/schedules", json=NEW_SCHEDULE)).json()["schedule"]["id"]
        listings = fake.listings

        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"index_pattern": "fortinet-*, -*-poc_*"})
        assert response.status_code == 200, response.text
        assert response.json()["matching_index_count"] == 1
        assert fake.listings == listings + 1

        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"enabled": False})
        assert response.status_code == 200, response.text
        assert response.json()["matching_index_count"] is None
        assert fake.listings == listings + 1

    call_api(fake, scenario)


def test_a_schedule_is_saved_even_when_the_indexer_cannot_count_its_matches():
    async def scenario(http, db):
        response = await http.post("/snapshots/schedules", json=NEW_SCHEDULE)
        assert response.status_code == 200, response.text
        assert response.json()["matching_index_count"] is None
        assert await db.count() == 1

    call_api(FakeIndexer(CLUSTER, unreachable=True), scenario)


def test_a_pattern_with_nothing_to_include_is_a_422_on_create_and_update():
    async def scenario(http, db):
        response = await http.post("/snapshots/schedules", json={**NEW_SCHEDULE, "index_pattern": "-wazuh-monitoring-*,-*-poc_*"})
        assert response.status_code == 422
        assert "only excludes" in response.text
        assert await db.count() == 0

        schedule_id = (await http.post("/snapshots/schedules", json=NEW_SCHEDULE)).json()["schedule"]["id"]
        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"index_pattern": " , "})
        assert response.status_code == 422
        assert "Enter an index pattern" in response.text
        assert (await db.get(schedule_id)).index_pattern == FULL_PATTERN

    call_api(FakeIndexer(CLUSTER), scenario)


# --- a manual snapshot's index list ------------------------------------------------------------


def test_a_manual_snapshot_list_expands_wildcards_honours_exclusions_and_keeps_names_as_written():
    assert expand_requested_indices(["fortinet-*", "-fortinet-poc_*", "wazuh-acme_30", "logs-alias"], CLUSTER) == [
        "fortinet-acme_12",
        "wazuh-acme_30",
        "logs-alias",
    ]
    # An entry may itself be a comma list; an index matched twice is listed once.
    assert expand_requested_indices(["fortinet-*, palo_alto-*", "fortinet-acme*"], CLUSTER) == [
        "fortinet-acme_12",
        "fortinet-poc_3",
        "palo_alto-globex_4",
    ]
    assert expand_requested_indices(["wazuh-monitoring-2026.48*"], ["wazuh-monitoring-2026x48w"]) == []


def test_a_manual_snapshot_no_longer_takes_an_index_it_excluded():
    # fortinet-poc_2 is not a write index (fortinet-poc_3 is), so only the exclusion keeps it out:
    # the old filter dropped "-fortinet-poc_*" and snapshotted it.
    fake = FakeIndexer(CLUSTER + ["fortinet-acme_11", "fortinet-poc_2"])

    async def _inner():
        with indexer_client(fake):
            return await snapshots.filter_write_indices(["fortinet-*", "-fortinet-poc_*"])

    to_snapshot, skipped = asyncio.run(_inner())
    assert to_snapshot == ["fortinet-acme_11"]
    assert skipped == ["fortinet-acme_12"]
