"""Read-only AI Analyst projections for the Customer Portal.

The AI Analyst routes under ``/ai_analyst`` are admin/analyst-scoped and carry
no per-request tenant check — they trust the caller. Rather than widening those
scopes to ``customer_user`` (which would expose every tenant's reports), this
module follows the auth-scope sidestep pattern documented in CLAUDE.md: it calls
the ai_analyst *service* layer directly and applies the portal's own customer +
tag visibility rules on top.

Everything the portal consumes here is read-only. Review submission, palace
lessons, replay and the Talon chat stay analyst-only by construction. The one
write path is the operator-facing per-customer switch
(``upsert_ai_report_settings``), which admins call from the CoPilot frontend —
not portal users.
"""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_analyst.services.ai_analyst import get_alert_analysis
from app.auth.models.users import User
from app.customer_portal.schema.ai_reports import PortalAiInsightAlert
from app.customer_portal.schema.ai_reports import PortalAiInvestigation
from app.customer_portal.schema.ai_reports import PortalAiIoc
from app.customer_portal.schema.ai_reports import PortalAiReport
from app.db.universal_models import AiAnalystReport
from app.db.universal_models import CustomerPortalAiReportSettings
from app.incidents.middleware.tag_access import tag_access_handler
from app.incidents.models import Alert
from app.incidents.models import AlertToTag
from app.middleware.customer_access import customer_access_handler

# Severity bucket used when a report was persisted without an assessment.
UNKNOWN_SEVERITY = "Unknown"


# --- Per-customer AI report switch ---
#
# Opt-in: a customer with no row is disabled. Every portal-facing read below
# goes through one of these, so flipping the switch off hides both surfaces
# (overview insights card and alert-detail AI Report tab) at once.


def _enabled_customer_codes_subquery():
    """Customer codes whose portal users may read AI analyst findings."""
    return select(CustomerPortalAiReportSettings.customer_code).where(CustomerPortalAiReportSettings.enabled.is_(True))


async def get_ai_report_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalAiReportSettings]:
    result = await session.execute(
        select(CustomerPortalAiReportSettings).where(CustomerPortalAiReportSettings.customer_code == customer_code),
    )
    return result.scalars().first()


async def is_ai_reports_enabled(customer_code: str, session: AsyncSession) -> bool:
    settings = await get_ai_report_settings(customer_code, session)
    return bool(settings and settings.enabled)


async def upsert_ai_report_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalAiReportSettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_ai_report_settings(customer_code, session)

    if settings is None:
        settings = CustomerPortalAiReportSettings(customer_code=customer_code)
        session.add(settings)

    settings.enabled = enabled
    settings.updated_at = datetime.utcnow()
    settings.updated_by = user_id

    return settings


async def _alert_visibility_filters(
    user: User,
    session: AsyncSession,
    customer_codes: Optional[List[str]] = None,
) -> Optional[List[Any]]:
    """Build the WHERE clauses that restrict ``Alert`` rows to what ``user`` may see.

    Mirrors the customer + tag filtering the ``*_for_user`` alert helpers apply, so
    an AI report can never surface for an alert the user cannot open. Returns
    ``None`` when the user can see nothing at all (caller should short-circuit).
    """
    filters: List[Any] = []

    accessible_customers = await customer_access_handler.resolve_effective_customers(user, customer_codes, session)
    if "*" not in accessible_customers:
        if not accessible_customers:
            return None
        filters.append(Alert.customer_code.in_(accessible_customers))

    tag_filters = await tag_access_handler.build_alert_query_filters(user, session)
    accessible_tags = tag_filters["accessible_tags"]

    if "*" not in accessible_tags:
        tag_conditions = []
        if accessible_tags:
            tag_conditions.append(
                exists(
                    select(AlertToTag.alert_id).where(
                        and_(
                            AlertToTag.alert_id == Alert.id,
                            AlertToTag.tag_id.in_(accessible_tags),
                        ),
                    ),
                ),
            )
        if tag_filters["include_untagged"]:
            tag_conditions.append(~exists(select(AlertToTag.alert_id).where(AlertToTag.alert_id == Alert.id)))

        if not tag_conditions:
            return None
        filters.append(or_(*tag_conditions))

    # Customers whose AI report surface is switched off contribute nothing, even
    # when the user is otherwise entitled to their alerts.
    filters.append(Alert.customer_code.in_(_enabled_customer_codes_subquery()))

    return filters


async def ensure_alert_visible(alert_id: int, user: User, session: AsyncSession) -> Alert:
    """Resolve an alert the user is entitled to see, or raise 404/403.

    Deliberately does not go through ``get_alert_by_id``: that eager-loads
    comments, assets, cases and IOCs which this surface never reads.
    """
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    if not await customer_access_handler.check_customer_access(user, alert.customer_code, session):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id} - insufficient customer permissions")

    if not await tag_access_handler.can_user_access_alert(user, alert_id, session):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id} - insufficient tag permissions")

    return alert


async def is_ai_reports_enabled_for_user(
    user: User,
    session: AsyncSession,
    customer_code: Optional[str] = None,
) -> Tuple[Optional[str], bool]:
    """Resolve the switch for the customer the portal is about to render.

    With an explicit ``customer_code`` the caller must be entitled to it. Without
    one, the answer is "enabled for any customer I can see" — which is what a
    portal user scoped to a single customer actually asks.
    """
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        return customer_code, await is_ai_reports_enabled(customer_code, session)

    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(func.count()).select_from(CustomerPortalAiReportSettings).where(CustomerPortalAiReportSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return None, False
        query = query.where(CustomerPortalAiReportSettings.customer_code.in_(accessible))

    return None, bool((await session.execute(query)).scalar_one())


async def get_portal_alert_analysis(
    alert_id: int,
    user: User,
    session: AsyncSession,
) -> Tuple[bool, Optional[PortalAiInvestigation], Optional[PortalAiReport], List[PortalAiIoc]]:
    """Latest investigation + report + IOCs for an alert, projected for the portal.

    The leading flag is the customer's AI report switch. When it is off nothing
    else is read — an operator reading the response can tell "switched off" apart
    from "no investigation ran", which returning a bare empty payload would hide.
    """
    alert = await ensure_alert_visible(alert_id, user, session)

    if not await is_ai_reports_enabled(alert.customer_code, session):
        return False, None, None, []

    job, report, iocs = await get_alert_analysis(alert_id, session)
    if not job:
        return True, None, None, []

    investigation = PortalAiInvestigation(
        status=job.status,
        triggered_by=job.triggered_by,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )

    portal_report = (
        PortalAiReport(
            id=report.id,
            alert_id=report.alert_id,
            customer_code=report.customer_code,
            severity_assessment=report.severity_assessment,
            summary=report.summary,
            report_markdown=report.report_markdown,
            recommended_actions=report.recommended_actions,
            created_at=report.created_at,
        )
        if report
        else None
    )

    portal_iocs = [
        PortalAiIoc(
            id=ioc.id,
            ioc_value=ioc.ioc_value,
            ioc_type=ioc.ioc_type,
            vt_verdict=ioc.vt_verdict,
            vt_score=ioc.vt_score,
            details=ioc.details,
            created_at=ioc.created_at,
        )
        for ioc in iocs
    ]

    return True, investigation, portal_report, portal_iocs


def _latest_report_ids_subquery():
    """One report per alert: the highest id, which is also the most recent insert.

    ``ai_analyst_report.id`` is a plain autoincrement PK, so max(id) and
    max(created_at) agree — and max(id) never ties, which max(created_at) can
    when a replay writes two reports inside the same second.
    """
    return select(func.max(AiAnalystReport.id)).group_by(AiAnalystReport.alert_id)


async def get_portal_ai_insights(
    user: User,
    session: AsyncSession,
    customer_codes: Optional[List[str]] = None,
    limit: int = 5,
) -> Tuple[int, Dict[str, int], List[PortalAiInsightAlert]]:
    """Aggregate AI-report coverage for the portal Overview card."""
    filters = await _alert_visibility_filters(user, session, customer_codes)
    if filters is None:
        return 0, {}, []

    latest_report_ids = _latest_report_ids_subquery()

    counts_query = (
        select(AiAnalystReport.severity_assessment, func.count(AiAnalystReport.id))
        .join(Alert, Alert.id == AiAnalystReport.alert_id)
        .where(AiAnalystReport.id.in_(latest_report_ids), *filters)
        .group_by(AiAnalystReport.severity_assessment)
    )

    severity_counts: Dict[str, int] = {}
    total = 0
    for severity, count in (await session.execute(counts_query)).all():
        severity_counts[severity or UNKNOWN_SEVERITY] = count
        total += count

    recent_query = (
        select(Alert, AiAnalystReport)
        .join(AiAnalystReport, AiAnalystReport.alert_id == Alert.id)
        .where(AiAnalystReport.id.in_(latest_report_ids), *filters)
        .order_by(AiAnalystReport.created_at.desc())
        .limit(limit)
    )

    recent = [
        PortalAiInsightAlert(
            alert_id=alert.id,
            alert_name=alert.alert_name,
            customer_code=alert.customer_code,
            severity_assessment=report.severity_assessment,
            summary=report.summary,
            report_created_at=report.created_at,
        )
        for alert, report in (await session.execute(recent_query)).all()
    ]

    return total, severity_counts, recent
