"""Behavioural guarantees for the event-loop instrumentation (#1072).

The harness in app/middleware/performance.py exists to settle one question:
when a page is slow, was the backend's single event loop blocked, and by which
endpoint? Its whole value is that the answer is trustworthy, so the two claims
it makes are asserted here rather than taken on faith:

1. A fully-async workload is not accused of blocking (no false positives).
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

# Configuration is passed explicitly below rather than through the environment.
# The module constants are read at import time, so setting env vars here only
# worked when this file happened to be imported before any other test module —
# which pytest does not guarantee, and which made these tests fail only when run
# as part of the full suite.
SAMPLE_INTERVAL = 0.05
LOG_RETENTION = 3

from app.middleware.performance import LAG_STALL_THRESHOLD_MS  # noqa: E402
from app.middleware.performance import SLOW_REQUEST_MS  # noqa: E402
from app.middleware.performance import EventLoopLagMonitor  # noqa: E402
from app.middleware.performance import PerformanceRegistry  # noqa: E402
from app.middleware.performance import RequestTimingMiddleware  # noqa: E402
from app.middleware.performance import _route_template  # noqa: E402
from app.performance.services import session_log as session_log_module  # noqa: E402
from app.performance.services.session_log import PerformanceSessionLog  # noqa: E402

BLOCK_SECONDS = 0.4
FAST_SECONDS = 0.01


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


def test_async_workload_is_not_accused_of_blocking():
    """Well-behaved async handlers must not be reported as blocking the loop.

    Asserted on the *distribution*, not on a hard "zero stalls": a developer
    laptop or a loaded CI box genuinely stalls its own event loop now and then
    (GC, scheduler pressure), and the watchdog is right to report it. Demanding
    zero made this test fail ~10% of the time while the code was perfectly fine.
    A real blocking call stalls the loop on *every* pass, so it moves p95; a
    machine hiccup is a single outlier and does not.
    """

    async def scenario():
        registry = PerformanceRegistry()

        async def healthy():
            await asyncio.sleep(FAST_SECONDS)

        middleware = RequestTimingMiddleware(_asgi_app(healthy), registry)

        # Warm up before measuring: the first pass through a fresh process pays
        # one-off costs (lazy imports inside asyncio, the first loguru write)
        # that genuinely stall the loop and are not what this test is about.
        await _call(middleware, "/api/warmup")
        await asyncio.sleep(0.1)
        registry.reset()

        monitor = EventLoopLagMonitor(registry, interval=SAMPLE_INTERVAL)
        monitor.start()

        # Sustained load for a fixed window, so the number of lag samples does
        # not depend on how fast the machine gets through a request count.
        deadline = time.perf_counter() + 1.2
        while time.perf_counter() < deadline:
            await asyncio.gather(*[_call(middleware, "/api/fast") for _ in range(10)])
        await monitor.stop()
        return registry

    registry = asyncio.run(scenario())

    assert registry.total_requests > 0

    samples = sorted(registry.lag_samples)
    assert len(samples) >= 10, f"too few lag samples to judge: {len(samples)}"
    p95 = samples[int(round(0.95 * (len(samples) - 1)))]
    assert p95 < LAG_STALL_THRESHOLD_MS, f"async work appears to block the loop: p95={p95:.0f}ms"

    # Each request asked for 10ms; none should have been dragged out anywhere
    # near the length of a real blocking call.
    slowest = max(record.duration_ms for record in registry.recent_requests)
    assert slowest < BLOCK_SECONDS * 1000, f"async request took {slowest:.0f}ms"


def test_blocking_call_is_detected_sized_and_attributed():
    """A blocking call inside an `async def` is the failure mode from #1072."""

    async def scenario():
        registry = PerformanceRegistry()
        monitor = EventLoopLagMonitor(registry, interval=SAMPLE_INTERVAL)
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


def test_a_disconnect_after_the_response_is_not_counted_as_abandoned():
    """Only requests the client walked away from count (#1072).

    Since level 1, ClientDisconnectMiddleware pumps the receive channel, so the
    ordinary connection close at the end of every served request now reaches the
    timing wrapper too. Counting those made `client_disconnects` read 36 in a
    session where only 9 requests were actually abandoned — the metric said users
    were leaving constantly while they were being served fine.
    """

    async def scenario():
        registry = PerformanceRegistry()

        async def answers_then_sees_the_hangup(scope, receive, send):
            # Exactly the shape level 1 produces: the response goes out, and the
            # disconnect arrives afterwards while something is still reading the
            # channel.
            scope.update({"endpoint": None, "path_params": {}})
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})
            await receive()

        middleware = RequestTimingMiddleware(answers_then_sees_the_hangup, registry)

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            pass

        await middleware({"type": "http", "method": "GET", "path": "/api/x"}, receive, send)
        return registry

    registry = asyncio.run(scenario())

    record = registry.recent_requests[-1]
    assert record.status_code == 200
    assert not record.client_disconnected, "a disconnect after a 200 is not an abandoned request"
    assert registry.total_disconnects == 0


def test_a_disconnect_before_the_response_is_counted():
    """The real case: the client left while we were still working."""

    async def scenario():
        registry = PerformanceRegistry()

        async def never_answers(scope, receive, send):
            # Reads the body, then the client hangs up before anything is sent.
            await receive()
            await receive()

        middleware = RequestTimingMiddleware(never_answers, registry)

        messages = [
            {"type": "http.request", "body": b"", "more_body": False},
            {"type": "http.disconnect"},
        ]

        async def receive():
            return messages.pop(0)

        async def send(message):
            pass

        await middleware({"type": "http", "method": "GET", "path": "/api/x"}, receive, send)
        return registry

    registry = asyncio.run(scenario())

    record = registry.recent_requests[-1]
    assert record.status_code == 0, "no response was ever started"
    assert record.client_disconnected
    assert registry.total_disconnects == 1


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


def test_session_log_prunes_old_files_but_keeps_the_new_one(tmp_path, monkeypatch):
    """`uvicorn --reload` can create hundreds of sessions a day."""
    monkeypatch.setattr(session_log_module, "PERF_LOG_RETENTION", LOG_RETENTION)
    for index in range(4):
        (tmp_path / f"perf-2020010{index}-000000-pid{index}.jsonl").write_text("{}\n")

    registry = PerformanceRegistry()
    session = PerformanceSessionLog(registry)
    path = session.start(log_dir=str(tmp_path))

    remaining = sorted(item.name for item in tmp_path.glob("perf-*.jsonl"))
    assert len(remaining) == LOG_RETENTION
    assert path.name in remaining
    # The oldest went first.
    assert "perf-20200100-000000-pid0.jsonl" not in remaining

    asyncio.run(session.stop())
