"""A Velociraptor action must not freeze the rest of CoPilot (#1226).

pyvelociraptor is synchronous gRPC. Every service called it straight from an
`async def`, so the call held the backend's single event loop for as long as
Velociraptor took to answer -- and waiting for a flow means waiting for the
endpoint, up to VELOCIRAPTOR_FLOW_TIMEOUT (300s). While a command ran, every
other request queued behind it and the reverse proxy answered them with 504s.
Reproduced against the lab server: a `sleep 45` Linux.Sys.BashShell command held
`GET /incidents/db_operations/alerts` for 47s; with the fix it answered in ~1s
throughout.

These tests pin the three properties that fix rests on:

* the `*_async` methods leave the loop free while gRPC blocks;
* flow waits draw from their own allowance, so a burst of slow collections
  queues behind itself instead of exhausting the pool every connector shares;
* no coroutine in the backend calls the blocking methods directly again.

Run with: cd backend && python -m pytest tests/test_velociraptor_offloading.py
"""

import ast
import asyncio
import json
import os
import pathlib
import threading
import time
from types import SimpleNamespace

import anyio
import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.connectors.velociraptor.utils.universal as universal  # noqa: E402

BLOCK_SECONDS = 0.4


class _SlowStub:
    """Stands in for `api_pb2_grpc.APIStub`: blocks the calling thread like real gRPC."""

    def __init__(self, seconds=BLOCK_SECONDS):
        self.seconds = seconds
        self.active = 0
        self.peak = 0
        self._lock = threading.Lock()

    def Query(self, request, timeout=None):  # noqa: N802 - mirrors the gRPC method name
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self.seconds)
            yield SimpleNamespace(Response=json.dumps([{"ok": True}]), log="")
        finally:
            with self._lock:
                self.active -= 1


def _service(stub):
    service = universal.UniversalService()
    service.stub = stub
    return service


async def _ticks_during(work):
    """Count heartbeats a concurrent "request" managed while `work` ran."""
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.05)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    result = await work()
    beat.cancel()
    return ticks, result


def test_sync_query_from_a_coroutine_freezes_the_loop():
    """The bug -- asserted so the test below cannot pass vacuously."""
    service = _service(_SlowStub())

    async def work():
        return service.execute_query("SELECT 1 FROM scope()")

    ticks, _ = asyncio.run(_ticks_during(work))

    assert ticks <= 1, f"a blocking gRPC call should starve concurrent work, got {ticks} ticks"


@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.execute_query_async("SELECT 1 FROM scope()"),
        lambda s: s.watch_flow_completion_async("F.CQMNTHE1CSPKC"),
        lambda s: s.read_collection_results_async("C.c4e8798fbab1d9c6", "F.CQMNTHE1CSPKC", artifact="Linux.Sys.BashShell"),
    ],
    ids=["query", "flow_wait", "read_results"],
)
def test_async_methods_leave_the_loop_free(call):
    service = _service(_SlowStub())

    ticks, result = asyncio.run(_ticks_during(lambda: call(service)))

    # One tick per 50ms over a 400ms call: ~8 when the loop is free.
    assert ticks >= 5, f"concurrent work should keep its schedule, got {ticks} ticks"
    assert result["success"] is True
    assert result["results"] == [{"ok": True}]


def test_async_query_keeps_the_error_mapping():
    """Offloading must not change what callers see: a deadline is still the 504."""
    import grpc
    from fastapi import HTTPException

    class _DeadlineError(grpc.RpcError):
        def code(self):
            return grpc.StatusCode.DEADLINE_EXCEEDED

        def details(self):
            return "Deadline Exceeded"

    class _ExpiringStub:
        def Query(self, request, timeout=None):  # noqa: N802
            raise _DeadlineError()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(_service(_ExpiringStub()).execute_query_async("SELECT 1 FROM scope()"))

    assert exc.value.status_code == 504


def test_flow_waits_have_their_own_allowance(monkeypatch):
    """Past the allowance, flow waits queue behind each other -- and ordinary queries
    are not stuck behind them, because they never draw from it."""
    monkeypatch.setattr(universal, "_flow_wait_limiter", anyio.CapacityLimiter(2))
    flow_stub = _SlowStub()
    query_stub = _SlowStub(seconds=0.05)

    async def scenario():
        waits = [_service(flow_stub).watch_flow_completion_async("F.CQMNTHE1CSPKC") for _ in range(4)]
        started = time.monotonic()
        wait_tasks = [asyncio.create_task(w) for w in waits]
        await asyncio.sleep(0.05)
        query_started = time.monotonic()
        await _service(query_stub).execute_query_async("SELECT 1 FROM scope()")
        query_seconds = time.monotonic() - query_started
        await asyncio.gather(*wait_tasks)
        return time.monotonic() - started, query_seconds

    total, query_seconds = asyncio.run(scenario())

    assert flow_stub.peak == 2, f"at most 2 flow waits should hold a thread at once, saw {flow_stub.peak}"
    assert total >= 2 * BLOCK_SECONDS * 0.9, "four waits through an allowance of two take two rounds"
    assert query_seconds < BLOCK_SECONDS, "an ordinary query must not queue behind flow waits"


def test_flow_wait_allowance_is_configurable(monkeypatch):
    import importlib

    monkeypatch.setenv("VELOCIRAPTOR_MAX_CONCURRENT_FLOW_WAITS", "7")
    try:
        module = importlib.reload(universal)
        assert module.FLOW_WAIT_CONCURRENCY == 7
        assert module._flow_wait_limiter.total_tokens == 7
    finally:
        monkeypatch.delenv("VELOCIRAPTOR_MAX_CONCURRENT_FLOW_WAITS")
        importlib.reload(universal)


# --- Guard: no coroutine calls the blocking methods directly ------------------------

BLOCKING_METHODS = {"execute_query", "watch_flow_completion", "read_collection_results"}
APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"


def _blocking_calls_in_coroutines(tree):
    """Yield (lineno, name) for un-awaited calls to a blocking method inside an `async def`.

    Nested sync functions and lambdas are skipped: they are what gets handed to a
    worker thread (`to_thread(_read_uploads, svc, ...)`). An awaited call is skipped
    too: `await MCPService.execute_query(...)` is an unrelated coroutine.
    """

    def visit(node, in_coroutine, awaited):
        if isinstance(node, (ast.FunctionDef, ast.Lambda)):
            in_coroutine = False
        elif isinstance(node, ast.AsyncFunctionDef):
            in_coroutine = True
        if (
            in_coroutine
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in BLOCKING_METHODS
            and node not in awaited
        ):
            yield node.lineno, node.func.attr
        for child in ast.iter_child_nodes(node):
            yield from visit(child, in_coroutine, awaited)

    awaited = {n.value for n in ast.walk(tree) if isinstance(n, ast.Await)}
    yield from visit(tree, False, awaited)


def test_no_coroutine_calls_velociraptor_synchronously():
    offenders = []
    for path in APP_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for lineno, name in _blocking_calls_in_coroutines(tree):
            offenders.append(f"{path.relative_to(APP_ROOT.parent)}:{lineno} {name}()")

    assert not offenders, (
        "Blocking Velociraptor calls inside async functions hold the event loop for the whole "
        "gRPC call (#1226). Use the *_async method instead:\n  " + "\n  ".join(sorted(offenders))
    )


def test_the_guard_catches_the_old_shape():
    """The scan above must recognise the pattern it exists to forbid."""
    old = (
        "async def run_remote_command(body):\n"
        "    svc = await UniversalService.create('Velociraptor')\n"
        "    flow = svc.execute_query('q')\n"
        "    done = svc.watch_flow_completion('F.X')\n"
        "    def offloaded():\n"
        "        return svc.execute_query('q')\n"
        "    return await MCPService.execute_query(flow)\n"
    )

    found = [name for _, name in _blocking_calls_in_coroutines(ast.parse(old))]

    assert found == ["execute_query", "watch_flow_completion"]
