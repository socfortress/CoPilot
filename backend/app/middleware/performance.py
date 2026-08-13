"""Runtime performance instrumentation for the CoPilot backend.

This module exists to answer one question with numbers instead of intuition:
**is the event loop being blocked, and which endpoint is blocking it?**

Context (issue #1072). The backend runs as a *single* uvicorn process with a
*single* event loop (`copilot.py:__main__` -> `uvicorn.run(app)`), while ~780
endpoints are declared `async def`. Any blocking call made from inside one of
those coroutines - the `requests.*` calls in the connector `universal.py`
helpers, the synchronous `Elasticsearch` client - stalls *every* concurrent
request, not just its own. From the browser this is indistinguishable from
"the backend is slow": the user navigates away, aborts the fetch, and the next
page still waits. A frontend timing harness cannot see the cause; this can.

Three signals are collected, all in-memory, all bounded, none persisted:

* **event-loop lag** - a watchdog task sleeps `LAG_SAMPLE_INTERVAL` and measures
  how late it actually woke up. On a healthy loop the drift is sub-millisecond;
  a blocking call shows up as drift equal to the length of the block.
* **stall attribution** - when the drift crosses `LAG_STALL_THRESHOLD_MS`, every
  request whose lifetime overlaps the stall window is recorded as a suspect.
  This is what turns "the backend is slow" into "GET /api/wazuh_manager/...
  blocked the loop for 4.2s". Attribution is by time overlap, so a stall with
  several requests in flight names all of them - repeated samples are what
  isolate the real culprit.
* **per-request timing** - duration, status, and the concurrency level at
  completion, plus the lag observed while the request was in flight.

There is deliberately no table and no migration: this is a measurement harness,
not a feature. `POST /performance/reset` zeroes the counters so a before/after
comparison can be taken against the same running process.
"""

import asyncio
import os
import time
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from typing import Callable
from typing import Deque
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"PERF: invalid float for {name}={raw!r}, using default {default}")
        return default


def _env_int(name: str, default: int) -> int:
    return int(_env_float(name, float(default)))


# Master switch. Left ON by default: the overhead is a handful of microseconds
# per request (two perf_counter calls and a dict insert/pop) and the whole point
# is to have the numbers available on a real deployment, not only in a lab.
PERF_MONITOR_ENABLED = _env_flag("PERF_MONITOR_ENABLED", True)

# How often the watchdog wakes. 250ms keeps the task cost negligible while still
# resolving stalls down to roughly a quarter second.
LAG_SAMPLE_INTERVAL = _env_float("PERF_LAG_SAMPLE_INTERVAL", 0.25)

# Drift above this is treated as "the loop was blocked". A healthy asyncio loop
# drifts by well under 10ms; 100ms is comfortably above scheduler noise and well
# below anything a user would notice, so it catches blocking early.
LAG_STALL_THRESHOLD_MS = _env_float("PERF_LAG_STALL_THRESHOLD_MS", 100.0)

# Requests slower than this are counted separately and kept in the recent list.
SLOW_REQUEST_MS = _env_float("PERF_SLOW_REQUEST_MS", 1000.0)

# Ring buffer sizes - these bound the memory this module can ever use.
RECENT_REQUESTS = _env_int("PERF_RECENT_REQUESTS", 500)
RECENT_STALLS = _env_int("PERF_RECENT_STALLS", 200)
LAG_SAMPLES = _env_int("PERF_LAG_SAMPLES", 2000)
DURATION_SAMPLES = _env_int("PERF_DURATION_SAMPLES", 200)

# Cap on distinct (method, path) keys tracked. Route templates are low
# cardinality, but an unmatched 404 path is not - see _normalise_path.
MAX_ENDPOINTS = _env_int("PERF_MAX_ENDPOINTS", 500)

_OVERFLOW_KEY = "OTHER"


@dataclass
class _InFlight:
    """A request currently being served."""

    request_id: int
    method: str
    raw_path: str
    started_mono: float
    started_wall: float
    blocked_ms: float = 0.0
    stall_hits: int = 0


@dataclass
class RequestRecord:
    """A completed request, kept in a bounded ring buffer."""

    request_id: int
    method: str
    path: str
    status_code: int
    duration_ms: float
    started_wall: float
    started_mono: float
    ended_mono: float
    concurrency: int
    blocked_ms: float
    stall_hits: int
    client_disconnected: bool


@dataclass
class StallRecord:
    """One detected event-loop stall, with the requests that overlapped it."""

    at_wall: float
    lag_ms: float
    window_ms: float
    concurrency: int
    suspects: List[str]


@dataclass
class EndpointStats:
    """Rolling aggregates for one (method, route template) pair."""

    method: str
    path: str
    count: int = 0
    error_count: int = 0
    slow_count: int = 0
    disconnects: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    stall_hits: int = 0
    stalled_ms: float = 0.0
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=DURATION_SAMPLES))

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"


def _normalise_path(raw_path: str) -> str:
    """Collapse identifier-looking segments so unmatched paths stay low cardinality.

    Only used when Starlette did not attach a matched route to the scope (404s,
    static mounts). Matched requests report their real route template instead.
    """
    parts = []
    for segment in raw_path.split("/"):
        if not segment:
            parts.append(segment)
            continue
        if segment.isdigit():
            parts.append("{id}")
        elif len(segment) >= 16 and all(c in "0123456789abcdefABCDEF-" for c in segment):
            parts.append("{uuid}")
        else:
            parts.append(segment)
    return "/".join(parts) or "/"


def _route_template(scope: Scope, raw_path: str) -> str:
    """Recover the route template so the endpoint table stays low cardinality.

    Starlette does **not** put the matched route object in the scope - `Route.matches`
    contributes only `endpoint` and `path_params`, which `Router.app` merges in with
    `scope.update(child_scope)` before handing off. So the template is rebuilt by
    substituting each matched parameter value back out of the concrete path:
    `/api/customers/SOC01/agents` -> `/api/customers/{customer_code}/agents`.

    This must be called *after* the downstream app has run, otherwise the routing
    has not happened yet and `path_params` is absent.

    Without this, every distinct customer code, story name and alert id would open
    its own row in the endpoint table and blow through MAX_ENDPOINTS. Unmatched
    requests (404s, static mounts) have no params and fall back to a heuristic.
    """
    params = scope.get("path_params") or {}
    if not params:
        return _normalise_path(raw_path)

    # value -> placeholder, skipping empties which would match every segment.
    replacements = {str(value): f"{{{name}}}" for name, value in params.items() if str(value)}

    segments = [replacements.get(segment, segment) for segment in raw_path.split("/")]
    template = "/".join(segments)

    # `:path` converters (e.g. the Detection Catalog's story names) swallow slashes,
    # so their value spans several segments and the per-segment pass above misses
    # it. Those are substituted whole, longest first so a short value cannot eat
    # part of a longer one.
    multi_segment = sorted((v for v in replacements if "/" in v), key=len, reverse=True)
    for value in multi_segment:
        template = template.replace(value, replacements[value])

    return template


class PerformanceRegistry:
    """In-memory, single-event-loop store for the collected signals.

    No locking: every mutation happens on the event loop thread (the ASGI
    middleware and the watchdog task both run there), so plain attribute
    updates are already atomic with respect to each other.
    """

    def __init__(self) -> None:
        self._in_flight: Dict[int, _InFlight] = {}
        self._next_id = 0
        # Optional consumer of notable events, set by the session logger so
        # stalls reach disk as they happen rather than only at shutdown. A plain
        # attribute rather than a subscriber list: there is exactly one consumer,
        # and see _emit for why its failures must never escape.
        self.event_sink: Optional[Callable[[str, dict], None]] = None
        self._reset_counters()

    def _emit(self, event_type: str, payload: dict) -> None:
        """Hand an event to the sink, swallowing anything it throws.

        This runs on the request path and inside the watchdog. A full disk or a
        permissions problem in the logger must degrade to "no session file",
        never to a failed request or a dead watchdog.
        """
        sink = self.event_sink
        if sink is None:
            return
        try:
            sink(event_type, payload)
        except Exception as exc:
            logger.warning(f"PERF: session log sink failed on {event_type}: {exc}")

    def _reset_counters(self) -> None:
        self.started_wall = time.time()
        self.started_mono = time.perf_counter()
        self._recent: Deque[RequestRecord] = deque(maxlen=RECENT_REQUESTS)
        self._stalls: Deque[StallRecord] = deque(maxlen=RECENT_STALLS)
        self._endpoints: Dict[str, EndpointStats] = {}
        self._lag_samples: Deque[float] = deque(maxlen=LAG_SAMPLES)
        self.total_requests = 0
        self.total_slow = 0
        self.total_errors = 0
        self.total_disconnects = 0
        self.total_stalls = 0
        self.total_stalled_ms = 0.0
        self.max_lag_ms = 0.0
        self.max_concurrency = len(self._in_flight)
        self.dropped_endpoints = 0

    def reset(self) -> None:
        """Zero every counter while leaving in-flight requests tracked.

        In-flight entries are deliberately preserved: dropping them would leak
        the ids and make the next `finish_request` account for a request the
        registry no longer knows about.
        """
        # Emitted before zeroing so the session file records what was discarded -
        # otherwise a reset mid-session looks indistinguishable from a quiet
        # period when the timeline is read back later.
        self._emit(
            "reset",
            {
                "discarded_uptime_seconds": round(self.uptime_seconds, 2),
                "discarded_total_requests": self.total_requests,
                "discarded_total_stalls": self.total_stalls,
                "discarded_max_lag_ms": round(self.max_lag_ms, 2),
            },
        )
        self._reset_counters()

    # ── request lifecycle ────────────────────────────────────────────────

    def start_request(self, method: str, raw_path: str) -> _InFlight:
        self._next_id += 1
        entry = _InFlight(
            request_id=self._next_id,
            method=method,
            raw_path=raw_path,
            started_mono=time.perf_counter(),
            started_wall=time.time(),
        )
        self._in_flight[entry.request_id] = entry
        if len(self._in_flight) > self.max_concurrency:
            self.max_concurrency = len(self._in_flight)
        return entry

    def finish_request(
        self,
        entry: _InFlight,
        status_code: int,
        path: str,
        client_disconnected: bool,
    ) -> RequestRecord:
        self._in_flight.pop(entry.request_id, None)
        ended_mono = time.perf_counter()
        duration_ms = (ended_mono - entry.started_mono) * 1000.0

        record = RequestRecord(
            request_id=entry.request_id,
            method=entry.method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            started_wall=entry.started_wall,
            started_mono=entry.started_mono,
            ended_mono=ended_mono,
            concurrency=len(self._in_flight) + 1,
            blocked_ms=entry.blocked_ms,
            stall_hits=entry.stall_hits,
            client_disconnected=client_disconnected,
        )
        self._recent.append(record)

        self.total_requests += 1
        stats = self._stats_for(entry.method, path)
        stats.count += 1
        stats.total_ms += duration_ms
        stats.samples.append(duration_ms)
        if duration_ms > stats.max_ms:
            stats.max_ms = duration_ms
        if status_code >= 500:
            self.total_errors += 1
            stats.error_count += 1
        if duration_ms >= SLOW_REQUEST_MS:
            self.total_slow += 1
            stats.slow_count += 1
            self._emit(
                "slow_request",
                {
                    "method": entry.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "concurrency": record.concurrency,
                    "blocked_ms": round(entry.blocked_ms, 2),
                    "stall_hits": entry.stall_hits,
                    "client_disconnected": client_disconnected,
                },
            )
        if client_disconnected:
            self.total_disconnects += 1
            stats.disconnects += 1
        # Stall time attributed while this request was still in flight is folded
        # into the endpoint totals here, so the endpoint table and the stall log
        # never disagree.
        if entry.stall_hits:
            stats.stall_hits += entry.stall_hits
            stats.stalled_ms += entry.blocked_ms
        return record

    def _stats_for(self, method: str, path: str) -> EndpointStats:
        key = f"{method} {path}"
        existing = self._endpoints.get(key)
        if existing is not None:
            return existing
        if len(self._endpoints) >= MAX_ENDPOINTS:
            self.dropped_endpoints += 1
            overflow = self._endpoints.get(_OVERFLOW_KEY)
            if overflow is None:
                overflow = EndpointStats(method="*", path=_OVERFLOW_KEY)
                self._endpoints[_OVERFLOW_KEY] = overflow
            return overflow
        created = EndpointStats(method=method, path=path)
        self._endpoints[key] = created
        return created

    # ── event-loop lag ───────────────────────────────────────────────────

    def record_lag(self, window_start: float, window_end: float, lag_ms: float) -> None:
        self._lag_samples.append(lag_ms)
        if lag_ms > self.max_lag_ms:
            self.max_lag_ms = lag_ms
        if lag_ms < LAG_STALL_THRESHOLD_MS:
            return

        self.total_stalls += 1
        self.total_stalled_ms += lag_ms
        suspects = self._attribute_stall(window_start, window_end, lag_ms)
        stall = StallRecord(
            at_wall=time.time(),
            lag_ms=lag_ms,
            window_ms=(window_end - window_start) * 1000.0,
            concurrency=len(self._in_flight),
            suspects=suspects,
        )
        self._stalls.append(stall)
        self._emit(
            "stall",
            {
                "lag_ms": round(lag_ms, 2),
                "window_ms": round(stall.window_ms, 2),
                "concurrency": stall.concurrency,
                "suspects": suspects,
            },
        )
        logger.warning(
            "PERF: event loop blocked for {lag:.0f}ms - in flight during the stall: {suspects}",
            lag=lag_ms,
            suspects=", ".join(suspects) if suspects else "<none observed>",
        )

    def _attribute_stall(self, window_start: float, window_end: float, lag_ms: float) -> List[str]:
        """Name every request whose lifetime overlaps the stall window.

        Both still-running and just-completed requests are considered. The
        just-completed half matters: a blocking call that returns and lets its
        handler finish before the watchdog is rescheduled would otherwise be
        invisible - which is precisely the blocking-call case we are hunting.
        """
        suspects: List[str] = []

        for entry in self._in_flight.values():
            if entry.started_mono > window_end:
                continue
            entry.stall_hits += 1
            entry.blocked_ms += lag_ms
            age_ms = (window_end - entry.started_mono) * 1000.0
            suspects.append(f"{entry.method} {_normalise_path(entry.raw_path)} (running, {age_ms:.0f}ms)")

        # `_recent` is append-on-completion, so it is ordered by ended_mono.
        for record in reversed(self._recent):
            if record.ended_mono < window_start:
                break
            if record.started_mono > window_end:
                continue
            record.stall_hits += 1
            record.blocked_ms += lag_ms
            stats = self._stats_for(record.method, record.path)
            stats.stall_hits += 1
            stats.stalled_ms += lag_ms
            suspects.append(f"{record.method} {record.path} (finished, {record.duration_ms:.0f}ms)")

        return suspects

    def record_event(self, event_type: str, payload: dict) -> None:
        """Append an arbitrary diagnostic record to the session log.

        For findings a request timer cannot express — "which of these 14
        indicators cost the 6 seconds?". Cheap and safe to call from a request
        path: it degrades to a no-op when session logging is off, and a failing
        sink is swallowed (see `_emit`).
        """
        self._emit(event_type, payload)

    # ── read-side snapshots ──────────────────────────────────────────────

    @property
    def in_flight(self) -> List[_InFlight]:
        return list(self._in_flight.values())

    @property
    def recent_requests(self) -> List[RequestRecord]:
        return list(self._recent)

    @property
    def stalls(self) -> List[StallRecord]:
        return list(self._stalls)

    @property
    def endpoints(self) -> List[EndpointStats]:
        return list(self._endpoints.values())

    @property
    def lag_samples(self) -> List[float]:
        return list(self._lag_samples)

    @property
    def uptime_seconds(self) -> float:
        return time.perf_counter() - self.started_mono


class RequestTimingMiddleware:
    """Pure-ASGI request timer.

    Deliberately *not* a `BaseHTTPMiddleware`: that base class wraps every
    response in an anyio task group, which adds real per-request overhead and
    has a long history of interfering with streaming responses - and CoPilot
    streams (Talon chat over SSE, `sseClient.ts` on the frontend). A plain ASGI
    callable forwards the message stream untouched.
    """

    def __init__(self, app: ASGIApp, registry: "PerformanceRegistry") -> None:
        self.app = app
        self.registry = registry

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_path = scope.get("path", "/")
        entry = self.registry.start_request(scope.get("method", "?"), raw_path)
        state = {"status": 0, "disconnected": False}

        async def wrapped_receive() -> Message:
            message = await receive()
            if message["type"] == "http.disconnect":
                state["disconnected"] = True
            return message

        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                elapsed_ms = (time.perf_counter() - entry.started_mono) * 1000.0
                # Surfaced so server time can be compared against total time in
                # the browser Network tab without correlating logs by hand.
                headers = MutableHeaders(scope=message)
                headers.append("X-Process-Time-Ms", f"{elapsed_ms:.1f}")
                headers.append("X-Request-Id", str(entry.request_id))
            await send(message)

        try:
            await self.app(scope, wrapped_receive, wrapped_send)
        except asyncio.CancelledError:
            # The client went away (or a future disconnect-aware middleware
            # cancelled us). Counted as a disconnect, not as a 500.
            state["disconnected"] = True
            raise
        except Exception:
            if state["status"] == 0:
                state["status"] = 500
            raise
        finally:
            self.registry.finish_request(
                entry,
                state["status"],
                _route_template(scope, raw_path),
                bool(state["disconnected"]),
            )


class EventLoopLagMonitor:
    """Watchdog task that measures how late `asyncio.sleep` actually returns.

    This is the whole diagnosis in one number. The task itself does nothing but
    sleep, so any delay in being rescheduled is time the event loop spent unable
    to run anything - i.e. time it was blocked inside synchronous code.
    """

    def __init__(self, registry: "PerformanceRegistry", interval: Optional[float] = None) -> None:
        self.registry = registry
        # Explicit interval beats reading the module constant at call time: tests
        # need a short one, and depending on an env var read at import time makes
        # the result depend on which test module imported this one first.
        self.interval = LAG_SAMPLE_INTERVAL if interval is None else interval
        self._task: Optional[asyncio.Task] = None

    async def _run(self) -> None:
        interval = self.interval
        while True:
            start = time.perf_counter()
            await asyncio.sleep(interval)
            end = time.perf_counter()
            lag_ms = max(0.0, (end - start - interval) * 1000.0)
            try:
                self.registry.record_lag(start, end, lag_ms)
            except Exception as exc:  # never let instrumentation kill the loop
                logger.error(f"PERF: lag monitor failed to record a sample: {exc}")

    def start(self) -> None:
        if not PERF_MONITOR_ENABLED:
            logger.info("PERF: monitoring disabled via PERF_MONITOR_ENABLED, lag monitor not started")
            return
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="event-loop-lag-monitor")
        logger.info(
            f"PERF: event loop lag monitor started (interval={LAG_SAMPLE_INTERVAL}s, " f"stall threshold={LAG_STALL_THRESHOLD_MS}ms)",
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(f"PERF: lag monitor stopped with an error: {exc}")
        finally:
            self._task = None
            logger.info("PERF: event loop lag monitor stopped")


# Process-wide singletons. The registry is imported by the read-side service
# layer; the monitor is started and stopped from the app lifespan.
performance_registry = PerformanceRegistry()
lag_monitor = EventLoopLagMonitor(performance_registry)
