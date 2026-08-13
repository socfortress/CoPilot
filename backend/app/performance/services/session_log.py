"""Per-session performance log files, written for later cross-session analysis.

One file per server start, under `backend/logs/performance/` by default. The
point is comparison over time: measure a session before the blocking calls are
moved off the event loop (#1072), measure another after, and diff them - which
is only possible if each run leaves a durable, self-describing artefact behind.

**Format is JSON Lines**, one record per line, `type` discriminating:

* `session_start` - timestamps, pid, host, app version, the *effective* config
  (thresholds are recorded, not assumed, so an old file stays readable after a
  default changes) and an optional operator label.
* `stall`         - written the instant a stall is detected, with suspects.
* `slow_request`  - written as each slow request completes.
* `snapshot`      - periodic aggregate roll-up, so a time series survives even
  if the process is killed and never gets to write a summary.
* `reset`         - emitted by `POST /performance/reset`, recording what was
  discarded so a zeroed counter is never mistaken for a quiet period.
* `session_end`   - final summary on clean shutdown.

Two properties are deliberate. **Records are appended and flushed as they
happen**, never buffered until shutdown: a `docker kill`, an OOM or a `--reload`
restart must still leave everything observed up to that moment on disk.
And **nothing here may ever break the server**: every entry point swallows its
exceptions and, on repeated failure, the logger disables itself for the rest of
the session rather than raising into the request path or the watchdog.

Set `PERF_SESSION_LABEL` before starting the server to tag a run
(`PERF_SESSION_LABEL=before-fix uvicorn copilot:app --port=5000`); the label
lands both in the filename and in `session_start`.
"""

import asyncio
import json
import os
import socket
import sys
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger

from app.middleware.performance import LAG_SAMPLE_INTERVAL
from app.middleware.performance import LAG_STALL_THRESHOLD_MS
from app.middleware.performance import MAX_ENDPOINTS
from app.middleware.performance import PERF_MONITOR_ENABLED
from app.middleware.performance import RECENT_REQUESTS
from app.middleware.performance import RECENT_STALLS
from app.middleware.performance import SLOW_REQUEST_MS
from app.middleware.performance import PerformanceRegistry
from app.middleware.performance import _env_flag
from app.middleware.performance import _env_float
from app.middleware.performance import _env_int
from app.middleware.performance import performance_registry

# backend/app/performance/services/session_log.py -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[3]

PERF_LOG_ENABLED = _env_flag("PERF_LOG_ENABLED", True)
PERF_LOG_DIR = os.environ.get("PERF_LOG_DIR") or str(_BACKEND_ROOT / "logs" / "performance")

# How often the aggregate roll-up is appended. 60s is frequent enough to leave a
# usable time series behind a killed process, rare enough to keep files small.
PERF_LOG_SNAPSHOT_INTERVAL = _env_float("PERF_LOG_SNAPSHOT_INTERVAL", 60.0)

# Session files to keep. `uvicorn --reload` restarts the app on every file save,
# so a dev day can produce hundreds of short sessions; the oldest are pruned.
PERF_LOG_RETENTION = _env_int("PERF_LOG_RETENTION", 50)

# Endpoints included in each snapshot / the final summary, worst first.
_TOP_ENDPOINTS = 15

# Consecutive write failures tolerated before the logger gives up for good.
_MAX_WRITE_FAILURES = 5

_FILE_PREFIX = "perf"
_FILE_SUFFIX = ".jsonl"


def _slugify(value: str) -> str:
    """Filename-safe, lowercase, no runs of separators. Empty if nothing usable."""
    kept = [char.lower() if char.isalnum() else "-" for char in value.strip()]
    slug = "".join(kept)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:40]


def _iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _percentile(samples: List[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    index = int(round((pct / 100.0) * (len(ordered) - 1)))
    return round(ordered[max(0, min(index, len(ordered) - 1))], 2)


class PerformanceSessionLog:
    """Owns one session file: opens it, appends records, prunes old ones."""

    def __init__(self, registry: Optional[PerformanceRegistry] = None) -> None:
        self.registry = registry if registry is not None else performance_registry
        self.path: Optional[Path] = None
        self._handle = None
        self._snapshot_task: Optional[asyncio.Task] = None
        self._write_failures = 0
        self._disabled = False
        self._started_wall = 0.0

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, log_dir: Optional[str] = None) -> Optional[Path]:
        """Open this session's file and begin recording. Never raises."""
        if not PERF_LOG_ENABLED:
            logger.info("PERF: session logging disabled via PERF_LOG_ENABLED")
            return None
        if not PERF_MONITOR_ENABLED:
            logger.info("PERF: monitoring disabled, session log not started")
            return None
        if self._handle is not None:
            return self.path

        label = os.environ.get("PERF_SESSION_LABEL", "")
        slug = _slugify(label)
        directory = Path(log_dir or PERF_LOG_DIR)

        try:
            directory.mkdir(parents=True, exist_ok=True)
            self._started_wall = time.time()
            stamp = datetime.fromtimestamp(self._started_wall).strftime("%Y%m%d-%H%M%S")
            # pid disambiguates two starts within the same second, which
            # `uvicorn --reload` produces routinely.
            parts = [_FILE_PREFIX, stamp, f"pid{os.getpid()}"]
            if slug:
                parts.append(slug)
            self.path = directory / ("-".join(parts) + _FILE_SUFFIX)
            self._handle = self.path.open("a", encoding="utf-8")
        except Exception as exc:
            logger.warning(f"PERF: could not open a session log in {directory}: {exc}")
            self._handle = None
            self.path = None
            return None

        self._prune(directory)
        self._write(
            "session_start",
            {
                "label": label or None,
                "pid": os.getpid(),
                "host": socket.gethostname(),
                "python": sys.version.split()[0],
                "environment": os.environ.get("ENVIRONMENT"),
                # Thresholds are recorded rather than assumed at read time: a file
                # written under different settings must still be interpretable.
                "config": {
                    "lag_sample_interval_seconds": LAG_SAMPLE_INTERVAL,
                    "lag_stall_threshold_ms": LAG_STALL_THRESHOLD_MS,
                    "slow_request_ms": SLOW_REQUEST_MS,
                    "snapshot_interval_seconds": PERF_LOG_SNAPSHOT_INTERVAL,
                    "recent_requests": RECENT_REQUESTS,
                    "recent_stalls": RECENT_STALLS,
                    "max_endpoints": MAX_ENDPOINTS,
                },
            },
        )

        self.registry.event_sink = self._write
        logger.info(f"PERF: session log -> {self.path}")
        return self.path

    def start_snapshots(self) -> None:
        """Start the periodic roll-up task. Requires a running event loop."""
        if self._handle is None or self._disabled:
            return
        if self._snapshot_task is not None and not self._snapshot_task.done():
            return
        self._snapshot_task = asyncio.create_task(self._snapshot_loop(), name="perf-session-snapshots")

    async def stop(self) -> None:
        """Write the final summary and close. Safe to call when never started."""
        if self._snapshot_task is not None:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.warning(f"PERF: snapshot task stopped with an error: {exc}")
            finally:
                self._snapshot_task = None

        if self._handle is None:
            return

        self._write("session_end", {"summary": self._summary()})

        if self.registry.event_sink is self._write:
            self.registry.event_sink = None

        try:
            self._handle.close()
        except Exception as exc:
            logger.warning(f"PERF: error closing the session log: {exc}")
        finally:
            self._handle = None
            logger.info(f"PERF: session log closed -> {self.path}")

    # ── internals ────────────────────────────────────────────────────────

    async def _snapshot_loop(self) -> None:
        while True:
            await asyncio.sleep(PERF_LOG_SNAPSHOT_INTERVAL)
            self._write("snapshot", self._summary())

    def _write(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Append one record and flush. This is the registry's event sink."""
        if self._handle is None or self._disabled:
            return
        record = {"ts": _iso(time.time()), "type": event_type, **payload}
        try:
            self._handle.write(json.dumps(record, default=str) + "\n")
            # Flushed per record on purpose: these are low-frequency events, and
            # an unflushed buffer is exactly what is lost when the process dies.
            self._handle.flush()
            self._write_failures = 0
        except Exception as exc:
            self._write_failures += 1
            logger.warning(f"PERF: failed writing {event_type} to the session log: {exc}")
            if self._write_failures >= _MAX_WRITE_FAILURES:
                self._disabled = True
                logger.error(
                    f"PERF: session logging disabled after {_MAX_WRITE_FAILURES} consecutive write failures",
                )

    def _summary(self) -> Dict[str, Any]:
        registry = self.registry
        samples = registry.lag_samples
        uptime = max(registry.uptime_seconds, 1e-9)

        endpoints = [stats for stats in registry.endpoints if stats.count]
        # Worst first by attributed stall time, then by total time spent: the two
        # questions a later comparison actually asks.
        endpoints.sort(key=lambda stats: (stats.stalled_ms, stats.total_ms), reverse=True)

        return {
            "uptime_seconds": round(uptime, 2),
            "counters_since": _iso(registry.started_wall),
            "requests": {
                "total": registry.total_requests,
                "slow": registry.total_slow,
                "errors": registry.total_errors,
                "client_disconnects": registry.total_disconnects,
                "max_concurrency": registry.max_concurrency,
                "in_flight": len(registry.in_flight),
            },
            "loop_lag": {
                "samples": len(samples),
                "p50_ms": _percentile(samples, 50),
                "p95_ms": _percentile(samples, 95),
                "p99_ms": _percentile(samples, 99),
                "max_ms": round(registry.max_lag_ms, 2),
                "stalls": registry.total_stalls,
                "total_stalled_ms": round(registry.total_stalled_ms, 2),
                "stalled_ratio": round(registry.total_stalled_ms / 1000.0 / uptime, 4),
            },
            "top_endpoints": [
                {
                    "method": stats.method,
                    "path": stats.path,
                    "count": stats.count,
                    "avg_ms": round(stats.total_ms / stats.count, 2),
                    "p95_ms": _percentile(list(stats.samples), 95),
                    "max_ms": round(stats.max_ms, 2),
                    "slow_count": stats.slow_count,
                    "stall_hits": stats.stall_hits,
                    "stalled_ms": round(stats.stalled_ms, 2),
                }
                for stats in endpoints[:_TOP_ENDPOINTS]
            ],
        }

    def _prune(self, directory: Path) -> None:
        """Keep the newest PERF_LOG_RETENTION session files, delete the rest."""
        if PERF_LOG_RETENTION <= 0:
            return
        try:
            # The timestamp is fixed-width and leading, so a name sort is a
            # chronological sort - no stat() call per file needed.
            existing = sorted(directory.glob(f"{_FILE_PREFIX}-*{_FILE_SUFFIX}"))
            for stale in existing[: max(0, len(existing) - PERF_LOG_RETENTION)]:
                if stale != self.path:
                    stale.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"PERF: could not prune old session logs in {directory}: {exc}")


# Process-wide singleton, started and stopped from the app lifespan.
session_log = PerformanceSessionLog()
