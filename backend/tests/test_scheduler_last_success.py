"""Every scheduled job records its success, without each job having to remember to (#1135).

`scheduled_job_metadata.last_success` used to be written by each job function, copy-pasted from
the one before. Five jobs were shipped without it — the four cache/sidebar refreshers from #1072
and `prune_audit_log` from #943 — so they ran correctly at their interval for months while the
scheduler UI and API reported `last_success: null`, making healthy jobs look like they had never
run once. A reporter on v0.1.90 had backend logs proving execution next to an API response saying
otherwise.

The stamp is now written centrally, in the scheduler's event listener, from APScheduler's own
verdict on whether the callable returned or raised. These tests pin the three things that makes
load-bearing:

* a job that returns is recorded, including one that deliberately did nothing this tick,
* a job that raises is not,
* and the listener is actually subscribed to the success event, which is the wiring that made
  the original bug invisible.

No DB, no network — the recorder is faked, and the one test that uses a real AsyncIOScheduler
runs an in-memory job.

Run with: cd backend && python -m pytest tests/test_scheduler_last_success.py
"""

import asyncio
import os
from datetime import datetime

import pytest
from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.events import EVENT_JOB_EXECUTED
from apscheduler.events import EVENT_JOB_MISSED
from apscheduler.events import JobExecutionEvent

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.schedulers import scheduler as scheduler_module  # noqa: E402
from app.schedulers.models.scheduler import JobMetadata  # noqa: E402
from app.schedulers.routes.scheduler import build_job_payload  # noqa: E402


class RecordedCalls:
    """Stands in for `record_job_success`, remembering which job ids it was asked to stamp."""

    def __init__(self):
        self.job_ids = []

    async def __call__(self, job_id):
        self.job_ids.append(job_id)
        return True


@pytest.fixture()
def recorder(monkeypatch):
    calls = RecordedCalls()
    monkeypatch.setattr(scheduler_module, "record_job_success", calls)
    return calls


def _event(code, job_id="some_job", exception=None):
    return JobExecutionEvent(
        code=code,
        job_id=job_id,
        jobstore="default",
        scheduled_run_time=datetime(2026, 1, 1, 12, 0, 0),
        exception=exception,
    )


async def _drain():
    """Let the listener's fire-and-forget task run to completion."""
    await asyncio.sleep(0)
    await asyncio.sleep(0)


def test_a_job_that_finished_is_recorded(recorder):
    async def scenario():
        scheduler_module.scheduler_listener(_event(EVENT_JOB_EXECUTED, "refresh_sidebar_health"))
        await _drain()

    asyncio.run(scenario())
    assert recorder.job_ids == ["refresh_sidebar_health"]


def test_a_job_that_did_nothing_this_tick_still_counts_as_a_success(recorder):
    """ "Cache still fresh, skipping" is a healthy run, and must not read as "never ran"."""

    async def scenario():
        # APScheduler cannot tell a no-op from any other completion: the callable returned.
        scheduler_module.scheduler_listener(_event(EVENT_JOB_EXECUTED, "refresh_catalog_caches"))
        await _drain()

    asyncio.run(scenario())
    assert recorder.job_ids == ["refresh_catalog_caches"]


def test_a_job_that_raised_is_not_recorded(recorder):
    async def scenario():
        scheduler_module.scheduler_listener(
            _event(EVENT_JOB_ERROR, "prune_audit_log", exception=RuntimeError("boom")),
        )
        await _drain()

    asyncio.run(scenario())
    assert recorder.job_ids == []


def test_a_missed_run_is_not_recorded(recorder):
    """A run that never happened is not a success, however healthy the job is."""

    async def scenario():
        scheduler_module.scheduler_listener(_event(EVENT_JOB_MISSED, "agent_sync"))
        await _drain()

    asyncio.run(scenario())
    assert recorder.job_ids == []


def test_the_listener_survives_being_called_without_an_event_loop(recorder):
    """A listener must never raise into whatever dispatched it."""
    scheduler_module.scheduler_listener(_event(EVENT_JOB_EXECUTED, "agent_sync"))
    assert recorder.job_ids == []


def test_the_scheduler_subscribes_the_listener_to_the_success_event():
    """The wiring is the fix: subscribing to failures alone is what hid the bug.

    Read from the source rather than by starting a scheduler, which would open a database
    connection and a job store.
    """
    import inspect

    source = inspect.getsource(scheduler_module.init_scheduler)
    assert "EVENT_JOB_EXECUTED" in source, "the listener must be subscribed to job-success events"
    assert "add_listener" in source


def test_a_real_scheduler_run_records_the_job(recorder):
    """End to end against a real AsyncIOScheduler, so the event wiring is not assumed.

    An in-memory job store and a trivial job: this asserts APScheduler actually emits the
    success event for a coroutine job and that the listener is reached.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    ran = asyncio.Event()

    async def job():
        ran.set()

    async def scenario():
        scheduler = AsyncIOScheduler()
        scheduler.add_listener(
            scheduler_module.scheduler_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )
        scheduler.add_job(job, "interval", seconds=0.1, id="e2e_job", max_instances=1)
        scheduler.start()
        try:
            await asyncio.wait_for(ran.wait(), timeout=5)
            # The success event and the recorder task both land after the job's own completion.
            for _ in range(50):
                if recorder.job_ids:
                    break
                await asyncio.sleep(0.05)
        finally:
            scheduler.shutdown(wait=False)

    asyncio.run(scenario())
    assert recorder.job_ids and recorder.job_ids[0] == "e2e_job"


def test_the_api_reports_the_persisted_timestamp():
    """The route projects whatever is on the row; a null there is what an operator saw."""

    class FakeJob:
        id = "refresh_sidebar_health"
        name = "refresh_sidebar_health"
        next_run_time = datetime(2026, 1, 1, 12, 0, 0)

    stamped = datetime(2026, 1, 1, 11, 59, 0)
    metadata = JobMetadata(
        job_id="refresh_sidebar_health",
        last_success=stamped,
        time_interval=6,
        enabled=True,
        job_description="…",
    )

    assert build_job_payload(FakeJob(), metadata)["last_success"] == stamped
    # No metadata row at all is the one case that legitimately reports null.
    assert build_job_payload(FakeJob(), None)["last_success"] is None
