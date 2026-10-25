"""Talon's ops findings, delivered through CoPilot's notification routes (talon-analyst SPEC §5.7
"Notifications", D96; plan OJ-5). The work of the ``invoke_talon_ops_notifications`` scheduler job.

talon-analyst never calls CoPilot's dispatch (FR-WB-6); CoPilot polls. One tick:

1. Only with the "Talon v2" setting on (off: nothing is asked), and only in the one process holding
   the poller's MySQL named lock (below).
2. ``GET /v2/ops/findings?status=open&notified=false`` page by page (``cursor``, at most
   ``MAX_PAGES`` of ``PAGE_SIZE``), with **no** ``since`` (the contract, review M4: a finding whose
   severity rises is open and unnotified again, whatever its age), as the poller's own identity
   (``identity.ops_poller_identity``: ``*``, so platform findings too). Each finding is parsed by the
   Ops tab's own parser (``talon_ops.parse_finding``); a malformed one is skipped and logged.
3. For each, one ``talon_ops_finding`` event (``event_builders.talon_ops_finding_event``) through the
   **outbox** (``outbox.queue``, then ``kick``), dedupe key ``ops:<id>:<severity>``, so a severity
   that rises is notified again and the same severity never twice. The trigger is internal-only
   (``INTERNAL_TRIGGERS``): it resolves against internal routes, whose ``min_severity`` applies.
4. Then ``POST /v2/ops/findings/{id}/notified`` with the severity notified (and the stored
   ``customer_code``). A 409 means the severity rose since it was read: nothing more is done now; the
   next tick reads the finding again at its new severity (a new key) and notifies that.

**What a failure does.** talon-analyst unreachable, or a page that isn't usable: the tick stops,
nothing is marked, the next tick starts again. The outbox can't be written: that finding isn't marked
(``notified`` is posted only once its event is durable), so the next tick tries again. ``notified``
fails: the event is already queued; the next tick finds the finding still unnotified, sees its key
in the outbox and only posts ``notified`` again. Nothing here raises into APScheduler.

**Several backend replicas: why nobody is told twice.** Three things, each covering a different race:

- **The poller's lock.** Every replica runs the job. A tick first takes the MySQL named lock
  ``LOCK_NAME`` with ``GET_LOCK(name, 0)`` (no wait) on a connection of its own and keeps it for the
  tick; a replica that can't take it skips its tick. So two replicas never read and emit the same
  page at once. (``max_instances=1`` already stops overlapping ticks within one process.) The lock is
  the server's, released with the connection, so a replica that dies never holds it.
- **The outbox, by dedupe key, across statuses.** Before queueing, the tick looks for any outbox row
  with the key (pending, processing, done or dead). The outbox's own ``queued_key`` stops a key being
  queued twice only *until its first claim*, after which the same key may be queued again (on
  purpose: A → B → A reassignment); so on its own it would not stop a second emission once the first
  was delivered. The lookup does: a finding read again because ``notified`` failed, or after a crash
  between the queue and the POST, is never emitted again while its row is kept (done rows 7 days,
  ``NOTIFICATION_OUTBOX_DONE_RETENTION_DAYS``).
- **talon-analyst's ``notified_at``.** Once posted, the finding leaves ``notified=false`` for good,
  until its severity rises (which clears it, and is a new key).

Delivery is then at least once in one narrow case, as everywhere in the outbox: a delivered row
pruned (after 7 days) while ``notified`` has failed every tick since, which would notify again once.

**No route, no backlog.** A finding with no route matching it is still marked notified: it was handed
to the notification engine, which found nobody to tell. Otherwise the first route created would
receive every old finding at once. A route created later hears about new findings, and rises.
"""
import json
from contextlib import asynccontextmanager
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Mapping
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy import text

from app.connectors.talon.services.identity import ops_poller_identity
from app.connectors.talon.services.talon_ops import Cleaners
from app.connectors.talon.services.talon_ops import TalonOpsFinding
from app.connectors.talon.services.talon_ops import caller_from_identity
from app.connectors.talon.services.talon_ops import cleaners_for
from app.connectors.talon.services.talon_ops import parse_finding
from app.connectors.talon.services.talon_v2 import is_v2_enabled
from app.connectors.talon.utils.universal import refusal_reason
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.talon.utils.v2_client import v2_request
from app.connectors.utils import get_connector_info_from_db
from app.db.universal_models import NotificationOutbox
from app.notifications.services import outbox
from app.notifications.services.event_builders import talon_ops_finding_event

#: The MySQL named lock one tick holds across every replica.
LOCK_NAME = "copilot.talon_ops_notifications"
PAGE_SIZE = 100
#: At most this many pages a tick (1,000 findings); the rest wait for the next tick.
MAX_PAGES = 10
#: talon-analyst's answer to a `notified` whose severity rose since (``api/ops.py``).
ROSE = "the finding's severity rose since; fetch it again"
MAX_BODY_BYTES = 4 * 1024 * 1024


def _counts() -> Dict[str, int]:
    return {"seen": 0, "emitted": 0, "already_queued": 0, "marked": 0, "rose": 0, "failed": 0, "malformed": 0}


@asynccontextmanager
async def poll_lock() -> AsyncIterator[bool]:
    """Whether this tick may run: the MySQL named lock taken without waiting, held until the tick
    ends (on its own connection). Another database (the tests' SQLite) has no named locks: one
    process, so it may."""
    session = outbox.new_session()
    held = False
    try:
        dialect = session.get_bind().dialect.name
        if dialect != "mysql":
            held = True
            yield True
            return
        try:
            result = await session.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": LOCK_NAME})
            held = result.scalar() == 1
        except Exception as e:  # noqa: BLE001 - no lock, no tick
            logger.error(f"Talon ops notifications: the poller's lock could not be taken ({type(e).__name__}); skipping this tick")
            held = False
        try:
            yield held
        finally:
            if held:
                try:
                    await session.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME})
                except Exception as e:  # noqa: BLE001 - closing the connection releases it anyway
                    logger.warning(f"Talon ops notifications: releasing the poller's lock failed ({type(e).__name__})")
    finally:
        await session.close()


async def _v2_on_and_cleaners() -> Optional[Cleaners]:
    """The cleaners for talon-analyst's answers, or None while "Talon v2" is off."""
    async with outbox.new_session() as session:
        if not await is_v2_enabled(session):
            return None
        attributes = await get_connector_info_from_db(TALON_CONNECTOR, session)
    return cleaners_for(attributes)


async def already_queued(dedupe_key: str) -> bool:
    """Whether the outbox has a row for ``dedupe_key`` in any status (queued, delivering, delivered
    or dead): the event was emitted already."""
    table = NotificationOutbox.__table__
    async with outbox.new_session() as session:
        result = await session.execute(select(table.c.id).where(table.c.dedupe_key == dedupe_key).limit(1))
        return result.scalars().first() is not None


async def _job_titles(identity: Mapping[str, str]) -> Dict[str, str]:
    """The jobs' display names (``GET /v2/ops/jobs``), for the summary; none on any failure."""
    answer = await v2_request("GET", "/v2/ops/jobs", identity)
    if answer.status is None or not 200 <= answer.status < 300:
        return {}
    try:
        raw = json.loads(answer.body)
        return {
            item["name"]: item["title"][:120]
            for item in raw.get("items", [])
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("title"), str)
            and item["title"].isprintable()
        }
    except Exception:  # noqa: BLE001 - the name is shown instead
        return {}


async def notify_finding(finding: TalonOpsFinding, identity: Mapping[str, str], counts: Dict[str, int], titles: Dict[str, str]) -> None:
    """Emit one finding through the outbox (unless its key is already there), then record it as
    notified at its severity. Never raises."""
    event = talon_ops_finding_event(finding, job_title=titles.get(finding.job))
    if await already_queued(event.dedupe_key):
        counts["already_queued"] += 1
    else:
        if not await outbox.queue(event):
            # Not durable, so not marked: the next tick tries again.
            counts["failed"] += 1
            logger.error(f"Talon ops notifications: finding {finding.id} could not be queued; it stays unnotified")
            return
        outbox.kick(event)
        counts["emitted"] += 1
    params = {"customer_code": finding.customer_code} if finding.customer_code is not None else None
    answer = await v2_request(
        "POST",
        f"/v2/ops/findings/{finding.id}/notified",
        identity,
        params=params,
        json_body={"severity": finding.severity},
    )
    if answer.status is not None and 200 <= answer.status < 300:
        counts["marked"] += 1
    elif answer.status == 409 and refusal_reason(409, answer.body) == ROSE:
        # Its severity rose since the page was read: the next tick reads it at the new severity.
        counts["rose"] += 1
    else:
        counts["failed"] += 1
        logger.warning(
            f"Talon ops notifications: finding {finding.id} not recorded as notified (HTTP {answer.status}); the next tick retries",
        )


async def run_poll() -> Dict[str, Any]:
    """One tick (module docstring). Returns its counts; never raises."""
    counts: Dict[str, Any] = _counts()
    try:
        async with poll_lock() as held:
            if not held:
                counts["skipped"] = "locked"
                return counts
            cleaners = await _v2_on_and_cleaners()
            if cleaners is None:
                counts["skipped"] = "v2_off"
                return counts
            await _poll(cleaners, counts)
    except Exception as e:  # noqa: BLE001 - the next tick tries again
        logger.error(f"Talon ops notifications: the tick failed: {type(e).__name__}")
        counts["failed"] += 1
    return counts


async def _poll(cleaners: Cleaners, counts: Dict[str, Any]) -> None:
    identity = ops_poller_identity()
    caller = caller_from_identity(identity)
    titles: Optional[Dict[str, str]] = None
    cursor: Optional[str] = None
    for _ in range(MAX_PAGES):
        params: Dict[str, Any] = {"status": "open", "notified": "false", "limit": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        answer = await v2_request("GET", "/v2/ops/findings", identity, params=params, max_body_bytes=MAX_BODY_BYTES)
        if answer.status is None or not 200 <= answer.status < 300:
            # An outage or a refusal: nothing is marked, the next tick starts again.
            logger.warning(f"Talon ops notifications: the findings could not be read (HTTP {answer.status}); nothing marked")
            counts["failed"] += 1
            return
        try:
            raw = json.loads(answer.body)
        except (ValueError, RecursionError):
            raw = None
        if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
            logger.warning("Talon ops notifications: a page of findings was not in the expected shape; nothing more read")
            counts["failed"] += 1
            return
        for item in raw["items"][:PAGE_SIZE]:
            finding = parse_finding(item, cleaners)
            if finding is None or not caller.sees(finding.customer_code):
                counts["malformed"] += 1
                continue
            if finding.status != "open" or finding.notified_at is not None:
                continue  # not what was asked for: never notified
            counts["seen"] += 1
            if titles is None:
                titles = await _job_titles(identity)
            await notify_finding(finding, identity, counts, titles)
        next_cursor = raw.get("next_cursor")
        if not isinstance(next_cursor, str) or not next_cursor:
            return
        cursor = next_cursor
