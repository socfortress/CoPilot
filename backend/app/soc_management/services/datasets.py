"""Loading facts: alerts and cases joined to their SLA tracking, within what the caller may see.

Visibility goes through the same definitions as every other list in CoPilot:

- alerts — ``alert_visibility_filters_for_user`` (customer scoping *and* tag RBAC), the
  single definition every alert read must use, so a tag-restricted analyst's dashboard
  can never count an alert their alert list would not show them;
- cases  — ``resolve_effective_customers``, as the case list does.

Queries select plain columns, not ORM rows: a month of a busy deployment is tens of
thousands of alerts, and the dashboard needs a dozen fields of each, not the object
graph ``AlertOut`` drags along.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set

from sqlalchemy import and_
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.db.universal_models import Customers
from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.middleware.customer_access import customer_access_handler
from app.soc_management.domain.analytics import ItemFact
from app.soc_management.domain.calendar import CalendarBook
from app.soc_management.domain.lifecycle import CLOSED
from app.soc_management.domain.periods import Period
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking


@dataclass(frozen=True)
class FactFilters:
    """Optional narrowing on top of visibility. Empty means "no narrowing"."""

    severities: Sequence[str] = field(default_factory=tuple)
    #: Alert sources (wazuh, office365, …). Cases have no source and are not narrowed.
    sources: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class Visibility:
    """What one caller may see.

    ``alert_filters=None`` — no alert at all. ``case_codes=None`` — every case;
    ``[]`` — no case.
    """

    alert_filters: Optional[List[Any]]
    case_codes: Optional[List[str]]

    @property
    def sees_alerts(self) -> bool:
        return self.alert_filters is not None

    @property
    def sees_cases(self) -> bool:
        return self.case_codes is None or bool(self.case_codes)


async def visibility_for(user: User, session: AsyncSession, requested_codes: Optional[List[str]]) -> Visibility:
    alert_filters = await alert_visibility_filters_for_user(user, session, requested_codes or None)
    resolved = await customer_access_handler.resolve_effective_customers(user, requested_codes or None, session)
    case_codes = None if "*" in resolved else list(resolved)
    return Visibility(alert_filters=alert_filters, case_codes=case_codes)


#: No calendar configured: business-hours facts run on the built-in default.
NO_CALENDARS = CalendarBook()


# ── column sets ──────────────────────────────────────────────────────────────

_TRACKING_FIELDS = (
    "severity",
    "opened_at",
    "tracked",
    "ack_due_at",
    "resolve_due_at",
    "first_ack_at",
    "first_ack_by",
    "resolved_at",
    "resolved_by",
    "reopen_count",
    "paused_at",
    "paused_seconds",
    "business_hours",
)

#: Tracking columns read as-is into ItemFact (the others are converted).
_DIRECT_FIELDS = tuple(name for name in _TRACKING_FIELDS if name not in ("tracked", "reopen_count", "paused_seconds", "business_hours"))


def _tracking_columns(model) -> List[Any]:
    return [getattr(model, name) for name in _TRACKING_FIELDS]


def _window_clause(model, period: Period):
    opened = and_(model.opened_at >= period.start, model.opened_at < period.end)
    resolved = and_(model.resolved_at >= period.start, model.resolved_at < period.end)
    return or_(opened, resolved)


def _common(mapping: Any, book: CalendarBook) -> dict:
    return {
        **{name: mapping[name] for name in _DIRECT_FIELDS},
        "tracked": bool(mapping["tracked"]),
        "reopen_count": mapping["reopen_count"] or 0,
        "paused_seconds": mapping["paused_seconds"] or 0,
        "clock": book.clock(mapping["customer_code"], bool(mapping["business_hours"])),
    }


def _alert_fact(row: Any, book: CalendarBook) -> ItemFact:
    mapping = row._mapping
    return ItemFact(
        entity=SlaEntity.ALERT,
        id=mapping["id"],
        title=mapping["alert_name"] or "",
        customer_code=mapping["customer_code"],
        status=mapping["status"] or "",
        assigned_to=mapping["assigned_to"] or None,
        source=mapping["source"],
        verdict=mapping["verdict"],
        escalated=bool(mapping["escalated"]),
        in_case=bool(mapping.get("in_case", False)),
        **_common(mapping, book),
    )


def _case_fact(row: Any, book: CalendarBook) -> ItemFact:
    mapping = row._mapping
    return ItemFact(
        entity=SlaEntity.CASE,
        id=mapping["id"],
        title=mapping["case_name"] or "",
        customer_code=mapping["customer_code"],
        status=mapping["case_status"] or "",
        assigned_to=mapping["assigned_to"] or None,
        escalated=bool(mapping["escalated"]),
        **_common(mapping, book),
    )


def _alert_select(include_case_link: bool):
    columns = [
        Alert.id,
        Alert.alert_name,
        Alert.customer_code,
        Alert.status,
        Alert.assigned_to,
        Alert.source,
        Alert.verdict,
        Alert.escalated,
        *_tracking_columns(AlertSlaTracking),
    ]
    if include_case_link:
        columns.append(exists(select(CaseAlertLink.alert_id).where(CaseAlertLink.alert_id == Alert.id)).label("in_case"))
    return select(*columns).join(AlertSlaTracking, AlertSlaTracking.alert_id == Alert.id)


def _case_select():
    return select(
        Case.id,
        Case.case_name,
        Case.customer_code,
        Case.case_status,
        Case.assigned_to,
        Case.escalated,
        *_tracking_columns(CaseSlaTracking),
    ).join(CaseSlaTracking, CaseSlaTracking.case_id == Case.id)


def _alert_narrowing(filters: FactFilters) -> List[Any]:
    clauses = []
    if filters.severities:
        clauses.append(AlertSlaTracking.severity.in_(list(filters.severities)))
    if filters.sources:
        clauses.append(Alert.source.in_(list(filters.sources)))
    return clauses


def _case_narrowing(visibility: Visibility, filters: FactFilters) -> List[Any]:
    clauses = []
    if visibility.case_codes is not None:
        clauses.append(Case.customer_code.in_(visibility.case_codes))
    if filters.severities:
        clauses.append(CaseSlaTracking.severity.in_(list(filters.severities)))
    return clauses


# ── loaders ──────────────────────────────────────────────────────────────────


async def window_alerts(
    session: AsyncSession,
    visibility: Visibility,
    period: Period,
    filters: FactFilters,
    book: CalendarBook = NO_CALENDARS,
) -> List[ItemFact]:
    """Alerts opened or resolved in ``period``."""
    if not visibility.sees_alerts:
        return []
    query = _alert_select(include_case_link=True).where(
        *visibility.alert_filters,
        *_alert_narrowing(filters),
        _window_clause(AlertSlaTracking, period),
    )
    result = await session.execute(query)
    return [_alert_fact(row, book) for row in result.all()]


async def open_alerts(
    session: AsyncSession,
    visibility: Visibility,
    filters: FactFilters,
    book: CalendarBook = NO_CALENDARS,
) -> List[ItemFact]:
    """Every alert not closed right now, whenever it was opened — the backlog."""
    if not visibility.sees_alerts:
        return []
    query = _alert_select(include_case_link=False).where(*visibility.alert_filters, *_alert_narrowing(filters), Alert.status != CLOSED)
    result = await session.execute(query)
    return [_alert_fact(row, book) for row in result.all()]


async def window_cases(
    session: AsyncSession,
    visibility: Visibility,
    period: Period,
    filters: FactFilters,
    book: CalendarBook = NO_CALENDARS,
) -> List[ItemFact]:
    if not visibility.sees_cases:
        return []
    query = _case_select().where(*_case_narrowing(visibility, filters), _window_clause(CaseSlaTracking, period))
    result = await session.execute(query)
    return [_case_fact(row, book) for row in result.all()]


async def open_cases(
    session: AsyncSession,
    visibility: Visibility,
    filters: FactFilters,
    book: CalendarBook = NO_CALENDARS,
) -> List[ItemFact]:
    if not visibility.sees_cases:
        return []
    query = _case_select().where(*_case_narrowing(visibility, filters), Case.case_status != CLOSED)
    result = await session.execute(query)
    return [_case_fact(row, book) for row in result.all()]


async def alert_fact(session: AsyncSession, visibility: Visibility, alert_id: int, book: CalendarBook = NO_CALENDARS) -> Optional[ItemFact]:
    if not visibility.sees_alerts:
        return None
    query = _alert_select(include_case_link=True).where(*visibility.alert_filters, Alert.id == alert_id)
    row = (await session.execute(query)).first()
    return _alert_fact(row, book) if row else None


async def case_fact(session: AsyncSession, visibility: Visibility, case_id: int, book: CalendarBook = NO_CALENDARS) -> Optional[ItemFact]:
    if not visibility.sees_cases:
        return None
    query = _case_select().where(*_case_narrowing(visibility, FactFilters()), Case.id == case_id)
    row = (await session.execute(query)).first()
    return _case_fact(row, book) if row else None


async def tracking_since(session: AsyncSession) -> Optional[datetime]:
    """When live tracking began: the earliest opening observed rather than backfilled."""
    earliest = []
    for model in (AlertSlaTracking, CaseSlaTracking):
        result = await session.execute(select(func.min(model.opened_at)).where(model.tracked.is_(True)))
        value = result.scalar_one_or_none()
        if value is not None:
            earliest.append(value)
    return min(earliest) if earliest else None


async def soc_usernames(session: AsyncSession) -> Set[str]:
    """Usernames of the SOC team (admins and analysts) — whose actions the dashboard attributes."""
    result = await session.execute(select(User.username).where(User.role_id.in_([RoleEnum.admin.value, RoleEnum.analyst.value])))
    return set(result.scalars().all())


async def customer_names(session: AsyncSession, codes: Sequence[str]) -> Dict[str, str]:
    if not codes:
        return {}
    result = await session.execute(select(Customers.customer_code, Customers.customer_name).where(Customers.customer_code.in_(list(codes))))
    return {code: name for code, name in result.all()}
