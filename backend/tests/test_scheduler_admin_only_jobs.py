"""Jobs only an admin may add, run, start, pause, reschedule or delete (``schedulers/routes/scheduler.py``:
``ADMIN_ONLY_JOBS``, ``refuse_unless_admin_for``; review of talon-analyst plan OJ-5).

The Talon ops poller (``invoke_talon_ops_notifications``) talks to talon-analyst as an admin with every
customer, and pausing, deleting or rescheduling it silently stops the SOC's ops notifications. The
scheduler routes are admin/analyst by token, so each one that changes or runs a job checks the job by
its id, its name and its function's name, and by the caller's database role, before changing anything.
Other jobs are unchanged: an analyst still manages them.

Real route functions, a fake APScheduler; no database (``manage_job_metadata`` is replaced).

Run with: cd backend && python -m pytest tests/test_scheduler_admin_only_jobs.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

from app.schedulers.routes import scheduler as routes  # noqa: E402

OPS = "invoke_talon_ops_notifications"
OTHER = "notify_sla_transitions"
ADMIN = SimpleNamespace(id=1, role_id=1)
ANALYST = SimpleNamespace(id=2, role_id=2)
RESPONDER = SimpleNamespace(id=5, role_id=5)


async def _ops_job():
    return None


async def _other_job():
    return None


async def _poller_under_another_name():
    return None


# What APScheduler records as the job's function: the poller itself, whatever the job is called.
_poller_under_another_name.__name__ = OPS


class FakeJob:
    def __init__(self, job_id, name, func):
        self.id, self.name, self.func = job_id, name, func
        self.calls = []

    def resume(self):
        self.calls.append("resume")

    def pause(self):
        self.calls.append("pause")

    def reschedule(self, **kwargs):
        self.calls.append("reschedule")


class FakeScheduler:
    running = True

    def __init__(self, jobs):
        self.jobs = {job.id: job for job in jobs}
        self.added, self.removed = [], []

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def get_jobs(self):
        return list(self.jobs.values())

    def add_job(self, func, *args, id, **kwargs):
        self.added.append(id)

    def remove_job(self, job_id):
        self.removed.append(job_id)


@pytest.fixture
def scheduler(monkeypatch):
    jobs = [
        FakeJob(OPS, OPS, _ops_job),
        FakeJob(OTHER, OTHER, _other_job),
        # The poller under another id: its name and function still say what it is.
        FakeJob("renamed", OPS, _ops_job),
        FakeJob("renamed_func", "something_else", _poller_under_another_name),
    ]
    fake = FakeScheduler(jobs)
    monkeypatch.setattr(routes, "get_scheduler_instance", AsyncMock(return_value=fake))
    monkeypatch.setattr(routes, "manage_job_metadata", AsyncMock())
    monkeypatch.setattr(routes, "get_function_by_name", lambda name: AsyncMock(return_value=None))
    return fake


def _call(route, job_id, user):
    session = AsyncMock()
    calls = {
        "add": lambda: routes.add_job(job_id, OTHER if job_id != OPS else OPS, 5, None, session, user),
        "run": lambda: routes.run_job_manually(job_id, session, user),
        "start": lambda: routes.start_job(job_id, user),
        "pause": lambda: routes.pause_job(job_id, user),
        "update": lambda: routes.update_job(job_id, 9, None, session, user),
        "delete": lambda: routes.delete_job(job_id, session, user),
    }
    return asyncio.run(calls[route]())


ROUTES = ["add", "run", "start", "pause", "update", "delete"]


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("user", [ANALYST, RESPONDER], ids=["analyst", "responder"])
def test_an_analyst_is_refused_on_the_ops_poller_and_nothing_changes(scheduler, route, user):
    with pytest.raises(HTTPException) as refused:
        _call(route, OPS, user)
    assert refused.value.status_code == 403
    assert scheduler.added == [] and scheduler.removed == []
    assert scheduler.jobs[OPS].calls == []
    routes.manage_job_metadata.assert_not_awaited()


@pytest.mark.parametrize("route", ROUTES)
def test_an_admin_passes_on_the_ops_poller(scheduler, route):
    result = _call(route, OPS, ADMIN)
    assert result["success"] is True
    if route == "add":
        assert scheduler.added == [OPS]
    elif route == "delete":
        assert scheduler.removed == [OPS]
    elif route in ("start", "pause", "update"):
        assert scheduler.jobs[OPS].calls == [{"start": "resume", "pause": "pause", "update": "reschedule"}[route]]


@pytest.mark.parametrize("route", ROUTES)
def test_an_analyst_still_manages_any_other_job(scheduler, route):
    assert _call(route, OTHER, ANALYST)["success"] is True


@pytest.mark.parametrize("route", ["run", "start", "pause", "update", "delete"])
@pytest.mark.parametrize("job_id", ["renamed", "renamed_func"])
def test_the_poller_is_recognised_by_its_name_or_function_whatever_its_id(scheduler, route, job_id):
    with pytest.raises(HTTPException) as refused:
        _call(route, job_id, ANALYST)
    assert refused.value.status_code == 403


def test_adding_a_job_that_runs_the_poller_or_replaces_it_needs_an_admin(scheduler):
    # A new id with the poller's function.
    with pytest.raises(HTTPException):
        asyncio.run(routes.add_job("innocent", OPS, 5, None, AsyncMock(), ANALYST))
    # The poller's id replaced with another function (replace_existing=True would drop the poller).
    with pytest.raises(HTTPException):
        asyncio.run(routes.add_job(OPS, OTHER, 5, None, AsyncMock(), ANALYST))
    # An existing id whose job is the poller under another name.
    with pytest.raises(HTTPException):
        asyncio.run(routes.add_job("renamed", OTHER, 5, None, AsyncMock(), ANALYST))
    assert scheduler.added == []
    assert asyncio.run(routes.add_job("innocent", OPS, 5, None, AsyncMock(), ADMIN))["success"] is True


def test_the_role_is_the_databases_not_the_tokens(scheduler):
    """A demoted admin (role analyst, an old token with the admin scope) is refused."""
    demoted = SimpleNamespace(id=4, role_id=2, scopes=["admin"])
    with pytest.raises(HTTPException):
        _call("pause", OPS, demoted)


def test_every_route_that_changes_or_runs_a_job_calls_the_guard():
    import inspect

    for name in ("add_job", "run_job_manually", "start_job", "pause_job", "update_job", "delete_job"):
        source = inspect.getsource(getattr(routes, name))
        assert "refuse_unless_admin_for(current_user" in source, name
        assert "current_user" in inspect.signature(getattr(routes, name)).parameters, name
