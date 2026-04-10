from fastapi import APIRouter
from fastapi import Depends
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
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
