"""The notification outbox: delivery that survives a restart.

``emit()`` used to schedule the dispatch as an in-memory asyncio task, so a notification was
lost if CoPilot restarted or crashed between the caller's commit and the dispatch, or during
it. The most important caller is the AI report write-back: a committed report whose
``investigation_complete`` notification never left.

Every event is now a ``notification_outbox`` row first:

- ``enqueue(event, session)`` adds the row to the caller's own transaction, so it commits
  (or rolls back) together with the caller's write. The caller then calls ``kick(event)``
  after its commit, or ``emit(event)`` if ``enqueue`` returned False (logged; the event is then
  durable but not atomic with the write). An error that has already aborted the caller's
  transaction (a MySQL deadlock, a lock-wait timeout that rolls back, a lost connection) is
  raised, never swallowed: the caller's own write is gone, and it must not commit and notify.
- ``queue(event)`` writes the row in a short transaction of its own. ``emit()`` uses it: the
  event is durable from that commit on, a few milliseconds after the call, but not atomic
  with the caller's write.

**The drain** claims a row, dispatches it through the existing ``dispatch_event`` and marks
it ``done``; or puts it back to ``pending`` with backoff; or, after ``max_attempts``, marks
it ``dead`` and logs an error. It runs right after the enqueue (the kick: ``drain_key``) and
from the ``drain_notification_outbox`` scheduler job every minute (``drain``), which also
picks up whatever a crash or a failed kick left behind, and starts a prune of old rows
(``prune``, a background task beside the sweep) on its first run in each process and then
daily.

**Claims are guarded UPDATEs**: ``UPDATE … SET status='processing', attempts=attempts+1 WHERE
id=? AND status='pending' …``, and only ``rowcount == 1`` dispatches. On MySQL the UPDATE
locks the row and re-reads it, so of two workers (processes or hosts) racing for one row
exactly one wins; the other matches nothing. Every later write to a claimed row is guarded on
``status='processing'``, ``claimed_by`` and ``attempts`` too, so a worker whose lease was
taken over can't overwrite the newer claim's outcome. A row left ``processing`` longer than
the lease (a crash mid-dispatch) goes back to ``pending`` from the job.

**Re-dispatch is safe per route, which the dispatch log alone does not give**: it is written
after the provider call, so a ``sent`` row refuses the second log write but not the second
delivery. The row therefore keeps ``route_outcomes``, the routes it has settled, written as
each route finishes (``dispatch_event(on_route_settled=…)``), and passes them back as
``skip_route_ids``. A partial fan-out (route A sent, route B down) retries only B. On every
retry, routes the dispatch log shows ``sent`` for the dedupe key since the row was created are
skipped too. A new emission of the key is a new row with a new ``created_at``, so an earlier
emission's ``sent`` rows never hold it back (A → B → A is delivered again).

**What is retried** (``is_transient_failure``) is only what cannot have delivered anything: a
connection that was never made (httpx's ``ConnectError``, ``ConnectTimeout``, ``PoolTimeout``,
a DNS failure) and a provider that refused the request for now (HTTP 429 and 503, read where
``dispatchers.py`` writes the status). Everything else is settled and logged, not retried:
a read or write timeout, a dropped connection, any other 5xx and a provider that raised could
each have come after the provider accepted the message, and the endpoints behind a webhook,
Teams or Shuffle don't de-duplicate; any other 4xx (an unverified Resend domain, a bad URL,
Shuffle authentication), an unconfigured connector, an invalid config, an unresolvable
recipient and every ``skipped`` route won't succeed by retrying. Resend also gets an
``Idempotency-Key`` per outbox row and route (``channels/resend.py``, built from the row's
random ``delivery_uuid``), so a retried 429/503 can't mail twice.

**The attempt policy.** A row gets up to ``max_attempts`` (8) attempts with backoff, about a
day; then it is ``dead``. One dispatch's time budget is ``route_timeout_seconds`` (45) per
route still to deliver, at most ``dispatch_timeout_max_seconds`` (600), so a large, healthy
fan-out isn't cut short; and the lease outlasts the largest budget. The whole dispatch raising
or running past its budget is retried on the same backoff. Only the same error on two attempts
in a row, from attempts that settled no route, is final at once (a broken route, a bug); never
an error an outage or a failover produces (a timeout, the database unreachable, a pool timeout,
a lost connection), and never an attempt that delivered something.

**Delivery is at least once in two cases**, both narrow: CoPilot stopping between a provider
accepting a message and the route's outcome being written (one UPDATE later); and the time
budget running out while a provider request is in flight (the request is cancelled, may
already have reached the provider, and is sent again on the retry; Resend's key covers that
route, the other channels don't).

**Queued once per key.** ``queued_key`` (unique) is the dedupe key until the row's first
claim. A second event for a key that is still queued replaces the queued event (the newest
state wins: the latest report's summary, say) instead of adding a row; once delivery has
started, the key can be queued afresh, so a re-emission is delivered again exactly as before
the outbox (A → B → A reassignment). Manual and test sends don't come through here, and their
per-invocation keys would never collide anyway.

**Known limits, accepted:**

- Throughput during a provider outage: a sweep claims at most ``batch_size`` (50) due rows a
  minute and dispatches them one at a time, each within its time budget, so a large backlog
  behind a dead provider drains over several sweeps.
- A retry matches routes as they are at the retry: a route created after the event (and
  matching it) receives it; one disabled or deleted since does not.
- ``event_json`` and ``last_error`` hold what the dispatch log already holds (the summary, the
  provider's error text, scrubbed of URLs and credentials here) and are pruned with the row.
- MySQL 8.0.20+ deprecates ``VALUES()`` in ``ON DUPLICATE KEY UPDATE`` (a warning, still
  supported); it is what SQLAlchemy renders for the upsert.
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
from uuid import uuid4

from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError
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
    #: One dispatch's time budget is this much per route still to deliver (the slowest
    #: provider, Shuffle, allows itself 30 s), so a large fan-out isn't cut short by a budget
    #: meant for one route…
    route_timeout_seconds: float = 45.0
    #: …and never more than this, whatever the fan-out.
    dispatch_timeout_max_seconds: float = 600.0
    #: Rows one job run claims at most.
    batch_size: int = 50
    done_retention_days: int = 7
    dead_retention_days: int = 30

    @property
    def effective_lease_seconds(self) -> float:
        """Longer than the largest budget plus the routes' lookup, so a dispatch still within
        its budget is never taken over (11 min with the defaults)."""
        return max(self.lease_seconds, self.dispatch_timeout_max_seconds + self.route_timeout_seconds + 15.0)

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
        # The exponent is clamped: past it the cap applies anyway, and 4.0 ** 1000 overflows.
        exponent = min(max(0, attempts - 1), 32)
        base = min(self.backoff_max_seconds, self.backoff_base_seconds * self.backoff_factor**exponent)
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

#: `dispatchers.py` starts every refusal with "<Provider> returned <code>: …", and Teams' throttle
#: with "Teams rate-limited this request (429)". Anchored there, so a code quoted inside a
#: response body (which follows the status) never counts.
_RETRYABLE_STATUS = re.compile(r"^(?:Webhook|Teams|Resend|Shuffle) returned (?:429|503)\b|^Teams rate-limited this request \(429\)")
#: …and a transport failure as "<ExceptionClass>: …". Only failures before the request left:
#: the connection (or the DNS lookup) never happened, or no pooled connection was free.
_NOT_SENT = re.compile(r"^(?:httpx\.)?(?:ConnectError|ConnectTimeout|PoolTimeout|gaierror|ConnectionRefusedError)\b")


def is_transient_failure(error_message: Optional[str]) -> bool:
    """Whether a route's `failed` outcome is safe and worth trying again later.

    Only a failure where nothing can have been delivered: no connection was made, or the
    provider answered 429 or 503. A read or write timeout, a dropped connection, any other 5xx
    or a provider that raised (`Dispatcher exception: …`) may come after the provider accepted
    the message, and a webhook, Teams or Shuffle won't de-duplicate a second one, so those are
    final. Matched on the texts `dispatchers.py` and the providers produce (pinned by the
    tests), since a failure reaches the dispatch loop as a status and a message.
    """
    if not error_message:
        return False
    return bool(_RETRYABLE_STATUS.match(error_message) or _NOT_SENT.match(error_message))


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
        "delivery_uuid": uuid4().hex,
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


#: MySQL errors after which the whole transaction is gone, not just the statement.
_DEADLOCK = 1213
_LOCK_WAIT_TIMEOUT = 1205


def _mysql_code(error: BaseException) -> Optional[int]:
    args = getattr(getattr(error, "orig", None), "args", None) or ()
    return args[0] if args and isinstance(args[0], int) else None


async def _lock_timeout_rolls_back(session: AsyncSession) -> bool:
    """Whether a lock-wait timeout (1205) rolled back the whole transaction:
    `innodb_rollback_on_timeout` ON. When it can't be read, assume so."""
    try:
        value = (await session.execute(select(text("@@innodb_rollback_on_timeout")))).scalar()
        return bool(int(value))
    except Exception:  # noqa: BLE001
        return True


async def _aborts_transaction(error: Exception, session: AsyncSession) -> bool:
    if isinstance(error, DBAPIError) and error.connection_invalidated:
        return True
    if not isinstance(error, OperationalError):
        return False
    code = _mysql_code(error)
    if code == _DEADLOCK:
        return True
    return code == _LOCK_WAIT_TIMEOUT and await _lock_timeout_rolls_back(session)


async def enqueue(event: NotificationEvent, session: AsyncSession) -> bool:
    """Add `event` to the caller's transaction, to commit (or roll back) with the caller's write.

    Never flushes the caller's pending objects (so a flush error of theirs is still raised by
    their own commit, where they handle it). Returns False when the row could not be added but
    the caller's transaction is intact; that is logged, and the caller should then
    ``emit(event)`` after its commit, which is durable but not atomic. After a successful
    commit, call ``kick(event)`` for an immediate delivery; without it the scheduler job
    delivers within a minute.

    **Raises** when the failure has already aborted the caller's transaction: a MySQL deadlock
    (1213), a lock-wait timeout (1205) with ``innodb_rollback_on_timeout`` on, or a lost
    connection. MySQL has then rolled back everything the caller wrote, flushed rows included;
    swallowing it would let the caller "commit" nothing and still notify. Call it before
    flushing where you can, so such a failure costs nothing but the request.
    """
    try:
        with session.no_autoflush:
            await _add(event, session)
        return True
    except Exception as e:  # noqa: BLE001 — failing to queue must not fail the caller's write…
        if await _aborts_transaction(e, session):
            # …unless the database has already failed it.
            logger.error(
                f"Notification outbox: queueing [{event.trigger.value}] {event.entity_type}#{event.entity_id} aborted the "
                f"caller's transaction ({type(e).__name__} {_mysql_code(e)}); raising, so the caller's write fails as it must.",
            )
            raise
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
    created_at: datetime
    claimed_at: datetime
    claimed_by: Optional[str]
    event_json: str
    #: The error the previous attempt recorded, to tell a repeated failure from a new one.
    previous_error: Optional[str] = None
    #: The row's install-unique delivery id (Resend's idempotency key is built from it).
    delivery_uuid: Optional[str] = None
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
                select(
                    table.c.dedupe_key,
                    table.c.attempts,
                    table.c.created_at,
                    table.c.event_json,
                    table.c.route_outcomes,
                    table.c.last_error,
                    table.c.delivery_uuid,
                ).where(table.c.id == row_id),
            )
        ).one()
        await session.commit()
    return _Claim(
        id=row_id,
        dedupe_key=row.dedupe_key,
        attempts=row.attempts,
        created_at=row.created_at,
        claimed_at=now,
        claimed_by=worker,
        event_json=row.event_json,
        previous_error=row.last_error,
        delivery_uuid=row.delivery_uuid,
        settled=_outcomes(row.route_outcomes),
    )


def _guard(table, claim: _Claim) -> list:
    return [
        table.c.id == claim.id,
        table.c.status == OutboxStatus.PROCESSING,
        table.c.claimed_by == claim.claimed_by,
        table.c.attempts == claim.attempts,
    ]


async def _finish(claim: _Claim, **values) -> bool:
    """Write a claimed row's outcome, only while the claim is still this one."""
    table = NotificationOutbox.__table__
    async with new_session() as session:
        result = await session.execute(update(table).where(*_guard(table, claim)).values(updated_at=_now(), **values))
        await session.commit()
    if result.rowcount != 1:
        logger.warning(f"Notification outbox row {claim.id}: the claim was taken over before its outcome was written; leaving it.")
        return False
    return True


async def _record_progress(claim: _Claim) -> None:
    """Persist the routes settled so far, mid-attempt (and renew the lease while at it)."""
    table = NotificationOutbox.__table__
    async with new_session() as session:
        await session.execute(
            update(table).where(*_guard(table, claim)).values(route_outcomes=json.dumps(claim.settled, sort_keys=True), updated_at=_now()),
        )
        await session.commit()


async def _sent_since(dedupe_key: str, since: datetime) -> Set[int]:
    """Routes the dispatch log shows `sent` for this key since `since`: the row's creation.

    A new emission of the key is a new row, so an earlier emission's `sent` rows predate it and
    don't count (A → B → A delivers again). The other side of the same fact: the log keeps the
    first `sent` row of a (route, key) and refuses later writes, so for a re-emission it can't
    show what this row delivered; `route_outcomes`, written as each route finishes, does.
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


async def _settle_from_log(claim: _Claim) -> None:
    for route_id in await _sent_since(claim.dedupe_key, claim.created_at):
        claim.settled.setdefault(str(route_id), "sent")


async def _retry_or_die(claim: _Claim, error: str, settings: OutboxSettings, *, final: bool = False) -> str:
    error = safe_error(error)
    outcomes = json.dumps(claim.settled, sort_keys=True)
    if final or claim.attempts >= settings.max_attempts:
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


def _outage_shaped(error: BaseException) -> bool:
    """A failure an outage or a failover produces, which is never final however often it repeats."""
    if isinstance(error, (asyncio.TimeoutError, OSError, OperationalError, SATimeoutError, DisconnectionError)):
        return True
    return isinstance(error, DBAPIError) and bool(error.connection_invalidated)


def _settle(claim: _Claim, outcome, transient: List[str]) -> bool:
    """Fold one route's outcome into the claim. True when it settled the route."""
    key = str(outcome.route_id)
    if key in claim.settled:
        return False
    status = outcome.status.value
    if status == "failed" and is_transient_failure(outcome.error_message):
        transient.append(f"route {outcome.route_id}: {outcome.error_message}")
        return False
    if status == "failed":
        logger.warning(
            f"Notification outbox row {claim.id} ({claim.dedupe_key}): route {outcome.route_id} failed and is not retried "
            f"(it may already have been delivered, or a retry can't fix it): {safe_error(outcome.error_message or '')}",
        )
    # sent, skipped, or failed for good.
    claim.settled[key] = status
    return True


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

    if claim.attempts > 1:
        # A retry: whatever the log shows delivered since this row was created, from an attempt
        # that died before recording it, is not delivered again.
        await _settle_from_log(claim)

    transient: List[str] = []

    async def on_route_settled(outcome) -> None:
        if _settle(claim, outcome, transient):
            await _record_progress(claim)

    skip = {int(k) for k in claim.settled if k.isdigit()}
    settled_before = len(claim.settled)
    try:
        async with new_session() as session:
            response = await asyncio.wait_for(
                dispatch_event(
                    event,
                    session,
                    skip_route_ids=skip,
                    on_route_settled=on_route_settled,
                    delivery_id=claim.delivery_uuid,
                    route_budget_seconds=settings.route_timeout_seconds,
                    budget_cap_seconds=settings.dispatch_timeout_max_seconds,
                ),
                # A backstop for the routes' lookup; the budget itself is dispatch_event's.
                timeout=settings.dispatch_timeout_max_seconds + settings.route_timeout_seconds,
            )
    except Exception as e:  # noqa: BLE001 — including the timeout: the whole attempt is retried
        if isinstance(e, asyncio.TimeoutError):
            error = "The dispatch ran past its time budget"
        else:
            error = f"The dispatch raised {type(e).__name__}: {e}"
            logger.error(f"Notification outbox row {claim.id} ({claim.dedupe_key}): {safe_error(error)}")
        await _settle_from_log(claim)
        # The same error twice in a row, from an attempt that settled nothing, is a fault that
        # won't go away (a broken route, a bug), so it is final. Never for what an outage or a
        # failover looks like (a timeout, the database unreachable, a lost connection): those
        # back off up to max_attempts like any retry, and an attempt that settled a route was
        # making progress, however it ended.
        repeated = (
            claim.previous_error is not None
            and safe_error(error) == claim.previous_error
            and len(claim.settled) == settled_before
            and not _outage_shaped(e)
        )
        return await _retry_or_die(claim, error, settings, final=repeated)

    # Every route's outcome reached `on_route_settled` as it finished (its real result, even
    # where the response reports the log's "Already dispatched"); the response adds nothing.
    if transient:
        return await _retry_or_die(claim, "; ".join(dict.fromkeys(transient)), settings)

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
    """One row, start to end. Never raises: a failure is logged and the row left for the sweep
    (still `pending`, or `processing` until its lease expires)."""
    try:
        claim = await _claim(row_id, due_by, queued_key=queued_key)
    except Exception as e:  # noqa: BLE001 — e.g. a deadlock on the claim: another sweep will take it
        logger.error(f"Notification outbox row {row_id}: the claim failed ({type(e).__name__}); leaving it for the next sweep.")
        return None
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
                select(
                    table.c.id,
                    table.c.dedupe_key,
                    table.c.attempts,
                    table.c.created_at,
                    table.c.claimed_at,
                    table.c.claimed_by,
                    table.c.route_outcomes,
                )
                .where(table.c.status == OutboxStatus.PROCESSING, table.c.updated_at < cutoff)
                .order_by(table.c.updated_at)
                .limit(settings.batch_size),
            )
        ).all()
    recovered = 0
    for row in rows:
        try:
            claim = _Claim(
                id=row.id,
                dedupe_key=row.dedupe_key,
                attempts=row.attempts,
                created_at=row.created_at,
                claimed_at=row.claimed_at or cutoff,
                claimed_by=row.claimed_by,
                event_json="",
                settled=_outcomes(row.route_outcomes),
            )
            await _settle_from_log(claim)
            logger.warning(f"Notification outbox row {row.id} ({row.dedupe_key}) was left processing by {row.claimed_by}; recovering it.")
            await _retry_or_die(claim, f"The worker processing attempt {row.attempts} stopped before finishing it", settings)
            recovered += 1
        except Exception as e:  # noqa: BLE001 — one row must not stop the sweep
            logger.error(f"Notification outbox row {row.id}: recovering the abandoned claim failed ({type(e).__name__}).")
    return recovered


async def drain(settings: Optional[OutboxSettings] = None, *, now: Optional[datetime] = None) -> Dict[str, int]:
    """One sweep: recover abandoned claims, then deliver up to `batch_size` due rows. Each row is
    handled on its own, so one failing row (or a deadlocked claim) never stops the rest."""
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


#: Rows one prune statement deletes at most, so a large backlog never holds one long lock.
PRUNE_BATCH = 1000


async def prune(settings: Optional[OutboxSettings] = None, *, now: Optional[datetime] = None, batch: int = PRUNE_BATCH) -> Dict[str, int]:
    """Delete `done` rows after `done_retention_days` and `dead` ones after `dead_retention_days`
    (0 keeps them), `batch` rows per transaction."""
    settings = settings or OutboxSettings.from_env()
    now = now or _now()
    table = NotificationOutbox.__table__
    deleted = {OutboxStatus.DONE: 0, OutboxStatus.DEAD: 0}
    for status, days in ((OutboxStatus.DONE, settings.done_retention_days), (OutboxStatus.DEAD, settings.dead_retention_days)):
        if days <= 0:
            continue
        cutoff = now - timedelta(days=days)
        while True:
            async with new_session() as session:
                ids = (
                    (await session.execute(select(table.c.id).where(table.c.status == status, table.c.updated_at < cutoff).limit(batch)))
                    .scalars()
                    .all()
                )
                if ids:
                    await session.execute(delete(table).where(table.c.id.in_(ids), table.c.status == status))
                    await session.commit()
            deleted[status] += len(ids)
            if len(ids) < batch:
                break
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


#: When this process last pruned. None until its first sweep, which prunes: a deployment that
#: restarts more often than daily still prunes (an interval job's first run would be a day
#: after each start).
_last_prune: Optional[datetime] = None
PRUNE_EVERY = timedelta(hours=24)


#: The running prune, held strongly (asyncio keeps only a weak reference to a task).
_PRUNES: Set[asyncio.Task] = set()


def _start_prune_if_due(settings: OutboxSettings) -> None:
    """Start the prune in the background when it is due and none is running: a large backlog of
    batches must not hold the sweep, which runs with `max_instances=1` and would skip ticks."""
    global _last_prune
    now = _now()
    if _PRUNES or (_last_prune is not None and now - _last_prune < PRUNE_EVERY):
        return
    _last_prune = now
    task = asyncio.get_running_loop().create_task(_prune(settings, now))
    _PRUNES.add(task)
    task.add_done_callback(_PRUNES.discard)


async def _prune(settings: OutboxSettings, now: datetime) -> None:
    try:
        deleted = await prune(settings, now=now)
    except Exception as e:  # noqa: BLE001 — pruning must not fail the sweep
        logger.error(f"Notification outbox prune failed ({type(e).__name__}); trying again in a day.")
        return
    if any(deleted.values()):
        logger.info(
            f"Notification outbox prune: deleted {deleted[OutboxStatus.DONE]} done row(s) older than {settings.done_retention_days} days "
            f"and {deleted[OutboxStatus.DEAD]} dead row(s) older than {settings.dead_retention_days} days.",
        )


async def drain_notification_outbox() -> None:
    """Scheduler entry point, every minute: one sweep, and (in a task of its own, so the sweep
    doesn't wait for it) the prune on the process's first sweep and daily after. A failed sweep is logged and re-raised, so the scheduler records an
    error rather than `last_success`; the next sweep tries again."""
    settings = OutboxSettings.from_env()
    try:
        counts = await drain(settings)
    except Exception as e:
        logger.exception(f"Notification outbox sweep failed: {e}")
        raise
    if any(counts.values()):
        logger.info(
            f"Notification outbox sweep: {counts[OutboxStatus.DONE]} delivered, {counts[OutboxStatus.PENDING]} to retry, "
            f"{counts[OutboxStatus.DEAD]} dead, {counts['recovered']} abandoned claim(s) recovered.",
        )
    _start_prune_if_due(settings)
