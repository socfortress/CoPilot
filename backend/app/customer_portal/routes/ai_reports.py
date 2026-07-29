from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.ai_reports import PortalAiAlertAnalysisResponse
from app.customer_portal.schema.ai_reports import PortalAiInsightsResponse
from app.customer_portal.services.ai_reports import get_portal_ai_insights
from app.customer_portal.services.ai_reports import get_portal_alert_analysis
from app.db.db_session import get_db

customer_portal_ai_reports_router = APIRouter()

# Read-only AI Analyst surface for end customers. GET only, by design: review
# submission, palace lessons, replay and the Talon chat remain analyst-only and
# are not proxied here.


@customer_portal_ai_reports_router.get(
    "/ai_reports/insights",
    response_model=PortalAiInsightsResponse,
    description="High-level AI report coverage for the portal overview",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_ai_insights(
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of customer codes to scope the insights to"),
    limit: int = Query(5, ge=1, le=25, description="How many recent reports to return"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalAiInsightsResponse:
    logger.info(f"Fetching AI analyst insights for user {current_user.username}")

    total, severity_counts, recent = await get_portal_ai_insights(
        current_user,
        db,
        customer_codes=customer_codes,
        limit=limit,
    )

    return PortalAiInsightsResponse(
        total_reports=total,
        severity_counts=severity_counts,
        recent=recent,
        success=True,
        message=f"{total} alerts with an AI report found",
    )


@customer_portal_ai_reports_router.get(
    "/ai_reports/alert/{alert_id}",
    response_model=PortalAiAlertAnalysisResponse,
    description="Read-only AI analyst findings for a single alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_alert_ai_report(
    alert_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalAiAlertAnalysisResponse:
    logger.info(f"Fetching AI analyst report for alert {alert_id} for user {current_user.username}")

    investigation, report, iocs = await get_portal_alert_analysis(alert_id, current_user, db)

    if investigation is None:
        return PortalAiAlertAnalysisResponse(
            alert_id=alert_id,
            has_analysis=False,
            success=True,
            message="No AI analysis has been performed for this alert",
        )

    return PortalAiAlertAnalysisResponse(
        alert_id=alert_id,
        has_analysis=True,
        investigation=investigation,
        report=report,
        iocs=iocs,
        success=True,
        message="AI analysis retrieved successfully",
    )
