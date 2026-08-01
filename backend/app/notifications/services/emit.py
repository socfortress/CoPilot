"""Fire-and-forget notification emission from inside CoPilot.

Until now the dispatch loop was only ever reached from Talon's HTTP call, where
blocking was fine — the caller was waiting for a dispatch result anyway. The
triggers added in #1006 sit somewhere much less forgiving: `alert_created` is on
the **ingest hot path**, and a slow Resend or Teams endpoint must never back up
alert creation.

So emission is scheduled and abandoned. The dispatch log is the durable record
of what happened; nothing is returned to the caller and nothing propagates back.

Two hazards this module exists to contain:

**A background task must open its own session.** Reusing the request-scoped one
after the response has been returned raises `MissingGreenlet` or a
closed-session error — the same async-SQLAlchemy hazard the notification models
already carry comments about. `_run` opens a fresh `AsyncSession` and owns it.

**A hung provider must not leak a task forever.** The whole dispatch is wrapped
in a timeout, so a black-holed endpoint produces a logged failure rather than a
task that never finishes.
"""

from __future__ import annotations

import asyncio
from typing import Optional
from typing import Set

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import async_engine
from app.notifications.schema.events import NotificationEvent

#: Ceiling for one whole emission — every matched route, including provider
#: calls. Generous because a batch may fan out to several channels; the point is
#: to bound a hang, not to be tight.
_EMIT_TIMEOUT_S = 60.0

#: asyncio keeps only a weak reference to a bare task, so one that is never
#: awaited can be garbage-collected mid-flight. Holding a strong reference until
#: it completes is the documented way to avoid that.
_IN_FLIGHT: Set[asyncio.Task] = set()


async def _run(event: NotificationEvent) -> None:
    """Dispatch on a session of our own, swallowing everything."""
    # Imported here rather than at module scope: the services module imports the
    # channels package, which imports schemas — a top-level import would make
    # this module part of that cycle.
    from app.notifications.services.notifications import dispatch_event

    try:
        async with AsyncSession(async_engine) as session:
            response = await asyncio.wait_for(dispatch_event(event, session), timeout=_EMIT_TIMEOUT_S)
        if response.routes_matched:
            logger.info(
                f"Notification emit [{event.trigger.value}] {event.entity_type}#{event.entity_id}: "
                f"{response.dispatched} sent, {response.skipped} skipped, {response.failed} failed "
                f"across {response.routes_matched} route(s).",
            )
    except asyncio.TimeoutError:
        logger.error(
            f"Notification emit [{event.trigger.value}] {event.entity_type}#{event.entity_id} "
            f"timed out after {_EMIT_TIMEOUT_S}s; abandoning.",
        )
    except Exception as e:  # noqa: BLE001 — nothing here may reach the caller
        logger.error(f"Notification emit [{event.trigger.value}] failed: {type(e).__name__}: {e}")


def emit(event: NotificationEvent) -> None:
    """Schedule `event` for dispatch and return immediately.

    Deliberately synchronous and returning None: callers sit on the ingest path
    and in request handlers, and must not be able to await this by accident.

    Safe to call with no running event loop (a sync context or a test): the
    emission is skipped with a warning rather than raising, because failing to
    notify must never fail the operation that triggered it.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            f"Notification emit [{event.trigger.value}] skipped: no running event loop.",
        )
        return

    task = loop.create_task(_run(event))
    _IN_FLIGHT.add(task)
    task.add_done_callback(_IN_FLIGHT.discard)


async def emit_now(event: NotificationEvent, session: Optional[AsyncSession] = None):
    """Dispatch inline and return the result. For tests and explicit callers.

    `emit` is the right entry point for production code; this exists so a test
    can assert on outcomes without racing a background task, and so a future
    synchronous "send test notification" button has something to await.
    """
    from app.notifications.services.notifications import dispatch_event

    if session is not None:
        return await dispatch_event(event, session)
    async with AsyncSession(async_engine) as own_session:
        return await dispatch_event(event, own_session)
