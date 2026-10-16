"""Deciding and running Talon v2 action proposals in CoPilot (plan M5-11a; talon-analyst SPEC §5.3
M5-11, §8 "v2 API" Actions, §9.5, D46, D47, INV-ACT-1).

**Approve**, in this order (``decide``):
1. refresh the proposal from talon-analyst with the approver's own headers (``sync_action``);
   only a ``pending``, unexpired record, ``pending`` here too, may be decided;
2. D47 in CoPilot (``talon_action_execution.check_d47``);
3. one run per proposal: a guarded ``UPDATE … SET state='claiming' WHERE state='pending'``; a
   second approver gets 409;
4. the claim, ``POST /v2/actions/{id}/outcome {outcome: "approved", decided_by, copilot_ref}``
   with the approver's headers. Only ``claimed: true`` lets it run. A 4xx refusal runs nothing
   (``refused``, or ``expired``/``withdrawn`` as talon-analyst says). No usable answer (no answer,
   a 5xx, a 2xx that isn't the record, or ``claimed: false``) runs nothing either: it is
   ``claim_lost``, and CoPilot posts ``failed`` "not run: …" (decision f), retried by the job;
5. the re-checks just before running (``recheck``); a failure ends ``failed``, nothing run;
6. the run, synchronously, through CoPilot's own route handler under the approver (decisions d, e);
7. the result, ``executed`` or ``failed`` with ``{success, message, status_code}``, posted inline
   up to 3 times; then ``next_attempt_at`` hands it to ``invoke_talon_action_outcomes``.

**Deny** takes steps 1–4 with ``outcome: "denied"`` and runs nothing. A denial whose answer was
lost is tried again with the same ``copilot_ref`` (a replay is harmless: it runs nothing), and if it
is still lost the row goes back to ``pending``: the next sync shows what talon-analyst recorded.

**The job** (``run_outcome_job``) re-posts unreported results as their approver, freshly computed,
with the same ``copilot_ref``, backing off from 1 minute to hourly, and stops on success, on
talon-analyst's "after its window" 409, or 24 h after the approval (``unreported``). It also settles
``claim_lost`` rows (``failed`` once talon-analyst takes it, else whatever its record became), and
rows a crashed request left behind: ``claiming`` → ``claim_lost``, ``claimed`` → ``failed`` (nothing
ran), ``executing`` → ``unreported`` (the outcome is unknown, so nothing is claimed about it).

Every state change is a guarded update in a short session of its own (``new_session``). The
request's session is used for the D47 checks, the re-checks and the route handler, and its
transaction is ended before each call to talon-analyst.
"""
import asyncio
import uuid
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.connectors.talon.models.talon_v2 import TalonActionRequest
from app.connectors.talon.schema.talon_actions import ActionListResponse
from app.connectors.talon.schema.talon_actions import ActionOut
from app.connectors.talon.schema.talon_actions import ActionResponse
from app.connectors.talon.schema.talon_actions import TalonOutcomeAnswer
from app.connectors.talon.services import talon_action_execution as execution
from app.connectors.talon.services import talon_action_sync as sync
from app.connectors.talon.services.identity import talon_identity_headers
from app.connectors.talon.services.talon_v2 import is_v2_enabled
from app.connectors.talon.utils.universal import refusal_reason
from app.connectors.talon.utils.v2_client import V2Answer
from app.connectors.talon.utils.v2_client import v2_request
from app.connectors.velociraptor.utils.universal import FLOW_TIMEOUT_SECONDS
from app.incidents.models import Alert
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.middleware.customer_access import customer_access_handler

#: talon-analyst's ``RESULT_WINDOW``: the result must reach it within 24 h of the approval.
RESULT_WINDOW = timedelta(hours=24)
#: How often the result is tried inline before the job takes it, and the pause between tries.
INLINE_TRIES = 3
INLINE_PAUSES = (0.5, 1.0)
#: The job's back-off: 1 minute, doubling, at most hourly.
FIRST_RETRY = timedelta(minutes=1)
LAST_RETRY = timedelta(hours=1)
#: A row left mid-decision this long ago belongs to a request that is gone (``state_changed_at``).
STALE_AFTER = timedelta(minutes=15)
#: A run is given at least Velociraptor's flow timeout plus this before it counts as dead.
RUN_MARGIN = timedelta(minutes=5)
#: Rows the job handles per tick, and rows a list shows.
JOB_BATCH = 50
LIST_LIMIT = 200

# talon-analyst's fixed 409 texts (``talon.actions``) that settle a row.
EXPIRED_TEXT = "this action expired before a decision"
WITHDRAWN_TEXT = "this action was withdrawn"
NOT_APPROVED_TEXT = "this action isn't approved"
AFTER_WINDOW_TEXT = "the result came after its window"

#: A result post talon-analyst refused for its body (besides its fixed 409s): not retried.
STOP_STATUSES = frozenset({400, 422})

NOT_FOUND = "Action not found"
FAILED_TEXT = "Talon request failed"
CLAIM_LOST = "not run: the claim's answer was lost"
CLAIM_NOT_GRANTED = "not run: talon-analyst did not grant this claim"
CLAIM_MISMATCH = "not run: talon-analyst's answer to the claim is not this proposal"
STOPPED_BEFORE = "not run: CoPilot stopped before running it"
STOPPED_DURING = "CoPilot stopped while running it: the outcome is unknown"

_STATE_TEXT = {
    "claiming": "this action is being decided",
    "claimed": "this action was approved and is being run",
    "executing": "this action is being run",
    "executed": "this action was already run",
    "failed": "this action was already decided",
    "denied": "this action was denied",
    "expired": "this action expired before a decision",
    "withdrawn": "this action was withdrawn",
    "refused": "this action can no longer be decided",
    "claim_lost": "this action was already decided",
    "unreported": "this action was already decided",
}


def executing_stale_after() -> timedelta:
    """How long a row may stay ``executing``: the larger of ``STALE_AFTER`` and
    ``VELOCIRAPTOR_FLOW_TIMEOUT`` plus ``RUN_MARGIN``, so a slow run isn't called dead."""
    return max(STALE_AFTER, timedelta(seconds=FLOW_TIMEOUT_SECONDS) + RUN_MARGIN)


def new_ref() -> str:
    """CoPilot's reference for one claim (talon-analyst: at most 255 printable characters)."""
    return f"copilot-{uuid.uuid4()}"


def _fail(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


def _upstream_failure(status: Optional[int], body: bytes = b"") -> HTTPException:
    """A talon-analyst answer that isn't a record, as CoPilot's answer: its 404 (and 403) as our own
    404, so ids can't be probed; its short 4xx reason otherwise; no answer, its 401 or a 5xx: 502."""
    if status in (403, 404):
        return _fail(404, NOT_FOUND)
    if status is not None and 400 <= status < 500 and status != 401:
        return _fail(status, refusal_reason(status, body) or FAILED_TEXT)
    if status == 503:  # e.g. "the alert's tags can't be checked right now": one short line, as a 4xx's
        return _fail(503, refusal_reason(400, body) or FAILED_TEXT)
    return _fail(502, FAILED_TEXT)


# ── the view ──────────────────────────────────────────────────────────────────


async def view(row: TalonActionRequest, user: Any, session: AsyncSession, decider: Optional[bool] = None) -> ActionOut:
    now = sync.utcnow()
    expired = sync.expired_locally(row, now)
    if decider is None:
        decider = await execution.may_decide(user, row, session)
    return ActionOut(
        id=row.id,
        thread_id=row.thread_id,
        customer_code=row.customer_code,
        requester_user_id=row.requester_user_id,
        action=row.action,
        side_effect=row.side_effect,
        executes_through=row.executes_through,
        target=dict(row.target or {}),
        args=dict(row.args or {}),
        reason=row.reason or "",
        links=bool(row.links),
        provenance=dict(row.provenance or {}),
        talon_status=row.talon_status,
        state=row.state,
        state_reason=row.state_reason,
        expired=expired,
        expires_at=row.expires_at,
        created_at=row.talon_created_at or row.created_at,
        decision=row.decision,
        approver_user_id=row.approver_user_id,
        approver_username=row.approver_username,
        decided_at=row.decided_at,
        execution_result=row.execution_result,
        executed_at=row.executed_at,
        outcome_reported=row.outcome_posted_at is not None,
        can_decide=bool(decider) and row.state == "pending" and row.talon_status == "pending" and not expired,
        is_requester=row.requester_user_id == str(getattr(user, "id", "")),
    )


async def _row(action_id: str) -> Optional[TalonActionRequest]:
    async with sync.new_session() as session:
        return await session.get(TalonActionRequest, action_id, populate_existing=True)


async def _identity_then_release(user: Any, session: AsyncSession) -> Dict[str, str]:
    """The user's identity headers, then the request's transaction ended: no connection is held
    while talon-analyst answers (the session is used again afterwards, on a new transaction)."""
    identity = await talon_identity_headers(user, session)
    await session.rollback()
    return identity


async def _refresh(action_id: str, user: Any, session: AsyncSession) -> Tuple[Dict[str, str], sync.SyncResult]:
    identity = await _identity_then_release(user, session)
    result = await sync.sync_action(action_id, user, identity)
    if result.row is None:
        raise _upstream_failure(result.status)
    return identity, result


# ── reading ───────────────────────────────────────────────────────────────────


async def get_action(action_id: str, user: Any, session: AsyncSession) -> ActionResponse:
    """The card's read: synced from talon-analyst as the caller, then shown only to its requester
    or to someone D47 lets decide it (anyone else: the unknown id's 404)."""
    _, result = await _refresh(action_id, user, session)
    row = result.row
    decider = await execution.may_decide(user, row, session)
    if not decider and not (row.requester_user_id == str(user.id) and await _alert_visible(user, session, row)):
        raise _fail(404, NOT_FOUND)
    return ActionResponse(success=True, message="Action retrieved", action=await view(row, user, session, decider))


def _alert_id(row: TalonActionRequest) -> Optional[int]:
    if row.action not in sync.ALERT_ACTIONS:
        return None
    value = (row.target or {}).get("alert_id")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


async def visible_alerts(user: Any, session: AsyncSession, alert_ids: List[int]) -> Dict[int, str]:
    """The alerts of ``alert_ids`` the user may see (customer and tags:
    ``alert_visibility_filters_for_user``), with their customer, in one query."""
    if not alert_ids:
        return {}
    filters = await alert_visibility_filters_for_user(user, session)
    if filters is None:
        return {}
    rows = await session.execute(select(Alert.id, Alert.customer_code).where(Alert.id.in_(sorted(set(alert_ids))), *filters))
    return {alert_id: customer for alert_id, customer in rows.all()}


async def _alert_visible(user: Any, session: AsyncSession, row: TalonActionRequest) -> bool:
    """A host action, or an alert action whose alert the user sees and that is the record's customer's."""
    if row.action not in sync.ALERT_ACTIONS:
        return True
    alert_id = _alert_id(row)
    return alert_id is not None and (await visible_alerts(user, session, [alert_id])).get(alert_id) == row.customer_code


async def list_actions(user: Any, session: AsyncSession, scope: str) -> ActionListResponse:
    """``pending``: what the caller may decide now, and their own pending proposals; ``mine``:
    every proposal of theirs. From the mirror only, within the customers the caller has now, and for
    an alert, only if the caller sees it now (customer and tags, one query for the whole page)."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    own = str(user.id)
    query = select(TalonActionRequest)
    if "*" not in accessible:
        if not accessible:
            return ActionListResponse(success=True, message="No actions", actions=[])
        query = query.where(TalonActionRequest.customer_code.in_(accessible))
    if scope == "mine":
        query = query.where(TalonActionRequest.requester_user_id == own)
    else:
        query = query.where(TalonActionRequest.state == "pending", TalonActionRequest.expires_at > sync.utcnow())
    rows = (await session.execute(query.order_by(TalonActionRequest.created_at.desc()).limit(LIST_LIMIT))).scalars().all()
    visible = await visible_alerts(user, session, [i for i in map(_alert_id, rows) if i is not None])
    shown: List[ActionOut] = []
    for row in rows:
        if row.action in sync.ALERT_ACTIONS:
            # D47 for an alert, batched: the role, the customer (the query's filter) and the alert seen.
            seen = visible.get(_alert_id(row)) == row.customer_code
            decider = seen and execution.role_may_decide(row.action, user)
        else:
            seen = True
            decider = await execution.may_decide(user, row, session)
        if seen and (decider or row.requester_user_id == own):
            shown.append(await view(row, user, session, decider))
    return ActionListResponse(success=True, message=f"{len(shown)} action(s)", actions=shown)


# ── state changes ─────────────────────────────────────────────────────────────


async def _move(action_id: str, before: Tuple[str, ...], after: str, **values: Any) -> bool:
    """One guarded update of a row's state, only from ``before``. Whether it happened."""
    async with sync.new_session() as session:
        result = await session.execute(
            update(TalonActionRequest)
            .where(TalonActionRequest.id == action_id, TalonActionRequest.state.in_(before))
            .values(state=after, updated_at=sync.utcnow(), state_changed_at=sync.utcnow(), **values),
        )
        await session.commit()
        return result.rowcount == 1


async def _set(action_id: str, **values: Any) -> None:
    async with sync.new_session() as session:
        await session.execute(
            update(TalonActionRequest).where(TalonActionRequest.id == action_id).values(updated_at=sync.utcnow(), **values),
        )
        await session.commit()


async def _audit(
    action: AuditAction,
    row: TalonActionRequest,
    *,
    actor_id: Optional[int],
    actor_name: Optional[str],
    ok: bool,
    details: str,
    request: Optional[Request] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    await record_audit_event(
        action=action,
        actor_user_id=actor_id,
        actor_username=actor_name,
        customer_code=row.customer_code,
        entity_type="talon_action",
        entity_id=row.id,
        result=AuditResult.SUCCESS if ok else AuditResult.FAILURE,
        new_value={
            "action": row.action,
            "target": row.target,
            "requester_user_id": row.requester_user_id,
            "copilot_ref": row.copilot_ref,
            **(extra or {}),
        },
        details=details,
        request=request,
    )


# ── the claim ─────────────────────────────────────────────────────────────────


def _claim_answer(answer: V2Answer, action_id: str, outcome: str, decided_by: str) -> Tuple[str, Optional[Any]]:
    """``("granted", body)``, ``("replay", body)``, ``("refused", (status, reason))`` or
    ``("lost", None)``. Only a 4xx is a refusal talon-analyst made before changing anything."""
    if answer.status is None:
        return "lost", None
    if 200 <= answer.status < 300:
        try:
            body = TalonOutcomeAnswer.model_validate_json(answer.body)
        except ValidationError:
            return "lost", None
        if body.id != action_id or body.status != outcome or body.decided_by != decided_by:
            return "lost", None
        if body.claimed is True:
            return "granted", body
        if body.claimed is False:
            return "replay", body
        return "lost", None
    if 400 <= answer.status < 500:
        return "refused", (answer.status, refusal_reason(answer.status, answer.body) or FAILED_TEXT)
    return "lost", None


async def _post_claim(row: TalonActionRequest, identity: Dict[str, str], outcome: str, decided_by: str, ref: str) -> V2Answer:
    return await v2_request(
        "POST",
        f"/v2/actions/{row.id}/outcome",
        identity,
        json_body={"thread_id": row.thread_id, "outcome": outcome, "decided_by": decided_by, "copilot_ref": ref},
    )


def _refused_state(reason: str) -> str:
    return {EXPIRED_TEXT: "expired", WITHDRAWN_TEXT: "withdrawn"}.get(reason, "refused")


async def decide(action_id: str, user: Any, session: AsyncSession, request: Optional[Request], approve: bool) -> ActionResponse:
    """Approve (and run) or deny one proposal (module docstring)."""
    identity, result = await _refresh(action_id, user, session)
    row, body = result.row, result.body
    if row.state != "pending":
        raise _fail(409, _STATE_TEXT.get(row.state, "this action can no longer be decided"))
    if body.status != "pending" or sync.expired_locally(row):
        raise _fail(409, "this action is no longer pending")
    await execution.check_d47(user, row, session)
    plan = None
    if approve:
        try:
            plan = execution.plan_for(row)
        except execution.ProposalShape as e:
            logger.error(f"Talon v2 action {action_id}: CoPilot can't run this proposal: {e}")
            raise _fail(409, "CoPilot can't run this proposal") from None
    await session.rollback()  # the reads are done; no connection is held while talon-analyst answers

    ref = new_ref()
    claimed = await _move(
        action_id,
        ("pending",),
        "claiming",
        decision="approve" if approve else "deny",
        approver_user_id=user.id,
        approver_username=user.username,
        decided_at=sync.utcnow(),
        copilot_ref=ref,
        state_reason=None,
    )
    if not claimed:
        raise _fail(409, "someone else is deciding this action")
    row = await _row(action_id)
    if approve:
        return await _approve(row, plan, user, session, request, identity)
    return await _deny(row, user, session, request, identity)


async def _approve(row, plan, user, session, request, identity) -> ActionResponse:
    decided_by = str(user.id)
    kind, detail = _claim_answer(await _post_claim(row, identity, "approved", decided_by, row.copilot_ref), row.id, "approved", decided_by)
    if kind == "refused":
        status, reason = detail
        after = _refused_state(reason)
        await _move(row.id, ("claiming",), after, state_reason=reason[:255])
        await _audit(
            AuditAction.TALON_ACTION_APPROVE,
            row,
            actor_id=user.id,
            actor_name=user.username,
            ok=False,
            details=f"Refused by talon-analyst: {reason}",
            request=request,
        )
        raise _fail(status if status in (403, 404, 409) else 409, reason)
    if kind == "granted" and (sync.proposal_of(detail) != sync.proposal_of(row) or detail.copilot_ref != row.copilot_ref):
        # The licence must be for this proposal, as mirrored, and this claim: otherwise it is none.
        logger.error(f"Talon v2 action {row.id}: the claim's answer doesn't match the mirrored proposal; nothing runs")
        kind = "mismatch"
    if kind in ("lost", "replay", "mismatch"):
        message = {"lost": CLAIM_LOST, "replay": CLAIM_NOT_GRANTED, "mismatch": CLAIM_MISMATCH}[kind]
        await _move(
            row.id,
            ("claiming",),
            "claim_lost",
            state_reason=message,
            execution_result={"success": False, "message": message, "status_code": None},
        )
        await _audit(
            AuditAction.TALON_ACTION_APPROVE,
            row,
            actor_id=user.id,
            actor_name=user.username,
            ok=False,
            details=f"Not run: {message}",
            request=request,
        )
        await _report_inline(row.id)
        raise _fail(502, "talon-analyst's answer to the approval was lost; nothing was run")

    await sync.store_body(detail)  # talon-analyst's decision time, for the result window
    if not await _move(row.id, ("claiming",), "claimed"):
        # The job found it stale first and settled it (claim_lost: "failed" is posted): nothing runs.
        await _audit(
            AuditAction.TALON_ACTION_APPROVE,
            row,
            actor_id=user.id,
            actor_name=user.username,
            ok=True,
            details="Approved, but the claim had already been settled as lost; nothing was run",
            request=request,
        )
        return ActionResponse(
            success=False,
            message="This action was settled while it waited",
            action=await view(await _row(row.id), user, session),
        )
    await _audit(
        AuditAction.TALON_ACTION_APPROVE,
        row,
        actor_id=user.id,
        actor_name=user.username,
        ok=True,
        details="Approved in CoPilot",
        request=request,
    )
    outcome = await _execute(row, plan, user, session, request)
    await _report_inline(row.id)
    fresh = await _row(row.id)
    message = "Action executed" if outcome.get("success") else "The action did not succeed"
    return ActionResponse(success=bool(outcome.get("success")), message=message, action=await view(fresh, user, session, True))


async def _execute(row, plan, user, session, request) -> Dict[str, Any]:
    """Steps 5 and 6: the re-checks, then the run, in the request's session (a fresh transaction,
    so the host's locks are taken before anything is read in it). Records the outcome."""
    outcome: Dict[str, Any]
    ran = False
    try:
        try:
            await execution.recheck(plan, row, session)
        except execution.RecheckFailed as e:
            outcome = {"success": False, "message": f"not run: {e}", "status_code": None}
        except Exception as e:  # noqa: BLE001 - checks that can't be made fail closed
            logger.error(f"Talon v2 action {row.id}: the checks before the run failed: {type(e).__name__}")
            outcome = {"success": False, "message": "not run: the checks before the run could not be made", "status_code": None}
        else:
            if not await _move(row.id, ("claimed",), "executing"):
                return {"success": False, "message": STOPPED_BEFORE, "status_code": None}
            ran = True
            outcome = await execution.run(plan, user, session, request)
    finally:
        try:
            await session.rollback()  # releases the host's locks if the route didn't commit
        except Exception as e:  # noqa: BLE001 - the outcome is what matters now
            logger.error(f"Talon v2 action {row.id}: ending the run's transaction failed: {type(e).__name__}")
    after = "executed" if ran and outcome.get("success") else "failed"
    executed_at = sync.utcnow() if ran else None
    if not await _move(
        row.id,
        ("executing", "claimed"),
        after,
        execution_result=outcome,
        executed_at=executed_at,
        state_reason=None if after == "executed" else str(outcome.get("message") or "")[:255],
    ):
        # The job settled it meanwhile (a run longer than its window): keep what happened anyway.
        logger.error(f"Talon v2 action {row.id}: settled while it ran; its outcome ({after}) is kept but not reported")
        await _set(row.id, execution_result=outcome, executed_at=executed_at)
    await _audit(
        AuditAction.TALON_ACTION_EXECUTE,
        row,
        actor_id=user.id,
        actor_name=user.username,
        ok=after == "executed",
        details="Run in CoPilot" if ran else f"Not run: {outcome.get('message')}",
        request=request,
        extra={"args": row.args, "result": outcome},
    )
    return outcome


async def _deny(row, user, session, request, identity) -> ActionResponse:
    decided_by = str(user.id)
    kind, detail = "lost", None
    for _ in range(INLINE_TRIES):  # a lost denial may be replayed with the same reference
        kind, detail = _claim_answer(await _post_claim(row, identity, "denied", decided_by, row.copilot_ref), row.id, "denied", decided_by)
        if kind != "lost":
            break
    if kind in ("granted", "replay"):
        await sync.store_body(detail)
        await _move(row.id, ("claiming",), "denied")
        await _audit(
            AuditAction.TALON_ACTION_DENY,
            row,
            actor_id=user.id,
            actor_name=user.username,
            ok=True,
            details="Denied in CoPilot",
            request=request,
        )
        return ActionResponse(success=True, message="Action denied", action=await view(await _row(row.id), user, session, True))
    if kind == "refused":
        status, reason = detail
        await _move(row.id, ("claiming",), _refused_state(reason), state_reason=reason[:255])
        await _audit(
            AuditAction.TALON_ACTION_DENY,
            row,
            actor_id=user.id,
            actor_name=user.username,
            ok=False,
            details=f"Refused by talon-analyst: {reason}",
            request=request,
        )
        raise _fail(status if status in (403, 404, 409) else 409, reason)
    # Still no answer: nothing ran either way. Undecided here again; the next sync shows the record.
    await _move(
        row.id,
        ("claiming",),
        "pending",
        decision=None,
        approver_user_id=None,
        approver_username=None,
        decided_at=None,
        copilot_ref=None,
    )
    await _audit(
        AuditAction.TALON_ACTION_DENY,
        row,
        actor_id=user.id,
        actor_name=user.username,
        ok=False,
        details="talon-analyst's answer to the denial was lost",
        request=request,
    )
    raise _fail(502, "talon-analyst's answer to the denial was lost; nothing was run; try again")


# ── withdraw ──────────────────────────────────────────────────────────────────


async def withdraw(action_id: str, user: Any, session: AsyncSession) -> ActionResponse:
    """The requester withdraws their pending proposal, at talon-analyst with their own headers."""
    identity, result = await _refresh(action_id, user, session)
    row = result.row
    if row.requester_user_id != str(user.id):
        raise _fail(404, NOT_FOUND)
    answer = await v2_request("POST", f"/v2/actions/{action_id}/withdraw", identity)
    if answer.status is None or not 200 <= answer.status < 300:
        raise _upstream_failure(answer.status, answer.body)
    await _move(action_id, ("pending",), "withdrawn", talon_status="withdrawn", state_reason="withdrawn by the requester")
    fresh = await _row(action_id)
    return ActionResponse(success=True, message="Action withdrawn", action=await view(fresh, user, session))


# ── the result ────────────────────────────────────────────────────────────────


def _window_end(row: TalonActionRequest) -> datetime:
    return (row.talon_decided_at or row.decided_at or row.created_at) + RESULT_WINDOW


def backoff(attempts: int) -> timedelta:
    """1 minute after the first failed attempt, doubling, at most an hour."""
    return min(FIRST_RETRY * (2 ** max(0, attempts - 1)), LAST_RETRY)


def retry_delay(attempts: int) -> timedelta:
    """The pause after ``attempts`` failed posts: the inline tries each leave a minute (the job's
    first try), then the job's own failures back off (``backoff``)."""
    return backoff(max(1, attempts - INLINE_TRIES + 1))


async def _retry_later(row: TalonActionRequest, error: str, now: Optional[datetime] = None) -> str:
    now = now or sync.utcnow()
    if now >= _window_end(row):
        await _move(
            row.id,
            (row.state,),
            "unreported",
            next_attempt_at=None,
            last_outcome_error=error[:255],
            state_reason="the result could not be reported within 24 hours",
        )
        logger.warning(f"Talon v2 action {row.id}: the result could not be reported within 24 h ({error})")
        return "stopped"
    attempts = (row.outcome_attempts or 0) + 1
    await _set(row.id, outcome_attempts=attempts, next_attempt_at=now + retry_delay(attempts), last_outcome_error=error[:255])
    return "retry"


async def _settle_claim_lost(row: TalonActionRequest, identity: Dict[str, str], reason: str, approver: Any, now: Optional[datetime]) -> str:
    """A lost claim that talon-analyst says isn't approved: read its record to learn what it is."""
    if reason in (EXPIRED_TEXT, WITHDRAWN_TEXT):
        await _move(row.id, ("claim_lost",), _refused_state(reason), next_attempt_at=None, state_reason=reason)
        return "stopped"
    if reason == NOT_APPROVED_TEXT:
        result = await sync.sync_action(row.id, approver, identity)
        status = result.body.status if result.body is not None else None
        if status in ("expired", "withdrawn", "denied"):
            await _move(row.id, ("claim_lost",), status, next_attempt_at=None, state_reason=f"{CLAIM_LOST}; the record is {status}")
            return "stopped"
        if status in ("pending", None):  # the claim never landed (yet): it expires within hours
            return await _retry_later(row, f"the record is {status or 'unreadable'}", now)
    await _move(row.id, ("claim_lost",), "refused", next_attempt_at=None, state_reason=reason[:255])
    return "stopped"


async def report_result(action_id: str, now: Optional[datetime] = None) -> str:
    """Post one row's result to talon-analyst as its approver. ``"posted"``, ``"retry"`` (with
    ``next_attempt_at`` set) or ``"stopped"``; a row with nothing to post is ``"done"``."""
    row = await _row(action_id)
    if row is None or row.state not in ("executed", "failed", "claim_lost") or row.outcome_posted_at is not None:
        return "done"
    approver = await sync.load_user(row.approver_user_id) if row.approver_user_id is not None else None
    if approver is None:
        return await _retry_later(row, "the approver no longer exists", now)
    try:
        identity = await sync.identity_for(approver)
    except HTTPException:
        return await _retry_later(row, "the approver's role may not use Talon", now)
    outcome = "executed" if row.state == "executed" else "failed"
    answer = await v2_request(
        "POST",
        f"/v2/actions/{row.id}/outcome",
        identity,
        json_body={
            "thread_id": row.thread_id,
            "outcome": outcome,
            "decided_by": str(row.approver_user_id),
            "result": row.execution_result,
            "copilot_ref": row.copilot_ref,
        },
    )
    if answer.status is not None and 200 <= answer.status < 300:
        try:
            body = TalonOutcomeAnswer.model_validate_json(answer.body)
        except ValidationError:
            return await _retry_later(row, "talon-analyst's answer is not the record", now)
        if body.id != row.id or body.status != outcome:
            return await _retry_later(row, "talon-analyst's answer is not the record", now)
        await sync.store_body(body)
        posted = {"outcome_posted_at": sync.utcnow(), "next_attempt_at": None, "last_outcome_error": None}
        if row.state == "claim_lost":
            await _move(row.id, ("claim_lost",), "failed", **posted)
        else:
            await _set(row.id, **posted)
        logger.info(f"Talon v2 action {row.id}: {outcome} reported (recorded now: {body.recorded})")
        return "posted"
    if answer.status == 409:
        reason = refusal_reason(409, answer.body) or FAILED_TEXT
        if reason == AFTER_WINDOW_TEXT:
            await _move(row.id, (row.state,), "unreported", next_attempt_at=None, last_outcome_error=reason, state_reason=reason)
            return "stopped"
        if row.state == "claim_lost":
            return await _settle_claim_lost(row, identity, reason, approver, now)
        await _move(row.id, (row.state,), "unreported", next_attempt_at=None, last_outcome_error=reason[:255], state_reason=reason[:255])
        logger.error(f"Talon v2 action {row.id}: talon-analyst refused the result: {reason}")
        return "stopped"
    if answer.status in STOP_STATUSES:  # the body itself was refused: sending it again can't help
        reason = refusal_reason(answer.status, answer.body) or f"HTTP {answer.status}"
        await _move(row.id, (row.state,), "unreported", next_attempt_at=None, last_outcome_error=reason[:255], state_reason=reason[:255])
        logger.error(f"Talon v2 action {row.id}: talon-analyst refused the result ({answer.status})")
        return "stopped"
    # No answer, a 5xx, 401 (CoPilot's key), 404, 408, 429…: tried again, within the 24 h.
    return await _retry_later(row, f"no usable answer ({answer.status or 'none'})", now)


async def _report_inline(action_id: str) -> None:
    """Up to ``INLINE_TRIES`` tries in the approve request; the job takes it from there."""
    for attempt in range(INLINE_TRIES):
        try:
            if await report_result(action_id) != "retry":
                return
        except Exception as e:  # noqa: BLE001 - the job tries again
            logger.error(f"Talon v2 action {action_id}: reporting the result failed: {type(e).__name__}")
        if attempt < INLINE_TRIES - 1:
            await asyncio.sleep(INLINE_PAUSES[min(attempt, len(INLINE_PAUSES) - 1)])
    # The job's first try a minute from now (``report_result`` set it, unless it raised).
    row = await _row(action_id)
    if (
        row is not None
        and row.outcome_posted_at is None
        and row.state in ("executed", "failed", "claim_lost")
        and row.next_attempt_at is None
    ):
        await _set(action_id, next_attempt_at=sync.utcnow() + FIRST_RETRY)


# ── the job ───────────────────────────────────────────────────────────────────


async def _settle_stale(now: datetime) -> None:
    """Rows a request left mid-decision (it crashed, or the process restarted), by when their
    state last changed: a card reading the record keeps ``updated_at`` fresh, not this."""
    cutoff, run_cutoff = now - STALE_AFTER, now - executing_stale_after()
    t = TalonActionRequest
    async with sync.new_session() as session:
        stale = or_(
            and_(t.state.in_(("claiming", "claimed")), t.state_changed_at < cutoff),
            and_(t.state == "executing", t.state_changed_at < run_cutoff),
        )
        rows = (await session.execute(select(t).where(stale).limit(JOB_BATCH))).scalars().all()
    for row in rows:
        actor = {"actor_id": row.approver_user_id, "actor_name": row.approver_username}
        if row.state == "claiming" and row.decision == "deny":
            reset = {"decision": None, "approver_user_id": None, "approver_username": None, "decided_at": None, "copilot_ref": None}
            if await _move(row.id, ("claiming",), "pending", **reset):
                await _audit(AuditAction.TALON_ACTION_DENY, row, **actor, ok=False, details="The denial's answer was lost; undecided again")
        elif row.state == "claiming":
            result = {"success": False, "message": CLAIM_LOST, "status_code": None}
            if await _move(row.id, ("claiming",), "claim_lost", execution_result=result, state_reason=CLAIM_LOST, next_attempt_at=now):
                await _audit(
                    AuditAction.TALON_ACTION_APPROVE,
                    row,
                    **actor,
                    ok=False,
                    details="The claim's answer was lost; nothing was run",
                )
        elif row.state == "claimed":
            result = {"success": False, "message": STOPPED_BEFORE, "status_code": None}
            if await _move(row.id, ("claimed",), "failed", execution_result=result, state_reason=STOPPED_BEFORE, next_attempt_at=now):
                await _audit(AuditAction.TALON_ACTION_EXECUTE, row, **actor, ok=False, details=f"Not run: {STOPPED_BEFORE}")
        elif await _move(row.id, ("executing",), "unreported", state_reason=STOPPED_DURING, next_attempt_at=None):
            await _audit(AuditAction.TALON_ACTION_EXECUTE, row, **actor, ok=False, details=STOPPED_DURING)


async def run_outcome_job(now: Optional[datetime] = None) -> Dict[str, int]:
    """One tick of ``invoke_talon_action_outcomes``. Skipped while the setting is off."""
    counts = {"posted": 0, "retry": 0, "stopped": 0, "done": 0}
    async with sync.new_session() as session:
        if not await is_v2_enabled(session):
            return counts
    now = now or sync.utcnow()
    await _settle_stale(now)
    async with sync.new_session() as session:
        due = (
            (
                await session.execute(
                    select(TalonActionRequest.id)
                    .where(
                        TalonActionRequest.state.in_(("executed", "failed", "claim_lost")),
                        TalonActionRequest.outcome_posted_at.is_(None),
                        TalonActionRequest.next_attempt_at.is_not(None),
                        TalonActionRequest.next_attempt_at <= now,
                    )
                    .order_by(TalonActionRequest.next_attempt_at.asc())
                    .limit(JOB_BATCH),
                )
            )
            .scalars()
            .all()
        )
    for action_id in due:
        try:
            counts[await report_result(action_id, now)] += 1
        except Exception as e:  # noqa: BLE001 - one row must not stop the rest
            logger.error(f"Talon v2 action {action_id}: the result job failed: {type(e).__name__}")
    return counts
