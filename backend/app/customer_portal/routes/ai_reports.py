from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.ai_reports import PortalAiAlertAnalysisResponse
from app.customer_portal.schema.ai_reports import PortalAiAnalysisRequestResponse
from app.customer_portal.schema.ai_reports import PortalAiInsightsResponse
from app.customer_portal.schema.ai_reports import PortalAiReportAvailabilityResponse
from app.customer_portal.schema.ai_reports import PortalAiReportSettings
from app.customer_portal.schema.ai_reports import PortalAiReportSettingsResponse
from app.customer_portal.schema.ai_reports import UpdatePortalAiReportSettingsRequest
from app.customer_portal.services.ai_reports import count_recent_requests
from app.customer_portal.services.ai_reports import get_ai_report_settings
from app.customer_portal.services.ai_reports import get_portal_ai_insights
from app.customer_portal.services.ai_reports import get_portal_alert_analysis
from app.customer_portal.services.ai_reports import is_ai_reports_enabled_for_user
from app.customer_portal.services.ai_reports import upsert_ai_report_settings
from app.customer_portal.services.ai_requests import request_alert_analysis
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_portal_ai_reports_router = APIRouter()

# Two audiences share this router:
#
# * End customers (portal) read their own findings — GET — and, where the
#   customer allows it, ask for an analysis of one of their alerts: the single
#   portal write, ``POST /ai_reports/alert/{alert_id}/investigate`` (#1215).
#   Review submission, palace lessons, replay and the Talon chat remain
#   analyst-only and are not proxied here.
# * CoPilot operators manage the per-customer settings under
#   ``/ai_reports/settings/{customer_code}`` (admin to write).
#
# NOTE: the static ``/ai_reports/insights`` and ``/ai_reports/settings/...``
# routes must stay declared above nothing wildcard-shaped in this router; the
# only path parameter here is ``/ai_reports/alert/{alert_id}``, which cannot
# collide. Keep it that way when appending routes (see CLAUDE.md route ordering).


def _settings_schema(customer_code: str, settings, requests_last_24h: int = 0) -> PortalAiReportSettings:
    """Project a row — or its absence, which means disabled — for the operator UI."""
    if settings is None:
        return PortalAiReportSettings(customer_code=customer_code, enabled=False)

    return PortalAiReportSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        allow_customer_requests=settings.allow_customer_requests,
        daily_request_limit=settings.daily_request_limit,
        requests_last_24h=requests_last_24h,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


def _settings_values(settings) -> dict:
    if settings is None:
        return {"enabled": False, "allow_customer_requests": False, "daily_request_limit": None}
    return {
        "enabled": settings.enabled,
        "allow_customer_requests": settings.allow_customer_requests,
        "daily_request_limit": settings.daily_request_limit,
    }


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
    used = await count_recent_requests(customer_code, session) if settings is not None else 0

    return PortalAiReportSettingsResponse(
        settings=_settings_schema(customer_code, settings, used),
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
    await ensure_customer_exists(session, customer_code)

    # Only the request settings the client sent are written (see the request schema).
    optional = {}
    if request.allow_customer_requests is not None:
        optional["allow_customer_requests"] = request.allow_customer_requests
    if "daily_request_limit" in request.model_fields_set:
        optional["daily_request_limit"] = request.daily_request_limit

    async with internal_errors("save customer AI report settings", session):
        before = _settings_values(await get_ai_report_settings(customer_code, session))
        settings = await upsert_ai_report_settings(
            customer_code,
            request.enabled,
            session,
            user_id=getattr(current_user, "id", None),
            **optional,
        )
        await session.commit()
        await session.refresh(settings)
        used = await count_recent_requests(customer_code, session)

    after = _settings_values(settings)
    logger.info(f"Customer portal AI report settings for {customer_code}: {after}")
    if after != before:
        await record_audit_event(
            action=AuditAction.AI_REPORT_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_ai_report_settings",
            entity_id=customer_code,
            old_value=before,
            new_value=after,
        )

    return PortalAiReportSettingsResponse(
        settings=_settings_schema(customer_code, settings, used),
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

    analysis = await get_portal_alert_analysis(alert_id, current_user, db)

    if not analysis.enabled:
        return PortalAiAlertAnalysisResponse(
            alert_id=alert_id,
            enabled=False,
            has_analysis=False,
            success=True,
            message="AI analyst findings are not enabled for this customer",
        )

    if analysis.investigation is None:
        return PortalAiAlertAnalysisResponse(
            alert_id=alert_id,
            enabled=True,
            can_request=analysis.can_request,
            has_analysis=False,
            success=True,
            message="No AI analysis has been performed for this alert",
        )

    return PortalAiAlertAnalysisResponse(
        alert_id=alert_id,
        enabled=True,
        can_request=analysis.can_request,
        has_analysis=True,
        investigation=analysis.investigation,
        report=analysis.report,
        iocs=analysis.iocs,
        success=True,
        message="AI analysis retrieved successfully",
    )


# --- Portal-facing request (#1215) ---


@customer_portal_ai_reports_router.post(
    "/ai_reports/alert/{alert_id}/investigate",
    response_model=PortalAiAnalysisRequestResponse,
    description="Ask the AI analyst to analyse an alert, where the alert's customer allows portal requests",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def request_alert_ai_analysis(
    alert_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalAiAnalysisRequestResponse:
    async with internal_errors("request an AI analysis", db):
        request = await request_alert_analysis(alert_id, current_user, db)

    return PortalAiAnalysisRequestResponse(
        alert_id=alert_id,
        requested_at=request.requested_at,
        success=True,
        message="AI analysis requested: it will appear here once the AI analyst has finished",
    )
