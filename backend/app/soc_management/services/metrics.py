"""Composing the dashboard: load facts once, derive every section from the same snapshot.

One request, one snapshot. The sections are not fetched separately because they must
agree — the Overview's breach count, the Workload tab's breach count and the attention
list are the same items evaluated at the same ``now`` — and because loading the facts
is the cost, while deriving a section from facts already in memory is cheap. The PDF
report renders the very same snapshot, so the PDF and the screen cannot disagree.

**Per-analyst figures are the admin's view** (#1187): an analyst sees every aggregate,
but only their own row in the Analysts table and in the per-assignee workload.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.incidents.models import Alert
from app.soc_management.clock import utc_now
from app.soc_management.domain import analytics
from app.soc_management.domain.periods import Bucket
from app.soc_management.domain.periods import Period
from app.soc_management.domain.periods import auto_bucket
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.sla import SlaState
from app.soc_management.models.sla import AlertSlaTracking
from app.soc_management.models.sla import CaseSlaTracking
from app.soc_management.schema.metrics import AnalystRowOut
from app.soc_management.schema.metrics import AttentionItemOut
from app.soc_management.schema.metrics import AttentionResponse
from app.soc_management.schema.metrics import CustomerRowOut
from app.soc_management.schema.metrics import DashboardResponse
from app.soc_management.schema.metrics import HeadlineOut
from app.soc_management.schema.metrics import ItemSlaResponse
from app.soc_management.schema.metrics import PeriodOut
from app.soc_management.schema.metrics import RuleRowOut
from app.soc_management.schema.metrics import SeverityRowOut
from app.soc_management.schema.metrics import SlaClockOut
from app.soc_management.schema.metrics import SourceOption
from app.soc_management.schema.metrics import SourcesResponse
from app.soc_management.schema.metrics import TrendPointOut
from app.soc_management.schema.metrics import Viewer
from app.soc_management.schema.metrics import WorkloadOut
from app.soc_management.schema.policy import PolicyMatrix
from app.soc_management.services import calendars as calendar_service
from app.soc_management.services import datasets
from app.soc_management.services import policy as policy_service
from app.soc_management.services.datasets import FactFilters
from app.soc_management.services.datasets import Visibility

#: The attention list on the dashboard is a teaser; the Workload tab pages the rest.
DASHBOARD_ATTENTION_LIMIT = 10
MAX_ATTENTION_LIMIT = 500


@dataclass(frozen=True)
class DashboardQuery:
    period: Period
    customer_codes: Optional[List[str]] = None
    filters: FactFilters = field(default_factory=FactFilters)
    bucket: Optional[Bucket] = None


@dataclass(frozen=True)
class Snapshot:
    """Every section, computed once at ``now`` for one viewer."""

    now: datetime
    period: Period
    previous: Period
    bucket: Bucket
    viewer: Viewer
    customer_codes: Optional[List[str]]
    tracking_since: Optional[datetime]
    headline: analytics.Headline
    previous_headline: analytics.Headline
    severities: List[analytics.SeverityRow]
    trends: List[analytics.TrendPoint]
    analysts: List[analytics.AnalystRow]
    rules: List[analytics.RuleRow]
    customers: List[analytics.CustomerRow]
    customer_names: Dict[str, str]
    workload: analytics.Workload
    attention: List[analytics.AttentionItem]
    policy: PolicyMatrix


def is_admin(user: User) -> bool:
    role = getattr(user.role_id, "value", user.role_id)
    return role == RoleEnum.admin.value


async def compute_snapshot(
    session: AsyncSession,
    query: DashboardQuery,
    *,
    viewer: Viewer,
    visibility: Visibility,
    attention_limit: int = DASHBOARD_ATTENTION_LIMIT,
) -> Snapshot:
    """The whole dashboard for an already-resolved viewer and visibility.

    Split from ``build_dashboard`` so a caller that is not a request — the customer PDF
    report, scoped to one customer by construction — can reuse every figure.
    """
    now = utc_now()
    period = query.period
    previous = period.previous()
    # One load covers both periods: the deltas compare against the same snapshot.
    loaded = Period(previous.start, period.end)
    bucket = query.bucket or auto_bucket(period)

    book = await calendar_service.load_book(session)
    alerts = await datasets.window_alerts(session, visibility, loaded, query.filters, book)
    cases = await datasets.window_cases(session, visibility, loaded, query.filters, book)
    open_alerts = await datasets.open_alerts(session, visibility, query.filters, book)
    open_cases = await datasets.open_cases(session, visibility, query.filters, book)
    soc_users = await datasets.soc_usernames(session)

    analyst_rows = analytics.analysts(alerts, cases, open_alerts, open_cases, period, now, soc_users)
    workload = analytics.workload(open_alerts, open_cases, now)
    if not viewer.sees_all_analysts:
        analyst_rows = [row for row in analyst_rows if row.username == viewer.username]
        workload = replace(workload, by_assignee=[load for load in workload.by_assignee if load.username == viewer.username])

    customer_rows = analytics.customers(alerts, cases, open_alerts, open_cases, period, now)
    single_customer = _single_customer(query.customer_codes, visibility)

    return Snapshot(
        now=now,
        period=period,
        previous=previous,
        bucket=bucket,
        viewer=viewer,
        customer_codes=visibility.case_codes,
        tracking_since=await datasets.tracking_since(session),
        headline=analytics.headline(alerts, cases, period, now, soc_users),
        previous_headline=analytics.headline(alerts, cases, previous, now, soc_users),
        severities=[
            row
            for entity, window, backlog in ((SlaEntity.ALERT, alerts, open_alerts), (SlaEntity.CASE, cases, open_cases))
            for row in analytics.severity_rows(entity, window, backlog, period, now)
        ],
        trends=analytics.trends(alerts, cases, period, bucket, now),
        analysts=analyst_rows,
        rules=analytics.rules(alerts, period, bucket, now),
        customers=customer_rows,
        customer_names=await datasets.customer_names(session, [row.customer_code for row in customer_rows]),
        workload=workload,
        attention=analytics.attention_items((*open_alerts, *open_cases), now, limit=attention_limit),
        policy=await policy_service.get_matrix(session, single_customer),
    )


async def snapshot_for_user(
    session: AsyncSession,
    user: User,
    query: DashboardQuery,
    attention_limit: int = DASHBOARD_ATTENTION_LIMIT,
) -> Snapshot:
    admin = is_admin(user)
    viewer = Viewer(username=user.username, is_admin=admin, sees_all_analysts=admin)
    visibility = await datasets.visibility_for(user, session, query.customer_codes)
    return await compute_snapshot(session, query, viewer=viewer, visibility=visibility, attention_limit=attention_limit)


def customer_visibility(customer_code: str) -> Visibility:
    """Exactly one customer, for callers that already authorised it (the customer report)."""
    return Visibility(alert_filters=[Alert.customer_code == customer_code], case_codes=[customer_code])


def to_response(snapshot: Snapshot) -> DashboardResponse:
    return DashboardResponse(
        generated_at=snapshot.now,
        period=PeriodOut(
            date_from=snapshot.period.start,
            date_to=snapshot.period.end,
            previous_from=snapshot.previous.start,
            previous_to=snapshot.previous.end,
            bucket=snapshot.bucket,
        ),
        viewer=snapshot.viewer,
        customer_codes=snapshot.customer_codes,
        tracking_since=snapshot.tracking_since,
        headline=HeadlineOut.model_validate(snapshot.headline),
        previous=HeadlineOut.model_validate(snapshot.previous_headline),
        severities=[SeverityRowOut.model_validate(row) for row in snapshot.severities],
        trends=[TrendPointOut.model_validate(point) for point in snapshot.trends],
        analysts=[AnalystRowOut.model_validate(row) for row in snapshot.analysts],
        rules=[RuleRowOut.model_validate(row) for row in snapshot.rules],
        customers=[
            CustomerRowOut.model_validate(row).model_copy(update={"customer_name": snapshot.customer_names.get(row.customer_code)})
            for row in snapshot.customers
        ],
        workload=WorkloadOut.model_validate(snapshot.workload),
        attention=[AttentionItemOut.model_validate(item) for item in snapshot.attention],
        policy=snapshot.policy,
    )


async def build_dashboard(session: AsyncSession, user: User, query: DashboardQuery) -> DashboardResponse:
    return to_response(await snapshot_for_user(session, user, query))


async def build_attention(
    session: AsyncSession,
    user: User,
    customer_codes: Optional[List[str]],
    filters: FactFilters,
    entity: Optional[SlaEntity],
    state: Optional[SlaState],
    limit: int,
) -> AttentionResponse:
    """Every open item that is breached or at risk, most urgent first."""
    now = utc_now()
    visibility = await datasets.visibility_for(user, session, customer_codes)
    book = await calendar_service.load_book(session)
    facts = []
    if entity in (None, SlaEntity.ALERT):
        facts.extend(await datasets.open_alerts(session, visibility, filters, book))
    if entity in (None, SlaEntity.CASE):
        facts.extend(await datasets.open_cases(session, visibility, filters, book))
    items = analytics.attention_items(facts, now, limit=len(facts))
    if state is not None:
        items = [item for item in items if item.state is state]
    return AttentionResponse(items=[AttentionItemOut.model_validate(item) for item in items[:limit]], total=len(items))


async def build_sources(session: AsyncSession, user: User, customer_codes: Optional[List[str]]) -> SourcesResponse:
    """The sources the caller's alerts come from, within the customers asked for."""
    visibility = await datasets.visibility_for(user, session, customer_codes)
    sources = await datasets.alert_sources(session, visibility)
    return SourcesResponse(sources=[SourceOption(source=source, alerts=alerts) for source, alerts in sources])


async def item_sla(session: AsyncSession, user: User, entity: SlaEntity, item_id: int) -> Optional[ItemSlaResponse]:
    """One item's SLA, or ``None`` when the caller cannot see it (the route answers 404)."""
    visibility = await datasets.visibility_for(user, session, None)
    load = datasets.alert_fact if entity is SlaEntity.ALERT else datasets.case_fact
    book = await calendar_service.load_book(session)
    fact = await load(session, visibility, item_id, book)
    if fact is None:
        return None
    tracking = await session.get(AlertSlaTracking if entity is SlaEntity.ALERT else CaseSlaTracking, item_id)
    credit = (tracking.pause_credit_seconds or 0) if tracking else 0
    now = utc_now()
    return ItemSlaResponse(
        entity=entity,
        id=item_id,
        severity=fact.severity,
        opened_at=fact.opened_at,
        tracked=fact.tracked,
        ack=SlaClockOut(
            due_at=fact.ack_due_at,
            achieved_at=fact.ack_achieved_at,
            state=fact.ack_state(now),
            by=fact.first_ack_by,
            action=tracking.first_ack_action if tracking else None,
            target_minutes=_target_minutes(fact, fact.ack_due_at, credit),
        ),
        resolve=SlaClockOut(
            due_at=fact.resolve_due_at,
            achieved_at=fact.resolved_at,
            state=fact.resolve_state(now),
            by=fact.resolved_by,
            target_minutes=_target_minutes(fact, fact.resolve_due_at, credit),
        ),
        first_assigned_at=tracking.first_assigned_at if tracking else None,
        reopen_count=fact.reopen_count,
        business_hours=fact.clock.business_hours,
        calendar_timezone=book.for_customer(fact.customer_code).timezone if fact.clock.business_hours else None,
        paused_at=fact.paused_at,
        paused_seconds=fact.paused_seconds + (round((now - fact.paused_at).total_seconds()) if fact.paused_at else 0),
        generated_at=now,
    )


def _target_minutes(fact: analytics.ItemFact, due_at: Optional[datetime], credit_seconds: int) -> Optional[int]:
    """The promised target, on the clock's own basis: a due time pushed back by waiting on
    the customer still promised the same number of minutes."""
    if due_at is None:
        return None
    return round((fact.clock.elapsed(fact.opened_at, due_at) - credit_seconds) / 60)


def _single_customer(requested: Optional[List[str]], visibility: Visibility) -> Optional[str]:
    """The one customer the figures cover, if there is exactly one — its policy is then shown."""
    codes = visibility.case_codes if visibility.case_codes is not None else requested
    return codes[0] if codes and len(codes) == 1 else None
