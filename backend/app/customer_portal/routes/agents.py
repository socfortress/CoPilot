from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Response
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_portal.schema.agents import PortalAgentsResponse
from app.customer_portal.services.agents import AgentFilters
from app.customer_portal.services.agents import export_portal_agents_csv
from app.customer_portal.services.agents import list_portal_agents
from app.db.db_session import get_db
from app.middleware.customer_query import customer_codes_query
from app.time_utils import now_utc

customer_portal_agents_router = APIRouter()

MAX_PAGE_SIZE = 100


def agent_filters(
    search: Optional[str] = Query(None, description="Case-insensitive match on hostname, IP address or agent id"),
    status: Optional[str] = Query(None, description="Wazuh agent status, e.g. active"),
    os: Optional[str] = Query(None, description="Operating system, as reported by the agent"),
    critical: bool = Query(False, description="Only critical assets"),
) -> AgentFilters:
    return AgentFilters(search=search or None, status=status or None, os=os or None, critical=critical)


# NOTE: the static /agents/export must stay above any /agents/{...} route added later.
@customer_portal_agents_router.get(
    "/agents/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
    description="Every agent matching the filters, as CSV",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def export_agents(
    filters: AgentFilters = Depends(agent_filters),
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    content = await export_portal_agents_csv(current_user, db, filters, customer_codes)
    stamp = now_utc().strftime("%Y-%m-%d-%H-%M-%S")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="assets-export-{stamp}.csv"'},
    )


@customer_portal_agents_router.get(
    "/agents",
    response_model=PortalAgentsResponse,
    description="One page of the agents the user can see, filtered, with the page's cards and filter options",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_agents_page(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=MAX_PAGE_SIZE),
    filters: AgentFilters = Depends(agent_filters),
    customer_codes: Optional[List[str]] = Depends(customer_codes_query),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortalAgentsResponse:
    logger.info(f"Fetching portal agents page {page} for user {current_user.username}")
    result = await list_portal_agents(current_user, db, filters, page, page_size, customer_codes)
    return PortalAgentsResponse(
        agents=result.agents,
        total=result.total,
        stats=result.stats,
        statuses=result.statuses,
        os_list=result.os_list,
        success=True,
        message=f"{result.total} agents found",
    )
