from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Security
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.exposure import ComplianceResponse
from app.customer_portal.schema.exposure import CveDetailResponse
from app.customer_portal.schema.exposure import PolicyAgentsResponse
from app.customer_portal.schema.exposure import PortalExposureAvailabilityResponse
from app.customer_portal.schema.exposure import PortalExposureSettings
from app.customer_portal.schema.exposure import PortalExposureSettingsResponse
from app.customer_portal.schema.exposure import Severity
from app.customer_portal.schema.exposure import UpdatePortalExposureSettingsRequest
from app.customer_portal.schema.exposure import VulnerabilitiesResponse
from app.customer_portal.services import exposure as exposure_service
from app.customer_portal.services import exposure_compliance
from app.customer_portal.services import exposure_vulnerabilities
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access
from app.time_utils import now_utc

customer_portal_exposure_router = APIRouter()

# Two audiences, like the SLA router (#1289):
#
# * End customers read their own exposure — GET only.
# * CoPilot operators manage the per-customer switch under ``/exposure/settings/{code}``
#   (admin to write).
#
# Static paths come before the ones with a parameter under the same prefix
# (``/vulnerabilities/export`` before ``/vulnerabilities/cve/{cve_id}``). Keep it that way.

READERS = Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))
CUSTOMER_CODES = Query(None, description="Optional subset of the caller's customers")
CVE_PATH = Path(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$", description="The CVE (or advisory) id")
POLICY_PATH = Path(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$", description="The SCA policy id")


def _settings_schema(customer_code: str, settings) -> PortalExposureSettings:
    if settings is None:
        return PortalExposureSettings(customer_code=customer_code, enabled=False)
    return PortalExposureSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


# --- Operator-facing switch ---


@customer_portal_exposure_router.get(
    "/exposure/settings/{customer_code}",
    response_model=PortalExposureSettingsResponse,
    description="Get whether a customer's portal users can see the Exposure page",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_customer_code_access),
    ],
)
async def get_customer_exposure_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> PortalExposureSettingsResponse:
    async with internal_errors("read customer exposure settings"):
        settings = await exposure_service.get_exposure_settings(customer_code, session)
    return PortalExposureSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer exposure settings retrieved successfully",
    )


@customer_portal_exposure_router.put(
    "/exposure/settings/{customer_code}",
    response_model=PortalExposureSettingsResponse,
    description="Enable or disable the Customer Portal Exposure page for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_customer_exposure_settings(
    customer_code: str,
    request: UpdatePortalExposureSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> PortalExposureSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save customer exposure settings", session):
        before = await exposure_service.get_exposure_settings(customer_code, session)
        was_enabled = bool(before and before.enabled)
        settings = await exposure_service.upsert_exposure_settings(
            customer_code,
            request.enabled,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)

    logger.info(f"Customer portal Exposure page {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    if was_enabled != request.enabled:
        await record_audit_event(
            action=AuditAction.EXPOSURE_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_exposure_settings",
            entity_id=customer_code,
            old_value={"enabled": was_enabled},
            new_value={"enabled": request.enabled},
        )
    return PortalExposureSettingsResponse(
        settings=_settings_schema(customer_code, settings),
        success=True,
        message="Customer exposure settings saved successfully",
    )


# --- Portal-facing reads ---


@customer_portal_exposure_router.get(
    "/exposure/availability",
    response_model=PortalExposureAvailabilityResponse,
    description="Whether the Exposure page should render for the caller (or for a specific customer)",
    dependencies=[READERS],
)
async def get_exposure_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalExposureAvailabilityResponse:
    async with internal_errors("resolve exposure availability"):
        resolved_code, enabled = await exposure_service.availability(current_user, session, customer_code)
    return PortalExposureAvailabilityResponse(
        customer_code=resolved_code,
        enabled=enabled,
        success=True,
        message="The Exposure page is enabled" if enabled else "The Exposure page is not enabled",
    )


@customer_portal_exposure_router.get(
    "/exposure/vulnerabilities",
    response_model=VulnerabilitiesResponse,
    description=(
        "Vulnerabilities across the caller's agents, read live from the Wazuh indexer: counts per severity, totals "
        "and one page of CVEs ranked by CVSS then by affected agents. Opt-in per customer."
    ),
    dependencies=[READERS],
)
async def get_exposure_vulnerabilities(
    severity: Optional[Severity] = Query(None, description="Critical, High, Medium or Low"),
    search: Optional[str] = Query(None, max_length=100, description="A CVE id prefix, or part of a package name"),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=exposure_vulnerabilities.MAX_PAGE_SIZE),
    customer_codes: Optional[List[str]] = CUSTOMER_CODES,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VulnerabilitiesResponse:
    async with internal_errors("load the vulnerabilities", session):
        scope = await exposure_service.resolve_scope(current_user, session, customer_codes)
    return await exposure_vulnerabilities.vulnerabilities(scope, severity, search, page, page_size)


@customer_portal_exposure_router.get(
    "/exposure/vulnerabilities/export",
    description="Every finding under the filter as CSV, one row per CVE × package × agent (at most EXPORT_LIMIT rows)",
    dependencies=[READERS],
    response_class=Response,
)
async def export_exposure_vulnerabilities(
    severity: Optional[Severity] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    customer_codes: Optional[List[str]] = CUSTOMER_CODES,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    async with internal_errors("export the vulnerabilities", session):
        scope = await exposure_service.resolve_scope(current_user, session, customer_codes)
    if not scope.enabled:
        raise HTTPException(status_code=404, detail="The Exposure page is not enabled for this customer")
    async with internal_errors("export the vulnerabilities"):
        content, truncated = await exposure_vulnerabilities.export_csv(scope, severity, search)
    filename = f"vulnerabilities-{now_utc().strftime('%Y%m%d-%H%M')}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Truncated": "true" if truncated else "false",
        },
    )


@customer_portal_exposure_router.get(
    "/exposure/vulnerabilities/cve/{cve_id}",
    response_model=CveDetailResponse,
    description="One CVE: what Wazuh says of it, and the caller's agents it affects",
    dependencies=[READERS],
)
async def get_exposure_cve(
    cve_id: str = CVE_PATH,
    customer_codes: Optional[List[str]] = CUSTOMER_CODES,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CveDetailResponse:
    async with internal_errors("load the vulnerability", session):
        scope = await exposure_service.resolve_scope(current_user, session, customer_codes)
    if not scope.enabled:
        raise HTTPException(status_code=404, detail="The Exposure page is not enabled for this customer")
    return await exposure_vulnerabilities.cve_detail(scope, cve_id)


@customer_portal_exposure_router.get(
    "/exposure/compliance",
    response_model=ComplianceResponse,
    description=(
        "SCA results across the caller's agents, by policy, from the Wazuh manager (kept a few minutes). "
        "Agents Wazuh could not answer for are counted. Opt-in per customer."
    ),
    dependencies=[READERS],
)
async def get_exposure_compliance(
    customer_codes: Optional[List[str]] = CUSTOMER_CODES,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComplianceResponse:
    async with internal_errors("load the compliance", session):
        scope = await exposure_service.resolve_scope(current_user, session, customer_codes)
    return await exposure_compliance.compliance(scope)


@customer_portal_exposure_router.get(
    "/exposure/compliance/{policy_id}/agents",
    response_model=PolicyAgentsResponse,
    description="The caller's agents assessed on one SCA policy, weakest score first",
    dependencies=[READERS],
)
async def get_exposure_policy_agents(
    policy_id: str = POLICY_PATH,
    customer_codes: Optional[List[str]] = CUSTOMER_CODES,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyAgentsResponse:
    async with internal_errors("load the policy", session):
        scope = await exposure_service.resolve_scope(current_user, session, customer_codes)
    if not scope.enabled:
        raise HTTPException(status_code=404, detail="The Exposure page is not enabled for this customer")
    return await exposure_compliance.compliance_policy(scope, policy_id)
