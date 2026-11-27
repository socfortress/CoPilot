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
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from elasticsearch7.exceptions import ConnectionTimeout  # noqa: E402
from elasticsearch7.exceptions import NotFoundError  # noqa: E402
from elasticsearch7.exceptions import TransportError  # noqa: E402
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

    def __init__(self, names, existing_snapshots=(), unreachable=False, delete_errors=None, snapshots_unreadable=False):
        self.names = list(names)
        self.existing_snapshots = list(existing_snapshots)
        self.unreachable = unreachable
        self.delete_errors = dict(delete_errors or {})
        self.snapshots_unreadable = snapshots_unreadable
        self.listings = 0
        self.snapshot_listings = 0
        self.created = []
        self.deleted = []
        self.delete_timeouts = []
        # Snapshot creations and deletions in the order they were asked for.
        self.calls = []
        self.indices = SimpleNamespace(get_alias=self._get_alias)
        self.snapshot = SimpleNamespace(get=self._get_snapshots, create=self._create, delete=self._delete)

    def _get_alias(self, index):
        self.listings += 1
        if self.unreachable:
            raise ConnectionError("indexer unreachable")
        assert index == "*"
        return {name: {"aliases": {}} for name in self.names}

    def _get_snapshots(self, repository, snapshot, ignore_unavailable):
        self.snapshot_listings += 1
        if self.snapshots_unreadable:
            raise ConnectionError("repository unreadable")
        return {"snapshots": self.existing_snapshots}

    def _create(self, repository, snapshot, body, wait_for_completion):
        self.created.append({"repository": repository, "snapshot": snapshot, "body": body})
        self.calls.append(("create", snapshot))
        return {"accepted": True}

    def _delete(self, repository, snapshot, request_timeout):
        assert repository == "cold"
        self.calls.append(("delete", snapshot))
        self.delete_timeouts.append(request_timeout)
        if snapshot in self.delete_errors:
            raise self.delete_errors[snapshot]
        self.deleted.append(snapshot)
        return {"acknowledged": True}


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


# --- retention ---------------------------------------------------------------------------------

SCHEDULE_ID = 7
# The run matches these and has fortinet-acme_11 to snapshot (the newest index of each set is a write index).
RUN_CLUSTER = CLUSTER + ["fortinet-acme_11"]


def scheduled_snapshot(days_ago, *, schedule_id=SCHEDULE_ID, prefix=SCHEDULE_PREFIX, state="SUCCESS", metadata=True, dated=True):
    """A snapshot as GET _snapshot/<repository>/_all lists it, named and tagged as the schedule's run would."""
    started = datetime.now(timezone.utc) - timedelta(days=days_ago)
    entry = {"snapshot": f"{prefix}{started:%Y%m%d_%H%M%S}", "state": state, "indices": []}
    if dated:
        entry["start_time_in_millis"] = int(started.timestamp() * 1000)
    if metadata:
        entry["metadata"] = {"schedule_id": schedule_id, "schedule_name": "Daily cold storage", "created_by": "scheduled_job"}
    return entry


def run_with_retention(fake, **overrides):
    fields = dict(id=SCHEDULE_ID, retention_days=30, last_execution_time=a_while_ago())
    fields.update(overrides)
    [result], stored = run_schedule(fake, **fields)
    return result, stored


def test_retention_deletes_only_this_schedules_finished_snapshots_past_the_limit_oldest_first():
    kept = [
        scheduled_snapshot(29),  # not old enough
        scheduled_snapshot(60, state="IN_PROGRESS"),  # deleting it would abort it
        scheduled_snapshot(61, state=None),  # a state we can't read
        scheduled_snapshot(62, dated=False),  # no start time to judge its age by
        scheduled_snapshot(90, schedule_id=8),  # another schedule's, or another deployment's
        scheduled_snapshot(91, metadata=False),  # named like ours, made by hand
        # Schedule "Daily cold storage archive": its names begin with our prefix too.
        scheduled_snapshot(92, prefix="scheduled_daily_cold_storage_archive_"),
    ]
    expired = [scheduled_snapshot(40), scheduled_snapshot(400, state="FAILED"), scheduled_snapshot(31, state="PARTIAL")]
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=kept + expired)

    result, stored = run_with_retention(fake)

    assert fake.deleted == [expired[1]["snapshot"], expired[0]["snapshot"], expired[2]["snapshot"]]
    assert fake.delete_timeouts == [snapshots.RETENTION_DELETE_TIMEOUT_SECONDS] * 3
    # Before this run's own snapshot starts.
    assert [kind for kind, _ in fake.calls] == ["delete", "delete", "delete", "create"]
    assert result.success is True
    assert stored.last_execution_status == "SUCCESS: retention deleted 3 snapshots older than 30 days"
    assert stored.last_snapshot_name == fake.created[0]["snapshot"]


def test_retention_also_runs_when_there_is_nothing_new_to_snapshot():
    expired = scheduled_snapshot(45)
    fake = FakeIndexer(CLUSTER, existing_snapshots=[expired])

    result, stored = run_with_retention(fake)

    assert fake.deleted == [expired["snapshot"]]
    assert fake.created == []
    assert stored.last_execution_status == (
        "SKIPPED: No new indices to snapshot (3 write indices skipped); retention deleted 1 snapshot older than 30 days"
    )
    assert result.message.endswith("; retention deleted 1 snapshot older than 30 days")


def test_without_retention_days_nothing_is_deleted():
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=[scheduled_snapshot(4000)])

    result, stored = run_with_retention(fake, retention_days=None)

    assert fake.deleted == []
    # Only the lookup of what is already snapshotted read the repository.
    assert fake.snapshot_listings == 1
    assert stored.last_execution_status == "SUCCESS"


@pytest.mark.parametrize("case", ["deferred", "no match", "indexer unreachable"])
def test_retention_deletes_nothing_on_a_run_that_matched_no_indices(case):
    fields = {}
    if case == "deferred":
        fields["last_execution_time"] = datetime.utcnow()
    if case == "no match":
        fields["index_pattern"] = "pfsense-*"
    fake = FakeIndexer(CLUSTER, existing_snapshots=[scheduled_snapshot(45)], unreachable=case == "indexer unreachable")

    run_with_retention(fake, **fields)

    assert fake.deleted == []
    assert fake.snapshot_listings == 0


def test_a_deletion_that_fails_is_reported_and_the_others_go_ahead():
    first, second, third = scheduled_snapshot(50), scheduled_snapshot(40), scheduled_snapshot(35)
    refused = TransportError(500, "repository_exception", {"error": "the bucket refused the delete"})
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=[first, second, third], delete_errors={second["snapshot"]: refused})

    result, stored = run_with_retention(fake)

    assert fake.deleted == [first["snapshot"], third["snapshot"]]
    assert result.success is True
    assert stored.last_execution_status == (
        "SUCCESS: retention deleted 2 snapshots older than 30 days; retention could not delete 1 snapshot (see the log)"
    )


def test_a_deletion_that_outlasts_its_timeout_ends_this_runs_deletions():
    # A deletion waits for any snapshot still writing to the repository; every later one would too.
    first, second, third = scheduled_snapshot(50), scheduled_snapshot(40), scheduled_snapshot(35)
    timed_out = ConnectionTimeout("TIMEOUT", "read timed out", TimeoutError("read timed out"))
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=[first, second, third], delete_errors={first["snapshot"]: timed_out})

    result, stored = run_with_retention(fake)

    assert [name for kind, name in fake.calls if kind == "delete"] == [first["snapshot"]]
    assert fake.created, "the run's own snapshot still starts"
    assert stored.last_execution_status == (
        f"SUCCESS: the indexer is still deleting {first['snapshot']} for retention; 2 more past retention left for the next run"
    )


def test_a_snapshot_already_gone_counts_as_deleted():
    gone = scheduled_snapshot(50)
    missing = NotFoundError(404, "snapshot_missing_exception", {})
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=[gone], delete_errors={gone["snapshot"]: missing})

    result, stored = run_with_retention(fake)

    assert stored.last_execution_status == "SUCCESS: retention deleted 1 snapshot older than 30 days"


def test_retention_deletes_at_most_its_cap_in_one_run_oldest_first(monkeypatch):
    monkeypatch.setattr(snapshots, "RETENTION_MAX_DELETES_PER_RUN", 2)
    expired = [scheduled_snapshot(days) for days in (31, 32, 33, 34, 35)]
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=expired)

    result, stored = run_with_retention(fake)

    assert fake.deleted == [expired[4]["snapshot"], expired[3]["snapshot"]]
    assert stored.last_execution_status == (
        "SUCCESS: retention deleted 2 snapshots older than 30 days; 3 more past retention left for the next run"
    )


def test_retention_stops_when_its_time_budget_is_spent(monkeypatch):
    monkeypatch.setattr(snapshots, "RETENTION_TIME_BUDGET_SECONDS", 0)
    fake = FakeIndexer(RUN_CLUSTER, existing_snapshots=[scheduled_snapshot(31), scheduled_snapshot(32)])

    result, stored = run_with_retention(fake)

    assert fake.deleted == []
    assert stored.last_execution_status == "SUCCESS: 2 past retention left for the next run"


def test_retention_that_cannot_read_the_repository_never_fails_the_run():
    fake = FakeIndexer(RUN_CLUSTER, snapshots_unreadable=True)

    result, stored = run_with_retention(fake)

    assert result.success is True
    assert fake.created
    assert stored.last_execution_status == "SUCCESS: retention could not read the repository's snapshots (see the log)"


def test_the_retention_cutoff_does_not_move_with_the_servers_timezone():
    # datetime.utcnow().timestamp() reads a UTC time as local time: on a server west of UTC the old
    # cutoff landed hours late, and snapshots short of their retention went too.
    schedule = SimpleNamespace(id=SCHEDULE_ID, name="Daily cold storage", snapshot_prefix="scheduled", repository="cold", retention_days=30)
    older, younger = scheduled_snapshot(30 + 1 / 24), scheduled_snapshot(30 - 1 / 24)
    fake = FakeIndexer([], existing_snapshots=[older, younger])

    async def _inner():
        with indexer_client(fake):
            return await snapshots.cleanup_old_snapshots(schedule)

    previous = os.environ.get("TZ")
    os.environ["TZ"] = "America/Los_Angeles"
    time.tzset()
    try:
        result = asyncio.run(_inner())
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()

    assert result.deleted == [older["snapshot"]]


@pytest.mark.parametrize("days", [0, -1, 36501])
def test_a_retention_outside_one_day_to_a_hundred_years_is_refused(days):
    # A negative one would put the cutoff in the future and delete every snapshot.
    with pytest.raises(ValidationError):
        SnapshotScheduleCreate(name="Daily cold storage", index_pattern="wazuh-*", repository="cold", retention_days=days)
    with pytest.raises(ValidationError):
        SnapshotScheduleUpdate(retention_days=days)


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


def test_clearing_retention_in_an_update_stops_it_and_other_updates_keep_it():
    # The form sends retention_days: null for "keep forever"; the update used to ignore it, so
    # a schedule kept deleting after its retention was cleared.
    async def scenario(http, db):
        response = await http.post("/snapshots/schedules", json={**NEW_SCHEDULE, "retention_days": 30})
        schedule_id = response.json()["schedule"]["id"]

        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"enabled": False})
        assert response.status_code == 200, response.text
        assert response.json()["schedule"]["retention_days"] == 30

        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"retention_days": None})
        assert response.status_code == 200, response.text
        assert response.json()["schedule"]["retention_days"] is None
        assert (await db.get(schedule_id)).retention_days is None

        response = await http.put(f"/snapshots/schedules/{schedule_id}", json={"retention_days": 0})
        assert response.status_code == 422

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
