"""The Customer Portal's Activity page (#1284): what the SOC handled for a customer, broken down.

The page answers "what reached the SOC, from where, about which assets, and how much of it
was real" over the last 7, 30 or 90 days, beside the same figures for the period before.
Rules that shape it:

* **Opt-in per customer.** ``customer_portal_activity_settings`` is the operator's switch;
  a missing row reads as off. The caller's customers are narrowed to those whose switch is
  on *before* anything is counted, so a disabled customer adds nothing to any figure.
* **Counted from when an item reached the SOC**: the SLA clocks' ``opened_at``, written
  once. ``alert_creation_time`` cannot serve: ingest moves it to the latest trigger while
  an alert stays open, so a busy old alert would keep counting as new. The alerts list
  takes the same window (``opened_from`` / ``opened_before`` on
  ``/incidents/db_operations/alerts/filter``), so a click on a slice lists exactly the
  alerts it counted.
* **Visibility is the lists' own**: ``alert_visibility_filters_for_user`` (customers and
  tag RBAC) for alerts, the enabled customers for cases.
* **Both periods in one statement per section**: each row is counted into the current or
  the previous window by a ``CASE`` on ``opened_at``, and alerts are counted ``DISTINCT``
  so an alert with two assets or two tags is still one alert per slice.
* **Sections fail on their own** (alerts, verdicts, cases): an error is logged, rolled
  back and reported on that section only, like the Overview's.

The PDF report asks the same questions per customer and calendar window; the verdict rates
(``verdict_stats.verdict_figures``) and case types (``case_type_key``) are shared with it,
so the two cannot compute them differently.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.activity import ACTIVITY_DAYS
from app.customer_portal.schema.activity import ActivityAlertsSection
from app.customer_portal.schema.activity import ActivityCasesSection
from app.customer_portal.schema.activity import ActivityCount
from app.customer_portal.schema.activity import ActivityNoisyDetection
from app.customer_portal.schema.activity import ActivityRange
from app.customer_portal.schema.activity import ActivityTotal
from app.customer_portal.schema.activity import ActivityVerdictFigures
from app.customer_portal.schema.activity import ActivityVerdictsSection
from app.customer_portal.schema.activity import PortalActivityResponse
from app.db.universal_models import CustomerPortalActivitySettings
from app.incidents.models import Alert
from app.incidents.models import AlertTag
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.services.alert_severity import SEVERITY_LEVELS
from app.incidents.services.alert_severity import default_severity
from app.incidents.services.alert_severity import normalize_severity
from app.incidents.services.customer_report_aggregations import case_type_key
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.incidents.services.verdict_stats import FALSE_POSITIVE
from app.incidents.services.verdict_stats import false_positive_reason_label
from app.incidents.services.verdict_stats import verdict_figures
from app.middleware.customer_access import customer_access_handler
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking
from app.time_utils import now_utc

#: How many slices a "top" list carries.
TOP_LIMIT = 10
#: Sources shown one by one; the rest are added up into ``other_sources``.
SOURCE_LIMIT = 8
#: Alert names with the most false positives.
NOISY_LIMIT = 5

CASE_TYPE_LABELS = {
    "INC": "Incident",
    "RFI": "Request for information",
    "CONF": "Configuration",
    "CTI": "Threat intelligence",
    "OTHER": "Other",
}

# Counted per period: (count in the current window, count in the previous one).
Split = Tuple[int, int]


# ── the switch ───────────────────────────────────────────────────────────────


async def get_activity_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalActivitySettings]:
    result = await session.execute(
        select(CustomerPortalActivitySettings).where(CustomerPortalActivitySettings.customer_code == customer_code),
    )
    return result.scalars().first()


async def upsert_activity_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalActivitySettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_activity_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalActivitySettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def enabled_customer_codes(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> List[str]:
    """The customers ``user`` may see *and* whose Activity page is on, optionally narrowed to ``requested``."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalActivitySettings.customer_code).where(CustomerPortalActivitySettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalActivitySettings.customer_code.in_(accessible))
    if requested:
        query = query.where(CustomerPortalActivitySettings.customer_code.in_(requested))
    return sorted((await session.execute(query)).scalars().all())


async def availability(user: User, session: AsyncSession, customer_code: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Whether the Activity page should render: for one customer the caller may see, else for any."""
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        settings = await get_activity_settings(customer_code, session)
        return customer_code, bool(settings and settings.enabled)
    return None, bool(await enabled_customer_codes(user, session))


# ── windows and pure shaping ────────────────────────────────────────────────


def activity_window(range_: ActivityRange, now: datetime) -> Tuple[datetime, datetime, datetime]:
    """``(previous_since, since, until)`` in naive UTC, whole seconds like the columns.

    The period is ``[since, until)`` and the one before it ``[previous_since, since)``.
    """
    until = now.replace(microsecond=0)
    length = timedelta(days=ACTIVITY_DAYS[range_])
    return until - 2 * length, until - length, until


def utc_iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def counts(rows: Iterable[Tuple[Optional[str], int, int]], labels: Optional[Dict[str, str]] = None) -> List[ActivityCount]:
    """Rows of ``(key, current, previous)`` as slices, keeping their order. Pure."""
    labels = labels or {}
    return [
        ActivityCount(key=key, label=labels.get(key), count=int(current or 0), previous=int(previous or 0))
        for key, current, previous in rows
        if key is not None
    ]


def ranked(totals: Dict[str, Split], limit: Optional[int] = None) -> List[Tuple[str, int, int]]:
    """``totals`` as ``(key, current, previous)``, busiest now first, then by name. Pure.

    A key with nothing in the current period is left out: a top list says what is busy now.
    """
    rows = sorted(((key, cur, prev) for key, (cur, prev) in totals.items() if cur > 0), key=lambda row: (-row[1], row[0]))
    return rows if limit is None else rows[:limit]


def fold_sources(rows: List[Tuple[Optional[str], int, int]]) -> Tuple[List[ActivityCount], ActivityTotal]:
    """The busiest sources one by one, the rest added up. Pure.

    A source with alerts only in the previous period still counts in the total it left.
    """
    totals: Dict[str, Split] = {}
    for key, cur, prev in rows:
        name = key or "Unknown"
        old_cur, old_prev = totals.get(name, (0, 0))
        totals[name] = (old_cur + int(cur or 0), old_prev + int(prev or 0))
    shown = ranked(totals, SOURCE_LIMIT)
    shown_keys = {key for key, _, _ in shown}
    other = ActivityTotal(
        count=sum(cur for key, (cur, _) in totals.items() if key not in shown_keys),
        previous=sum(prev for key, (_, prev) in totals.items() if key not in shown_keys),
    )
    return counts(shown), other


def severity_counts(rows: Iterable[Tuple[Optional[str], int, int]]) -> List[ActivityCount]:
    """Every level, most severe first; an alert whose source gave none takes the default. Pure.

    Grouped by the stored value in SQL, resolved here like everywhere else (``severity_of``):
    a NULL severity is the deployment's default, never "unimportant".
    """
    totals: Dict[str, Split] = {level: (0, 0) for level in SEVERITY_LEVELS}
    fallback = default_severity()
    for stored, cur, prev in rows:
        level = normalize_severity(stored) or fallback
        old_cur, old_prev = totals[level]
        totals[level] = (old_cur + int(cur or 0), old_prev + int(prev or 0))
    return counts((level, *totals[level]) for level in reversed(SEVERITY_LEVELS))


def verdict_section_figures(rows: Iterable[Tuple[Optional[str], int, int]]) -> Tuple[ActivityVerdictFigures, ActivityVerdictFigures]:
    """The verdict headline of each period from ``(verdict, current, previous)``. Pure."""
    current: Dict[Optional[str], int] = {}
    previous: Dict[Optional[str], int] = {}
    for verdict, cur, prev in rows:
        current[verdict] = current.get(verdict, 0) + int(cur or 0)
        previous[verdict] = previous.get(verdict, 0) + int(prev or 0)
    return ActivityVerdictFigures(**verdict_figures(current)), ActivityVerdictFigures(**verdict_figures(previous))


def case_breakdown(rows: Iterable[Tuple[Optional[str], Optional[str], bool]]) -> ActivityCasesSection:
    """Cases opened in each period from ``(case_name, case_status, in_current_period)``. Pure."""
    opened = [0, 0]
    types: Dict[str, Split] = {key: (0, 0) for key in CASE_TYPE_LABELS}
    statuses: Dict[str, Split] = {}
    for name, status, current in rows:
        index = 0 if current else 1
        opened[index] += 1
        type_key = case_type_key(name) or "OTHER"
        status_key = status or "UNKNOWN"
        for bucket, key in ((types, type_key), (statuses, status_key)):
            pair = list(bucket.get(key, (0, 0)))
            pair[index] += 1
            bucket[key] = (pair[0], pair[1])
    return ActivityCasesSection(
        opened=ActivityTotal(count=opened[0], previous=opened[1]),
        by_type=counts(((key, cur, prev) for key, (cur, prev) in types.items() if cur or prev), CASE_TYPE_LABELS),
        by_status=counts((key, cur, prev) for key, (cur, prev) in sorted(statuses.items(), key=lambda item: -item[1][0])),
    )


# ── the queries ─────────────────────────────────────────────────────────────


def _alert_columns(since: datetime):
    """Distinct alerts opened in the current period, and in the previous one."""
    current = func.count(func.distinct(case((AlertSlaTracking.opened_at >= since, Alert.id))))
    previous = func.count(func.distinct(case((AlertSlaTracking.opened_at < since, Alert.id))))
    return current.label("current"), previous.label("previous")


def _alerts_in_window(columns, visibility: list, previous_since: datetime, until: datetime):
    """``select(columns)`` over the visible alerts opened in either period."""
    return (
        select(*columns)
        .select_from(Alert)
        .join(AlertSlaTracking, AlertSlaTracking.alert_id == Alert.id)
        .where(*visibility, AlertSlaTracking.opened_at >= previous_since, AlertSlaTracking.opened_at < until)
    )


def _grouped(key, visibility: list, window: Tuple[datetime, datetime, datetime], join=None, where: Iterable = ()):
    previous_since, since, until = window
    current, previous = _alert_columns(since)
    statement = _alerts_in_window((key, current, previous), visibility, previous_since, until)
    for target, on in join or ():
        statement = statement.join(target, on)
    return statement.where(*where).group_by(key)


def _top(key, visibility: list, window, join=None, where: Iterable = ()):
    """The ``TOP_LIMIT`` busiest keys of the current period, in SQL."""
    current, _ = _alert_columns(window[1])
    return (
        _grouped(key, visibility, window, join=join, where=where).having(current > 0).order_by(current.desc(), key.asc()).limit(TOP_LIMIT)
    )


async def _rows(session: AsyncSession, statement) -> List[Tuple[Optional[str], int, int]]:
    return [(row[0], int(row[1] or 0), int(row[2] or 0)) for row in (await session.execute(statement)).all()]


async def alerts_section(session: AsyncSession, visibility: list, window) -> ActivityAlertsSection:
    by_source, other = fold_sources(await _rows(session, _grouped(Alert.source, visibility, window)))
    opened = ActivityTotal(
        count=sum(item.count for item in by_source) + other.count,
        previous=sum(item.previous for item in by_source) + other.previous,
    )
    return ActivityAlertsSection(
        opened=opened,
        by_source=by_source,
        other_sources=other,
        by_severity=severity_counts(await _rows(session, _grouped(Alert.severity, visibility, window))),
        top_detections=counts(await _rows(session, _top(Alert.alert_name, visibility, window))),
        top_assets=counts(
            await _rows(session, _top(Asset.asset_name, visibility, window, join=[(Asset, Asset.alert_linked == Alert.id)])),
        ),
        top_tags=counts(
            await _rows(
                session,
                _top(
                    AlertTag.tag,
                    visibility,
                    window,
                    join=[(AlertToTag, AlertToTag.alert_id == Alert.id), (AlertTag, AlertTag.id == AlertToTag.tag_id)],
                ),
            ),
        ),
    )


async def verdicts_section(session: AsyncSession, visibility: list, window) -> ActivityVerdictsSection:
    previous_since, since, until = window
    current, previous = verdict_section_figures(await _rows(session, _grouped(Alert.verdict, visibility, window)))

    reason_rows = await _rows(session, _grouped(Alert.verdict_reason, visibility, window, where=[Alert.verdict == FALSE_POSITIVE]))
    reasons: Dict[str, Split] = {}
    for reason, cur, prev in reason_rows:
        key = reason or "UNSPECIFIED"
        old_cur, old_prev = reasons.get(key, (0, 0))
        reasons[key] = (old_cur + cur, old_prev + prev)
    labels = {key: false_positive_reason_label(None if key == "UNSPECIFIED" else key) for key in reasons}

    in_current = AlertSlaTracking.opened_at >= since
    false_positives = func.count(func.distinct(case((in_current & (Alert.verdict == FALSE_POSITIVE), Alert.id))))
    reviewed = func.count(func.distinct(case((in_current & Alert.verdict.is_not(None), Alert.id))))
    noisy = await session.execute(
        _alerts_in_window((Alert.alert_name, false_positives, reviewed), visibility, previous_since, until)
        .group_by(Alert.alert_name)
        .having(false_positives > 0)
        .order_by(false_positives.desc(), Alert.alert_name.asc())
        .limit(NOISY_LIMIT),
    )
    return ActivityVerdictsSection(
        current=current,
        previous=previous,
        reasons=counts(ranked(reasons), labels),
        noisy_detections=[
            ActivityNoisyDetection(
                name=name or "Unknown",
                false_positives=int(fp or 0),
                reviewed=int(seen or 0),
                false_positive_rate=round(int(fp or 0) / int(seen) * 100, 1) if seen else None,
            )
            for name, fp, seen in noisy.all()
        ],
    )


async def cases_section(session: AsyncSession, codes: List[str], window) -> ActivityCasesSection:
    previous_since, since, until = window
    rows = await session.execute(
        select(Case.case_name, Case.case_status, CaseSlaTracking.opened_at >= since)
        .select_from(Case)
        .join(CaseSlaTracking, CaseSlaTracking.case_id == Case.id)
        .where(Case.customer_code.in_(codes), CaseSlaTracking.opened_at >= previous_since, CaseSlaTracking.opened_at < until),
    )
    return case_breakdown((name, status, bool(current)) for name, status, current in rows.all())


async def _section(session: AsyncSession, name: str, load, empty):
    """Run one section; a failure is logged, rolled back and reported on that section only."""
    try:
        return await load()
    except Exception as e:
        logger.error(f"Customer portal activity: failed to load {name}: {e}")
        await session.rollback()
        return empty(error=f"Failed to load the {name}")


async def activity(
    user: User,
    session: AsyncSession,
    range_: ActivityRange,
    now: datetime,
    requested: Optional[List[str]] = None,
) -> PortalActivityResponse:
    codes = await enabled_customer_codes(user, session, requested)
    if not codes:
        return PortalActivityResponse(enabled=False, range=range_, message="The Activity page is not enabled for this customer")

    window = activity_window(range_, now)
    previous_since, since, until = window
    response = PortalActivityResponse(
        enabled=True,
        customer_codes=codes,
        range=range_,
        since=utc_iso(since),
        until=utc_iso(until),
        previous_since=utc_iso(previous_since),
    )

    # Customers and tag RBAC, built once for both alert sections. None: no alert visible.
    alert_filters = await alert_visibility_filters_for_user(user, session, codes)
    if alert_filters is not None:
        visibility = [*alert_filters, Alert.customer_code.in_(codes)]
        response.alerts = await _section(session, "alerts", lambda: alerts_section(session, visibility, window), ActivityAlertsSection)
        response.verdicts = await _section(
            session,
            "verdicts",
            lambda: verdicts_section(session, visibility, window),
            ActivityVerdictsSection,
        )
    response.cases = await _section(session, "cases", lambda: cases_section(session, codes, window), ActivityCasesSection)
    return response
