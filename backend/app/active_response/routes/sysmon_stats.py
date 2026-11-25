"""The weekly Sysmon noise statistics sent to SOCFortress (services/sysmon_stats/): status, per-customer sharing, the
preview and Send now. Admin only. Mounted at /api/sysmon_config/stats, before the Sysmon config router, whose
/{customer_code} route would otherwise take "stats" for a customer code."""
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_stats import StatsPreviewResponse
from app.active_response.schema.sysmon_stats import StatsRunResponse
from app.active_response.schema.sysmon_stats import StatsSharingRequest
from app.active_response.schema.sysmon_stats import StatsSharingResponse
from app.active_response.schema.sysmon_stats import StatsStatusResponse
from app.active_response.services.sysmon_stats import runner
from app.active_response.services.sysmon_stats import settings
from app.active_response.services.sysmon_stats.sharing import set_sharing
from app.active_response.services.sysmon_stats.status import get_status
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

sysmon_stats_router = APIRouter()

RUNNING_DETAIL = "A noise statistics run or preview is already in progress on this CoPilot; try again in a minute"


@sysmon_stats_router.get(
    "",
    response_model=StatsStatusResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_sysmon_stats_status(session: AsyncSession = Depends(get_db)):
    """The noise statistics' mode, SOCFortress's state, the last run, and per customer its sharing, pseudonym and reports.
    Reads the database and MinIO only."""
    status = await get_status(session)
    return StatsStatusResponse(success=True, message="Retrieved the Sysmon noise statistics status", status=status)


@sysmon_stats_router.put(
    "/customers/{customer_code}",
    response_model=StatsSharingResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)],
)
async def put_sysmon_stats_customer(
    customer_code: str,
    body: StatsSharingRequest,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Turn a customer's noise statistics off or on, and set its redaction hints. Turning it off asks SOCFortress to
    delete the customer's reports (now when possible, else with the next run)."""
    withdraw = await set_sharing(session, customer_code, body, actor=current_user, request=request)
    status = await get_status(session)
    customer = next((c for c in status.customers if c.customer_code == customer_code), None)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    state = "on" if body.sharing else "off"
    message = f"Noise statistics {state} for {customer_code}."
    if withdraw is not None:
        message = f"{message} {withdraw.message}"
    return StatsSharingResponse(success=True, message=message, customer=customer, withdraw=withdraw)


@sysmon_stats_router.post(
    "/customers/{customer_code}/preview",
    response_model=StatsPreviewResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)],
)
async def preview_sysmon_stats(
    customer_code: str,
    week: Optional[str] = Query(None, description="YYYY-Www: the previous complete ISO week (default) or the one before."),
    session: AsyncSession = Depends(get_db),
):
    """Build the customer's report exactly as it would be sent, from the indexer, and return it. Sends nothing and writes
    no state."""
    if week is not None and week not in runner.accepted_weeks(runner._now()):
        raise HTTPException(status_code=400, detail="week must be one of the two weeks SOCFortress accepts (YYYY-Www)")
    if not settings.sharing_on():
        raise HTTPException(status_code=409, detail="Noise statistics are off on this CoPilot (SYSMON_STATS_SHARING)")
    if runner.running():
        raise HTTPException(status_code=409, detail=RUNNING_DETAIL)
    from app.active_response.services.sysmon_stats.runner import read_customers

    customers = await read_customers(session)
    await runner._end(session)
    if customer_code not in customers:
        raise HTTPException(status_code=404, detail="Customer not found")
    preview = await runner.preview(session, customer_code, week)
    return StatsPreviewResponse(success=True, message=preview.message or "Nothing was sent.", preview=preview)


@sysmon_stats_router.post(
    "/send-now",
    response_model=StatsRunResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def send_sysmon_stats_now(
    request: Request,
    customer_code: Optional[str] = Query(None, description="Only this customer."),
    resume: bool = Query(False, description="Lift the pause set after SOCFortress refused a report for its content."),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Send the due reports now, the way the scheduled run does but without waiting for each customer's send time. A week
    already done for a customer is not sent again."""
    if runner.running():
        raise HTTPException(status_code=409, detail=RUNNING_DETAIL)
    result = await runner.run_tick(
        session,
        actor=current_user,
        request=request,
        customer_code=customer_code,
        ignore_jitter=True,
        resume=resume,
    )
    if result.outcome.value == "locked":
        raise HTTPException(status_code=409, detail="Another CoPilot replica is sending noise statistics right now; try again in a minute")
    status = await get_status(session)
    return StatsRunResponse(success=True, message=result.message, result=result, status=status)
