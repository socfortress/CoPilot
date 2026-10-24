from typing import List
from typing import Literal
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
from app.customer_portal.schema.soc_requests import AskOnAlertRequest
from app.customer_portal.schema.soc_requests import AskOnCaseRequest
from app.customer_portal.schema.soc_requests import AskResponse
from app.customer_portal.schema.soc_requests import PortalSocRequestsResponse
from app.customer_portal.schema.soc_requests import SocRequestAvailabilityResponse
from app.customer_portal.schema.soc_requests import SocRequestResponse
from app.customer_portal.schema.soc_requests import SocRequestSettings
from app.customer_portal.schema.soc_requests import SocRequestSettingsResponse
from app.customer_portal.schema.soc_requests import SocRequestsResponse
from app.customer_portal.schema.soc_requests import UpdateSocRequestSettingsRequest
from app.customer_portal.services import soc_requests as service
from app.customer_portal.services.customers import ensure_customer_exists
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_portal_soc_requests_router = APIRouter()

# "Ask the SOC" (#1305), three audiences:
#
# * Portal users ask about their own alerts and cases, and read their questions' state.
# * CoPilot's analysts list their customers' questions and mark one answered by hand.
# * Operators manage the per-customer switch under ``/soc_requests/settings/{code}`` (admin to write).
#
# Static paths before those with a parameter under the same prefix. Keep it that way.

PORTAL = Security(AuthHandler().require_any_scope("customer_user"))
SOC = Security(AuthHandler().require_any_scope("admin", "analyst"))


def _id():
    """A database id in the path. A fresh ``Path`` per parameter: FastAPI binds one to the first name it serves."""
    return Path(..., ge=1, le=2_147_483_647)


def _settings_schema(customer_code: str, settings) -> SocRequestSettings:
    if settings is None:
        return SocRequestSettings(customer_code=customer_code, enabled=False)
    return SocRequestSettings(
        customer_code=settings.customer_code,
        enabled=settings.enabled,
        daily_request_limit=settings.daily_request_limit,
        updated_at=settings.updated_at.isoformat() if settings.updated_at else None,
        updated_by=settings.updated_by,
    )


# --- Operator-facing switch ---


@customer_portal_soc_requests_router.get(
    "/soc_requests/settings/{customer_code}",
    response_model=SocRequestSettingsResponse,
    description="Whether a customer's portal users can ask the SOC about their alerts and cases, and their daily limit",
    dependencies=[SOC, Depends(verify_customer_code_access)],
)
async def get_soc_request_settings(customer_code: str, session: AsyncSession = Depends(get_db)) -> SocRequestSettingsResponse:
    async with internal_errors("read the Ask the SOC settings"):
        settings = await service.get_settings(customer_code, session)
    return SocRequestSettingsResponse(settings=_settings_schema(customer_code, settings), success=True, message="Settings retrieved")


@customer_portal_soc_requests_router.put(
    "/soc_requests/settings/{customer_code}",
    response_model=SocRequestSettingsResponse,
    description="Turn 'Ask the SOC' on or off for a customer and set its daily limit (null = unlimited)",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def set_soc_request_settings(
    customer_code: str,
    request: UpdateSocRequestSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
) -> SocRequestSettingsResponse:
    await ensure_customer_exists(session, customer_code)
    async with internal_errors("save the Ask the SOC settings", session):
        before = await service.get_settings(customer_code, session)
        old = {"enabled": bool(before and before.enabled), "daily_request_limit": before.daily_request_limit if before else None}
        settings = await service.upsert_settings(
            customer_code,
            request.enabled,
            request.daily_request_limit,
            session,
            user_id=getattr(current_user, "id", None),
        )
        await session.commit()
        await session.refresh(settings)

    new = {"enabled": request.enabled, "daily_request_limit": request.daily_request_limit}
    logger.info(f"Ask the SOC {'enabled' if request.enabled else 'disabled'} for customer {customer_code}")
    if old != new:
        await record_audit_event(
            action=AuditAction.SOC_REQUEST_SETTINGS_UPDATE,
            actor_user_id=getattr(current_user, "id", None),
            actor_username=getattr(current_user, "username", None),
            customer_code=customer_code,
            entity_type="customer_portal_soc_request_settings",
            entity_id=customer_code,
            old_value=old,
            new_value=new,
        )
    return SocRequestSettingsResponse(settings=_settings_schema(customer_code, settings), success=True, message="Settings saved")


# --- Portal-facing ---


@customer_portal_soc_requests_router.get(
    "/soc_requests/availability",
    response_model=SocRequestAvailabilityResponse,
    description="Whether 'Ask the SOC' shows for the caller (or for one of their customers)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_soc_request_availability(
    customer_code: Optional[str] = Query(None, description="Resolve the switch for one customer instead of the caller's scope"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SocRequestAvailabilityResponse:
    async with internal_errors("resolve the Ask the SOC availability"):
        resolved, enabled = await service.availability(current_user, session, customer_code)
    return SocRequestAvailabilityResponse(
        customer_code=resolved,
        enabled=enabled,
        success=True,
        message="Asking the SOC is enabled" if enabled else "Asking the SOC is not enabled",
    )


@customer_portal_soc_requests_router.get(
    "/soc_requests/alert/{alert_id}",
    response_model=PortalSocRequestsResponse,
    description="The caller's questions about an alert (on it, or filed on a case from it), newest first, and its open case",
    dependencies=[PORTAL],
)
async def get_alert_soc_requests(
    alert_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalSocRequestsResponse:
    async with internal_errors("load the questions"):
        requests, open_case_id = await service.list_for_alert(alert_id, current_user, session)
    return PortalSocRequestsResponse(requests=requests, open_case_id=open_case_id, success=True, message="Questions retrieved")


@customer_portal_soc_requests_router.post(
    "/soc_requests/alert/{alert_id}",
    response_model=AskResponse,
    description="Ask the SOC about an alert: on its open case (or a new case from it), or on the alert itself",
    dependencies=[PORTAL],
)
async def ask_about_alert(
    body: AskOnAlertRequest,
    alert_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AskResponse:
    async with internal_errors("send the question", session):
        request = await service.ask_on_alert(alert_id, body, current_user, session)
    return AskResponse(request=request, success=True, message="Your question was sent to the SOC")


@customer_portal_soc_requests_router.get(
    "/soc_requests/case/{case_id}",
    response_model=PortalSocRequestsResponse,
    description="The caller's questions about a case, newest first",
    dependencies=[PORTAL],
)
async def get_case_soc_requests(
    case_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PortalSocRequestsResponse:
    async with internal_errors("load the questions"):
        requests = await service.list_for_case(case_id, current_user, session)
    return PortalSocRequestsResponse(requests=requests, success=True, message="Questions retrieved")


@customer_portal_soc_requests_router.post(
    "/soc_requests/case/{case_id}",
    response_model=AskResponse,
    description="Ask the SOC about a case: left on the case as a comment",
    dependencies=[PORTAL],
)
async def ask_about_case(
    body: AskOnCaseRequest,
    case_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AskResponse:
    async with internal_errors("send the question", session):
        request = await service.ask_on_case(case_id, body, current_user, session)
    return AskResponse(request=request, success=True, message="Your question was sent to the SOC")


# --- SOC-facing ---


@customer_portal_soc_requests_router.get(
    "/soc_requests",
    response_model=SocRequestsResponse,
    description="Customer questions of the caller's customers, newest first (at most SOC_LIST_LIMIT), with the counts",
    dependencies=[SOC],
)
async def list_soc_requests(
    status: Optional[Literal["open", "answered"]] = Query(None),
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of the caller's customers"),
    case_id: Optional[int] = Query(None, ge=1),
    alert_id: Optional[int] = Query(None, ge=1),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SocRequestsResponse:
    async with internal_errors("load the customer questions"):
        requests, total, open_count = await service.list_for_soc(
            current_user,
            session,
            status=status,
            customer_codes=customer_codes,
            case_id=case_id,
            alert_id=alert_id,
        )
    return SocRequestsResponse(requests=requests, total=total, open=open_count, success=True, message="Customer questions retrieved")


@customer_portal_soc_requests_router.post(
    "/soc_requests/{request_id}/answered",
    response_model=SocRequestResponse,
    description="Mark a customer question answered (a reply outside CoPilot, e.g. by phone)",
    dependencies=[SOC],
)
async def mark_soc_request_answered(
    request_id: int = _id(),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SocRequestResponse:
    async with internal_errors("mark the question answered", session):
        request = await service.mark_answered(request_id, current_user, session)
    return SocRequestResponse(request=request, success=True, message="Question marked answered")
