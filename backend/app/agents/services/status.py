from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.schema.agents import OutdatedVelociraptorAgentsResponse
from app.agents.schema.agents import OutdatedWazuhAgentsResponse
from app.connectors.velociraptor.utils.universal import UniversalService
from app.db.db_session import session
from app.db.universal_models import Agents


def get_agent(agent_id: str) -> List[Agents]:
    """
    Retrieves a specific agent from the database using its ID.

    Args:
        agent_id (str): The ID of the agent to retrieve.

    Returns:
        AgentMetadata: The agent object if found, otherwise None.
    """
    try:
        return session.query(Agents).filter(Agents.agent_id == agent_id).first()
    except Exception as e:
        logger.error(f"Failed to fetch agent with agent_id {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent with agent_id {agent_id}: {e}",
        )


async def get_agents_by_customer_code(customer_code: str, session: AsyncSession) -> List[Agents]:
    """
    Retrieves all agents associated with a specific customer code from the database asynchronously.

    Args:
        customer_code (str): The customer code to filter agents by.
        session (AsyncSession): The SQLAlchemy asynchronous session to use for the query.

    Returns:
        List[Agents]: A list of agents associated with the customer code.
    """
    try:
        agents_result = await session.execute(select(Agents).filter(Agents.customer_code == customer_code))
        agents = agents_result.scalars().all()

        return agents
    except Exception as e:
        logger.error(f"Failed to fetch agents with customer_code {customer_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agents with customer_code {customer_code}: {e}",
        )


async def get_agent_os_by_id(agent_id: str, session: AsyncSession) -> str:
    """
    Retrieves the operating system of a specific agent from the database using its ID.

    Args:
        agent_id (str): The ID of the agent to retrieve.
        session (AsyncSession): The SQLAlchemy asynchronous session to use for the query.

    Returns:
        str: The operating system of the agent if found, otherwise None.
    """
    try:
        agent_result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = agent_result.scalars().first()

        if agent is None:
            logger.error(f"Agent with agent_id {agent_id} not found.")
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found.",
            )

        return agent.os
    except Exception as e:
        logger.error(f"Failed to fetch agent with agent_id {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent with agent_id {agent_id}: {e}",
        )


async def get_outdated_agents_wazuh(
    session: AsyncSession,
) -> OutdatedWazuhAgentsResponse:
    """
    Retrieves all agents with outdated Wazuh agent versions from the database asynchronously.

    Args:
        session (AsyncSession): The SQLAlchemy asynchronous session to use for the query.

    Returns:
        OutdatedWazuhAgentsResponse: Response object containing the outdated agents.
    """
    try:
        wazuh_manager_result = await session.execute(
            select(Agents).filter(Agents.agent_id == "000"),
        )
        wazuh_manager = wazuh_manager_result.scalars().first()

        if wazuh_manager is None:
            logger.error("Wazuh Manager with agent_id '000' not found.")
            raise HTTPException(
                status_code=404,
                detail="Wazuh Manager with agent_id '000' not found.",
            )

        outdated_agents_result = await session.execute(
            select(Agents).filter(
                Agents.agent_id != "000",
                Agents.wazuh_agent_version != wazuh_manager.wazuh_agent_version,
            ),
        )
        outdated_wazuh_agents = outdated_agents_result.scalars().all()

        return OutdatedWazuhAgentsResponse(
            message="Outdated Wazuh agents fetched successfully.",
            success=True,
            outdated_wazuh_agents=outdated_wazuh_agents,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch outdated Wazuh agents: {e}",
        )


async def get_outdated_agents_velociraptor(
    session: AsyncSession,
) -> OutdatedVelociraptorAgentsResponse:
    """
    Retrieves all agents with outdated Velociraptor client versions from the database asynchronously.

    Args:
        session (AsyncSession): The SQLAlchemy asynchronous session to use for the query.

    Returns:
        OutdatedVelociraptorAgentsResponse: Response object containing the outdated agents.
    """
    vql_server_version = "select * from config"
    velociraptor_service = await UniversalService().create("Velociraptor")

    try:
        # Assuming _get_server_version is an async function
        server_version = await velociraptor_service._get_server_version(
            vql_server_version,
        )
        agents_result = await session.execute(select(Agents))
        agents = agents_result.scalars().all()
        outdated_velociraptor_agents = [agent for agent in agents if agent.velociraptor_agent_version != server_version]

        return OutdatedVelociraptorAgentsResponse(
            message="Outdated Velociraptor agents fetched successfully.",
            success=True,
            outdated_velociraptor_agents=outdated_velociraptor_agents,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch outdated Velociraptor agents: {e}",
        )
