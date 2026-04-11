from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.dashboard import CustomerDashboardAlertStatsResponse
from app.customer_portal.schema.dashboard import CustomerDashboardStatsResponse
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.incidents.models import Alert
from app.incidents.models import Case
from app.middleware.customer_access import customer_access_handler

customer_portal_dashboard_router = APIRouter()


@customer_portal_dashboard_router.get(
    "/dashboard/stats",
    response_model=CustomerDashboardStatsResponse,
)
async def get_customer_dashboard_stats(
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get total alerts, cases, and agents for the logged-in customer."""
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)
    logger.info(f"Fetching dashboard stats for user {current_user.username}, customers: {accessible_customers}")

    if "*" in accessible_customers:
        alert_count_q = select(func.count(Alert.id))
        case_count_q = select(func.count(Case.id))
        agent_count_q = select(func.count(Agents.id))
    else:
        alert_count_q = select(func.count(Alert.id)).where(Alert.customer_code.in_(accessible_customers))
        case_count_q = select(func.count(Case.id)).where(Case.customer_code.in_(accessible_customers))
        agent_count_q = select(func.count(Agents.id)).where(Agents.customer_code.in_(accessible_customers))

    total_alerts = (await db.execute(alert_count_q)).scalar_one()
    total_cases = (await db.execute(case_count_q)).scalar_one()
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
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alert counts (total, open, in-progress, closed) for the logged-in customer."""
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)
    logger.info(f"Fetching dashboard alert stats for user {current_user.username}, customers: {accessible_customers}")

    if "*" in accessible_customers:
        total_q = select(func.count(Alert.id))
        open_q = select(func.count(Alert.id)).where(Alert.status == "OPEN")
        in_progress_q = select(func.count(Alert.id)).where(Alert.status == "IN_PROGRESS")
        closed_q = select(func.count(Alert.id)).where(Alert.status == "CLOSED")
    else:
        customer_filter = Alert.customer_code.in_(accessible_customers)
        total_q = select(func.count(Alert.id)).where(customer_filter)
        open_q = select(func.count(Alert.id)).where(customer_filter, Alert.status == "OPEN")
        in_progress_q = select(func.count(Alert.id)).where(customer_filter, Alert.status == "IN_PROGRESS")
        closed_q = select(func.count(Alert.id)).where(customer_filter, Alert.status == "CLOSED")

    total = (await db.execute(total_q)).scalar_one()
    open_count = (await db.execute(open_q)).scalar_one()
    in_progress_count = (await db.execute(in_progress_q)).scalar_one()
    closed_count = (await db.execute(closed_q)).scalar_one()

    return CustomerDashboardAlertStatsResponse(
        total=total,
        open=open_count,
        in_progress=in_progress_count,
        closed=closed_count,
        success=True,
        message="Dashboard alert stats retrieved successfully",
    )
