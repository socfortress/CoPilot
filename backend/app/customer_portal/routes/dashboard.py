from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.dashboard import CustomerDashboardAlertStatsResponse
from app.customer_portal.schema.dashboard import CustomerDashboardCaseStatsResponse
from app.customer_portal.schema.dashboard import CustomerDashboardStatsResponse
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.incidents.services.db_operations import alert_total_for_user
from app.incidents.services.db_operations import alerts_closed_for_user
from app.incidents.services.db_operations import alerts_in_progress_for_user
from app.incidents.services.db_operations import alerts_open_for_user
from app.incidents.services.db_operations import case_total_for_user
from app.incidents.services.db_operations import cases_closed_for_user
from app.incidents.services.db_operations import cases_in_progress_for_user
from app.incidents.services.db_operations import cases_open_for_user
from app.middleware.customer_access import customer_access_handler

customer_portal_dashboard_router = APIRouter()

# The dashboard stat endpoints delegate to the same ``*_for_user`` helpers that the
# alerts/cases *list* endpoints use, so the counts shown always match the rows the
# user can actually see. This matters because alert visibility is additionally gated
# by tag-based RBAC (see app/incidents/middleware/tag_access.py): counting alerts by
# customer_code alone would report totals the user isn't entitled to view.


@customer_portal_dashboard_router.get(
    "/dashboard/stats",
    response_model=CustomerDashboardStatsResponse,
)
async def get_customer_dashboard_stats(
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of customer codes to scope the stats to"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get total alerts, cases, and agents for the logged-in customer."""
    accessible_customers = await customer_access_handler.resolve_effective_customers(current_user, customer_codes, db)
    logger.info(f"Fetching dashboard stats for user {current_user.username}, customers: {accessible_customers}")

    # Alerts/cases via the tag- and customer-aware helpers so totals match the lists.
    total_alerts = await alert_total_for_user(current_user, db, customer_codes=customer_codes)
    total_cases = await case_total_for_user(current_user, db, customer_codes=customer_codes)

    # Agents are not tag-scoped, so a plain customer-scoped count is correct here.
    if "*" in accessible_customers:
        agent_count_q = select(func.count(Agents.id))
    else:
        agent_count_q = select(func.count(Agents.id)).where(Agents.customer_code.in_(accessible_customers))
    total_agents = (await db.execute(agent_count_q)).scalar_one()

    return CustomerDashboardStatsResponse(
        total_alerts=total_alerts,
        total_cases=total_cases,
        total_agents=total_agents,
        success=True,
        message="Dashboard stats retrieved successfully",
    )


@customer_portal_dashboard_router.get(
    "/dashboard/alert-stats",
    response_model=CustomerDashboardAlertStatsResponse,
)
async def get_customer_dashboard_alert_stats(
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of customer codes to scope the stats to"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alert counts (total, open, in-progress, closed) for the logged-in customer."""
    logger.info(f"Fetching dashboard alert stats for user {current_user.username}")

    # Same tag- and customer-aware helpers the /alerts list uses, so the counts
    # never diverge from what the user sees in the list.
    total = await alert_total_for_user(current_user, db, customer_codes=customer_codes)
    open_count = await alerts_open_for_user(current_user, db, customer_codes=customer_codes)
    in_progress_count = await alerts_in_progress_for_user(current_user, db, customer_codes=customer_codes)
    closed_count = await alerts_closed_for_user(current_user, db, customer_codes=customer_codes)

    return CustomerDashboardAlertStatsResponse(
        total=total,
        open=open_count,
        in_progress=in_progress_count,
        closed=closed_count,
        success=True,
        message="Dashboard alert stats retrieved successfully",
    )


@customer_portal_dashboard_router.get(
    "/dashboard/case-stats",
    response_model=CustomerDashboardCaseStatsResponse,
)
async def get_customer_dashboard_case_stats(
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of customer codes to scope the stats to"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get case counts (total, open, in-progress, closed) for the logged-in customer."""
    logger.info(f"Fetching dashboard case stats for user {current_user.username}")

    # Same customer-aware helpers the /cases list uses (cases are not tag-scoped).
    total = await case_total_for_user(current_user, db, customer_codes=customer_codes)
    open_count = await cases_open_for_user(current_user, db, customer_codes=customer_codes)
    in_progress_count = await cases_in_progress_for_user(current_user, db, customer_codes=customer_codes)
    closed_count = await cases_closed_for_user(current_user, db, customer_codes=customer_codes)

    return CustomerDashboardCaseStatsResponse(
        total=total,
        open=open_count,
        in_progress=in_progress_count,
        closed=closed_count,
        success=True,
        message="Dashboard case stats retrieved successfully",
    )
