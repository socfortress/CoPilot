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
from app.customer_portal.schema.activity import ActivityRange
from app.customer_portal.schema.activity import PortalActivityAvailabilityResponse
from app.customer_portal.schema.activity import PortalActivityResponse
from app.customer_portal.schema.activity import PortalActivitySettings
from app.customer_portal.schema.activity import PortalActivitySettingsResponse
from app.customer_portal.schema.activity import UpdatePortalActivitySettingsRequest
from app.customer_portal.services import activity as activity_service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

customer_portal_activity_router = APIRouter()

# Two audiences, like the SLA router (#1284):
#
# * End customers read their own activity — GET only.
# * CoPilot operators manage the per-customer switch under ``/activity/settings/{code}``
#   (admin to write).
#
# Every path here is static except ``/activity/settings/{customer_code}``, which cannot
# collide with the others. Keep it that way when appending routes.


def _settings_schema(customer_code: str, settings) -> PortalActivitySettings:
    if settings is None:
        return PortalActivitySettings(customer_code=customer_code, enabled=False)
    return PortalActivitySettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


# --- Operator-facing switch ---


@customer_portal_activity_router.get(
    "/activity/settings/{customer_code}",
    response_model=PortalActivitySettingsResponse,
    description="Get whether a customer's portal users can see the Activity page",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_activity_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> PortalActivitySettingsResponse:
    async with internal_errors("read customer activity settings"):
        settings = await activity_service.get_activity_settings(customer_code, session)
    return PortalActivitySettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer activity settings retrieved successfully",
    )


@customer_portal_activity_router.put(
    "/activity/settings/{customer_code}",
    response_model=PortalActivitySettingsResponse,
    description="Enable or disable the Customer Portal Activity page for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_activity_settings(
    customer_code: str,
    request: UpdatePortalActivitySettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalActivitySettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save customer activity settings", session):
        before = await activity_service.get_activity_settings(customer_code, session)
        was_enabled = bool(before and before.enabled)
        settings = await activity_service.upsert_activity_settings(
            customer_code,
            request.enabled,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)

    logger.info(f"Customer portal Activity page {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    if was_enabled != request.enabled:
        await record_audit_event(
            action=AuditAction.ACTIVITY_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_activity_settings",
            entity_id=customer_code,
            old_value={"enabled": was_enabled},
            new_value={"enabled": request.enabled},
        )
    return PortalActivitySettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer activity settings saved successfully",
    )


# --- Portal-facing reads ---


@customer_portal_activity_router.get(
    "/activity/availability",
    response_model=PortalActivityAvailabilityResponse,
    description="Whether the Activity page should render for the caller (or for a specific customer)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_activity_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalActivityAvailabilityResponse:
    async with internal_errors("resolve activity availability"):
        resolved_code, enabled = await activity_service.availability(current_user, session, customer_code)
    return PortalActivityAvailabilityResponse(
        customer_code=resolved_code,
        enabled=enabled,
        success=True,
        message="The Activity page is enabled" if enabled else "The Activity page is not enabled",
    )


@customer_portal_activity_router.get(
    "/activity",
    response_model=PortalActivityResponse,
    description=(
        "What the SOC handled for the caller's customers over the last 7, 30 or 90 days and the period before: alerts by "
        "source, severity, detection, asset and tag, the SOC's verdicts, and cases by type and status. Counted from when each "
        "alert or case reached the SOC (its SLA clock's opened_at). Opt-in per customer; same visibility as the lists."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_activity(
    range_: ActivityRange = Query("30d", alias="range", description="7d, 30d or 90d"),
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of the caller's customers"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalActivityResponse:
    async with internal_errors("load the activity", session):
        return await activity_service.activity(current_user, session, range_, to_naive_utc(now_utc()), customer_codes)
