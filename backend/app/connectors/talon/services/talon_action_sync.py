"""The mirror of talon-analyst's action proposals (plan M5-11a; talon-analyst SPEC §5.3 M5-11, §8 "v2
API" Actions, §9.5).

``talon_action_request`` is filled **only** from talon-analyst's ``GET /v2/actions/{id}``, read
with a CoPilot user's own identity headers (``sync_action``): never from the chat stream, a
read-back of the thread, or the model's text. The stream only tells CoPilot *which* ids to read:

- the chat proxy's tap (``utils/approval_tap.py``) hands over each card's ``approvalId`` when the
  stream ends, however it ends, and ``sync_later`` reads them back as the requester in a detached
  task (a strong reference, its own sessions, errors logged and never raised into the stream);
- the browser's card reads ``GET /api/talon/actions/{id}``, which syncs on demand, so a missed
  sync heals itself;
- archiving a thread re-reads its pending rows (``resync_thread_later``), since talon-analyst
  withdraws them in the same transaction.

What a sync may change: talon-analyst's own fields (status, decision, times) always; CoPilot's
``state`` only while it is ``pending`` (to ``expired``, ``withdrawn`` or ``denied`` as the record
says; to ``refused`` for a decision this CoPilot didn't make). The proposal itself (customer,
action, target, arguments, requester, thread) is written once: an answer that changes it is not
believed, and a pending row whose record changed is ``refused`` (fail closed).

Every database write here uses a short session of its own (``new_session``), opened after
talon-analyst has answered, so no pooled connection waits on it.
"""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Set
from typing import Union

from loguru import logger
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import TalonActionRequest
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings
from app.connectors.talon.schema.talon_actions import TalonActionBody
from app.connectors.talon.services.identity import is_talon_customer_code
from app.connectors.talon.services.identity import talon_identity_headers
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.talon.utils.v2_client import v2_request
from app.db.db_session import AsyncSessionLocal
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

#: The §9.5 actions (talon-analyst ``talon.actions.ACTIONS``), by name: the class D47 decides by,
#: and what they target. Read here, never from talon-analyst's answer: an unknown action, or one
#: whose ``side_effect`` disagrees, is not mirrored.
ACTION_CLASSES: Dict[str, str] = {
    "set_alert_status": "external-action",
    "assign_alert": "external-action",
    "comment_on_alert": "external-action",
    "quarantine_host": "endpoint-action",
    "release_host": "endpoint-action",
}
ALERT_ACTIONS = frozenset({"set_alert_status", "assign_alert", "comment_on_alert"})
HOST_ACTIONS = frozenset({"quarantine_host", "release_host"})
#: D47: the CoPilot roles (``RoleEnum(role_id).name``, never the token's scopes) that may decide an
#: action of each class. talon-analyst checks the same (``talon.actions.APPROVER_ROLES``).
APPROVER_ROLES: Dict[str, frozenset] = {
    "endpoint-action": frozenset({"admin", "responder"}),
    "external-action": frozenset({"admin", "analyst", "responder"}),
}
#: talon-analyst's ids (lowercase UUIDs, ``talon.api.actions._ID``).
ACTION_ID_LEN = 36

#: talon-analyst status → CoPilot state, for a row nobody here has decided.
_UNDECIDED = {"pending": "pending", "expired": "expired", "withdrawn": "withdrawn", "denied": "denied"}

# Detached sync tasks, held until done (asyncio keeps only a weak reference to a task).
_background: Set["asyncio.Task[Any]"] = set()


def new_session() -> AsyncSession:
    """A short session of the mirror's own (tests point this at their database)."""
    return AsyncSessionLocal()


def utcnow() -> datetime:
    """Now as the naive UTC the ``DATETIME`` columns hold."""
    return to_naive_utc(now_utc())


def is_action_id(value: object) -> bool:
    if not isinstance(value, str) or len(value) != ACTION_ID_LEN:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


class ProposalProblem(ValueError):
    """talon-analyst's answer isn't a proposal CoPilot can mirror."""


def parse_body(raw: bytes, action_id: str) -> TalonActionBody:
    """talon-analyst's answer for ``action_id``, checked: its own id, a known action of the class
    CoPilot knows it by, a customer code talon-analyst's grammar accepts."""
    try:
        body = TalonActionBody.model_validate_json(raw)
    except ValidationError as e:
        raise ProposalProblem("the answer is not an action record") from e
    if body.id != action_id:
        raise ProposalProblem("the answer is another record")
    side_effect = ACTION_CLASSES.get(body.action)
    if side_effect is None:
        raise ProposalProblem("an action CoPilot doesn't know")
    if body.side_effect is not None and body.side_effect != side_effect:
        raise ProposalProblem("the action's class disagrees with CoPilot's")
    if not is_talon_customer_code(body.customer_code):
        raise ProposalProblem("not a customer code")
    return body


def proposal_of(body: Union[TalonActionBody, TalonActionRequest]) -> Dict[str, Any]:
    """The part of a record that never changes once proposed: what a decision is about."""
    if isinstance(body, TalonActionBody):
        return {
            "thread_id": body.thread_id,
            "tool_call_id": body.tool_call_id,
            "customer_code": body.customer_code,
            "requester_user_id": body.user_id,
            "action": body.action,
            "target": body.target,
            "args": body.args,
        }
    return {
        "thread_id": body.thread_id,
        "tool_call_id": body.tool_call_id,
        "customer_code": body.customer_code,
        "requester_user_id": body.requester_user_id,
        "action": body.action,
        "target": body.target,
        "args": body.args,
    }


def _talon_fields(body: TalonActionBody) -> Dict[str, Any]:
    return {
        "talon_status": body.status,
        "talon_decided_by": body.decided_by,
        "talon_decided_at": to_naive_utc(body.decided_at),
        "talon_reported_at": to_naive_utc(body.reported_at),
        "talon_created_at": to_naive_utc(body.created_at),
        "expires_at": to_naive_utc(body.expires_at),
        "result_due_by": to_naive_utc(body.result_due_by),
    }


def _new_row(body: TalonActionBody, now: datetime) -> TalonActionRequest:
    state = _UNDECIDED.get(body.status, "refused")
    return TalonActionRequest(
        id=body.id,
        thread_id=body.thread_id,
        tool_call_id=body.tool_call_id,
        customer_code=body.customer_code,
        requester_user_id=body.user_id,
        action=body.action,
        side_effect=ACTION_CLASSES[body.action],
        executes_through=body.executes_through,
        target=dict(body.target),
        args=dict(body.args),
        reason=body.reason,
        links=body.links,
        provenance=dict(body.provenance),
        state=state,
        state_reason=None if state != "refused" else "decided outside this CoPilot",
        synced_at=now,
        created_at=now,
        updated_at=now,
        state_changed_at=now,
        **_talon_fields(body),
    )


async def store_body(body: TalonActionBody) -> TalonActionRequest:
    """Insert or refresh the mirror row from talon-analyst's record (module docstring rules)."""
    for attempt in range(2):
        now = utcnow()
        async with new_session() as session:
            row = await session.get(TalonActionRequest, body.id, populate_existing=True)
            if row is None:
                row = _new_row(body, now)
                session.add(row)
                try:
                    await session.commit()
                except IntegrityError:  # another sync inserted it first: refresh that row instead
                    await session.rollback()
                    if attempt:
                        raise
                    continue
                logger.info(f"Talon v2 action {body.id}: mirrored ({body.action}, {body.status})")
                return row
            values: Dict[str, Any] = {**_talon_fields(body), "synced_at": now, "updated_at": now}
            await session.execute(update(TalonActionRequest).where(TalonActionRequest.id == body.id).values(**values))
            if proposal_of(body) != proposal_of(row):
                # talon-analyst never changes a proposal: whatever changed it, nothing decides it now.
                logger.error(f"Talon v2 action {body.id}: the record no longer matches the mirror; refused")
                await _move(session, body.id, "pending", "refused", "the record changed after it was mirrored", now)
            elif body.status != "pending":
                after = _UNDECIDED.get(body.status, "refused")
                reason = None if after != "refused" else "decided outside this CoPilot"
                await _move(session, body.id, "pending", after, reason, now)
            await session.commit()
            fresh = await session.get(TalonActionRequest, body.id, populate_existing=True)
            return fresh
    raise AssertionError("unreachable")


async def _move(session: AsyncSession, action_id: str, before: str, after: str, reason: Optional[str], now: datetime) -> bool:
    """One guarded state change: only from ``before``. Whether it happened."""
    if before == after:
        return False
    result = await session.execute(
        update(TalonActionRequest)
        .where(TalonActionRequest.id == action_id, TalonActionRequest.state == before)
        .values(state=after, state_reason=reason, updated_at=now, state_changed_at=now),
    )
    return result.rowcount == 1


@dataclass
class SyncResult:
    """What a sync found: talon-analyst's status (None: no usable answer), the record, the row."""

    status: Optional[int]
    body: Optional[TalonActionBody] = None
    row: Optional[TalonActionRequest] = None


async def load_user(user_id: int) -> Optional[User]:
    async with new_session() as session:
        return await session.get(User, user_id)


async def identity_for(user: Union[User, Any]) -> Dict[str, str]:
    """The user's five identity headers, computed now in a session of its own."""
    async with new_session() as session:
        return await talon_identity_headers(user, session)


async def sync_action(action_id: str, user: Union[User, Any], identity: Optional[Dict[str, str]] = None) -> SyncResult:
    """Read ``action_id`` back from talon-analyst as ``user`` (with their own identity headers) and
    mirror it. talon-analyst answers only the requester, an admin or a D47 approver of the action
    with its customer (and, for an alert, the alert inside their tag filter): anyone else gets its
    404, which is passed on as is and changes nothing here."""
    if not is_action_id(action_id):
        return SyncResult(404)
    identity = identity if identity is not None else await identity_for(user)
    answer = await v2_request("GET", f"/v2/actions/{action_id}", identity)
    if answer.status is None or not 200 <= answer.status < 300:
        return SyncResult(answer.status)
    try:
        body = parse_body(answer.body, action_id)
    except ProposalProblem as e:
        logger.error(f"Talon v2 action {action_id}: not mirrored: {e}")
        return SyncResult(None)
    return SyncResult(answer.status, body, await store_body(body))


# ── detached syncs (the chat tap, the archive) ────────────────────────────────


async def _v2_on() -> bool:
    async with new_session() as session:
        result = await session.execute(
            select(TalonConnectorSettings.v2_enabled).where(TalonConnectorSettings.connector_name == TALON_CONNECTOR),
        )
        return bool(result.scalars().first())


async def _sync_as(action_ids: Iterable[str], user_id: int, what: str) -> None:
    """Sync each id as the user, in this task's own sessions. Never raises."""
    try:
        if not await _v2_on():
            return
        user = await load_user(user_id)
        if user is None:
            logger.warning(f"Talon v2: {what}: user {user_id} no longer exists; nothing synced")
            return
        identity = await identity_for(user)
        for action_id in action_ids:
            try:
                result = await sync_action(action_id, user, identity)
                if result.row is None:
                    logger.warning(f"Talon v2 action {action_id}: {what}: talon-analyst answered {result.status}; not mirrored")
            except Exception as e:  # noqa: BLE001 - one record must not stop the others
                logger.error(f"Talon v2 action {action_id}: {what} failed: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 - a detached task: logged, never raised
        logger.error(f"Talon v2: {what} failed: {type(e).__name__}")


def spawn(coro: Any) -> "asyncio.Task[Any]":
    """Run ``coro`` detached from the request, held until it is done."""
    task = asyncio.get_running_loop().create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task


def sync_later(action_ids: Iterable[str], user_id: int) -> None:
    """The chat tap's hand-off: mirror the stream's cards as their requester, after the stream."""
    ids = [action_id for action_id in action_ids if is_action_id(action_id)]
    if ids:
        spawn(_sync_as(ids, user_id, "the chat stream's sync"))


async def _resync_thread(thread_id: str, user_id: int) -> None:
    try:
        async with new_session() as session:
            result = await session.execute(
                select(TalonActionRequest.id).where(TalonActionRequest.thread_id == thread_id, TalonActionRequest.state == "pending"),
            )
            ids = list(result.scalars().all())
    except Exception as e:  # noqa: BLE001 - a detached task: logged, never raised
        logger.error(f"Talon v2: reading thread {thread_id}'s pending actions failed: {type(e).__name__}")
        return
    if ids:
        await _sync_as(ids, user_id, "the archive's re-sync")


def resync_thread_later(thread_id: str, user_id: int) -> None:
    """Archiving a thread withdraws its pending proposals at talon-analyst: read them again."""
    spawn(_resync_thread(str(thread_id), user_id))


async def wait_for_background(timeout: float = 5.0) -> None:
    """Wait for the detached syncs (tests; a shutdown)."""
    deadline = asyncio.get_running_loop().time() + timeout
    while _background and asyncio.get_running_loop().time() < deadline:
        await asyncio.wait(set(_background), timeout=max(0.0, deadline - asyncio.get_running_loop().time()))


def expired_locally(row: TalonActionRequest, now: Optional[datetime] = None) -> bool:
    """A row nobody decided whose ``expires_at`` has passed (shown locally, M5-11 "Expiry")."""
    return row.state == "pending" and row.expires_at <= (now or utcnow())


__all__ = [
    "ACTION_CLASSES",
    "ALERT_ACTIONS",
    "APPROVER_ROLES",
    "HOST_ACTIONS",
    "ProposalProblem",
    "SyncResult",
    "expired_locally",
    "identity_for",
    "is_action_id",
    "load_user",
    "new_session",
    "parse_body",
    "proposal_of",
    "resync_thread_later",
    "spawn",
    "store_body",
    "sync_action",
    "sync_later",
    "utcnow",
    "wait_for_background",
]
