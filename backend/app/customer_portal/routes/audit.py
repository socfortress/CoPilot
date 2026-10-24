from datetime import datetime
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.audit import PAGE_SIZE_DEFAULT
from app.customer_portal.schema.audit import PAGE_SIZE_MAX
from app.customer_portal.schema.audit import AuditCategory
from app.customer_portal.schema.audit import PortalAuditAvailabilityResponse
from app.customer_portal.schema.audit import PortalAuditResponse
from app.customer_portal.schema.audit import PortalAuditSettings
from app.customer_portal.schema.audit import PortalAuditSettingsResponse
from app.customer_portal.schema.audit import UpdatePortalAuditSettingsRequest
from app.customer_portal.services import audit as audit_service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

customer_portal_audit_router = APIRouter()

# Two audiences, like the Activity router (#1298):
#
# * A customer admin reads their customers' audit log: GET only, customer_user by token and a
#   customer admin by the database (403 otherwise, and for a customer whose switch is off).
# * CoPilot operators manage the per-customer switch under ``/audit/settings/{code}`` (admin to write).
#
# Every path is static except ``/audit/settings/{customer_code}``, which cannot collide with the
# others. Keep it that way when appending routes.

READERS = Security(AuthHandler().require_any_scope("customer_user"))
NO_STORE = {"Cache-Control": "no-store"}


def _settings_schema(customer_code: str, settings) -> PortalAuditSettings:
    if settings is None:
        return PortalAuditSettings(customer_code=customer_code, enabled=False)
    return PortalAuditSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


def _window(since: Optional[datetime], until: Optional[datetime]):
    since_utc = to_naive_utc(since) if since else None
    until_utc = to_naive_utc(until) if until else None
    if since_utc and until_utc and since_utc >= until_utc:
        raise HTTPException(status_code=422, detail="'since' must be before 'until'")
    return since_utc, until_utc


# --- Operator-facing switch ---


@customer_portal_audit_router.get(
    "/audit/settings/{customer_code}",
    response_model=PortalAuditSettingsResponse,
    description="Get whether a customer's administrators can read their audit log in the portal",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_audit_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> PortalAuditSettingsResponse:
    async with internal_errors("read customer audit log settings"):
        settings = await audit_service.get_audit_settings(customer_code, session)
    return PortalAuditSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer audit log settings retrieved successfully",
    )


@customer_portal_audit_router.put(
    "/audit/settings/{customer_code}",
    response_model=PortalAuditSettingsResponse,
    description="Enable or disable the Customer Portal Audit Log page for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_audit_settings(
    customer_code: str,
    request: UpdatePortalAuditSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalAuditSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save customer audit log settings", session):
        before = await audit_service.get_audit_settings(customer_code, session)
        was_enabled = bool(before and before.enabled)
        settings = await audit_service.upsert_audit_settings(
            customer_code,
            request.enabled,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)

    logger.info(f"Customer portal Audit Log page {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    if was_enabled != request.enabled:
        await record_audit_event(
            action=AuditAction.AUDIT_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_audit_settings",
            entity_id=customer_code,
            old_value={"enabled": was_enabled},
            new_value={"enabled": request.enabled},
        )
    return PortalAuditSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer audit log settings saved successfully",
    )


# --- Portal-facing reads ---


@customer_portal_audit_router.get(
    "/audit/availability",
    response_model=PortalAuditAvailabilityResponse,
    description="Whether the Audit Log page should render for the caller: a customer admin of a customer that has it on",
    dependencies=[READERS],
)
async def get_audit_availability(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalAuditAvailabilityResponse:
    async with internal_errors("resolve audit log availability"):
        customers = await audit_service.availability(current_user, session)
    return PortalAuditAvailabilityResponse(
        available=bool(customers),
        customers=customers,
        success=True,
        message="The audit log is available" if customers else "The audit log is not available",
    )


@customer_portal_audit_router.get(
    "/audit",
    response_model=PortalAuditResponse,
    description=(
        "Who did what in the caller's customers, newest first: status changes and comments on alerts and cases, cases opened, "
        "reports, AI analysis requests and the portal users' account events. The SOC is shown as the SOC, never by name. "
        "For customer admins of customers whose switch is on."
    ),
    dependencies=[READERS],
)
async def get_audit_log(
    response: Response,
    category: Optional[AuditCategory] = Query(None),
    user_id: Optional[int] = Query(
        None,
        description="One of the customers' portal users: what they did, or what was done to their account",
    ),
    since: Optional[datetime] = Query(None, description="From this time (inclusive), ISO 8601 with an offset"),
    until: Optional[datetime] = Query(None, description="Before this time (exclusive), ISO 8601 with an offset"),
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of the caller's customers"),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalAuditResponse:
    since_utc, until_utc = _window(since, until)
    response.headers.update(NO_STORE)
    async with internal_errors("load the audit log", session):
        scope = await audit_service.resolve(current_user, session, customer_codes)
        return await audit_service.list_entries(
            scope,
            session,
            category=category,
            user_id=user_id,
            since=since_utc,
            until=until_utc,
            page=page,
            page_size=page_size,
        )


@customer_portal_audit_router.get(
    "/audit/export",
    description="The filtered audit log as CSV, newest first (at most EXPORT_LIMIT rows; X-Export-Truncated says when cut)",
    dependencies=[READERS],
    response_class=Response,
)
async def export_audit_log(
    category: Optional[AuditCategory] = Query(None),
    user_id: Optional[int] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    customer_codes: Optional[List[str]] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    since_utc, until_utc = _window(since, until)
    async with internal_errors("export the audit log", session):
        scope = await audit_service.resolve(current_user, session, customer_codes)
        content, truncated = await audit_service.export_csv(
            scope,
            session,
            category=category,
            user_id=user_id,
            since=since_utc,
            until=until_utc,
        )
    filename = f"audit-log-{now_utc().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            **NO_STORE,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Truncated": "true" if truncated else "false",
        },
    )
