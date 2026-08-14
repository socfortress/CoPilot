"""Stop working on a request the client has already abandoned (#1072).

Starlette does not cancel a handler when the client goes away: the coroutine runs
to completion and writes its response into a closed socket. On this deployment
that is not a rounding error — `/wazuh_manager/mitre/atomic-tests` was measured
at 34s, `/mitre/techniques/alerts` at 25s and `/vulnerabilities/search` at 20s.
A user who navigates away three seconds in leaves the backend querying
Elasticsearch for another half minute, for nobody.

The frontend already aborts obsolete requests on navigation, which closes the
socket. This is the other half: the server notices and stops.

Three rules keep it safe:

1. **GET only.** Aborting a POST/PUT/DELETE half-way does not undo it — it only
   destroys the caller's knowledge of whether it happened. Mutations always run
   to completion.
2. **Streaming responses are excluded.** Their whole lifecycle is "hold the
   connection open", and they manage disconnection themselves.
3. **Cancellation is cooperative.** A task is only cancelled at an `await`, so
   this can only work because level 0 moved the blocking calls off the loop —
   before that, a thread stuck in `requests.get()` had no cancellation point at
   all.

Why a receive-channel watcher rather than polling `request.is_disconnected()`:
polling means a timer, and the ASGI receive channel already delivers
`http.disconnect` the moment it happens. The messages it consumes are forwarded
to the application through a queue, so a handler that reads the request body
still sees everything it would otherwise.
"""

import asyncio
import os
from typing import Set

from loguru import logger
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


def _env_paths(name: str, default: Set[str]) -> Set[str]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return {part.strip() for part in raw.split(",") if part.strip()}


CANCEL_ON_DISCONNECT_ENABLED = _env_flag("CANCEL_ON_DISCONNECT", True)

# Server-sent-events and downloads: the connection staying open *is* the feature.
# Matched as prefixes against the raw path.
CANCEL_EXCLUDED_PATHS = _env_paths(
    "CANCEL_ON_DISCONNECT_EXCLUDE",
    {"/api/agents/sca/overview/stream"},
)

# Set on the scope so the performance middleware can report the request as
# abandoned rather than as a mystery with no status code.
SCOPE_FLAG = "copilot_client_disconnected"


class ClientDisconnectMiddleware:
    """Cancels the handler of a GET whose client has gone away."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    def _applies_to(self, scope: Scope) -> bool:
        if scope["type"] != "http":
            return False
        if scope.get("method", "").upper() != "GET":
            return False
        path = scope.get("path", "")
        return not any(path.startswith(prefix) for prefix in CANCEL_EXCLUDED_PATHS)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not CANCEL_ON_DISCONNECT_ENABLED or not self._applies_to(scope):
            await self.app(scope, receive, send)
            return

        # Everything the watcher reads is forwarded here, so the application sees
        # an unmodified message stream even though it no longer owns the channel.
        forwarded: asyncio.Queue = asyncio.Queue()
        disconnected = asyncio.Event()

        async def watch() -> None:
            while True:
                message = await receive()
                await forwarded.put(message)
                if message["type"] == "http.disconnect":
                    disconnected.set()
                    return

        async def app_receive() -> Message:
            return await forwarded.get()

        answered = asyncio.Event()

        async def watched_send(message: Message) -> None:
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                answered.set()

        watcher = asyncio.create_task(watch(), name="client-disconnect-watcher")
        handler = asyncio.create_task(self.app(scope, app_receive, watched_send), name="request-handler")
        disconnect = asyncio.create_task(disconnected.wait(), name="client-disconnect-wait")

        try:
            while True:
                done, _ = await asyncio.wait({handler, disconnect}, return_when=asyncio.FIRST_COMPLETED)

                if handler in done:
                    # Normal completion — re-raise whatever the handler raised so
                    # the exception handlers upstream still see it.
                    handler.result()
                    return

                if not answered.is_set():
                    break

                # The response is already out; the client hanging up now saves
                # nothing. The task is still running only because FastAPI is
                # unwinding it — and that includes `Depends(get_db)` closing its
                # session in the `async with` teardown. Cancelling there is an
                # await point where a connection can fail to return to the pool,
                # so a served request is always allowed to finish.
                await handler
                return

            # The client is gone before we answered. Stop the work.
            scope[SCOPE_FLAG] = True
            handler.cancel()
            try:
                await handler
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001 — it was already abandoned
                logger.debug(f"Abandoned request raised while being cancelled: {exc}")

            logger.info(f"Cancelled {scope.get('method')} {scope.get('path')} — client disconnected")
        finally:
            for task in (watcher, disconnect):
                task.cancel()
