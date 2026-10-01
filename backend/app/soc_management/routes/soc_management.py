"""SOC Management API (#1187), mounted under ``/api/soc_management``.

Admin and analyst only. Every read is narrowed to what the caller may see by the
services (customer scoping + tag RBAC), and per-analyst rows are the admin's view.
Policy writes are admin only: an SLA is a commitment the SOC makes to its customers,
not a per-analyst preference.
"""

from datetime import datetime
from datetime import timezone
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Security
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_query import customer_codes_query
from app.soc_management.domain.periods import Bucket
from app.soc_management.domain.periods import requested_period
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.sla import SlaState
from app.soc_management.schema.calendar import CalendarIn
from app.soc_management.schema.calendar import CalendarResponse
from app.soc_management.schema.metrics import AttentionResponse
from app.soc_management.schema.metrics import DashboardResponse
from app.soc_management.schema.metrics import ItemSlaResponse
from app.soc_management.schema.policy import PolicyOverridesResponse
from app.soc_management.schema.policy import PolicyResponse
from app.soc_management.schema.policy import PolicyUpdateRequest
from app.soc_management.services import calendars as calendar_service
from app.soc_management.services import metrics as metrics_service
from app.soc_management.services import policy as policy_service
from app.soc_management.services import report as report_service
from app.soc_management.services.datasets import FactFilters
from app.soc_management.services.lifecycle import retarget_open

soc_management_router = APIRouter()

_SOC = Security(AuthHandler().require_any_scope("admin", "analyst"))
_ADMIN = Security(AuthHandler().require_any_scope("admin"))


def _list_param(request: Request, name: str) -> List[str]:
    """``?x=a&x=b`` or axios's ``?x[]=a&x[]=b``, de-duplicated, order kept."""
    values = [*request.query_params.getlist(name), *request.query_params.getlist(f"{name}[]")]
    return list(dict.fromkeys(value for value in values if value))


def fact_filters(request: Request) -> FactFilters:
    return FactFilters(severities=tuple(_list_param(request, "severities")), sources=tuple(_list_param(request, "sources")))


def _period(date_from: datetime, date_to: datetime):
    try:
        return requested_period(_naive_utc(date_from), _naive_utc(date_to))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _naive_utc(moment: datetime) -> datetime:
    """Stored timestamps are naive UTC; an offset-carrying query value is converted to that."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


# ── dashboard ────────────────────────────────────────────────────────────────


@soc_management_router.get(
    "/dashboard",
    response_model=DashboardResponse,
    description="Every SOC Management section for one period, computed from one snapshot",
    dependencies=[_SOC],
)
async def get_dashboard(
    date_from: datetime = Query(..., description="Period start (inclusive), UTC"),
    date_to: datetime = Query(..., description="Period end (exclusive), UTC"),
    bucket: Optional[Bucket] = Query(None, description="Trend granularity; chosen from the period length when omitted"),
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    filters: FactFilters = Depends(fact_filters),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    query = metrics_service.DashboardQuery(
        period=_period(date_from, date_to),
        customer_codes=customer_codes,
        filters=filters,
        bucket=bucket,
    )
    return await metrics_service.build_dashboard(session, current_user, query)


@soc_management_router.get(
    "/attention",
    response_model=AttentionResponse,
    description="Open alerts and cases that breached or are about to breach their SLA, most urgent first",
    dependencies=[_SOC],
)
async def get_attention(
    entity: Optional[SlaEntity] = Query(None),
    state: Optional[SlaState] = Query(None, description="breached | at_risk"),
    limit: int = Query(100, ge=1, le=metrics_service.MAX_ATTENTION_LIMIT),
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    filters: FactFilters = Depends(fact_filters),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AttentionResponse:
    if state is not None and state not in (SlaState.BREACHED, SlaState.AT_RISK):
        raise HTTPException(status_code=400, detail="state must be breached or at_risk")
    return await metrics_service.build_attention(session, current_user, customer_codes, filters, entity, state, limit)


@soc_management_router.get(
    "/items/{entity}/{item_id}/sla",
    response_model=ItemSlaResponse,
    description="One alert's or case's SLA clocks",
    dependencies=[_SOC],
)
async def get_item_sla(
    entity: SlaEntity,
    item_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemSlaResponse:
    result = await metrics_service.item_sla(session, current_user, entity, item_id)
    if result is None:
        # 404 whether it does not exist or belongs to a tenant the caller cannot see:
        # distinguishing them would confirm ids across tenants.
        raise HTTPException(status_code=404, detail=f"{entity.value.capitalize()} not found")
    return result


# ── report ───────────────────────────────────────────────────────────────────


@soc_management_router.get(
    "/report",
    response_class=Response,
    description="SOC operational report (PDF) for a period",
    dependencies=[_SOC],
)
async def get_report(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    filters: FactFilters = Depends(fact_filters),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    query = metrics_service.DashboardQuery(period=_period(date_from, date_to), customer_codes=customer_codes, filters=filters)
    try:
        pdf, file_name = await report_service.render_report(session, current_user, query)
    except Exception as e:
        logger.exception(f"SOC report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate the SOC report")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"', "Cache-Control": "no-store"},
    )


# ── policies ─────────────────────────────────────────────────────────────────


async def _check_scope(customer_code: Optional[str], user: User, session: AsyncSession) -> None:
    if customer_code is not None:
        await customer_access_handler.enforce_customer_access(user, customer_code, session)


@soc_management_router.get(
    "/policies",
    response_model=PolicyResponse,
    description="The SLA targets of a scope (global when no customer), each labelled with its source",
    dependencies=[_SOC],
)
async def get_policy(
    customer_code: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await _check_scope(customer_code, current_user, session)
    return PolicyResponse(policy=await policy_service.get_matrix(session, customer_code))


@soc_management_router.get(
    "/policies/overrides",
    response_model=PolicyOverridesResponse,
    description="Customers whose SLA overrides the global policy",
    dependencies=[_SOC],
)
async def get_policy_overrides(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyOverridesResponse:
    accessible = await customer_access_handler.get_user_accessible_customers(current_user, session)
    codes = None if "*" in accessible else accessible
    return PolicyOverridesResponse(overrides=await policy_service.list_overrides(session, codes))


@soc_management_router.put(
    "/policies",
    response_model=PolicyResponse,
    description="Replace a scope's SLA targets; optionally re-target items still open",
    dependencies=[_ADMIN],
)
async def put_policy(
    body: PolicyUpdateRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await _check_scope(body.customer_code, current_user, session)
    try:
        matrix = await policy_service.replace_scope(session, body.customer_code, body.cells, current_user.username)
        retargeted = await retarget_open(session, body.customer_code) if body.apply_to_open else 0
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"Failed to save the SLA policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to save the SLA policy")
    scope = f"customer {body.customer_code}" if body.customer_code else "the global policy"
    message = f"Saved {scope}" + (f"; {retargeted} open item(s) re-targeted" if body.apply_to_open else "")
    return PolicyResponse(message=message, policy=matrix, retargeted=retargeted)


@soc_management_router.delete(
    "/policies/{customer_code}",
    response_model=PolicyResponse,
    description="Remove a customer's overrides so it follows the global policy again",
    dependencies=[_ADMIN],
)
async def delete_policy_override(
    customer_code: str,
    apply_to_open: bool = Query(False),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyResponse:
    await _check_scope(customer_code, current_user, session)
    try:
        removed = await policy_service.clear_scope(session, customer_code)
        retargeted = await retarget_open(session, customer_code) if apply_to_open else 0
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"Failed to remove the SLA overrides of {customer_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove the SLA overrides")
    return PolicyResponse(
        message=f"Removed {removed} override(s); {customer_code} now follows the global policy",
        policy=await policy_service.get_matrix(session, customer_code),
        retargeted=retargeted,
    )


# ── business-hours calendars ─────────────────────────────────────────────────


async def _calendar_response(session: AsyncSession, user: User, customer_code: Optional[str], message: str = "", retargeted: int = 0):
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    codes = None if "*" in accessible else accessible
    return CalendarResponse(
        message=message,
        calendar=await calendar_service.get_calendar(session, customer_code),
        customers_with_calendar=await calendar_service.customers_with_calendar(session, codes),
        retargeted=retargeted,
    )


@soc_management_router.get(
    "/calendars",
    response_model=CalendarResponse,
    description="The business-hours calendar a scope runs on (global when no customer), labelled with its source",
    dependencies=[_SOC],
)
async def get_calendar(
    customer_code: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    await _check_scope(customer_code, current_user, session)
    return await _calendar_response(session, current_user, customer_code)


@soc_management_router.put(
    "/calendars",
    response_model=CalendarResponse,
    description="Replace a scope's business-hours calendar; optionally re-target open business-hours items",
    dependencies=[_ADMIN],
)
async def put_calendar(
    body: CalendarIn,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    await _check_scope(body.customer_code, current_user, session)
    try:
        await calendar_service.replace_calendar(session, body, current_user.username)
        retargeted = await retarget_open(session, body.customer_code) if body.apply_to_open else 0
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"Failed to save the business-hours calendar: {e}")
        raise HTTPException(status_code=500, detail="Failed to save the business-hours calendar")
    scope = f"customer {body.customer_code}" if body.customer_code else "the global calendar"
    message = f"Saved {scope}" + (f"; {retargeted} open item(s) re-targeted" if body.apply_to_open else "")
    return await _calendar_response(session, current_user, body.customer_code, message, retargeted)


@soc_management_router.delete(
    "/calendars/{customer_code}",
    response_model=CalendarResponse,
    description="Remove a customer's calendar so it follows the global one again",
    dependencies=[_ADMIN],
)
async def delete_calendar(
    customer_code: str,
    apply_to_open: bool = Query(False),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    await _check_scope(customer_code, current_user, session)
    try:
        removed = await calendar_service.clear_calendar(session, customer_code)
        retargeted = await retarget_open(session, customer_code) if apply_to_open else 0
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.exception(f"Failed to remove the calendar of {customer_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove the business-hours calendar")
    message = f"{customer_code} now follows the global calendar" if removed else f"{customer_code} had no calendar of its own"
    return await _calendar_response(session, current_user, customer_code, message, retargeted)
