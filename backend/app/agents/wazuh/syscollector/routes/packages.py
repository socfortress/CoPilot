from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.wazuh.syscollector.schema.packages import AgentPackagesResponse
from app.agents.wazuh.syscollector.services.packages import collect_agent_packages
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.middleware.customer_access import customer_access_handler

packages_router = APIRouter()


@packages_router.get(
    "/{agent_id}/packages",
    response_model=AgentPackagesResponse,
    description="Get installed packages for a specific agent from the Wazuh Manager syscollector",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_agent_packages(
    agent_id: str,
    limit: int = Query(500, ge=1, le=100000, description="Maximum number of packages to return"),
    offset: int = Query(0, ge=0, description="First element to return"),
    sort: Optional[str] = Query(None, description="Sort by field(s). Use +/- prefix for asc/desc order"),
    search: Optional[str] = Query(None, description="Free-text search string"),
    select: Optional[List[str]] = Query(None, description="Fields to return"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    name: Optional[str] = Query(None, description="Filter by package name"),
    architecture: Optional[str] = Query(None, description="Filter by architecture"),
    format: Optional[str] = Query(None, alias="format", description="Filter by package format (e.g. deb, rpm)"),
    version: Optional[str] = Query(None, description="Filter by package version"),
    q: Optional[str] = Query(None, description="Advanced query filter (e.g. q=\"name=openssl\")"),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentPackagesResponse:
    """
    Fetch installed packages for a specific agent via the Wazuh Manager
    syscollector API.

    Returns package name, version, architecture, vendor, format, and other
    metadata for every installed package on the agent.
    """
    logger.info(f"Fetching packages for agent {agent_id}")

    # Verify the user has access to this agent's customer
    base_query = sa_select(Agents).filter(Agents.agent_id == agent_id)
    filtered_query = await customer_access_handler.filter_query_by_customer_access(
        current_user, session, base_query, Agents.customer_code,
    )
    result = await session.execute(filtered_query)
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with agent_id {agent_id} not found or access denied",
        )

    return await collect_agent_packages(
        agent_id=agent_id,
        limit=limit,
        offset=offset,
        sort=sort,
        search=search,
        select=select,
        vendor=vendor,
        name=name,
        architecture=architecture,
        format=format,
        version=version,
        q=q,
    )
