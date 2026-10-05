"""The Customer Portal's SLA page (#1187): the SOC's promise to a customer, and how it was kept.

Two rules shape everything here:

- **Opt-in per customer.** ``customer_portal_sla_settings`` is the operator's switch; a
  missing row reads as disabled. Every read narrows the caller's customers to those
  whose switch is on *before* a single figure is computed, so a disabled customer
  contributes nothing — not even to an aggregate across several customers.
- **The same numbers as the SOC sees, never who produced them.** The figures come from
  ``soc_management.services.metrics.compute_snapshot`` — the snapshot the analyst
  dashboard and the PDF report render — and are projected into
  ``schema/sla.py``, which has no field that could carry an analyst's name.

Visibility is the portal's usual: customers through ``customer_access_handler``, alerts
through ``alert_visibility_filters_for_user`` (tag RBAC included), so the SLA page can
never count an alert the alerts list would not show.
"""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.sla import PortalSlaClock
from app.customer_portal.schema.sla import PortalSlaEntity
from app.customer_portal.schema.sla import PortalSlaOpenNow
from app.customer_portal.schema.sla import PortalSlaOverviewResponse
from app.customer_portal.schema.sla import PortalSlaTarget
from app.customer_portal.schema.sla import PortalSlaTrendPoint
from app.db.universal_models import CustomerPortalSlaSettings
from app.incidents.models import Alert
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.middleware.customer_access import customer_access_handler
from app.soc_management.domain import analytics
from app.soc_management.domain.periods import Period
from app.soc_management.domain.sla import Compliance
from app.soc_management.schema.metrics import Viewer
from app.soc_management.services import metrics as metrics_service
from app.soc_management.services.datasets import Visibility
from app.time_utils import now_utc

# ── the switch ───────────────────────────────────────────────────────────────


async def get_sla_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalSlaSettings]:
    result = await session.execute(select(CustomerPortalSlaSettings).where(CustomerPortalSlaSettings.customer_code == customer_code))
    return result.scalars().first()


async def upsert_sla_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalSlaSettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_sla_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalSlaSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def enabled_customer_codes(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> List[str]:
    """The customers ``user`` may see *and* whose SLA page is on, optionally narrowed to ``requested``."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalSlaSettings.customer_code).where(CustomerPortalSlaSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalSlaSettings.customer_code.in_(accessible))
    if requested:
        query = query.where(CustomerPortalSlaSettings.customer_code.in_(requested))
    return sorted((await session.execute(query)).scalars().all())


async def availability(user: User, session: AsyncSession, customer_code: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Whether the SLA page should render: for one customer the caller may see, else for any."""
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        settings = await get_sla_settings(customer_code, session)
        return customer_code, bool(settings and settings.enabled)
    return None, bool(await enabled_customer_codes(user, session))


# ── the page ─────────────────────────────────────────────────────────────────


async def sla_overview(
    user: User,
    session: AsyncSession,
    period: Period,
    requested: Optional[List[str]] = None,
) -> PortalSlaOverviewResponse:
    codes = await enabled_customer_codes(user, session, requested)
    if not codes:
        return PortalSlaOverviewResponse(enabled=False, message="The SLA page is not enabled for this customer")
    alert_filters = await alert_visibility_filters_for_user(user, session, codes)
    visibility = Visibility(
        alert_filters=None if alert_filters is None else [*alert_filters, Alert.customer_code.in_(codes)],
        case_codes=codes,
    )
    snapshot = await metrics_service.compute_snapshot(
        session,
        metrics_service.DashboardQuery(period=period, customer_codes=codes),
        viewer=Viewer(username=user.username, is_admin=False, sees_all_analysts=False),
        visibility=visibility,
        attention_limit=0,
    )
    return project(snapshot, codes)


def project(snapshot: metrics_service.Snapshot, codes: List[str]) -> PortalSlaOverviewResponse:
    """The portal's view of a snapshot. Pure, so what crosses to the customer is testable."""
    load = snapshot.workload
    return PortalSlaOverviewResponse(
        enabled=True,
        customer_codes=codes,
        date_from=snapshot.period.start,
        date_to=snapshot.period.end,
        bucket=snapshot.bucket.value,
        tracking_since=snapshot.tracking_since,
        alerts=_entity(snapshot.headline.alerts),
        cases=_entity(snapshot.headline.cases),
        previous_alerts=_entity(snapshot.previous_headline.alerts),
        previous_cases=_entity(snapshot.previous_headline.cases),
        targets=_targets(snapshot),
        trend=[
            PortalSlaTrendPoint(
                start=point.start,
                opened=point.alerts_opened + point.cases_opened,
                resolved=point.alerts_resolved + point.cases_resolved,
                rate=point.sla_rate,
            )
            for point in snapshot.trends
        ],
        open_now=PortalSlaOpenNow(
            alerts=load.open_alerts,
            cases=load.open_cases,
            breached=load.breached,
            at_risk=load.at_risk,
            waiting_on_you=load.waiting_on_customer,
        ),
        message="SLA figures retrieved successfully",
    )


def _clock(compliance: Compliance) -> PortalSlaClock:
    return PortalSlaClock(met=compliance.met, breached=compliance.breached, rate=compliance.rate)


def _entity(headline: analytics.EntityHeadline) -> PortalSlaEntity:
    return PortalSlaEntity(
        opened=headline.opened,
        resolved=headline.resolved,
        acknowledge=_clock(headline.sla.ack),
        resolve=_clock(headline.sla.resolve),
        time_to_acknowledge=headline.tta.median,
        time_to_resolve=headline.ttr.median,
    )


def _targets(snapshot: metrics_service.Snapshot) -> List[PortalSlaTarget]:
    """Each severity's promise next to how it was kept. Severities with no promise at all are left out."""
    rows: Dict[Tuple[str, str], analytics.SeverityRow] = {(row.entity.value, row.severity): row for row in snapshot.severities}
    targets = []
    for cell in snapshot.policy.cells:
        if cell.ack_minutes is None and cell.resolve_minutes is None:
            continue
        row = rows.get((cell.entity.value, cell.severity))
        targets.append(
            PortalSlaTarget(
                entity=cell.entity.value,
                severity=cell.severity,
                acknowledge_minutes=cell.ack_minutes,
                resolve_minutes=cell.resolve_minutes,
                business_hours=cell.business_hours,
                opened=row.opened if row else 0,
                acknowledge_rate=row.sla.ack.rate if row else None,
                resolve_rate=row.sla.resolve.rate if row else None,
                time_to_resolve=row.ttr.median if row else None,
            ),
        )
    return targets
