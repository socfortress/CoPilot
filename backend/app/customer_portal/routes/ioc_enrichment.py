from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.ioc_enrichment import AlertIocEnrichmentResponse
from app.customer_portal.schema.ioc_enrichment import IocEnrichmentAvailabilityResponse
from app.customer_portal.schema.ioc_enrichment import IocEnrichmentConnectors
from app.customer_portal.schema.ioc_enrichment import IocEnrichmentSettings
from app.customer_portal.schema.ioc_enrichment import IocEnrichmentSettingsResponse
from app.customer_portal.schema.ioc_enrichment import IocLookupResponse
from app.customer_portal.schema.ioc_enrichment import UpdateIocEnrichmentSettingsRequest
from app.customer_portal.services import ioc_enrichment as service
from app.customer_portal.services import ioc_enrichment_sources as sources
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_portal_ioc_enrichment_router = APIRouter()

# Threat Intel enrichment of a customer's own IOCs (#1318), two audiences:
#
# * Portal users read what is cached about their alerts' IOCs and check one against the sources.
# * Operators manage the per-customer switch under ``/ioc_enrichment/settings/{code}`` (admin to write).
#
# Static paths before those with a parameter under the same prefix. Keep it that way.

PORTAL = Security(AuthHandler().require_any_scope("customer_user"))


def _id():
    """A database id in the path. A fresh ``Path`` per parameter: FastAPI binds one to the first name it serves."""
    return Path(..., ge=1, le=2_147_483_647)


def _settings_schema(customer_code: str, settings) -> IocEnrichmentSettings:
    if settings is None:
        return IocEnrichmentSettings(customer_code=customer_code, enabled=False)
    return IocEnrichmentSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        daily_lookup_limit=settings.daily_lookup_limit,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


async def _settings_response(customer_code: str, settings, message: str) -> IocEnrichmentSettingsResponse:
    available = await sources.available_sources()
    return IocEnrichmentSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        connectors=IocEnrichmentConnectors(virustotal=sources.VIRUSTOTAL in available, opencti=sources.OPENCTI in available),
        cache_hours=int(service.CACHE_TTL.total_seconds() // 3600),
        success=True,
        message=message,
    )


# --- Operator-facing switch ---


@customer_portal_ioc_enrichment_router.get(
    "/ioc_enrichment/settings/{customer_code}",
    response_model=IocEnrichmentSettingsResponse,
    description="Whether a customer's portal users can check their alerts' IOCs against Threat Intel, their daily limit, and the sources",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(verify_customer_code_access)],
)
async def get_ioc_enrichment_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> IocEnrichmentSettingsResponse:
    async with internal_errors("read the IOC enrichment settings"):
        settings = await service.get_settings(customer_code, session)
        return await _settings_response(customer_code, settings, "Settings retrieved")


@customer_portal_ioc_enrichment_router.put(
    "/ioc_enrichment/settings/{customer_code}",
    response_model=IocEnrichmentSettingsResponse,
    description="Turn IOC enrichment on or off for a customer and set its daily limit (null = unlimited)",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_ioc_enrichment_settings(
    customer_code: str,
    request: UpdateIocEnrichmentSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> IocEnrichmentSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save the IOC enrichment settings", session):
        before = await service.get_settings(customer_code, session)
        old = {"enabled": bool(before and before.enabled), "daily_lookup_limit": before.daily_lookup_limit if before else None}
        settings = await service.upsert_settings(
            customer_code,
            request.enabled,
            request.daily_lookup_limit,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)

    new = {"enabled": request.enabled, "daily_lookup_limit": request.daily_lookup_limit}
    logger.info(f"IOC enrichment {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    if old != new:
        await record_audit_event(
            action=AuditAction.IOC_ENRICHMENT_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_ioc_enrichment_settings",
            entity_id=customer_code,
            old_value=old,
            new_value=new,
        )
    async with internal_errors("read the IOC enrichment sources"):
        return await _settings_response(customer_code, settings, "Settings saved")


# --- Portal-facing ---


@customer_portal_ioc_enrichment_router.get(
    "/ioc_enrichment/availability",
    response_model=IocEnrichmentAvailabilityResponse,
    description="Whether IOC enrichment shows for the caller (or for one of their customers), and from which sources",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_ioc_enrichment_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IocEnrichmentAvailabilityResponse:
    async with internal_errors("resolve the IOC enrichment availability"):
        resolved, enabled, available = await service.availability(current_user, session, customer_code)
    return IocEnrichmentAvailabilityResponse(
        customer_code=resolved,
        enabled=enabled,
        sources=available,
        success=True,
        message="IOC enrichment is enabled" if enabled else "IOC enrichment is not enabled",
    )


@customer_portal_ioc_enrichment_router.get(
    "/ioc_enrichment/alert/{alert_id}",
    response_model=AlertIocEnrichmentResponse,
    description="What is known about every IOC of one of the caller's alerts, from the cache: no source is asked",
    dependencies=[PORTAL],
)
async def get_alert_ioc_enrichment(
    alert_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AlertIocEnrichmentResponse:
    async with internal_errors("load the IOC enrichment"):
        iocs, available = await service.list_for_alert(alert_id, current_user, session)
    return AlertIocEnrichmentResponse(alert_id=alert_id, iocs=iocs, sources=available, success=True, message="IOC enrichment retrieved")


@customer_portal_ioc_enrichment_router.post(
    "/ioc_enrichment/alert/{alert_id}/ioc/{ioc_id}",
    response_model=IocLookupResponse,
    description="Check one IOC of one of the caller's alerts against the Threat Intel sources whose answer is missing or stale",
    dependencies=[PORTAL],
)
async def check_alert_ioc(
    alert_id: int = _id(),
    ioc_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IocLookupResponse:
    async with internal_errors("check the IOC", session):
        ioc = await service.check(alert_id, ioc_id, current_user, session)
    return IocLookupResponse(ioc=ioc, success=True, message="IOC checked")
