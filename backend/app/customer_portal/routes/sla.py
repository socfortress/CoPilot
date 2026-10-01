from datetime import datetime
from datetime import timezone
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.sla import PortalSlaAvailabilityResponse
from app.customer_portal.schema.sla import PortalSlaOverviewResponse
from app.customer_portal.schema.sla import PortalSlaSettings
from app.customer_portal.schema.sla import PortalSlaSettingsResponse
from app.customer_portal.schema.sla import UpdatePortalSlaSettingsRequest
from app.customer_portal.services import sla as sla_service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access
from app.soc_management.domain.periods import requested_period

customer_portal_sla_router = APIRouter()

INVALID_PERIOD = "Invalid period: it must start before it ends and span at most 366 days"

# Two audiences, like the AI reports router:
#
# * End customers read their own SLA figures — GET only. Nothing a portal user can
#   send changes a target, a calendar or a clock.
# * CoPilot operators manage the per-customer switch under ``/sla/settings/{code}``
#   (admin to write).
#
# Every path here is static except ``/sla/settings/{customer_code}``, which cannot
# collide with the others. Keep it that way when appending routes.


def _settings_schema(customer_code: str, settings) -> PortalSlaSettings:
    if settings is None:
        return PortalSlaSettings(customer_code=customer_code, enabled=False)
    return PortalSlaSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


def _naive_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo is None else moment.astimezone(timezone.utc).replace(tzinfo=None)


# --- Operator-facing switch ---


@customer_portal_sla_router.get(
    "/sla/settings/{customer_code}",
    response_model=PortalSlaSettingsResponse,
    description="Get whether a customer's portal users can see the SLA page",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_sla_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> PortalSlaSettingsResponse:
    async with internal_errors("read customer SLA settings"):
        settings = await sla_service.get_sla_settings(customer_code, session)
    return PortalSlaSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer SLA settings retrieved successfully",
    )


@customer_portal_sla_router.put(
    "/sla/settings/{customer_code}",
    response_model=PortalSlaSettingsResponse,
    description="Enable or disable the Customer Portal SLA page for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_sla_settings(
    customer_code: str,
    request: UpdatePortalSlaSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalSlaSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save customer SLA settings", session):
        settings = await sla_service.upsert_sla_settings(customer_code, request.enabled, session, user_id=getattr(current_user, "id", None))
        await session.commit()
        await session.refresh(settings)
    logger.info(f"Customer portal SLA page {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    return PortalSlaSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer SLA settings saved successfully",
    )


# --- Portal-facing reads ---


@customer_portal_sla_router.get(
    "/sla/availability",
    response_model=PortalSlaAvailabilityResponse,
    description="Whether the SLA page should render for the caller (or for a specific customer)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_sla_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalSlaAvailabilityResponse:
    async with internal_errors("resolve SLA availability"):
        resolved_code, enabled = await sla_service.availability(current_user, session, customer_code)
    return PortalSlaAvailabilityResponse(
        customer_code=resolved_code,
        enabled=enabled,
        success=True,
        message="The SLA page is enabled" if enabled else "The SLA page is not enabled",
    )


@customer_portal_sla_router.get(
    "/sla/overview",
    response_model=PortalSlaOverviewResponse,
    description="The SOC's SLA for the caller's customers over a period: targets, compliance, response times and trend",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_sla_overview(
    date_from: datetime = Query(..., description="Period start (inclusive)"),
    date_to: datetime = Query(..., description="Period end (exclusive)"),
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of the caller's customers"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalSlaOverviewResponse:
    try:
        period = requested_period(_naive_utc(date_from), _naive_utc(date_to))
    except ValueError:
        raise HTTPException(status_code=400, detail=INVALID_PERIOD)
    async with internal_errors("load the SLA overview", session):
        return await sla_service.sla_overview(current_user, session, period, customer_codes)
