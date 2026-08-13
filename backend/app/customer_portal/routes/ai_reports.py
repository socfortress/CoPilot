from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from fastapi import status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.ai_reports import PortalAiAlertAnalysisResponse
from app.customer_portal.schema.ai_reports import PortalAiInsightsResponse
from app.customer_portal.schema.ai_reports import PortalAiReportAvailabilityResponse
from app.customer_portal.schema.ai_reports import PortalAiReportSettings
from app.customer_portal.schema.ai_reports import PortalAiReportSettingsResponse
from app.customer_portal.schema.ai_reports import UpdatePortalAiReportSettingsRequest
from app.customer_portal.services.ai_reports import get_ai_report_settings
from app.customer_portal.services.ai_reports import get_portal_ai_insights
from app.customer_portal.services.ai_reports import get_portal_alert_analysis
from app.customer_portal.services.ai_reports import is_ai_reports_enabled_for_user
from app.customer_portal.services.ai_reports import upsert_ai_report_settings
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.middleware.customer_access import verify_customer_code_access

customer_portal_ai_reports_router = APIRouter()

# Two audiences share this router:
#
# * End customers (portal) read their own findings — GET only, by design.
#   Review submission, palace lessons, replay and the Talon chat remain
#   analyst-only and are not proxied here.
# * CoPilot operators manage the per-customer switch under
#   ``/ai_reports/settings/{customer_code}`` (admin to write).
#
# NOTE: the static ``/ai_reports/insights`` and ``/ai_reports/settings/...``
# routes must stay declared above nothing wildcard-shaped in this router; the
# only path parameter here is ``/ai_reports/alert/{alert_id}``, which cannot
# collide. Keep it that way when appending routes (see CLAUDE.md route ordering).


async def _ensure_customer_exists(session: AsyncSession, customer_code: str) -> None:
    result = await session.execute(select(Customers).where(Customers.customer_code == customer_code))
    if result.scalars().first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_code} not found")


def _settings_schema(customer_code: str, settings) -> PortalAiReportSettings:
    """Project a row — or its absence, which means disabled — for the operator UI."""
    if settings is None:
        return PortalAiReportSettings(customer_code=customer_code, enabled=False)

    return PortalAiReportSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


# --- Operator-facing switch ---


@customer_portal_ai_reports_router.get(
    "/ai_reports/settings/{customer_code}",
    response_model=PortalAiReportSettingsResponse,
    description="Get whether a customer's portal users can see AI analyst findings",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_ai_report_settings(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> PortalAiReportSettingsResponse:
    settings = await get_ai_report_settings(customer_code, session)

    return PortalAiReportSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer AI report settings retrieved successfully",
    )


@customer_portal_ai_reports_router.put(
    "/ai_reports/settings/{customer_code}",
    response_model=PortalAiReportSettingsResponse,
    description="Enable or disable the Customer Portal AI report surfaces for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_ai_report_settings(
    customer_code: str,
    request: UpdatePortalAiReportSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalAiReportSettingsResponse:
    await _ensure_customer_exists(session, customer_code)

    try:
        settings = await upsert_ai_report_settings(
            customer_code,
            request.enabled,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)
    except Exception as e:
        logger.error(f"Failed to save AI report settings for customer {customer_code}: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save customer AI report settings: {str(e)}",
        )

    logger.info(f"Customer portal AI reports {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")

    return PortalAiReportSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer AI report settings saved successfully",
    )


# --- Portal-facing reads ---


@customer_portal_ai_reports_router.get(
    "/ai_reports/availability",
    response_model=PortalAiReportAvailabilityResponse,
    description="Whether the AI report surfaces should render for the caller (or for a specific customer)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_ai_report_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalAiReportAvailabilityResponse:
    resolved_code, enabled = await is_ai_reports_enabled_for_user(current_user, db, customer_code=customer_code)

    return PortalAiReportAvailabilityResponse(
        customer_code=resolved_code,
        enabled=enabled,
        success=True,
        message="AI reports are enabled" if enabled else "AI reports are not enabled",
    )


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

    enabled, investigation, report, iocs = await get_portal_alert_analysis(alert_id, current_user, db)

    if not enabled:
        return PortalAiAlertAnalysisResponse(
            alert_id=alert_id,
            enabled=False,
            has_analysis=False,
            success=True,
            message="AI analyst findings are not enabled for this customer",
        )

    if investigation is None:
        return PortalAiAlertAnalysisResponse(
            alert_id=alert_id,
            enabled=True,
            has_analysis=False,
            success=True,
            message="No AI analysis has been performed for this alert",
        )

    return PortalAiAlertAnalysisResponse(
        alert_id=alert_id,
        enabled=True,
        has_analysis=True,
        investigation=investigation,
        report=report,
        iocs=iocs,
        success=True,
        message="AI analysis retrieved successfully",
    )
