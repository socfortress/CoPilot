import asyncio

# from fastapi import BackgroundTasks
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.dfir_iris.services.cases import collect_agent_soc_cases
from app.agents.schema.agents import AgentModifyResponse
from app.agents.schema.agents import AgentsResponse
from app.agents.schema.agents import OutdatedVelociraptorAgentsResponse
from app.agents.schema.agents import OutdatedWazuhAgentsResponse
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.services.status import get_outdated_agents_velociraptor
from app.agents.services.status import get_outdated_agents_wazuh
from app.agents.services.sync import sync_agents
from app.agents.velociraptor.services.agents import delete_agent_velociraptor
from app.agents.wazuh.schema.agents import WazuhAgentScaPolicyResultsResponse
from app.agents.wazuh.schema.agents import WazuhAgentScaResponse
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.agents.wazuh.services.agents import delete_agent_wazuh
from app.agents.wazuh.services.sca import collect_agent_sca
from app.agents.wazuh.services.sca import collect_agent_sca_policy_results
from app.agents.wazuh.services.vulnerabilities import collect_agent_vulnerabilities

# App specific imports
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_db

# App specific imports
# from app.db.db_session import session
from app.db.universal_models import Agents

agents_router = APIRouter()


async def fetch_velociraptor_id(db: AsyncSession, agent_id: str) -> str:
    """
    Fetches the velociraptor ID of an agent from the database.

    Args:
        db (AsyncSession): The database session.
        agent_id (str): The ID of the agent.

    Returns:
        str: The velociraptor ID of the agent.

    Raises:
        HTTPException: If the agent is not found in the database.
        HTTPException: If there is an error fetching the agent from the database.
    """
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return agent.velociraptor_id
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except Exception as e:
        logger.error(f"Failed to fetch agent {agent_id} from database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent {agent_id} from database: {e}",
        )


async def delete_agent_from_database(db: AsyncSession, agent_id: str):
    """
    Delete an agent from the database.

    Args:
        db (AsyncSession): The async database session.
        agent_id (str): The ID of the agent to be deleted.

    Raises:
        HTTPException: If there is an error deleting the agent from the database.

    """
    try:
        await db.execute(delete(Agents).filter(Agents.agent_id == agent_id))
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id} from database: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete agent {agent_id} from database: {e}",
        )


@agents_router.get(
    "",
    response_model=AgentsResponse,
    description="Get all agents currently synced to the database",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agents(db: AsyncSession = Depends(get_db)) -> AgentsResponse:
    """
    Retrieve all agents currently synced to the database.

    Returns:
        AgentsResponse: The response containing the list of agents, success status, and message.

    Raises:
        HTTPException: If there is an error while fetching the agents.
    """
    logger.info("Fetching all agents")
    try:
        result = await db.execute(select(Agents))
        agents = result.scalars().all()
        return AgentsResponse(
            agents=agents,
            success=True,
            message="Agents fetched successfully",
        )
    except Exception as e:
        logger.error(f"Failed to fetch agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {e}")


@agents_router.get(
    "/{agent_id}",
    response_model=AgentsResponse,
    description="Get agent by agent_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentsResponse:
    """
    Retrieve an agent by agent_id.

    Args:
        agent_id (str): The ID of the agent to retrieve.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentsResponse: The response containing the agent information.

    Raises:
        HTTPException: If the agent with the specified agent_id is not found or if there is an error fetching the agent.
    """
    logger.info(f"Fetching agent with agent_id: {agent_id}")
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(
                agents=[agent],
                success=True,
                message="Agent fetched successfully",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )
    except Exception as e:
        logger.error(
            f"Failed to fetch agent: {agent_id} with error {e}. Does it exist?",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent: {agent_id}. Does it exist?",
        )


@agents_router.get(
    "/hostname/{hostname}",
    response_model=AgentsResponse,
    description="Get agent by hostname",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_by_hostname(
    hostname: str,
    db: AsyncSession = Depends(get_db),
) -> AgentsResponse:
    """
    Retrieve an agent by its hostname.

    Args:
        hostname (str): The hostname of the agent.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentsResponse: The response containing the agent information.

    Raises:
        HTTPException: If the agent with the specified hostname is not found or if there is an error fetching the agent.
    """
    logger.info(f"Fetching agent with hostname: {hostname}")
    try:
        result = await db.execute(select(Agents).filter(Agents.hostname == hostname))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(
                agents=[agent],
                success=True,
                message="Agent fetched successfully",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with hostname {hostname} not found",
            )
    except Exception as e:
        logger.error(f"Failed to fetch agent: {e}")
        # The exception message should not be exposed directly, especially in production
        raise HTTPException(status_code=500, detail="Failed to fetch agent")


@agents_router.post(
    "/sync",
    response_model=SyncedAgentsResponse,
    description="Sync agents from Wazuh Manager",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst", "scheduler")),
    ],
)
async def sync_all_agents(
    # backgroud_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> SyncedAgentsResponse:
    """
    Sync all agents from Wazuh Manager.

    This endpoint triggers the synchronization of all agents from the Wazuh Manager.
    It requires authentication with any of the following scopes: "admin", "analyst", "scheduler".

    Parameters:
    - backgroud_tasks (BackgroundTasks): The background tasks object used to add the sync_agents task.
    - session (AsyncSession, optional): The async session object used to interact with the database. Defaults to Depends(get_db).

    Returns:
    - SyncedAgentsResponse: The response model indicating the success of the sync operation.

    """
    logger.info("Syncing agents from Wazuh Manager")
    # backgroud_tasks.add_task(sync_agents, session)
    loop = asyncio.get_event_loop()
    loop.create_task(sync_agents(session=session))
    return SyncedAgentsResponse(
        success=True,
        message="Agents synced started successfully",
    )


@agents_router.post(
    "/{agent_id}/critical",
    response_model=AgentModifyResponse,
    description="Mark agent as critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_critical(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Marks the specified agent as critical.

    Args:
        agent_id (str): The ID of the agent to mark as critical.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of marking the agent as critical.
    """
    logger.info(f"Marking agent {agent_id} as critical")
    try:
        # Asynchronously fetch the agent by id
        result = await session.execute(
            select(Agents).filter(Agents.agent_id == agent_id),
        )
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )

        agent.critical_asset = True
        await session.commit()

        return AgentModifyResponse(
            success=True,
            message=f"Agent {agent_id} marked as critical: {True}",
        )
    except Exception as e:
        session.rollback()  # Roll back the session in case of error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark agent as critical: {str(e)}",
        )


@agents_router.post(
    "/{agent_id}/noncritical",
    response_model=AgentModifyResponse,
    description="Mark agent as not critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_not_critical(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Marks the specified agent as not critical.

    Args:
        agent_id (str): The ID of the agent to mark as not critical.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the operation.

    Raises:
        HTTPException: If the agent with the specified ID is not found or if there is an error marking the agent as not critical.
    """
    logger.info(f"Marking agent {agent_id} as not critical")
    try:
        result = await session.execute(
            select(Agents).filter(Agents.agent_id == agent_id),
        )
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )

        agent.critical_asset = False
        await session.commit()

        return AgentModifyResponse(
            success=True,
            message=f"Agent {agent_id} marked as not critical",
        )
    except Exception as e:
        await session.rollback()  # Roll back the session in case of error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark agent as not critical: {str(e)}",
        )


@agents_router.get(
    "/{agent_id}/vulnerabilities",
    response_model=WazuhAgentVulnerabilitiesResponse,
    description="Get agent vulnerabilities",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_vulnerabilities(agent_id: str) -> WazuhAgentVulnerabilitiesResponse:
    """
    Fetches the vulnerabilities of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentVulnerabilitiesResponse: The response containing the agent vulnerabilities.
    """
    logger.info(f"Fetching agent {agent_id} vulnerabilities")
    return await collect_agent_vulnerabilities(agent_id)


@agents_router.get(
    "/{agent_id}/sca",
    response_model=WazuhAgentScaResponse,
    description="Get agent sca results",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_sca(agent_id: str) -> WazuhAgentScaResponse:
    """
    Fetches the sca results of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentScaResponse: The response containing the agent sca.
    """
    logger.info(f"Fetching agent {agent_id} sca")
    return await collect_agent_sca(agent_id)


@agents_router.get(
    "/{agent_id}/sca/{policy_id}",
    response_model=WazuhAgentScaPolicyResultsResponse,
    description="Get agent sca results",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_sca_policy_results(agent_id: str, policy_id: str) -> WazuhAgentScaPolicyResultsResponse:
    """
    Fetches the sca results of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentScaPolicyResultsResponse: The response containing the agent sca.
    """
    logger.info(f"Fetching agent {agent_id} sca policy results")
    return await collect_agent_sca_policy_results(agent_id, policy_id)


@agents_router.get(
    "/{agent_id}/soc_cases",
    # response_model=SocCasesResponse,
    description="Get SOC cases for agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_soc_cases(agent_id: str, session: AsyncSession = Depends(get_db)):
    """
    Fetches the SOC cases of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        SocCasesResponse: The response containing the agent SOC cases.
    """
    logger.info(f"Fetching agent {agent_id} SOC cases")
    return await collect_agent_soc_cases(agent_id, session)


@agents_router.get(
    "/wazuh/outdated",
    response_model=OutdatedWazuhAgentsResponse,
    description="Get all outdated Wazuh agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_wazuh_agents(
    session: AsyncSession = Depends(get_db),
) -> OutdatedWazuhAgentsResponse:
    """
    Retrieve all outdated Wazuh agents.

    This endpoint requires the user to have either the "admin" or "analyst" scope.

    Returns:
        OutdatedWazuhAgentsResponse: The response containing the outdated Wazuh agents.
    """
    logger.info("Fetching all outdated Wazuh agents")
    return await get_outdated_agents_wazuh(session)


@agents_router.get(
    "/velociraptor/outdated",
    response_model=OutdatedVelociraptorAgentsResponse,
    description="Get all outdated Velociraptor agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_velociraptor_agents(
    session: AsyncSession = Depends(get_db),
) -> OutdatedVelociraptorAgentsResponse:
    """
    Fetches all outdated Velociraptor agents.

    Parameters:
    - session: The database session.

    Returns:
    - OutdatedVelociraptorAgentsResponse: The response containing the outdated Velociraptor agents.
    """
    logger.info("Fetching all outdated Velociraptor agents")
    return await get_outdated_agents_velociraptor(session)


# ! TODO: FINISH THIS
@agents_router.delete(
    "/{agent_id}/delete",
    response_model=AgentModifyResponse,
    description="Delete agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Delete an agent.

    Args:
        agent_id (str): The ID of the agent to be deleted.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the deletion.
    """
    logger.info(f"Deleting agent {agent_id}")
    await delete_agent_wazuh(agent_id)
    client_id = await fetch_velociraptor_id(db=session, agent_id=agent_id)
    logger.info(f"Client ID: {client_id}")
    if client_id != "Unknown":
        await delete_agent_velociraptor(client_id)
    await delete_agent_from_database(db=session, agent_id=agent_id)
    return AgentModifyResponse(
        success=True,
        message=f"Agent {agent_id} deleted successfully",
    )


# ! TODO: CURRENTLY UPDATES IN THE DB BUT NEED TO UPDATE IN WAZUH # !
# @agents_router.put(
#     "/{agent_id}/update-customer-code",
#     response_model=AgentUpdateCustomerCodeResponse,
#     description="Update `agent` customer code",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def update_agent_customer_code(agent_id: str, body: AgentUpdateCustomerCodeBody, db: AsyncSession = Depends(get_db)) -> AgentUpdateCustomerCodeResponse:
#     logger.info(f"Updating agent {agent_id} customer code to {body.customer_code}")
#     try:
#         result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
#         agent = result.scalars().first()
#         if not agent:
#             raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
#         agent.customer_code = body.customer_code
#         await db.commit()
#         logger.info(f"Agent {agent_id} customer code updated to {body.customer_code}")
#         return {"success": True, "message": f"Agent {agent_id} customer code updated to {body.customer_code}"}
#     except Exception as e:
#         if not agent:
#             raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
