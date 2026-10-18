"""The Overview's trend (#1273): how many alerts and cases opened and closed, hour by hour.

* **Opened** is ``soc_sla_*_tracking.opened_at``, written once when the item reached
  CoPilot. ``alert_creation_time`` cannot serve: ingest moves it to the latest trigger
  while the alert stays open, so it reads "last seen".
* **Closed** is the same row's ``resolved_at``: the item's current resolution, cleared on
  a reopen, so a reopened item is not counted closed.
* Buckets are **UTC hours, counted in SQL** (one ``UNION ALL … GROUP BY`` per entity). The
  portal sums them into the viewer's *local* days, which no server-side day could match
  for every timezone and across a daylight-saving change; 30 days are at most 720 rows.
* Visibility is the lists' own: ``alert_visibility_filters_for_user`` (customers **and**
  tag RBAC) for alerts, ``resolve_effective_customers`` for cases. The PDF report's
  ``monthly_trend`` filters by customer only, which would count alerts the portal hides.

Alerts and cases fail independently, like the Overview's sections.
"""

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy import func
from sqlalchemy import literal
from sqlalchemy import select
from sqlalchemy import union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.overview import TREND_DAYS
from app.customer_portal.schema.overview import OverviewTrendHour
from app.customer_portal.schema.overview import OverviewTrendResponse
from app.customer_portal.schema.overview import TrendRange
from app.incidents.models import Alert
from app.incidents.models import Case
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.middleware.customer_access import customer_access_handler
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking

HOUR_FORMAT = "%Y-%m-%d %H:00:00"

# hour -> (opened, closed)
HourCounts = Dict[str, Tuple[int, int]]


def trend_window(range_: TrendRange, now: datetime) -> Tuple[datetime, datetime]:
    """``[since, until)`` in naive UTC: whole hours, the range plus a day.

    The extra day lets the portal fill every local day of the range, whatever the
    viewer's offset from UTC (up to ±14 h).
    """
    until = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return until - timedelta(days=TREND_DAYS[range_] + 1), until


def _utc_iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hour(column):
    return func.date_format(column, HOUR_FORMAT)


def _hours_statement(entity, tracking, link, filters: list, since: datetime, until: datetime):
    """One statement: per UTC hour, how many of ``entity`` opened and how many closed in the window."""
    opened = (
        select(_hour(tracking.opened_at).label("hour"), literal(1).label("opened"), literal(0).label("closed"))
        .select_from(entity)
        .join(tracking, link)
        .where(*filters, tracking.opened_at >= since, tracking.opened_at < until)
    )
    closed = (
        select(_hour(tracking.resolved_at).label("hour"), literal(0).label("opened"), literal(1).label("closed"))
        .select_from(entity)
        .join(tracking, link)
        .where(*filters, tracking.resolved_at >= since, tracking.resolved_at < until)
    )
    events = union_all(opened, closed).subquery("events")
    return select(events.c.hour, func.sum(events.c.opened), func.sum(events.c.closed)).group_by(events.c.hour)


def alert_hours_statement(visibility: list, since: datetime, until: datetime):
    return _hours_statement(Alert, AlertSlaTracking, AlertSlaTracking.alert_id == Alert.id, visibility, since, until)


def case_hours_statement(customers: List[str], since: datetime, until: datetime):
    filters = [] if "*" in customers else [Case.customer_code.in_(customers)]
    return _hours_statement(Case, CaseSlaTracking, CaseSlaTracking.case_id == Case.id, filters, since, until)


async def _read(session: AsyncSession, statement) -> HourCounts:
    rows = (await session.execute(statement)).all()
    return {str(hour): (int(opened or 0), int(closed or 0)) for hour, opened, closed in rows if hour is not None}


def merge_hours(alerts: HourCounts, cases: HourCounts) -> List[OverviewTrendHour]:
    """The hours with any activity, oldest first, as ISO 8601 UTC."""
    merged = []
    for hour in sorted(set(alerts) | set(cases)):
        alerts_opened, alerts_closed = alerts.get(hour, (0, 0))
        cases_opened, cases_closed = cases.get(hour, (0, 0))
        merged.append(
            OverviewTrendHour(
                hour=hour.replace(" ", "T") + "Z",
                alerts_opened=alerts_opened,
                alerts_closed=alerts_closed,
                cases_opened=cases_opened,
                cases_closed=cases_closed,
            ),
        )
    return merged


async def get_overview_trend(
    user: User,
    session: AsyncSession,
    range_: TrendRange,
    now: datetime,
    customer_codes: Optional[List[str]] = None,
) -> OverviewTrendResponse:
    since, until = trend_window(range_, now)
    alerts: HourCounts = {}
    cases: HourCounts = {}
    alerts_error: Optional[str] = None
    cases_error: Optional[str] = None

    try:
        visibility = await alert_visibility_filters_for_user(user, session, customer_codes)
        # None: the caller sees no alert. Never run the query (it would mean "all").
        if visibility is not None:
            alerts = await _read(session, alert_hours_statement(visibility, since, until))
    except Exception as e:
        logger.error(f"Customer portal overview trend: failed to load alerts: {e}")
        await session.rollback()
        alerts_error = "Failed to load the alert trend"

    try:
        customers = await customer_access_handler.resolve_effective_customers(user, customer_codes, session)
        if "*" in customers or customers:
            cases = await _read(session, case_hours_statement(customers, since, until))
    except Exception as e:
        logger.error(f"Customer portal overview trend: failed to load cases: {e}")
        await session.rollback()
        cases_error = "Failed to load the case trend"

    return OverviewTrendResponse(
        range=range_,
        since=_utc_iso(since),
        until=_utc_iso(until),
        hours=merge_hours(alerts, cases),
        alerts_error=alerts_error,
        cases_error=cases_error,
    )
