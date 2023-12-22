from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.status import HTTP_401_UNAUTHORIZED

from app.agents.schema.agents import AgentModifyResponse
from app.agents.schema.agents import AgentsResponse
from app.agents.schema.agents import AgentUpdateCustomerCodeBody
from app.agents.schema.agents import AgentUpdateCustomerCodeResponse
from app.agents.schema.agents import OutdatedVelociraptorAgentsResponse
from app.agents.schema.agents import OutdatedWazuhAgentsResponse
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.services.status import get_outdated_agents_velociraptor
from app.agents.services.status import get_outdated_agents_wazuh
from app.agents.services.sync import sync_agents
from app.agents.velociraptor.services.agents import delete_agent_velociraptor
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.agents.wazuh.services.agents import delete_agent_wazuh
from app.agents.wazuh.services.vulnerabilities import collect_agent_vulnerabilities

# App specific imports
from app.auth.routes.auth import AuthHandler
from app.db.db_session import get_session, get_db

# App specific imports
# from app.db.db_session import session
from app.db.universal_models import Agents

agents_router = APIRouter()

# ! OLD
# def fetch_velociraptor_id(agent_id: str) -> str:
#     try:
#         return session.query(Agents).filter(Agents.agent_id == agent_id).first().velociraptor_id
#     except Exception as e:
#         logger.error(f"Failed to fetch agent {agent_id} from database: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to fetch agent {agent_id} from database: {e}")


# def delete_agent_from_database(agent_id: str):
#     try:
#         session.query(Agents).filter(Agents.agent_id == agent_id).delete()
#         session.commit()
#     except Exception as e:
#         logger.error(f"Failed to delete agent {agent_id} from database: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to delete agent {agent_id} from database: {e}")
async def fetch_velociraptor_id(db: AsyncSession, agent_id: str) -> str:
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return agent.velociraptor_id
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except Exception as e:
        logger.error(f"Failed to fetch agent {agent_id} from database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent {agent_id} from database: {e}")


async def delete_agent_from_database(db: AsyncSession, agent_id: str):
    try:
        await db.execute(select(Agents).filter(Agents.agent_id == agent_id).delete())
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id} from database: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete agent {agent_id} from database: {e}")


@agents_router.get(
    "",
    response_model=AgentsResponse,
    description="Get all agents currently synced to the database",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agents(db: AsyncSession = Depends(get_db)) -> AgentsResponse:
    logger.info("Fetching all agents")
    try:
        # agents = session.query(Agents).all()
        result = await db.execute(select(Agents))
        agents = result.scalars().all()
        return AgentsResponse(agents=agents, success=True, message="Agents fetched successfully")
    except Exception as e:
        logger.error(f"Failed to fetch agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {e}")


@agents_router.get(
    "/{agent_id}",
    response_model=AgentsResponse,
    description="Get agent by agent_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)) -> AgentsResponse:
    logger.info(f"Fetching agent with agent_id: {agent_id}")
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(agents=[agent], success=True, message="Agent fetched successfully")
        else:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
    except Exception as e:
        logger.error(f"Failed to fetch agent: {agent_id}. Does it exist?")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent: {agent_id}. Does it exist?")


@agents_router.get(
    "/hostname/{hostname}",
    response_model=AgentsResponse,
    description="Get agent by hostname",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_by_hostname(hostname: str, db: AsyncSession = Depends(get_db)) -> AgentsResponse:
    logger.info(f"Fetching agent with hostname: {hostname}")
    try:
        result = await db.execute(select(Agents).filter(Agents.hostname == hostname))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(agents=[agent], success=True, message="Agent fetched successfully")
        else:
            raise HTTPException(status_code=404, detail=f"Agent with hostname {hostname} not found")
    except Exception as e:
        logger.error(f"Failed to fetch agent: {e}")
        # The exception message should not be exposed directly, especially in production
        raise HTTPException(status_code=500, detail="Failed to fetch agent")


@agents_router.post(
    "/sync",
    response_model=SyncedAgentsResponse,
    description="Sync agents from Wazuh Manager",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "scheduler"))],
)
async def sync_all_agents(backgroud_tasks: BackgroundTasks, session: AsyncSession = Depends(get_db)) -> SyncedAgentsResponse:
    logger.info("Syncing agents from Wazuh Manager")
    backgroud_tasks.add_task(sync_agents, session)
    # return sync_agents()
    return SyncedAgentsResponse(success=True, message="Agents synced started successfully")


@agents_router.post(
    "/{agent_id}/critical",
    response_model=AgentModifyResponse,
    description="Mark agent as critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_critical(agent_id: str, session: AsyncSession = Depends(get_db)) -> AgentModifyResponse:
    logger.info(f"Marking agent {agent_id} as critical")
    # return mark_agent_criticality(agent_id, True)
    try:
        # Asynchronously fetch the agent by id
        result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")

        agent.critical_asset = True
        await session.commit()

        return AgentModifyResponse(success=True, message=f"Agent {agent_id} marked as critical: {True}")
    except Exception as e:
        session.rollback()  # Roll back the session in case of error
        raise HTTPException(status_code=500, detail=f"Failed to mark agent as critical: {str(e)}")


@agents_router.post(
    "/{agent_id}/noncritical",
    response_model=AgentModifyResponse,
    description="Mark agent as not critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_not_critical(agent_id: str, session: AsyncSession = Depends(get_db)) -> AgentModifyResponse:
    logger.info(f"Marking agent {agent_id} as not critical")
    try:
        # Asynchronously fetch the agent by id
        result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")

        agent.critical_asset = False
        await session.commit()

        return AgentModifyResponse(success=True, message=f"Agent {agent_id} marked as not critical")
    except Exception as e:
        await session.rollback()  # Roll back the session in case of error
        raise HTTPException(status_code=500, detail=f"Failed to mark agent as not critical: {str(e)}")


@agents_router.get(
    "/{agent_id}/vulnerabilities",
    response_model=WazuhAgentVulnerabilitiesResponse,
    description="Get agent vulnerabilities",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_vulnerabilities(agent_id: str) -> WazuhAgentVulnerabilitiesResponse:
    logger.info(f"Fetching agent {agent_id} vulnerabilities")
    return await collect_agent_vulnerabilities(agent_id)


@agents_router.get(
    "/wazuh/outdated",
    response_model=OutdatedWazuhAgentsResponse,
    description="Get all outdated Wazuh agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_wazuh_agents(session: AsyncSession = Depends(get_db)) -> OutdatedWazuhAgentsResponse:
    logger.info("Fetching all outdated Wazuh agents")
    return await get_outdated_agents_wazuh(session)


@agents_router.get(
    "/velociraptor/outdated",
    response_model=OutdatedVelociraptorAgentsResponse,
    description="Get all outdated Velociraptor agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_velociraptor_agents(session: AsyncSession = Depends(get_db)) -> OutdatedVelociraptorAgentsResponse:
    logger.info("Fetching all outdated Velociraptor agents")
    return await get_outdated_agents_velociraptor(session)


# ! TODO: FINISH THIS
# @agents_router.delete(
#     "/{agent_id}/delete",
#     response_model=AgentModifyResponse,
#     description="Delete agent",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def delete_agent(agent_id: str) -> AgentModifyResponse:
#     logger.info(f"Deleting agent {agent_id}")
#     delete_agent_wazuh(agent_id)
#     client_id = fetch_velociraptor_id(agent_id)
#     delete_agent_velociraptor(client_id)
#     delete_agent_from_database(agent_id)
#     return {"success": True, "message": f"Agent {agent_id} deleted from database, Wazuh, and Velociraptor"}


# @agents_router.put(
#     "/{agent_id}/update-customer-code",
#     response_model=AgentUpdateCustomerCodeResponse,
#     description="Update `agent` customer code",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def update_agent_customer_code(agent_id: str, body: AgentUpdateCustomerCodeBody) -> AgentUpdateCustomerCodeResponse:
#     logger.info(f"Updating agent {agent_id} customer code to {body.customer_code}")
#     try:
#         agent = session.query(Agents).filter(Agents.agent_id == agent_id).first()
#         agent.customer_code = body.customer_code
#         session.commit()
#         return {"success": True, "message": f"Agent {agent_id} customer code updated to {body.customer_code}"}
#     except Exception as e:
#         if not agent:
#             raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
