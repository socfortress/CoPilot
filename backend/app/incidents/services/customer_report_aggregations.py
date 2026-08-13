"""Aggregation queries for the customer Incident-Management PDF report.

All helpers take ``(session, customer_code, date_from, date_to)`` and read
directly from the ``incident_management_*`` tables. Timestamps in those tables
default to naive UTC (``datetime.utcnow``), so callers should pass naive UTC
datetimes.

Monthly bucketing is done in Python rather than with ``func.year``/``func.month``
so the same code works on MySQL (production) and SQLite (tests / settings
fallback), which do not share date-extraction functions.
"""
from datetime import datetime
from typing import List
from typing import Tuple

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.incidents.models import Alert
from app.incidents.models import AlertTag
from app.incidents.models import AlertToIoC
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink


def _alert_window(customer_code: str, date_from: datetime, date_to: datetime):
    """Predicate: alerts created within [date_from, date_to] for the customer."""
    return and_(
        Alert.customer_code == customer_code,
        Alert.alert_creation_time >= date_from,
        Alert.alert_creation_time <= date_to,
    )


def _case_active_window(customer_code: str, date_from: datetime, date_to: datetime):
    """Predicate: cases *active* during the window.

    A case is active in the window when it was created on or before ``date_to``
    and is either still open or was closed on or after ``date_from``. This
    captures cases created before the window that remained open into it.
    """
    return and_(
        Case.customer_code == customer_code,
        Case.case_creation_time <= date_to,
        or_(Case.case_closed_time.is_(None), Case.case_closed_time >= date_from),
    )


async def count_alerts(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> int:
    result = await session.execute(select(func.count()).select_from(Alert).where(_alert_window(customer_code, date_from, date_to)))
    return int(result.scalar_one() or 0)


async def alerts_by_source(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> List[Tuple[str, int]]:
    result = await session.execute(
        select(Alert.source, func.count().label("cnt"))
        .where(_alert_window(customer_code, date_from, date_to))
        .group_by(Alert.source)
        .order_by(func.count().desc()),
    )
    return [(row[0] or "Unknown", int(row[1])) for row in result.all()]


async def alerts_by_status(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> List[Tuple[str, int]]:
    result = await session.execute(
        select(Alert.status, func.count().label("cnt"))
        .where(_alert_window(customer_code, date_from, date_to))
        .group_by(Alert.status)
        .order_by(func.count().desc()),
    )
    return [(row[0] or "Unknown", int(row[1])) for row in result.all()]


async def top_alerts_by_name(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
    limit: int = 15,
) -> List[Tuple[str, int]]:
    result = await session.execute(
        select(Alert.alert_name, func.count().label("cnt"))
        .where(_alert_window(customer_code, date_from, date_to))
        .group_by(Alert.alert_name)
        .order_by(func.count().desc())
        .limit(limit),
    )
    return [(row[0] or "Unknown", int(row[1])) for row in result.all()]


async def top_tags(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
    limit: int = 15,
) -> List[Tuple[str, int]]:
    result = await session.execute(
        select(AlertTag.tag, func.count().label("cnt"))
        .select_from(Alert)
        .join(AlertToTag, AlertToTag.alert_id == Alert.id)
        .join(AlertTag, AlertTag.id == AlertToTag.tag_id)
        .where(_alert_window(customer_code, date_from, date_to))
        .group_by(AlertTag.tag)
        .order_by(func.count().desc())
        .limit(limit),
    )
    return [(row[0] or "Unknown", int(row[1])) for row in result.all()]


async def count_cases(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> int:
    result = await session.execute(select(func.count()).select_from(Case).where(_case_active_window(customer_code, date_from, date_to)))
    return int(result.scalar_one() or 0)


async def cases_by_status(session: AsyncSession, customer_code: str, date_from: datetime, date_to: datetime) -> List[Tuple[str, int]]:
    result = await session.execute(
        select(Case.case_status, func.count().label("cnt"))
        .where(_case_active_window(customer_code, date_from, date_to))
        .group_by(Case.case_status)
        .order_by(func.count().desc()),
    )
    return [(row[0] or "Unknown", int(row[1])) for row in result.all()]


async def open_closed_case_counts(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
) -> Tuple[int, int]:
    """Return (open_cases, closed_cases) within the active window.

    Open = no ``case_closed_time``; closed = has a ``case_closed_time``.
    """
    closed_result = await session.execute(
        select(func.count())
        .select_from(Case)
        .where(_case_active_window(customer_code, date_from, date_to), Case.case_closed_time.is_not(None)),
    )
    open_result = await session.execute(
        select(func.count())
        .select_from(Case)
        .where(_case_active_window(customer_code, date_from, date_to), Case.case_closed_time.is_(None)),
    )
    return int(open_result.scalar_one() or 0), int(closed_result.scalar_one() or 0)


async def monthly_trend(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
) -> List[dict]:
    """Per-month alert vs case counts across the window, bucketed in Python.

    Returns a chronological list of ``{"month": "YYYY-MM", "alerts": n,
    "cases": n, "ratio": float}`` where ratio = cases / alerts (0 when no alerts).
    """
    alert_rows = await session.execute(
        select(Alert.alert_creation_time).where(_alert_window(customer_code, date_from, date_to)),
    )
    case_rows = await session.execute(
        select(Case.case_creation_time).where(
            Case.customer_code == customer_code,
            Case.case_creation_time >= date_from,
            Case.case_creation_time <= date_to,
        ),
    )

    buckets: dict = {}

    def _key(dt: datetime) -> str:
        return f"{dt.year:04d}-{dt.month:02d}"

    for (ts,) in alert_rows.all():
        if ts is None:
            continue
        buckets.setdefault(_key(ts), {"alerts": 0, "cases": 0})["alerts"] += 1
    for (ts,) in case_rows.all():
        if ts is None:
            continue
        buckets.setdefault(_key(ts), {"alerts": 0, "cases": 0})["cases"] += 1

    trend = []
    for month in sorted(buckets.keys()):
        alerts = buckets[month]["alerts"]
        cases = buckets[month]["cases"]
        trend.append(
            {
                "month": month,
                "alerts": alerts,
                "cases": cases,
                "ratio": round(cases / alerts, 2) if alerts else 0.0,
            },
        )
    return trend


async def fetch_active_cases(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
    limit: int = 50,
) -> Tuple[List[Case], int]:
    """Fetch cases active in the window with related data eager-loaded.

    Returns ``(cases, total_count)`` where ``cases`` is capped at ``limit`` and
    ``total_count`` is the full number of matching cases (for the "and N more"
    note in the PDF). Mirrors the eager-load chain used by the single-case PDF.
    """
    total_result = await session.execute(
        select(func.count()).select_from(Case).where(_case_active_window(customer_code, date_from, date_to)),
    )
    total_count = int(total_result.scalar_one() or 0)

    result = await session.execute(
        select(Case)
        .where(_case_active_window(customer_code, date_from, date_to))
        .order_by(Case.case_creation_time.desc())
        .limit(limit)
        .options(
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .options(
                selectinload(Alert.assets).selectinload(Asset.alert_context),
                selectinload(Alert.tags).selectinload(AlertToTag.tag),
                selectinload(Alert.comments),
                selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
            ),
            selectinload(Case.comments),
        ),
    )
    return list(result.scalars().all()), total_count


def _case_detail_loader_options():
    """The eager-load chain shared by the case-detail fetch helpers."""
    return (
        selectinload(Case.alerts)
        .selectinload(CaseAlertLink.alert)
        .options(
            selectinload(Alert.assets).selectinload(Asset.alert_context),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.comments),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        ),
        selectinload(Case.comments),
    )


async def _fetch_cases_where(session: AsyncSession, predicate, limit: int) -> Tuple[List[Case], int]:
    total_result = await session.execute(select(func.count()).select_from(Case).where(predicate))
    total_count = int(total_result.scalar_one() or 0)
    result = await session.execute(
        select(Case).where(predicate).order_by(Case.case_creation_time.desc()).limit(limit).options(*_case_detail_loader_options()),
    )
    return list(result.scalars().all()), total_count


async def fetch_open_cases(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
    limit: int = 50,
) -> Tuple[List[Case], int]:
    """Cases still open at period end: active in the window with no close time."""
    predicate = and_(_case_active_window(customer_code, date_from, date_to), Case.case_closed_time.is_(None))
    return await _fetch_cases_where(session, predicate, limit)


async def fetch_closed_cases(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
    limit: int = 50,
) -> Tuple[List[Case], int]:
    """Cases closed *within* the window (``case_closed_time`` in [from, to])."""
    predicate = and_(
        Case.customer_code == customer_code,
        Case.case_closed_time.is_not(None),
        Case.case_closed_time >= date_from,
        Case.case_closed_time <= date_to,
    )
    return await _fetch_cases_where(session, predicate, limit)


async def cases_reported_by_type(
    session: AsyncSession,
    customer_code: str,
    date_from: datetime,
    date_to: datetime,
) -> dict:
    """Count cases *created* in the window bucketed by ``[RFI]/[INC]/[CONF]/[CTI]``.

    Case type is not a native column (see issue #961 gap analysis); it is parsed
    best-effort from a bracketed prefix in ``case_name``. Anything else counts as
    ``OTROS``. Returns a dict with keys INC, RFI, CONF, CTI, OTROS and ``total``.
    """
    result = await session.execute(
        select(Case.case_name).where(
            Case.customer_code == customer_code,
            Case.case_creation_time >= date_from,
            Case.case_creation_time <= date_to,
        ),
    )
    counts = {"INC": 0, "RFI": 0, "CONF": 0, "CTI": 0, "OTROS": 0}
    total = 0
    for (name,) in result.all():
        total += 1
        upper = (name or "").upper()
        matched = next((key for key in ("INC", "RFI", "CONF", "CTI") if f"[{key}]" in upper), "OTROS")
        counts[matched] += 1
    counts["total"] = total
    return counts
