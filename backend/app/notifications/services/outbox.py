"""The notification outbox: delivery that survives a restart.

``emit()`` used to schedule the dispatch as an in-memory asyncio task, so a notification was
lost if CoPilot restarted or crashed between the caller's commit and the dispatch, or during
it. The most important caller is the AI report write-back: a committed report whose
``investigation_complete`` notification never left.

Every event is now a ``notification_outbox`` row first:

- ``enqueue(event, session)`` adds the row to the caller's own transaction, so it commits
  (or rolls back) together with the caller's write. The caller then calls ``kick(event)``
  after its commit, or ``emit(event)`` if ``enqueue`` returned False.
- ``queue(event)`` writes the row in a short transaction of its own. ``emit()`` uses it: the
  event is durable from that commit on, a few milliseconds after the call, but not atomic
  with the caller's write.

**The drain** claims a row, dispatches it through the existing ``dispatch_event`` and marks
it ``done``; or puts it back to ``pending`` with backoff; or, after ``max_attempts``, marks
it ``dead`` and logs an error. It runs right after the enqueue (the kick: ``drain_key``) and
from the ``drain_notification_outbox`` scheduler job every minute (``drain``), which also
picks up whatever a crash or a failed kick left behind.

**Claims are guarded UPDATEs**: ``UPDATE … SET status='processing', attempts=attempts+1 WHERE
id=? AND status='pending' …``, and only ``rowcount == 1`` dispatches. On MySQL the UPDATE
locks the row and re-reads it, so of two workers (processes or hosts) racing for one row
exactly one wins; the other matches nothing. Every later write to a claimed row is guarded on
``status='processing'``, ``claimed_by`` and ``attempts`` too, so a worker whose lease was
taken over can't overwrite the newer claim's outcome. A row left ``processing`` longer than
the lease (a crash mid-dispatch) goes back to ``pending`` from the job.

**Re-dispatch is safe per route, which the dispatch log alone does not give**: it is written
after the provider call, so a ``sent`` row refuses the second log write but not the second
delivery. The row therefore keeps ``route_outcomes``, the routes it has settled, and passes
them to ``dispatch_event(skip_route_ids=…)``. A partial fan-out (route A sent, route B down)
retries only B. When an attempt dies before it can record its outcomes (a timeout, a crash),
the routes the dispatch log shows ``sent`` for this dedupe key since the attempt's claim are
counted as settled. Delivery is at least once, not exactly once: a provider that accepted a
message and then timed out, or a crash between a send and its log row, can repeat one.

**What is retried** (``is_transient_failure``): a provider's 5xx, 408, 425 or 429; a transport
error or timeout (httpx's ``ConnectError``, ``ReadTimeout`` …, as ``dispatchers.py`` formats
them); a provider that raised (``Dispatcher exception: …``); and the whole dispatch raising or
timing out. **Not retried**: any other 4xx (an unverified Resend domain, a bad webhook URL,
Shuffle authentication), a connector that isn't configured, an invalid route config, an
unresolvable recipient, and every ``skipped`` route (the AI-report switch, a disabled
integration, no assignee). Those are settled; only the transient routes are tried again.

**Queued once per key.** ``queued_key`` (unique) is the dedupe key until the row's first
claim. A second event for a key that is still queued replaces the queued event (the newest
state wins: the latest report's summary, say) instead of adding a row; once delivery has
started, the key can be queued afresh, so a re-emission is delivered again exactly as before
the outbox (A → B → A reassignment). Manual and test sends don't come through here, and their
per-invocation keys would never collide anyway.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import socket
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set

from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import async_engine
from app.db.universal_models import NotificationDispatchLog
from app.db.universal_models import NotificationOutbox
from app.notifications.schema.events import NotificationEvent


class OutboxStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    DEAD = "dead"


def _env_number(name: str, default: float, *, minimum: float, cast: Callable = int):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        logger.warning(f"Invalid {name}={raw!r}; using the default {default}.")
        return default
    if value < minimum:
        logger.warning(f"{name}={raw!r} is below {minimum}; using the default {default}.")
        return default
    return value


@dataclass(frozen=True)
class OutboxSettings:
    """How hard the drain tries. Defaults: 8 attempts over about 24 hours.

    The delay after attempt *k* is ``min(backoff_max, backoff_base · backoff_factor^(k−1))``,
    times a random factor in ``[1 − jitter, 1 + jitter]``: 1.5 min, 6 min, 24 min, 1.6 h,
    then 6.4 h, 8 h, 8 h, about 24.5 hours from the first attempt to the eighth.
    """

    max_attempts: int = 8
    backoff_base_seconds: float = 90.0
    backoff_factor: float = 4.0
    backoff_max_seconds: float = 8 * 3600.0
    jitter: float = 0.2
    #: A ``processing`` row older than this is presumed abandoned. Always longer than a
    #: dispatch may take (see ``effective_lease_seconds``), or a slow dispatch would be
    #: taken over while still running.
    lease_seconds: float = 300.0
    #: Ceiling for one dispatch of one row, every route and provider call included.
    dispatch_timeout_seconds: float = 60.0
    #: Rows one job run claims at most.
    batch_size: int = 50
    done_retention_days: int = 7
    dead_retention_days: int = 30

    @property
    def effective_lease_seconds(self) -> float:
        return max(self.lease_seconds, self.dispatch_timeout_seconds + 60.0)

    @classmethod
    def from_env(cls) -> "OutboxSettings":
        d = cls()
        return cls(
            max_attempts=_env_number("NOTIFICATION_OUTBOX_MAX_ATTEMPTS", d.max_attempts, minimum=1),
            backoff_base_seconds=_env_number(
                "NOTIFICATION_OUTBOX_BACKOFF_BASE_SECONDS",
                d.backoff_base_seconds,
                minimum=1,
                cast=float,
            ),
            backoff_max_seconds=_env_number("NOTIFICATION_OUTBOX_BACKOFF_MAX_SECONDS", d.backoff_max_seconds, minimum=1, cast=float),
            lease_seconds=_env_number("NOTIFICATION_OUTBOX_LEASE_SECONDS", d.lease_seconds, minimum=1, cast=float),
            done_retention_days=_env_number("NOTIFICATION_OUTBOX_DONE_RETENTION_DAYS", d.done_retention_days, minimum=0),
            dead_retention_days=_env_number("NOTIFICATION_OUTBOX_DEAD_RETENTION_DAYS", d.dead_retention_days, minimum=0),
        )

    def backoff(self, attempts: int, rng: Callable[[float, float], float] = random.uniform) -> timedelta:
        """The wait before the next attempt, after ``attempts`` attempts (1 or more)."""
        base = min(self.backoff_max_seconds, self.backoff_base_seconds * self.backoff_factor ** max(0, attempts - 1))
        return timedelta(seconds=base * rng(1.0 - self.jitter, 1.0 + self.jitter))


def _new_session() -> AsyncSession:
    return AsyncSession(async_engine, expire_on_commit=False)


#: Every session the outbox opens comes from here; tests point it at their own database.
new_session: Callable[[], AsyncSession] = _new_session


def _now() -> datetime:
    """Naive UTC, whole seconds: what MySQL's DATETIME stores, so a value never reads back later
    than it was written (MySQL rounds fractions, and a row queued at .6 s would otherwise not be
    due until the next second)."""
    return datetime.utcnow().replace(microsecond=0)


def _worker_id() -> str:
    """Who holds a claim. Read per claim, not at import: a forked worker has its own pid."""
    return f"{socket.gethostname()}:{os.getpid()}"[:128]


# ---------------------------------------------------------------------------
# What is worth retrying
# ---------------------------------------------------------------------------

#: `dispatchers.py` formats an HTTP refusal as "<Provider> returned <code>: …" and Teams'
#: throttling as "… (429) …".
_TRANSIENT_STATUS = re.compile(r"\breturned (?:5\d\d|408|425|429)\b|\(429\)")
#: …and a transport failure as "<ExceptionClass>: …".
_TRANSIENT_EXCEPTION = re.compile(
    r"^(?:httpx\.)?(?:ConnectError|ConnectTimeout|ReadTimeout|WriteTimeout|PoolTimeout|TimeoutException|Timeout|ReadError|WriteError"
    r"|CloseError|NetworkError|TransportError|RemoteProtocolError|ProxyError|TimeoutError|ConnectionError|ConnectionResetError"
    r"|ConnectionRefusedError|ConnectionAbortedError|BrokenPipeError|gaierror|OSError)\b",
)


def is_transient_failure(error_message: Optional[str]) -> bool:
    """Whether a route's `failed` outcome may succeed if tried again later.

    Matched on the texts `dispatchers.py` and the providers produce (pinned by the tests), since
    a failure reaches the dispatch loop as a status and a message, not an exception.
    """
    if not error_message:
        return False
    if error_message.startswith("Dispatcher exception:"):
        # The provider raised instead of returning a result: nothing says it is permanent,
        # and the attempts are capped.
        return True
    return bool(_TRANSIENT_STATUS.search(error_message) or _TRANSIENT_EXCEPTION.match(error_message))


_URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s'\"<>]+")
_AUTH_SCHEME = re.compile(r"(?i)\b(bearer|basic)\s+[^\s,;'\"]+")
_CREDENTIAL = re.compile(
    r"(?i)\b(token|api[_-]?key|apikey|password|secret|authorization)([\s:=\"']+)(?!(?:bearer|basic)\b|<redacted>)[^\s,;'\"]+",
)
_ERROR_LIMIT = 1000


def safe_error(text: str) -> str:
    """`last_error` as stored: URLs (a Teams or webhook URL is itself a credential) and anything
    shaped like a credential masked, then truncated."""
    cleaned = _URL.sub("<url>", text or "")
    cleaned = _AUTH_SCHEME.sub(lambda m: f"{m.group(1)} <redacted>", cleaned)
    cleaned = _CREDENTIAL.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", cleaned)
    return cleaned if len(cleaned) <= _ERROR_LIMIT else cleaned[: _ERROR_LIMIT - 1] + "…"


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------

#: What a queued row takes from a newer event for its key.
_REPLACED_ON_CONFLICT = ("event_json", "customer_code", "trigger", "updated_at")


def _queue_values(event: NotificationEvent, now: datetime) -> Dict[str, Any]:
    return {
        "event_json": event.model_dump_json(),
        "dedupe_key": event.dedupe_key,
        "queued_key": event.dedupe_key,
        "customer_code": event.customer_code,
        "trigger": event.trigger.value,
        "status": OutboxStatus.PENDING,
        "attempts": 0,
        "next_attempt_at": now,
        "created_at": now,
        "updated_at": now,
    }


async def _add(event: NotificationEvent, session: AsyncSession) -> None:
    """Queue `event` in `session`'s transaction; a queued row for its key takes the newer event.

    One statement that never fails on the queued key, so a duplicate can't turn the caller's
    commit into an IntegrityError: MySQL's ``INSERT … ON DUPLICATE KEY UPDATE`` and SQLite's
    ``ON CONFLICT DO UPDATE``. Any other dialect falls back to a read then a write.
    """
    values = _queue_values(event, _now())
    table = NotificationOutbox.__table__
    dialect = session.get_bind().dialect.name
    if dialect == "mysql":
        stmt = mysql_insert(table).values(**values)
        await session.execute(stmt.on_duplicate_key_update({c: stmt.inserted[c] for c in _REPLACED_ON_CONFLICT}))
        return
    if dialect == "sqlite":
        stmt = sqlite_insert(table).values(**values)
        await session.execute(
            stmt.on_conflict_do_update(index_elements=["queued_key"], set_={c: stmt.excluded[c] for c in _REPLACED_ON_CONFLICT}),
        )
        return
    existing = await session.execute(select(table.c.id).where(table.c.queued_key == event.dedupe_key))
    row_id = existing.scalars().first()
    if row_id is None:
        await session.execute(table.insert().values(**values))
    else:
        await session.execute(update(table).where(table.c.id == row_id).values({c: values[c] for c in _REPLACED_ON_CONFLICT}))


async def enqueue(event: NotificationEvent, session: AsyncSession) -> bool:
    """Add `event` to the caller's transaction, to commit (or roll back) with the caller's write.

    Never raises, and never flushes the caller's pending objects (so a flush error of theirs is
    still raised by their own commit, where they handle it). Returns False when the row could
    not be added; that is logged, and the caller should then ``emit(event)`` after its commit,
    which is durable but not atomic. After a successful commit, call ``kick(event)`` for an
    immediate delivery; without it the scheduler job delivers within a minute.
    """
    try:
        with session.no_autoflush:
            await _add(event, session)
        return True
    except Exception as e:  # noqa: BLE001 — failing to queue must not fail the caller's write
        logger.error(
            f"Notification outbox: could not queue [{event.trigger.value}] {event.entity_type}#{event.entity_id} "
            f"in the caller's transaction ({type(e).__name__}); it will be emitted after the commit instead.",
        )
        return False


async def queue(event: NotificationEvent) -> bool:
    """Queue `event` in a short transaction of its own. Never raises; False when it couldn't."""
    try:
        async with new_session() as session:
            await _add(event, session)
            await session.commit()
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(
            f"Notification outbox: could not queue [{event.trigger.value}] {event.entity_type}#{event.entity_id}: "
            f"{type(e).__name__}: {safe_error(str(e))[:300]}",
        )
        return False


#: Strong references to kicked drains until they finish (asyncio keeps only weak ones).
_KICKS: Set[asyncio.Task] = set()


def kick(event: NotificationEvent) -> None:
    """Deliver `event`'s queued row now, in the background. Call after the enqueue committed.

    Synchronous and never raises. Without a running loop it does nothing: the row is queued,
    and the scheduler job delivers it.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(drain_key(event.dedupe_key))
    _KICKS.add(task)
    task.add_done_callback(_KICKS.discard)


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------


@dataclass
class _Claim:
    id: int
    dedupe_key: str
    attempts: int
    claimed_at: datetime
    claimed_by: str
    event_json: str
    settled: Dict[str, str] = field(default_factory=dict)


def _outcomes(raw: Optional[str]) -> Dict[str, str]:
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


async def _claim(row_id: int, due_by: datetime, *, queued_key: Optional[str] = None) -> Optional[_Claim]:
    """Take one row, or None if another worker has it (or it is no longer due).

    `queued_key` claims a row still waiting for its first attempt (the kick) whatever its
    `next_attempt_at`; without it, only a `pending` row due by `due_by` is claimed. The claim is
    stamped with the time it is taken, not `due_by`, so a long sweep can't start a row's lease
    in the past.
    """
    table = NotificationOutbox.__table__
    worker = _worker_id()
    now = _now()
    conditions = [table.c.id == row_id, table.c.status == OutboxStatus.PENDING]
    if queued_key is not None:
        conditions.append(table.c.queued_key == queued_key)
    else:
        conditions.append(table.c.next_attempt_at <= due_by)
    async with new_session() as session:
        result = await session.execute(
            update(table)
            .where(*conditions)
            .values(
                status=OutboxStatus.PROCESSING,
                queued_key=None,
                attempts=table.c.attempts + 1,
                claimed_at=now,
                claimed_by=worker,
                updated_at=now,
            ),
        )
        if result.rowcount != 1:
            await session.rollback()
            return None
        row = (
            await session.execute(
                select(table.c.dedupe_key, table.c.attempts, table.c.event_json, table.c.route_outcomes).where(table.c.id == row_id),
            )
        ).one()
        await session.commit()
    return _Claim(
        id=row_id,
        dedupe_key=row.dedupe_key,
        attempts=row.attempts,
        claimed_at=now,
        claimed_by=worker,
        event_json=row.event_json,
        settled=_outcomes(row.route_outcomes),
    )


async def _finish(claim: _Claim, **values) -> bool:
    """Write a claimed row's outcome, only while the claim is still this one."""
    table = NotificationOutbox.__table__
    async with new_session() as session:
        result = await session.execute(
            update(table)
            .where(
                table.c.id == claim.id,
                table.c.status == OutboxStatus.PROCESSING,
                table.c.claimed_by == claim.claimed_by,
                table.c.attempts == claim.attempts,
            )
            .values(updated_at=_now(), **values),
        )
        await session.commit()
    if result.rowcount != 1:
        logger.warning(f"Notification outbox row {claim.id}: the claim was taken over before its outcome was written; leaving it.")
        return False
    return True


async def _sent_since(dedupe_key: str, since: datetime) -> Set[int]:
    """Routes the dispatch log shows `sent` for this key since an attempt began.

    Used when an attempt ended without reporting its outcomes, so what it did deliver isn't
    delivered again. Misses a route whose `sent` row predates the attempt (the log keeps the
    first `sent` and refuses later writes): such a route can be sent again.
    """
    try:
        async with new_session() as session:
            result = await session.execute(
                select(NotificationDispatchLog.route_id).where(
                    NotificationDispatchLog.dedupe_key == dedupe_key,
                    NotificationDispatchLog.status == "sent",
                    NotificationDispatchLog.dispatched_at >= since,
                ),
            )
            return set(result.scalars().all())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Notification outbox: could not read the dispatch log for {dedupe_key!r}: {type(e).__name__}")
        return set()


async def _retry_or_die(claim: _Claim, error: str, settings: OutboxSettings) -> str:
    error = safe_error(error)
    outcomes = json.dumps(claim.settled, sort_keys=True)
    if claim.attempts >= settings.max_attempts:
        if await _finish(claim, status=OutboxStatus.DEAD, last_error=error, route_outcomes=outcomes, claimed_by=None):
            logger.error(f"Notification outbox row {claim.id} ({claim.dedupe_key}) is dead after {claim.attempts} attempt(s): {error}")
        return OutboxStatus.DEAD
    delay = settings.backoff(claim.attempts)
    if await _finish(
        claim,
        status=OutboxStatus.PENDING,
        next_attempt_at=_now() + delay,
        last_error=error,
        route_outcomes=outcomes,
        claimed_by=None,
    ):
        logger.warning(
            f"Notification outbox row {claim.id} ({claim.dedupe_key}): attempt {claim.attempts} of {settings.max_attempts} failed; "
            f"retrying in {int(delay.total_seconds())}s: {error}",
        )
    return OutboxStatus.PENDING


async def _process(claim: _Claim, settings: OutboxSettings) -> str:
    """Dispatch one claimed row and record what happened. Returns the row's new status."""
    from app.notifications.services.notifications import dispatch_event

    try:
        event = NotificationEvent.model_validate_json(claim.event_json)
    except Exception as e:  # noqa: BLE001 — a row that can't be read will never be deliverable
        error = f"The queued event could not be read: {type(e).__name__}"
        if await _finish(claim, status=OutboxStatus.DEAD, last_error=error, claimed_by=None):
            logger.error(f"Notification outbox row {claim.id} is dead: {error}")
        return OutboxStatus.DEAD

    skip = {int(k) for k in claim.settled if k.isdigit()}
    try:
        async with new_session() as session:
            response = await asyncio.wait_for(
                dispatch_event(event, session, skip_route_ids=skip),
                timeout=settings.dispatch_timeout_seconds,
            )
    except Exception as e:  # noqa: BLE001 — including the timeout: the whole attempt is retried
        if isinstance(e, asyncio.TimeoutError):
            error = f"The dispatch timed out after {settings.dispatch_timeout_seconds:g}s"
        else:
            error = f"The dispatch raised {type(e).__name__}: {e}"
            logger.error(f"Notification outbox row {claim.id} ({claim.dedupe_key}): {safe_error(error)}")
        for route_id in await _sent_since(claim.dedupe_key, claim.claimed_at):
            claim.settled.setdefault(str(route_id), "sent")
        return await _retry_or_die(claim, error, settings)

    transient: List[str] = []
    for outcome in response.outcomes:
        key = str(outcome.route_id)
        if key in claim.settled:
            continue
        status = outcome.status.value
        if status == "failed" and is_transient_failure(outcome.error_message):
            transient.append(f"route {outcome.route_id}: {outcome.error_message}")
        else:
            # sent, skipped, or failed for good: nothing a retry would change.
            claim.settled[key] = status
    if transient:
        return await _retry_or_die(claim, "; ".join(transient), settings)

    await _finish(
        claim,
        status=OutboxStatus.DONE,
        last_error=None,
        route_outcomes=json.dumps(claim.settled, sort_keys=True),
        claimed_by=None,
    )
    if response.routes_matched:
        logger.info(
            f"Notification [{event.trigger.value}] {event.entity_type}#{event.entity_id}: "
            f"{response.dispatched} sent, {response.skipped} skipped, {response.failed} failed "
            f"across {response.routes_matched} route(s).",
        )
    else:
        # Named rather than silent: a trigger nobody subscribed to used to look exactly like an
        # engine that never fired.
        logger.info(
            f"Notification [{event.trigger.value}] {event.entity_type}#{event.entity_id}: "
            f"no route is configured for this trigger; nothing sent.",
        )
    return OutboxStatus.DONE


async def _claim_and_process(row_id: int, due_by: datetime, settings: OutboxSettings, *, queued_key: Optional[str] = None) -> Optional[str]:
    claim = await _claim(row_id, due_by, queued_key=queued_key)
    if claim is None:
        return None
    try:
        return await _process(claim, settings)
    except Exception as e:  # noqa: BLE001 — the lease sweep will bring the row back
        logger.error(f"Notification outbox row {row_id}: recording the outcome failed ({type(e).__name__}); the lease sweep will retry it.")
        return None


async def drain_key(dedupe_key: str, settings: Optional[OutboxSettings] = None) -> None:
    """Deliver the row queued for `dedupe_key` now: the kick after an enqueue. Never raises."""
    settings = settings or OutboxSettings.from_env()
    table = NotificationOutbox.__table__
    try:
        async with new_session() as session:
            result = await session.execute(
                select(table.c.id).where(table.c.queued_key == dedupe_key, table.c.status == OutboxStatus.PENDING),
            )
            row_ids = result.scalars().all()
        for row_id in row_ids:
            await _claim_and_process(row_id, _now(), settings, queued_key=dedupe_key)
    except Exception as e:  # noqa: BLE001 — the row stays queued for the scheduler job
        logger.error(f"Notification outbox: immediate delivery of {dedupe_key!r} failed ({type(e).__name__}); the job will retry it.")


async def _recover_expired(now: datetime, settings: OutboxSettings) -> int:
    """Put rows whose worker vanished mid-dispatch back to `pending` (or `dead`)."""
    table = NotificationOutbox.__table__
    cutoff = now - timedelta(seconds=settings.effective_lease_seconds)
    async with new_session() as session:
        rows = (
            await session.execute(
                select(table.c.id, table.c.dedupe_key, table.c.attempts, table.c.claimed_at, table.c.claimed_by, table.c.route_outcomes)
                .where(table.c.status == OutboxStatus.PROCESSING, table.c.updated_at < cutoff)
                .order_by(table.c.updated_at)
                .limit(settings.batch_size),
            )
        ).all()
    recovered = 0
    for row in rows:
        claim = _Claim(
            id=row.id,
            dedupe_key=row.dedupe_key,
            attempts=row.attempts,
            claimed_at=row.claimed_at or cutoff,
            claimed_by=row.claimed_by,
            event_json="",
            settled=_outcomes(row.route_outcomes),
        )
        for route_id in await _sent_since(claim.dedupe_key, claim.claimed_at):
            claim.settled.setdefault(str(route_id), "sent")
        logger.warning(f"Notification outbox row {row.id} ({row.dedupe_key}) was left processing by {row.claimed_by}; recovering it.")
        await _retry_or_die(claim, f"The worker processing attempt {row.attempts} stopped before finishing it", settings)
        recovered += 1
    return recovered


async def drain(settings: Optional[OutboxSettings] = None, *, now: Optional[datetime] = None) -> Dict[str, int]:
    """One sweep: recover abandoned claims, then deliver up to `batch_size` due rows."""
    settings = settings or OutboxSettings.from_env()
    now = now or _now()
    counts = {"recovered": await _recover_expired(now, settings), OutboxStatus.DONE: 0, OutboxStatus.PENDING: 0, OutboxStatus.DEAD: 0}
    table = NotificationOutbox.__table__
    async with new_session() as session:
        result = await session.execute(
            select(table.c.id)
            .where(table.c.status == OutboxStatus.PENDING, table.c.next_attempt_at <= now)
            .order_by(table.c.next_attempt_at, table.c.id)
            .limit(settings.batch_size),
        )
        row_ids = result.scalars().all()
    for row_id in row_ids:
        status = await _claim_and_process(row_id, now, settings)
        if status in counts:
            counts[status] += 1
    return counts


async def prune(settings: Optional[OutboxSettings] = None, *, now: Optional[datetime] = None) -> Dict[str, int]:
    """Delete `done` rows after `done_retention_days` and `dead` ones after `dead_retention_days`
    (0 keeps them)."""
    settings = settings or OutboxSettings.from_env()
    now = now or _now()
    table = NotificationOutbox.__table__
    deleted = {OutboxStatus.DONE: 0, OutboxStatus.DEAD: 0}
    async with new_session() as session:
        for status, days in ((OutboxStatus.DONE, settings.done_retention_days), (OutboxStatus.DEAD, settings.dead_retention_days)):
            if days <= 0:
                continue
            result = await session.execute(delete(table).where(table.c.status == status, table.c.updated_at < now - timedelta(days=days)))
            deleted[status] = result.rowcount or 0
        await session.commit()
    return deleted


async def summary(customer_code: str, session: AsyncSession, *, now: Optional[datetime] = None) -> Dict[str, Optional[int]]:
    """The customer's outbox at a glance: rows waiting, being delivered and dead, and how long
    the oldest waiting one has waited."""
    table = NotificationOutbox.__table__
    now = now or datetime.utcnow()
    rows = (
        await session.execute(
            select(table.c.status, func.count(), func.min(table.c.created_at))
            .where(
                table.c.customer_code == customer_code,
                table.c.status.in_([OutboxStatus.PENDING, OutboxStatus.PROCESSING, OutboxStatus.DEAD]),
            )
            .group_by(table.c.status),
        )
    ).all()
    counts = {status: (count, oldest) for status, count, oldest in rows}
    waiting = [counts[s][1] for s in (OutboxStatus.PENDING, OutboxStatus.PROCESSING) if s in counts and counts[s][1] is not None]
    oldest = min(waiting) if waiting else None
    return {
        "pending": counts.get(OutboxStatus.PENDING, (0, None))[0],
        "processing": counts.get(OutboxStatus.PROCESSING, (0, None))[0],
        "dead": counts.get(OutboxStatus.DEAD, (0, None))[0],
        "oldest_pending_age_seconds": max(0, int((now - oldest).total_seconds())) if oldest else None,
    }


# ---------------------------------------------------------------------------
# Scheduler jobs
# ---------------------------------------------------------------------------


async def drain_notification_outbox() -> None:
    """Scheduler entry point, every minute. A failed sweep is logged and re-raised, so the
    scheduler records an error rather than `last_success`; the next sweep tries again."""
    try:
        counts = await drain()
    except Exception as e:
        logger.exception(f"Notification outbox sweep failed: {e}")
        raise
    if any(counts.values()):
        logger.info(
            f"Notification outbox sweep: {counts[OutboxStatus.DONE]} delivered, {counts[OutboxStatus.PENDING]} to retry, "
            f"{counts[OutboxStatus.DEAD]} dead, {counts['recovered']} abandoned claim(s) recovered.",
        )


async def prune_notification_outbox() -> None:
    """Scheduler entry point, daily."""
    settings = OutboxSettings.from_env()
    deleted = await prune(settings)
    logger.info(
        f"Notification outbox prune: deleted {deleted[OutboxStatus.DONE]} done row(s) older than {settings.done_retention_days} days "
        f"and {deleted[OutboxStatus.DEAD]} dead row(s) older than {settings.dead_retention_days} days.",
    )
