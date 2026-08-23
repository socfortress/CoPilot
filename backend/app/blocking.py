"""Run blocking calls off the event loop.

The backend serves every request from a *single* uvicorn process with a *single*
event loop, while ~780 endpoints are declared `async def`. A synchronous call
made from inside one of those coroutines — `requests.get(...)` against Wazuh, a
sync `Elasticsearch` search — does not just make its own request slow: it stops
the loop, so *every* concurrent request waits for it. The instrumentation added
for #1072 measured the loop blocked ~6% of the time on a normal session, with
individual stalls up to 4.7s.

`await run_blocking(fn, *args, **kwargs)` moves such a call to anyio's worker
thread pool. The coroutine still waits for the result, so call sites keep their
exact shape and semantics — but the loop is free to serve other requests while
the thread waits on the socket.

**Why not just switch everything to httpx?** Long term that is the better
answer, and new code should use it. But several of these helpers have
load-bearing quirks — `wazuh_manager.send_put_request` form-encodes dicts even
under a JSON content-type, and the rule-file-upload flow depends on it (see
CLAUDE.md) — so a transport swap changes behaviour in ways a threadpool hop does
not. This keeps the fix mechanical and reviewable; the transport can be migrated
per connector afterwards, with the numbers to prove it.

**Cancellation.** `run_blocking` does not abandon the thread when the caller is
cancelled: a half-finished HTTP call has no safe abort, and abandoning threads
leaks them. The event loop is freed either way, which is the point.
"""

from typing import Any
from typing import Callable
from typing import TypeVar

import anyio
import anyio.to_thread
from loguru import logger

T = TypeVar("T")

# anyio's default worker pool is 40 threads. Every blocking call now competes for
# one, and a single slow connector (Wazuh under load answers in seconds) can hold
# many at once, so the default is raised. Threads waiting on a socket cost little
# beyond their stack; the cap exists to bound runaway usage, not to ration work.
DEFAULT_THREAD_LIMIT = 80

# Almost no blocking HTTP call in this codebase had a timeout. On the event loop
# that risked hanging the whole process; in a worker pool it pins one of a finite
# number of workers forever, which is worse — the symptom is the pool slowly
# dying rather than one obviously stuck request. Generous enough for a connector
# under load, finite either way.
DEFAULT_HTTP_TIMEOUT = 60


async def run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Await a blocking callable without holding the event loop.

    Exceptions propagate unchanged, so existing `try/except` around the call site
    keeps working exactly as before.
    """
    if kwargs:
        return await anyio.to_thread.run_sync(lambda: func(*args, **kwargs))
    return await anyio.to_thread.run_sync(func, *args)


def configure_thread_limit(limit: int = DEFAULT_THREAD_LIMIT) -> None:
    """Raise anyio's worker-thread cap. Call once, from the app lifespan.

    Must run inside the event loop: the limiter is bound to the running async
    backend.
    """
    try:
        limiter = anyio.to_thread.current_default_thread_limiter()
        previous = limiter.total_tokens
        limiter.total_tokens = limit
        logger.info(f"Blocking-call thread pool: {previous} -> {limit} workers")
    except Exception as exc:
        # Never fatal: the default of 40 still works, just with less headroom.
        logger.warning(f"Could not raise the worker-thread limit to {limit}: {exc}")
