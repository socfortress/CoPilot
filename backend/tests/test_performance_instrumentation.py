"""Behavioural guarantees for the event-loop instrumentation (#1072).

The harness in app/middleware/performance.py exists to settle one question:
when a page is slow, was the backend's single event loop blocked, and by which
endpoint? Its whole value is that the answer is trustworthy, so the two claims
it makes are asserted here rather than taken on faith:

1. A fully-async workload produces **no** stalls (no false accusations).
2. A synchronous/blocking call inside an `async def` handler is detected, sized
   correctly, attributed to the endpoint that made it, and shown to have
   inflated an unrelated concurrent request.

Claim 2 is the exact mechanism behind the issue: the reporter sees an unrelated
page take seconds, and cancelling the previous fetch client-side does not help
because the loop - not the request - is the thing that is stuck.

No DB, no network: a fake ASGI app is driven through the real middleware.

Run with: cd backend && python -m pytest tests/test_performance_instrumentation.py
"""

import asyncio
import json
import os
import time

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
# A short watchdog interval keeps the test fast; the stall threshold is left at
# the production default so the assertions exercise the shipped configuration.
os.environ.setdefault("PERF_LAG_SAMPLE_INTERVAL", "0.05")
# Small retention so the pruning test stays legible.
os.environ.setdefault("PERF_LOG_RETENTION", "3")

from app.middleware.performance import LAG_STALL_THRESHOLD_MS  # noqa: E402
from app.middleware.performance import SLOW_REQUEST_MS  # noqa: E402
from app.middleware.performance import EventLoopLagMonitor  # noqa: E402
from app.middleware.performance import PerformanceRegistry  # noqa: E402
from app.middleware.performance import RequestTimingMiddleware  # noqa: E402
from app.middleware.performance import _route_template  # noqa: E402
from app.performance.services.session_log import PERF_LOG_RETENTION  # noqa: E402
from app.performance.services.session_log import PerformanceSessionLog  # noqa: E402

BLOCK_SECONDS = 0.4
FAST_SECONDS = 0.01
PERF_LOG_RETENTION_FOR_TEST = PERF_LOG_RETENTION


def _asgi_app(behaviour, path_params=None):
    """Minimal ASGI app that runs `behaviour` then replies 200.

    It merges `path_params` into the scope exactly the way Starlette's router
    does (`scope.update(child_scope)` in `Router.app`), so the middleware
    exercises its real route-template reconstruction rather than a stand-in.
    """

    async def app(scope, receive, send):
        await behaviour()
        scope.update({"endpoint": behaviour, "path_params": dict(path_params or {})})
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return app


async def _call(middleware, path):
    scope = {"type": "http", "method": "GET", "path": path}
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)
    return sent


def _endpoints_by_key(registry):
    return {f"{stats.method} {stats.path}": stats for stats in registry.endpoints}


def test_async_workload_reports_no_stalls():
    """Well-behaved async handlers must never be reported as blocking."""

    async def scenario():
        registry = PerformanceRegistry()
        monitor = EventLoopLagMonitor(registry)
        monitor.start()

        async def healthy():
            await asyncio.sleep(FAST_SECONDS)

        middleware = RequestTimingMiddleware(_asgi_app(healthy), registry)
        await asyncio.gather(*[_call(middleware, "/api/fast") for _ in range(10)])
        await asyncio.sleep(0.2)
        await monitor.stop()
        return registry

    registry = asyncio.run(scenario())

    assert registry.total_requests == 10
    assert registry.total_stalls == 0, f"false positive: {registry.stalls}"
    assert registry.max_lag_ms < LAG_STALL_THRESHOLD_MS


def test_blocking_call_is_detected_sized_and_attributed():
    """A blocking call inside an `async def` is the failure mode from #1072."""

    async def scenario():
        registry = PerformanceRegistry()
        monitor = EventLoopLagMonitor(registry)
        monitor.start()

        async def blocking():
            # Stands in for `requests.get(...)` inside an async connector helper.
            time.sleep(BLOCK_SECONDS)

        async def fast():
            await asyncio.sleep(FAST_SECONDS)

        culprit = RequestTimingMiddleware(_asgi_app(blocking), registry)
        victim = RequestTimingMiddleware(_asgi_app(fast), registry)

        # Order matters: gather runs the victim up to its first await, so it is
        # suspended-but-in-flight when the blocking handler seizes the loop.
        await asyncio.gather(
            _call(victim, "/api/healthcheck"),
            _call(culprit, "/api/wazuh_manager/rules"),
        )
        await asyncio.sleep(0.2)
        await monitor.stop()
        return registry

    registry = asyncio.run(scenario())

    # 1. Detected, and sized to the length of the block (allowing for the
    #    watchdog only observing the portion after its last successful wakeup).
    assert registry.total_stalls >= 1
    assert registry.max_lag_ms >= BLOCK_SECONDS * 1000 * 0.5

    # 2. The blocking endpoint is named among the stall's suspects.
    suspects = " | ".join(entry for stall in registry.stalls for entry in stall.suspects)
    assert "/api/wazuh_manager/rules" in suspects, suspects

    # 3. Stall time is attributed to it in the endpoint table.
    endpoints = _endpoints_by_key(registry)
    blocker = endpoints["GET /api/wazuh_manager/rules"]
    assert blocker.stall_hits >= 1
    assert blocker.stalled_ms > 0

    # 4. The unrelated request paid for it — this is what the user perceives.
    victim = endpoints["GET /api/healthcheck"]
    assert victim.max_ms > BLOCK_SECONDS * 1000 * 0.5, (
        f"the victim only waited {victim.max_ms:.0f}ms; it should have been dragged out "
        f"to roughly the {BLOCK_SECONDS * 1000:.0f}ms block"
    )


def test_timing_header_is_emitted():
    """Server-side duration is exposed so it can be compared with the browser's."""

    async def scenario():
        registry = PerformanceRegistry()

        async def fast():
            await asyncio.sleep(0)

        middleware = RequestTimingMiddleware(_asgi_app(fast), registry)
        return await _call(middleware, "/api/x")

    messages = asyncio.run(scenario())
    start = next(message for message in messages if message["type"] == "http.response.start")
    header_names = {key.decode().lower() for key, _ in start["headers"]}

    assert "x-process-time-ms" in header_names
    assert "x-request-id" in header_names


def test_route_template_is_rebuilt_from_path_params():
    """Concrete paths must collapse to their route template.

    Starlette contributes only `endpoint` and `path_params` to the scope - never
    the route object - so the template is reconstructed from the matched values.
    Getting this wrong is not a crash: it silently gives every customer code and
    alert id its own row until the endpoint cap is hit and real data is dropped.
    """
    # Single string param — the case a digit-based heuristic would miss entirely.
    assert (
        _route_template(
            {"path_params": {"customer_code": "SOC01"}},
            "/api/customers/SOC01/agents",
        )
        == "/api/customers/{customer_code}/agents"
    )

    # Several params of mixed type in one path.
    assert (
        _route_template(
            {"path_params": {"customer_code": "SOC01", "alert_id": 4211}},
            "/api/customers/SOC01/alerts/4211",
        )
        == "/api/customers/{customer_code}/alerts/{alert_id}"
    )

    # A `:path` converter spans several segments — the Detection Catalog's story
    # names contain spaces and slashes.
    assert (
        _route_template(
            {"path_params": {"story_name": "Cloud/Ransomware Activity"}},
            "/api/copilot_searches/catalog/stories/Cloud/Ransomware Activity",
        )
        == "/api/copilot_searches/catalog/stories/{story_name}"
    )

    # Unmatched request (404, static mount): no params, so the heuristic runs and
    # must still keep an id from opening its own row.
    assert _route_template({}, "/static/42/thing") == "/static/{id}/thing"


def test_reset_clears_counters_without_losing_in_flight_requests():
    """`POST /performance/reset` must give a clean before/after on a live process."""
    registry = PerformanceRegistry()
    entry = registry.start_request("GET", "/api/slow")

    registry.reset()

    assert registry.total_requests == 0
    assert registry.total_stalls == 0
    # The in-flight request survives, so its eventual completion is still
    # accounted for instead of referencing an entry the registry forgot.
    assert [flight.request_id for flight in registry.in_flight] == [entry.request_id]

    registry.finish_request(entry, 200, "/api/slow", False)
    assert registry.total_requests == 1
    assert registry.in_flight == []


def test_session_log_records_a_full_timeline(tmp_path):
    """A session file must be self-describing and survive a killed process.

    Each record is flushed as it happens, so the assertions below read the file
    while the session is still open — exactly what a `docker kill` or a
    `--reload` restart would leave behind.
    """
    registry = PerformanceRegistry()
    session = PerformanceSessionLog(registry)

    path = session.start(log_dir=str(tmp_path))
    assert path is not None and path.exists()

    # A stall and a slow request reach disk without waiting for shutdown.
    entry = registry.start_request("GET", "/api/wazuh_manager/rules")
    entry.started_mono -= 5.0  # pretend it has been running for 5s
    registry.finish_request(entry, 200, "/api/wazuh_manager/rules", False)
    registry.record_lag(time.perf_counter() - 1.0, time.perf_counter(), 850.0)

    mid_session = [json.loads(line) for line in path.read_text().splitlines()]
    types_seen = [record["type"] for record in mid_session]
    assert types_seen[0] == "session_start"
    assert "slow_request" in types_seen
    assert "stall" in types_seen

    # The config is recorded, not assumed, so the file stays readable after a
    # default changes.
    config = mid_session[0]["config"]
    assert config["lag_stall_threshold_ms"] == LAG_STALL_THRESHOLD_MS
    assert config["slow_request_ms"] == SLOW_REQUEST_MS

    stall = next(record for record in mid_session if record["type"] == "stall")
    assert stall["lag_ms"] == 850.0
    assert any("/api/wazuh_manager/rules" in suspect for suspect in stall["suspects"])

    asyncio.run(session.stop())

    final = [json.loads(line) for line in path.read_text().splitlines()]
    end = final[-1]
    assert end["type"] == "session_end"
    assert end["summary"]["loop_lag"]["stalls"] == 1
    assert end["summary"]["requests"]["total"] == 1
    assert end["summary"]["top_endpoints"][0]["path"] == "/api/wazuh_manager/rules"

    # Every line is valid JSON with a timestamp — the file is machine-readable
    # end to end, which is the whole point of comparing sessions later.
    assert all("ts" in record and "type" in record for record in final)


def test_session_log_reset_records_what_it_discarded(tmp_path):
    """A zeroed counter must never be mistaken for a quiet period."""
    registry = PerformanceRegistry()
    session = PerformanceSessionLog(registry)
    path = session.start(log_dir=str(tmp_path))

    entry = registry.start_request("GET", "/api/x")
    registry.finish_request(entry, 200, "/api/x", False)
    registry.reset()

    records = [json.loads(line) for line in path.read_text().splitlines()]
    reset = next(record for record in records if record["type"] == "reset")
    assert reset["discarded_total_requests"] == 1

    asyncio.run(session.stop())


def test_session_log_never_breaks_the_server(tmp_path):
    """Instrumentation failures must degrade to "no file", never to an error."""
    # An unwritable location must not raise out of start().
    blocked = tmp_path / "file-not-a-dir"
    blocked.write_text("occupied")
    registry = PerformanceRegistry()
    session = PerformanceSessionLog(registry)

    assert session.start(log_dir=str(blocked / "nested")) is None
    # ...and the registry stays fully usable with no sink attached.
    entry = registry.start_request("GET", "/api/x")
    registry.finish_request(entry, 200, "/api/x", False)
    assert registry.total_requests == 1

    # A sink that throws is swallowed rather than propagated into the request path.
    def exploding_sink(event_type, payload):
        raise RuntimeError("disk on fire")

    registry.event_sink = exploding_sink
    registry.record_lag(time.perf_counter() - 1.0, time.perf_counter(), 900.0)
    assert registry.total_stalls == 1

    asyncio.run(session.stop())


def test_session_log_prunes_old_files_but_keeps_the_new_one(tmp_path):
    """`uvicorn --reload` can create hundreds of sessions a day."""
    for index in range(4):
        (tmp_path / f"perf-2020010{index}-000000-pid{index}.jsonl").write_text("{}\n")

    registry = PerformanceRegistry()
    session = PerformanceSessionLog(registry)
    path = session.start(log_dir=str(tmp_path))

    remaining = sorted(item.name for item in tmp_path.glob("perf-*.jsonl"))
    assert len(remaining) == PERF_LOG_RETENTION_FOR_TEST
    assert path.name in remaining
    # The oldest went first.
    assert "perf-20200100-000000-pid0.jsonl" not in remaining

    asyncio.run(session.stop())
