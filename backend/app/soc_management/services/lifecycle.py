"""Recording what happens to alerts and cases into their SLA tracking rows.

This is the one entry point the incidents module calls. Two kinds of call:

- **opened** — from the services that create alerts and cases, so no creation path can
  skip it (ingest, the manual ``POST /alert``, case creation from scratch or from an
  alert). Inserts the row and snapshots the targets in force.
- **action** — from the API routes, where a person is known to be acting. Never from
  the shared services, which automation also calls (see ``domain/lifecycle.py``).

**Best effort, never raising, in its own session.** Triage is the product; SLA
bookkeeping must not turn a successful status change into a 500. Each call runs in a
session of its own, after the caller's change is committed: a failure is logged and
rolled back *there*, and cannot expire or poison the objects the caller is about to
return — which a rollback of the request's session would do.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Awaitable
from typing import Callable
from typing import Iterable
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from loguru import logger
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.services.alert_severity import default_severity
from app.incidents.services.alert_severity import normalize_severity
from app.incidents.services.alert_severity import severity_of
from app.incidents.services.alert_severity import severity_rank
from app.soc_management.clock import utc_now
from app.soc_management.domain.lifecycle import Actor
from app.soc_management.domain.lifecycle import GuardedUpdate
from app.soc_management.domain.lifecycle import Increment
from app.soc_management.domain.lifecycle import LifecycleAction
from app.soc_management.domain.lifecycle import LifecycleEvent
from app.soc_management.domain.lifecycle import plan_milestones
from app.soc_management.domain.lifecycle import retarget_values
from app.soc_management.domain.policy import PolicyRow
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.policy import resolve_targets
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking
from app.soc_management.services import policy as policy_service

Tracking = Union[AlertSlaTracking, CaseSlaTracking]
SessionFactory = Callable[[], AbstractAsyncContextManager]


def _default_session_factory() -> SessionFactory:
    from app.db.db_session import AsyncSessionLocal

    return AsyncSessionLocal


async def case_effective_severity(session: AsyncSession, case: Case) -> str:
    """A case's severity: the analyst's choice, else its most severe linked alert, else the default."""
    explicit = normalize_severity(case.severity)
    if explicit:
        return explicit
    linked_alerts = select(Alert).join(CaseAlertLink, CaseAlertLink.alert_id == Alert.id).where(CaseAlertLink.case_id == case.id)
    linked = [severity_of(alert) for alert in (await session.execute(linked_alerts)).scalars().all()]
    if not linked:
        return default_severity()
    return max(linked, key=severity_rank)


class SlaLifecycleRecorder:
    """Writes lifecycle milestones, each call in a short transaction of its own."""

    def __init__(self, session_factory: Optional[SessionFactory] = None, clock: Callable[[], datetime] = utc_now):
        self._session_factory = session_factory or _default_session_factory()
        self.clock = clock

    # ── opening ──────────────────────────────────────────────────────────────

    async def alert_opened(self, alert: Alert) -> None:
        """A new alert reached CoPilot. Automation's doing: no acknowledgement here."""
        alert_id, severity, customer_code = alert.id, severity_of(alert), alert.customer_code
        await self._safely(f"alert {alert_id} opened", lambda s: _open(s, SlaEntity.ALERT, alert_id, severity, customer_code, self.clock()))

    async def case_opened(self, case: Case) -> None:
        case_id = case.id

        async def _run(session: AsyncSession) -> None:
            stored = await session.get(Case, case_id)
            if stored is None:
                raise LookupError(f"case {case_id} does not exist")
            severity = await case_effective_severity(session, stored)
            await _open(session, SlaEntity.CASE, case_id, severity, stored.customer_code, self.clock())

        await self._safely(f"case {case_id} opened", _run)

    # ── actions ──────────────────────────────────────────────────────────────

    async def alert_action(
        self,
        alert_id: int,
        action: LifecycleAction,
        actor: Actor,
        *,
        to_status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> None:
        event = LifecycleEvent(action=action, actor=actor, at=self.clock(), to_status=to_status, assignee=assignee)
        await self._safely(f"alert {alert_id} {action.value}", lambda s: _apply(s, SlaEntity.ALERT, alert_id, event))

    async def alerts_action(
        self,
        alert_ids: Iterable[int],
        action: LifecycleAction,
        actor: Actor,
        *,
        to_status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> None:
        for alert_id in alert_ids:
            await self.alert_action(alert_id, action, actor, to_status=to_status, assignee=assignee)

    async def case_action(
        self,
        case_id: int,
        action: LifecycleAction,
        actor: Actor,
        *,
        to_status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> None:
        event = LifecycleEvent(action=action, actor=actor, at=self.clock(), to_status=to_status, assignee=assignee)
        await self._safely(f"case {case_id} {action.value}", lambda s: _apply(s, SlaEntity.CASE, case_id, event))

    async def case_severity_changed(self, case_id: int, actor: Actor) -> None:
        """Re-target the case's running clocks, then record the change as a response."""

        async def _run(session: AsyncSession) -> None:
            await _retarget_case(session, case_id, self.clock())
            await _apply(session, SlaEntity.CASE, case_id, LifecycleEvent(LifecycleAction.SEVERITY_CHANGED, actor, self.clock()))

        await self._safely(f"case {case_id} severity changed", _run)

    async def case_links_changed(self, case_id: int) -> None:
        """Alerts were linked or unlinked: a case without an explicit severity may change tier."""
        await self._safely(f"case {case_id} links changed", lambda s: _retarget_case(s, case_id, self.clock()))

    # ── plumbing ─────────────────────────────────────────────────────────────

    async def _safely(self, what: str, work: Callable[[AsyncSession], Awaitable[None]]) -> None:
        try:
            async with self._session_factory() as session:
                await work(session)
                await session.commit()
        except Exception as e:  # noqa: BLE001 — bookkeeping must never fail triage
            logger.error(f"SLA tracking: failed to record {what}: {e}")


async def retarget_open(session: AsyncSession, customer_code: Optional[str] = None, now: Optional[datetime] = None) -> int:
    """Recompute running clocks of every open tracked item in a scope after a policy change.

    Runs in the caller's session and transaction (the policy save) and raises: unlike a
    lifecycle action, this *is* the operation the caller asked for. ``customer_code=None``
    covers every customer — the global policy can apply to any of them, and resolution
    still honours each customer's overrides. Returns how many items' due times moved.
    """
    now = now or utc_now()
    rows = await policy_service.load_rows(session)
    moved = 0
    for entity, model, owner in ((SlaEntity.ALERT, AlertSlaTracking, Alert), (SlaEntity.CASE, CaseSlaTracking, Case)):
        query = (
            select(model, owner.customer_code)
            .join(owner, owner.id == _key_column(model))
            .where(model.tracked.is_(True), model.resolved_at.is_(None))
        )
        if customer_code is not None:
            query = query.where(owner.customer_code == customer_code)
        for tracking, code in (await session.execute(query)).all():
            moved += _retarget_row(tracking, entity, code, rows, now)
    await session.flush()
    return moved


# ── internals ────────────────────────────────────────────────────────────────


async def _open(session: AsyncSession, entity: SlaEntity, item_id: int, severity: str, customer_code: Optional[str], now: datetime) -> None:
    model = _model(entity)
    if await session.get(model, item_id) is not None:
        return  # opening is idempotent
    targets = await policy_service.targets_for(session, entity, severity, customer_code)
    session.add(
        model(
            **{_key_name(model): item_id},
            severity=severity,
            opened_at=now,
            ack_due_at=targets.ack_due(now),
            resolve_due_at=targets.resolve_due(now),
            tracked=True,
            updated_at=now,
        ),
    )
    await session.flush()


async def _apply(session: AsyncSession, entity: SlaEntity, item_id: int, event: LifecycleEvent) -> None:
    await _ensure_row(session, entity, item_id, event.at)
    await _execute_plan(session, _model(entity), item_id, plan_milestones(event), event.at)


async def _execute_plan(session: AsyncSession, model: Type[Tracking], item_id: int, plan: List[GuardedUpdate], now: datetime) -> None:
    """Each step is one ``UPDATE … WHERE key = :id AND <guard>`` — atomic under concurrency."""
    key = _key_column(model)
    for step in plan:
        guard_column = getattr(model, step.guard_column)
        guard = guard_column.is_(None) if step.guard_is_null else guard_column.is_not(None)
        values = {
            column: getattr(model, column) + value.by if isinstance(value, Increment) else value for column, value in step.values.items()
        }
        values["updated_at"] = now
        await session.execute(update(model).where(key == item_id, guard).values(**values).execution_options(synchronize_session=False))


async def _ensure_row(session: AsyncSession, entity: SlaEntity, item_id: int, now: datetime) -> None:
    """Create an untracked row for an item that somehow has none.

    Every item gets a row at opening (and the migration backfilled the rest), so this
    only fires if a future creation path forgets the hook. The row is untracked — its
    real opening time is unknown — so the action is kept without inventing a clock.
    """
    model = _model(entity)
    if await session.get(model, item_id) is not None:
        return
    owner = await session.get(Alert if entity is SlaEntity.ALERT else Case, item_id)
    if owner is None:
        raise LookupError(f"{entity.value} {item_id} does not exist")
    if entity is SlaEntity.ALERT:
        severity, opened_at = severity_of(owner), owner.alert_creation_time
    else:
        severity, opened_at = await case_effective_severity(session, owner), owner.case_creation_time
    logger.warning(f"SLA tracking row missing for {entity.value} {item_id}; created untracked")
    session.add(model(**{_key_name(model): item_id}, severity=severity, opened_at=opened_at or now, tracked=False, updated_at=now))
    await session.flush()


async def _retarget_case(session: AsyncSession, case_id: int, now: datetime) -> None:
    case = await session.get(Case, case_id)
    tracking = await session.get(CaseSlaTracking, case_id)
    if case is None or tracking is None:
        return
    severity = await case_effective_severity(session, case)
    if severity == tracking.severity:
        return
    tracking.severity = severity
    tracking.updated_at = now
    rows = await policy_service.load_rows(session, [case.customer_code] if case.customer_code else [])
    _retarget_row(tracking, SlaEntity.CASE, case.customer_code, rows, now)
    await session.flush()


def _retarget_row(tracking: Tracking, entity: SlaEntity, customer_code: Optional[str], rows: List[PolicyRow], now: datetime) -> int:
    if not tracking.tracked:
        return 0
    targets = resolve_targets(entity, tracking.severity, customer_code, rows)
    values = retarget_values(
        tracking.opened_at,
        targets,
        ack_running=tracking.first_ack_at is None and tracking.resolved_at is None,
        resolve_running=tracking.resolved_at is None,
    )
    changed = {column: value for column, value in values.items() if getattr(tracking, column) != value}
    if not changed:
        return 0
    for column, value in changed.items():
        setattr(tracking, column, value)
    tracking.updated_at = now
    return 1


def _model(entity: SlaEntity) -> Type[Tracking]:
    return AlertSlaTracking if entity is SlaEntity.ALERT else CaseSlaTracking


def _key_name(model: Type[Tracking]) -> str:
    return "alert_id" if model is AlertSlaTracking else "case_id"


def _key_column(model: Type[Tracking]):
    return getattr(model, _key_name(model))
