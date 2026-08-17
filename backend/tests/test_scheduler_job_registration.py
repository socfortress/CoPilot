"""A scheduled job must be registered in both places, or the app will not start.

Adding a job takes two edits that live ~150 lines apart:

1. `known_jobs` in `initialize_job_metadata` — seeds the `scheduled_job_metadata`
   row that makes the job appear and be enabled.
2. `function_map` in `get_function_by_name` — resolves the job id to the callable.

Miss the second and the job used to be handed a fallback lambda, which
APScheduler cannot pickle into its SQLAlchemy jobstore. The result was not a
skipped job: `scheduler.start()` raised and the whole application refused to
boot, with an error naming an anonymous lambda and nothing else.

These tests close that gap: the two registries must agree, and an unmapped job
must fail loudly and specifically rather than producing an unpicklable object.

Run with: cd backend && python -m pytest tests/test_scheduler_job_registration.py
"""

import ast
import asyncio
import inspect
import os
import pathlib

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.schedulers import scheduler as scheduler_module  # noqa: E402

SCHEDULER_SOURCE = pathlib.Path(scheduler_module.__file__)


def _known_job_ids():
    """Job ids from `known_jobs`, read from the source.

    Parsed rather than called: `initialize_job_metadata` opens a database
    session, and this property should be checkable without one.
    """
    tree = ast.parse(SCHEDULER_SOURCE.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if node.name != "initialize_job_metadata":
            continue
        for assignment in ast.walk(node):
            if not isinstance(assignment, ast.Assign):
                continue
            targets = [t.id for t in assignment.targets if isinstance(t, ast.Name)]
            if "known_jobs" not in targets or not isinstance(assignment.value, ast.List):
                continue
            ids = []
            for element in assignment.value.elts:
                if not isinstance(element, ast.Dict):
                    continue
                for key, value in zip(element.keys, element.values):
                    if isinstance(key, ast.Constant) and key.value == "job_id":
                        ids.append(value.value)
            return ids
    raise AssertionError("known_jobs not found in initialize_job_metadata")


def test_every_seeded_job_resolves_to_a_callable():
    """The two registries must agree — this is the check that was missing."""
    missing = []
    for job_id in _known_job_ids():
        try:
            scheduler_module.get_function_by_name(job_id)
        except ValueError:
            missing.append(job_id)

    assert not missing, (
        f"these jobs are seeded into scheduled_job_metadata but absent from "
        f"get_function_by_name's function_map, so the scheduler cannot start: {missing}"
    )


def test_resolved_jobs_are_real_functions_not_lambdas():
    """APScheduler needs a `module:function` reference it can pickle."""
    for job_id in _known_job_ids():
        function = scheduler_module.get_function_by_name(job_id)

        assert callable(function)
        # A lambda is exactly what broke startup: it has no importable reference.
        assert function.__name__ != "<lambda>", f"{job_id} resolves to a lambda"
        assert inspect.getmodule(function) is not None, f"{job_id} has no importable module"


def test_unmapped_job_raises_a_specific_error():
    """The caller catches ValueError per job, so one bad row must not stop boot."""
    with pytest.raises(ValueError) as excinfo:
        scheduler_module.get_function_by_name("a_job_that_does_not_exist")

    message = str(excinfo.value)
    assert "function_map" in message
    assert "known_jobs" in message


def test_wazuh_rules_cache_refresh_is_scheduled_below_the_cache_ttl():
    """A refresh slower than the TTL would let the cache expire under a request.

    The whole point of the job (#1072) is that a cold load — measured at 80–110s
    against a real Wazuh Manager — never lands on a user request.
    """
    from app.integrations.copilot_searches.services.wazuh_rules_cache import (
        CACHE_TTL_MINUTES,
    )

    tree = ast.parse(SCHEDULER_SOURCE.read_text())
    interval = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        entries = {key.value: value for key, value in zip(node.keys, node.values) if isinstance(key, ast.Constant)}
        job_id = entries.get("job_id")
        if isinstance(job_id, ast.Constant) and job_id.value == "refresh_wazuh_rules_cache":
            interval = entries["time_interval"].value

    assert interval is not None, "the refresh job is no longer seeded"
    assert interval < CACHE_TTL_MINUTES, (
        f"refresh runs every {interval} min but the cache goes stale after "
        f"{CACHE_TTL_MINUTES} min, so requests would still pay for a cold load"
    )


def _job_interval(job_id):
    tree = ast.parse(SCHEDULER_SOURCE.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        entries = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
        found = entries.get("job_id")
        if isinstance(found, ast.Constant) and found.value == job_id:
            return entries["time_interval"].value
    return None


def test_every_warming_job_runs_more_often_than_the_ttl_it_feeds():
    """A job slower than its TTL lets the value expire under a request.

    That is the whole point of these jobs (#1072): the request path reads a value
    somebody else paid for. If the interval ever creeps past the TTL, requests
    silently start paying again — a regression with no error and no crash, only a
    return of the latency we spent this work removing.
    """
    from app.status.services.context import SHARED_INDICATORS_TTL_SECONDS
    from app.status.services.context_indicators import _INFLUX_INDICATOR_TTL_SECONDS

    for job_id, ttl_seconds in (
        ("refresh_sidebar_indicators", SHARED_INDICATORS_TTL_SECONDS),
        ("refresh_sidebar_health", _INFLUX_INDICATOR_TTL_SECONDS),
    ):
        interval_minutes = _job_interval(job_id)
        assert interval_minutes is not None, f"{job_id} is no longer seeded"
        assert interval_minutes * 60 < ttl_seconds, (
            f"{job_id} runs every {interval_minutes} min but the value it feeds " f"expires after {ttl_seconds}s"
        )


def test_the_background_refresh_is_gentler_than_the_request_path():
    """Nobody waits for the job, so it must not compete as hard as a request."""
    from app.status.services.context import INDICATOR_CONCURRENCY
    from app.status.services.context import SHARED_REFRESH_CONCURRENCY

    assert SHARED_REFRESH_CONCURRENCY < INDICATOR_CONCURRENCY
    assert SHARED_REFRESH_CONCURRENCY >= 1


def test_refresh_job_is_a_coroutine_function():
    """`schedule_enabled_jobs` branches on this to add the job correctly."""
    function = scheduler_module.get_function_by_name("refresh_wazuh_rules_cache")
    assert asyncio.iscoroutinefunction(function)
