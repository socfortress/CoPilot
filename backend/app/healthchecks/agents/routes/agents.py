from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.healthchecks.agents.schema.agents import AgentHealthCheckResponse
from app.healthchecks.agents.schema.agents import HostLogsSearchBody
from app.healthchecks.agents.schema.agents import HostLogsSearchResponse
from app.healthchecks.agents.schema.agents import TimeCriteriaModel
from app.healthchecks.agents.services.agents import host_logs
from app.healthchecks.agents.services.agents import velociraptor_agent_healthcheck
from app.healthchecks.agents.services.agents import velociraptor_agents_healthcheck
from app.healthchecks.agents.services.agents import wazuh_agent_healthcheck
from app.healthchecks.agents.services.agents import wazuh_agents_healthcheck

healtcheck_agents_router = APIRouter()


@healtcheck_agents_router.get(
    "/wazuh",
    response_model=AgentHealthCheckResponse,
    description="Get Wazuh agents healthcheck",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_wazuh_agent_healthcheck(
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Get the healthcheck of Wazuh agents based on the specified time criteria.

    Args:
        session (AsyncSession): The asynchronous database session.
        minutes (int): Number of minutes within which the agent should have been last seen to be considered healthy. Default is 60.
        hours (int): Number of hours within which the agent should have been last seen to be considered healthy. Default is 0.
        days (int): Number of days within which the agent should have been last seen to be considered healthy. Default is 0.

    Returns:
        AgentHealthCheckResponse: The response containing the healthcheck information of Wazuh agents.
    """
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)

    # Asynchronously fetch all agents
    result = await session.execute(select(Agents))
    agents = result.scalars().all()
    return await wazuh_agents_healthcheck(agents, time_criteria)


@healtcheck_agents_router.get(
    "/wazuh/{agent_id}",
    response_model=AgentHealthCheckResponse,
    description="Get Wazuh agent healthcheck by agent_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_wazuh_agent_healthcheck_by_agent_id(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Get the healthcheck of a Wazuh agent by agent_id.

    Args:
        agent_id (str): The ID of the agent.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).
        minutes (int, optional): Number of minutes within which the agent should have been last seen to be considered healthy. Defaults to 60.
        hours (int, optional): Number of hours within which the agent should have been last seen to be considered healthy. Defaults to 0.
        days (int, optional): Number of days within which the agent should have been last seen to be considered healthy. Defaults to 0.

    Returns:
        AgentHealthCheckResponse: The healthcheck response for the agent.

    Raises:
        HTTPException: If the agent with the specified agent_id is not found.
    """
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)

    # Asynchronously fetch the agent by id
    result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with agent_id {agent_id} not found",
        )
    return await wazuh_agent_healthcheck(agent, time_criteria)


@healtcheck_agents_router.get(
    "/velociraptor",
    response_model=AgentHealthCheckResponse,
    description="Get Velociraptor agents healthcheck",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_velociraptor_agent_healthcheck(
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Get Velociraptor agents healthcheck.

    Args:
        session (AsyncSession): The async session object.
        minutes (int): Number of minutes within which the agent should have been last seen to be considered healthy. Default is 60.
        hours (int): Number of hours within which the agent should have been last seen to be considered healthy. Default is 0.
        days (int): Number of days within which the agent should have been last seen to be considered healthy. Default is 0.

    Returns:
        AgentHealthCheckResponse: The response model containing the healthcheck results.
    """
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)

    # Asynchronously fetch all agents
    result = await session.execute(select(Agents))
    agents = result.scalars().all()
    return await velociraptor_agents_healthcheck(agents, time_criteria)


@healtcheck_agents_router.get(
    "/velociraptor/{agent_id}",
    response_model=AgentHealthCheckResponse,
    description="Get Velociraptor agent healthcheck by agent_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_velociraptor_agent_healthcheck_by_agent_id(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Get Velociraptor agent healthcheck by agent_id.

    Args:
        agent_id (str): The ID of the agent.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).
        minutes (int, optional): Number of minutes within which the agent should have been last seen to be considered healthy. Defaults to 60.
        hours (int, optional): Number of hours within which the agent should have been last seen to be considered healthy. Defaults to 0.
        days (int, optional): Number of days within which the agent should have been last seen to be considered healthy. Defaults to 0.

    Returns:
        AgentHealthCheckResponse: The agent health check response.
    """
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)

    # Asynchronously fetch the agent by id
    result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with agent_id {agent_id} not found",
        )
    return await velociraptor_agent_healthcheck(agent, time_criteria)


@healtcheck_agents_router.post(
    "/logs",
    response_model=HostLogsSearchResponse,
    description="Get host logs",
    dependencies=[
        Security(AuthHandler().get_current_user, scopes=["admin", "analyst"]),
    ],
)
async def get_host_logs(
    body: HostLogsSearchBody,
    session: AsyncSession = Depends(get_db),
) -> HostLogsSearchResponse:
    """
    Get host logs for a specific agent.

    Args:
        body (HostLogsSearchBody): The search criteria for host logs.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        HostLogsSearchResponse: The response containing the host logs.

    Raises:
        HTTPException: If the agent with the specified hostname is not found.
    """
    logger.info(f"Received request to get host logs for {body.agent_name}")

    # Asynchronously verify the agent exists
    result = await session.execute(
        select(Agents).filter(Agents.hostname == body.agent_name),
    )
    agent = result.scalars().first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent with hostname {body.agent_name} not found",
        )
    return await host_logs(body)
