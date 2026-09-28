"""Everything the Customer Portal Overview renders, in one request.

The Overview used to make four calls: the full alert and case *lists* (each eager-
loading comments, assets, tags, IoCs and linked cases to show six rows), every agent
the user can see (to count them), and the AI insights. This builds the same page from
light projections instead:

* alert visibility (customer + tag ACL) is built **once** and shared by the alert
  counts, the recent alerts and the AI findings;
* each list reads only the columns a row shows, plus one query for the assets of the
  rows actually returned;
* agents are counted in SQL, never loaded.

Sections fail independently, as the four calls did: an error is logged, reported on
that section only, and the transaction is rolled back so the next section still runs.
"""

from collections import defaultdict
from typing import Awaitable
from typing import Callable
from typing import List
from typing import Optional
from typing import TypeVar

from loguru import logger
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.overview import CustomerPortalOverviewResponse
from app.customer_portal.schema.overview import OverviewAgentsSection
from app.customer_portal.schema.overview import OverviewAiSection
from app.customer_portal.schema.overview import OverviewAlert
from app.customer_portal.schema.overview import OverviewAlertsSection
from app.customer_portal.schema.overview import OverviewCase
from app.customer_portal.schema.overview import OverviewCasesSection
from app.customer_portal.schema.overview import OverviewStatusCounts
from app.customer_portal.services.ai_reports import ai_insights_within
from app.customer_portal.services.ai_reports import with_ai_report_switch
from app.db.universal_models import Agents
from app.incidents.models import Alert
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.services.db_operations import alert_status_counts
from app.incidents.services.db_operations import alert_visibility_filters_for_user
from app.incidents.services.db_operations import case_status_counts_for_user
from app.middleware.customer_access import customer_access_handler

Section = TypeVar("Section")


async def _recent_alerts(session: AsyncSession, visibility: list, limit: int) -> List[OverviewAlert]:
    rows = (
        await session.execute(
            select(
                Alert.id,
                Alert.alert_name,
                Alert.alert_description,
                Alert.status,
                Alert.alert_creation_time,
                Alert.source,
                Alert.customer_code,
            )
            .where(*visibility)
            .order_by(Alert.id.desc())
            .limit(limit),
        )
    ).all()
    if not rows:
        return []

    asset_names = defaultdict(list)
    assets = await session.execute(
        select(Asset.alert_linked, Asset.asset_name).where(Asset.alert_linked.in_([row.id for row in rows])).order_by(Asset.id),
    )
    for alert_id, asset_name in assets.all():
        asset_names[alert_id].append(asset_name)

    return [OverviewAlert(**row._mapping, asset_names=asset_names[row.id]) for row in rows]


async def _alerts_section(session: AsyncSession, visibility: Optional[list], limit: int) -> OverviewAlertsSection:
    if visibility is None:
        return OverviewAlertsSection()
    counts = await alert_status_counts(session, visibility)
    return OverviewAlertsSection(
        counts=OverviewStatusCounts(**counts._asdict()),
        recent=await _recent_alerts(session, visibility, limit),
    )


async def _cases_section(user: User, session: AsyncSession, customer_codes: Optional[List[str]], limit: int) -> OverviewCasesSection:
    counts = await case_status_counts_for_user(user, session, customer_codes)

    customers = await customer_access_handler.resolve_effective_customers(user, customer_codes, session)
    if "*" not in customers and not customers:
        return OverviewCasesSection()

    alert_count = select(func.count()).where(CaseAlertLink.case_id == Case.id).correlate(Case).scalar_subquery()
    query = select(
        Case.id,
        Case.case_name,
        Case.case_description,
        Case.case_status,
        Case.case_creation_time,
        Case.assigned_to,
        Case.customer_code,
        alert_count.label("alert_count"),
    )
    if "*" not in customers:
        query = query.where(Case.customer_code.in_(customers))

    rows = (await session.execute(query.order_by(Case.id.desc()).limit(limit))).all()
    return OverviewCasesSection(
        counts=OverviewStatusCounts(**counts._asdict()),
        recent=[OverviewCase(**row._mapping) for row in rows],
    )


async def _agents_section(user: User, session: AsyncSession, customer_codes: Optional[List[str]]) -> OverviewAgentsSection:
    # Agents are not tag-scoped: customer scoping is the whole rule.
    customers = await customer_access_handler.resolve_effective_customers(user, customer_codes, session)
    if "*" not in customers and not customers:
        return OverviewAgentsSection()

    query = select(
        func.count(Agents.id),
        func.coalesce(func.sum(case((Agents.wazuh_agent_status == "active", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Agents.critical_asset.is_(True), 1), else_=0)), 0),
    )
    if "*" not in customers:
        query = query.where(Agents.customer_code.in_(customers))

    total, online, critical = (await session.execute(query)).one()
    return OverviewAgentsSection(total=total, online=online, offline=total - online, critical=critical)


async def _ai_section(session: AsyncSession, visibility: Optional[list], limit: int) -> OverviewAiSection:
    if visibility is None:
        return OverviewAiSection()
    total, severity_counts, recent = await ai_insights_within(session, with_ai_report_switch(visibility), limit)
    return OverviewAiSection(total_reports=total, severity_counts=severity_counts, recent=recent)


async def _isolated(
    session: AsyncSession,
    name: str,
    load: Callable[[], Awaitable[Section]],
    on_error: Callable[[str], Section],
) -> Section:
    """Run one section; on failure log it, roll back so later sections still run, and report it."""
    try:
        return await load()
    except Exception as e:
        logger.error(f"Customer portal overview: failed to load {name}: {e}")
        await session.rollback()
        return on_error(f"Failed to load {name}")


async def get_portal_overview(
    user: User,
    session: AsyncSession,
    customer_codes: Optional[List[str]] = None,
    recent_limit: int = 6,
    ai_limit: int = 3,
) -> CustomerPortalOverviewResponse:
    # Built once and shared by the alert counts, recent alerts and AI findings. If it
    # fails, those sections report the error; cases and agents do not depend on it.
    visibility_error: Optional[str] = None
    try:
        visibility = await alert_visibility_filters_for_user(user, session, customer_codes)
    except Exception as e:
        logger.error(f"Customer portal overview: failed to resolve alert visibility: {e}")
        await session.rollback()
        visibility, visibility_error = None, "Failed to load alerts"

    alerts = (
        OverviewAlertsSection(error=visibility_error)
        if visibility_error
        else await _isolated(
            session,
            "alerts",
            lambda: _alerts_section(session, visibility, recent_limit),
            lambda error: OverviewAlertsSection(error=error),
        )
    )
    cases = await _isolated(
        session,
        "cases",
        lambda: _cases_section(user, session, customer_codes, recent_limit),
        lambda error: OverviewCasesSection(error=error),
    )
    agents = await _isolated(
        session,
        "agents",
        lambda: _agents_section(user, session, customer_codes),
        lambda error: OverviewAgentsSection(error=error),
    )
    ai = (
        OverviewAiSection(error=visibility_error)
        if visibility_error
        else await _isolated(
            session,
            "AI findings",
            lambda: _ai_section(session, visibility, ai_limit),
            lambda error: OverviewAiSection(error=error),
        )
    )

    return CustomerPortalOverviewResponse(
        alerts=alerts,
        cases=cases,
        agents=agents,
        ai=ai,
        success=True,
        message="Overview retrieved successfully",
    )
