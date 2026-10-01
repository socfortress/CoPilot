"""The SLA notifier: tell the SOC, once, when a clock turns at risk or breaches (#1187).

Runs as the ``notify_sla_transitions`` scheduler job. Each run reads every open tracked
item, asks ``domain/notices.py`` what it owes, and for each notice:

1. claims it with a guarded ``UPDATE … SET <stamp> = now WHERE <stamp> IS NULL``;
2. sends it only if the claim won (``rowcount == 1``).

Claim first, send second: two overlapping runs (a slow provider, two workers) can both
*see* an unstamped clock, but only one can stamp it, so only one sends. The cost is
that a send that fails after its claim is not retried — the dispatch log records the
failure, and a missed SLA nag is far cheaper than a duplicated one every two minutes.

Notifications go to **internal routes only** (``sla_at_risk`` / ``sla_breached`` are in
``INTERNAL_TRIGGERS``): a SOC running late is never the customer's notification.
"""

from __future__ import annotations

from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.db_session import async_engine
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.services.emit import emit
from app.notifications.services.event_builders import sla_event
from app.soc_management.clock import utc_now
from app.soc_management.domain.analytics import ItemFact
from app.soc_management.domain.notices import STAMP_COLUMNS
from app.soc_management.domain.notices import Notice
from app.soc_management.domain.notices import NoticeKind
from app.soc_management.domain.notices import notices_for
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking
from app.soc_management.services import calendars as calendar_service
from app.soc_management.services import datasets
from app.soc_management.services.datasets import FactFilters
from app.soc_management.services.datasets import Visibility

#: Every alert and every case: the job runs for the deployment, not for a user.
EVERYTHING = Visibility(alert_filters=[], case_codes=None)

_MODELS = {SlaEntity.ALERT: (AlertSlaTracking, AlertSlaTracking.alert_id), SlaEntity.CASE: (CaseSlaTracking, CaseSlaTracking.case_id)}
_ENTITY_TYPES = {SlaEntity.ALERT: EntityType.ALERT, SlaEntity.CASE: EntityType.CASE}


class SlaNotifier:
    def __init__(
        self,
        session_factory: Optional[Callable[[], AsyncSession]] = None,
        send: Callable[[NotificationEvent], None] = emit,
        clock: Callable = utc_now,
    ):
        self._sessions = session_factory or async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        self._send = send
        self._clock = clock

    async def run(self) -> Dict[str, int]:
        """One pass. Returns counts per outcome, for the job log and the tests."""
        now = self._clock()
        counts = {"sent": 0, "silenced": 0, "lost_race": 0}
        async with self._sessions() as session:
            book = await calendar_service.load_book(session)
            facts = [
                *await datasets.open_alerts(session, EVERYTHING, FactFilters(), book),
                *await datasets.open_cases(session, EVERYTHING, FactFilters(), book),
            ]
            owed = await self._owed(session, facts, now)
            for fact, notice in owed:
                if not await self._claim(session, fact, notice, now):
                    counts["lost_race"] += 1
                    continue
                if notice.silent:
                    counts["silenced"] += 1
                    continue
                self._send(_event(fact, notice, now))
                counts["sent"] += 1
        return counts

    async def _owed(self, session: AsyncSession, facts: List[ItemFact], now) -> List[tuple]:
        """Every (fact, notice) owed, reading the stamps only of items that might owe one."""
        candidates = [fact for fact in facts if fact.tracked and fact.live_state(now).value in ("at_risk", "breached")]
        owed = []
        for entity in SlaEntity:
            subset = [fact for fact in candidates if fact.entity is entity]
            if not subset:
                continue
            model, key = _MODELS[entity]
            rows = await session.execute(
                select(key, *(getattr(model, column) for column in STAMP_COLUMNS)).where(key.in_([f.id for f in subset])),
            )
            stamps = {row[0]: dict(zip(STAMP_COLUMNS, row[1:])) for row in rows.all()}
            owed.extend((fact, notice) for fact in subset for notice in notices_for(fact, stamps.get(fact.id, {}), now))
        return owed

    async def _claim(self, session: AsyncSession, fact: ItemFact, notice: Notice, now) -> bool:
        model, key = _MODELS[fact.entity]
        column = getattr(model, notice.column)
        result = await session.execute(update(model).where(key == fact.id, column.is_(None)).values({notice.column: now}))
        for settled in notice.settles:
            settled_column = getattr(model, settled)
            await session.execute(update(model).where(key == fact.id, settled_column.is_(None)).values({settled: now}))
        await session.commit()
        return result.rowcount == 1


def _event(fact: ItemFact, notice: Notice, now) -> NotificationEvent:
    return sla_event(
        breached=notice.kind is NoticeKind.BREACHED,
        entity_type=_ENTITY_TYPES[fact.entity],
        entity_id=fact.id,
        title=fact.title,
        severity=fact.severity,
        customer_code=fact.customer_code,
        assignee=fact.assigned_to,
        clock=notice.clock.label,
        due_at=notice.due_at,
        opened_at=fact.opened_at,
        now=now,
        status=fact.status,
    )


async def notify_sla_transitions() -> None:
    """Scheduler entry point.

    A failed pass is logged and re-raised, so the scheduler records it as an error rather
    than stamping ``last_success``; the next pass simply tries again.
    """
    try:
        counts = await SlaNotifier().run()
    except Exception as e:
        logger.exception(f"SLA notifier pass failed: {e}")
        raise
    if any(counts.values()):
        logger.info(f"SLA notifier: {counts['sent']} sent, {counts['silenced']} stale breach(es) stamped silently")
