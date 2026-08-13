"""The event loop must survive a blocking connector call (#1072).

The backend runs one uvicorn process with one event loop while ~780 endpoints are
`async def`. A synchronous call inside one of them — `requests.get(...)` against
Wazuh, a sync `Elasticsearch` search — stops the loop, so every concurrent
request waits for it. The session logs measured the loop blocked ~6% of the time,
with individual stalls up to 4.7s.

`app.blocking.run_blocking` moves such calls to anyio's worker pool. This test
asserts the property that matters, using the #1072 watchdog itself as the
measuring instrument: with the offload in place, a 400ms blocking call produces
no event-loop stall, and unrelated concurrent work keeps running on time.

Run with: cd backend && python -m pytest tests/test_blocking_offloading.py
"""

import asyncio
import os
import time

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

# Passed explicitly, not via the environment: the module constant is read at
# import time, so an env var here only takes effect when this file is imported
# before every other test module — which pytest does not guarantee.
SAMPLE_INTERVAL = 0.05

from app.blocking import run_blocking  # noqa: E402
from app.middleware.performance import LAG_STALL_THRESHOLD_MS  # noqa: E402
from app.middleware.performance import EventLoopLagMonitor  # noqa: E402
from app.middleware.performance import PerformanceRegistry  # noqa: E402

BLOCK_SECONDS = 0.4


async def _measure(work):
    """Run `work` under the lag watchdog and report what the loop experienced."""
    registry = PerformanceRegistry()
    monitor = EventLoopLagMonitor(registry, interval=SAMPLE_INTERVAL)
    monitor.start()
    await asyncio.sleep(0.15)  # let the watchdog reach steady state

    ticks = 0

    async def heartbeat():
        """Stands in for another request being served concurrently."""
        nonlocal ticks
        while True:
            await asyncio.sleep(0.05)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    await work()
    beat.cancel()

    await asyncio.sleep(0.15)
    await monitor.stop()
    return registry, ticks


def test_direct_blocking_call_stalls_the_loop():
    """The failure mode being fixed — asserted so the test above cannot pass vacuously."""

    async def scenario():
        async def work():
            time.sleep(BLOCK_SECONDS)  # what `requests.get(...)` does today

        return await _measure(work)

    registry, ticks = asyncio.run(scenario())

    assert registry.total_stalls >= 1, "a blocking call on the loop must be detected as a stall"
    assert registry.max_lag_ms >= BLOCK_SECONDS * 1000 * 0.5
    # The concurrent "request" was frozen for the whole block: at one tick per
    # 50ms it should have managed ~8 during a 400ms window.
    assert ticks <= 2, f"concurrent work should have been starved, got {ticks} ticks"


def test_offloaded_blocking_call_leaves_the_loop_free():
    """The fix: same 400ms call, no stall, concurrent work keeps its schedule."""

    async def scenario():
        async def work():
            await run_blocking(time.sleep, BLOCK_SECONDS)

        return await _measure(work)

    registry, ticks = asyncio.run(scenario())

    assert registry.total_stalls == 0, f"offloaded call still stalled the loop: {registry.stalls}"
    assert registry.max_lag_ms < LAG_STALL_THRESHOLD_MS
    # Roughly 400ms / 50ms of heartbeats got through while the thread waited.
    assert ticks >= 5, f"concurrent work should have kept running, got {ticks} ticks"


def test_run_blocking_preserves_return_values_and_exceptions():
    """Call sites keep their exact shape: same result, same exception type."""

    async def scenario():
        result = await run_blocking(lambda: "value")

        positional = await run_blocking(lambda a, b: a + b, 2, 3)

        def with_kwargs(a, *, b):
            return a * b

        keyword = await run_blocking(with_kwargs, 4, b=5)

        def boom():
            raise ValueError("original error")

        try:
            await run_blocking(boom)
            raised = None
        except ValueError as exc:  # must propagate unchanged, not be wrapped
            raised = exc

        return result, positional, keyword, raised

    result, positional, keyword, raised = asyncio.run(scenario())

    assert result == "value"
    assert positional == 5
    assert keyword == 20
    assert isinstance(raised, ValueError)
    assert str(raised) == "original error"


def test_blocking_calls_run_concurrently_with_each_other():
    """Several offloaded calls share the pool instead of queueing one behind another."""

    async def scenario():
        started = time.perf_counter()
        await asyncio.gather(*[run_blocking(time.sleep, 0.2) for _ in range(5)])
        return time.perf_counter() - started

    elapsed = asyncio.run(scenario())

    # Serialised they would take ~1s; in the pool they overlap.
    assert elapsed < 0.6, f"offloaded calls did not overlap: {elapsed:.2f}s for 5x200ms"
