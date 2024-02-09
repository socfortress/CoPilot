from typing import List

import app.agents.velociraptor.services.agents as velociraptor_services
import app.agents.wazuh.services.agents as wazuh_services
from app.agents.schema.agents import SyncedAgent, SyncedAgentsResponse
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.wazuh.schema.agents import WazuhAgent, WazuhAgentsList
from app.connectors.models import Connectors
from app.db.universal_models import Agents
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


async def fetch_wazuh_agents() -> WazuhAgentsList:
    """Fetch agents from Wazuh service.

    This function retrieves a list of agents from the Wazuh service.
    It calls the `collect_wazuh_agents` function from the `wazuh_services` module
    and returns a `WazuhAgentsList` object containing the collected agents.

    Returns:
        WazuhAgentsList: A list of agents retrieved from the Wazuh service.

    """
    collected_wazuh_agents = await wazuh_services.collect_wazuh_agents()
    return WazuhAgentsList(
        agents=collected_wazuh_agents.agents,
        success=collected_wazuh_agents.success,
        message=collected_wazuh_agents.message,
    )


async def fetch_velociraptor_agent(agent_name: str) -> VelociraptorAgent:
    """
    Fetches agent details from Velociraptor service.

    Args:
        agent_name (str): The name of the agent to fetch.

    Returns:
        VelociraptorAgent: The fetched agent details.
    """
    return await velociraptor_services.collect_velociraptor_agent(agent_name)


async def add_agent_to_db(
    session: AsyncSession,
    agent: WazuhAgent,
    client: VelociraptorAgent,
    customer_code: str,
):
    """Add new agent to database.

    Args:
        session (AsyncSession): The asynchronous session object for database operations.
        agent (WazuhAgent): The Wazuh agent object to be added.
        client (VelociraptorAgent): The Velociraptor agent object associated with the Wazuh agent.
        customer_code (str): The customer code for the agent.

    Returns:
        None

    """
    new_agent = Agents.create_from_model(agent, client, customer_code)
    session.add(new_agent)
    await session.commit()  # Use the await keyword to commit asynchronously
    logger.info(f"Agent {agent.agent_name} added to the database")


async def update_agent_in_db(
    session: AsyncSession,
    existing_agent: Agents,
    agent: WazuhAgent,
    client: VelociraptorAgent,
    customer_code: str,
):
    """Update existing agent in database.

    Args:
        session (AsyncSession): The async session object for database operations.
        existing_agent (Agents): The existing agent object in the database.
        agent (WazuhAgent): The updated agent object.
        client (VelociraptorAgent): The updated client object.
        customer_code (str): The customer code associated with the agent.

    Returns:
        None

    """
    existing_agent.update_from_model(agent, client, customer_code)
    await session.commit()  # Use the await keyword to commit asynchronously
    logger.info(f"Agent {agent.agent_name} updated in the database")


def extract_customer_code(customer_code: str):
    """Extracts the customer code from the agent label.

    Args:
        customer_code (str): The agent label containing the customer code.

    Returns:
        str: The extracted customer code, or None if the agent label is invalid.
    """
    parts = customer_code.split("_")
    return parts[1] if len(parts) > 1 else None


async def get_velociraptor_connector(session):
    """
    Retrieves the Velociraptor connector from the database.

    Args:
        session: The database session.

    Returns:
        The first result of the query as a scalar value.
    """
    connector_query = select(Connectors).filter(
        Connectors.connector_name == "Velociraptor",
    )
    result = await session.execute(connector_query)
    return result.scalars().first()


async def get_velociraptor_agent(agent_name):
    """
    Retrieves a Velociraptor agent with the specified name.

    Args:
        agent_name (str): The name of the agent to retrieve.

    Returns:
        VelociraptorAgent: The retrieved Velociraptor agent, or None if retrieval fails.
    """
    try:
        return await fetch_velociraptor_agent(agent_name)
    except Exception as e:
        logger.error(f"Failed to collect Velociraptor Agent for {agent_name}: {e}")
        return None


async def process_velociraptor_agent(session, wazuh_agent):
    """
    Process the Velociraptor agent for a given Wazuh agent.

    Args:
        session (object): The session object for the connection.
        wazuh_agent (object): The Wazuh agent object.

    Returns:
        object: The Velociraptor agent object if successful, None otherwise.
    """
    try:
        velociraptor_connector = await get_velociraptor_connector(session)
        if velociraptor_connector.connector_verified:
            velociraptor_agent = await get_velociraptor_agent(wazuh_agent.agent_name)
        else:
            velociraptor_agent = VelociraptorAgent(
                client_id="Unknown",
                client_last_seen="1970-01-01T00:00:00+00:00",
                client_version="Unknown",
            )
        return velociraptor_agent
    except Exception as e:
        logger.error(f"Failed to process agent {wazuh_agent.agent_name}: {e}")
        return None


async def sync_agents(session: AsyncSession) -> SyncedAgentsResponse:
    """
    Synchronize agents from Wazuh and Velociraptor services.

    This function fetches the list of Wazuh agents, collects the corresponding Velociraptor agent for each Wazuh agent,
    and synchronizes the agents in the database. It returns a response indicating the success of the synchronization
    operation and the list of agents that were added.

    :param session: The database session to use for querying and updating agents.
    :type session: AsyncSession
    :return: The response indicating the success of the synchronization operation and the list of agents added.
    :rtype: SyncedAgentsResponse
    """
    wazuh_agents_list = await fetch_wazuh_agents()
    logger.info(f"Collected Wazuh Agents: {wazuh_agents_list}")

    agents_added_list: List[WazuhAgent] = []

    for wazuh_agent in wazuh_agents_list.agents:
        logger.info(f"Collecting Velociraptor Agent for {wazuh_agent.agent_name}")

        try:
            velociraptor_agent = await process_velociraptor_agent(session, wazuh_agent)
        except Exception as e:
            logger.error(
                f"Failed to collect Velociraptor Agent for {wazuh_agent.agent_name}: {e}",
            )
            continue

        customer_code = extract_customer_code(wazuh_agent.agent_label)

        # Asynchronously fetch the existing agent
        existing_agent_query = select(Agents).filter(
            Agents.hostname == wazuh_agent.agent_name,
        )
        result = await session.execute(existing_agent_query)
        existing_agent = result.scalars().first()

        if existing_agent:
            await update_agent_in_db(
                session,
                existing_agent,
                wazuh_agent,
                velociraptor_agent,
                customer_code,
            )
        else:
            await add_agent_to_db(
                session,
                wazuh_agent,
                velociraptor_agent,
                customer_code,
            )

        # Combine the wazuh agent and velociraptor agent into one object
        synced_agent = SyncedAgent(**wazuh_agent.dict(), **velociraptor_agent.dict())
        agents_added_list.append(synced_agent)

    logger.info(f"Agents Added List: {agents_added_list}")
    return SyncedAgentsResponse(
        success=True,
        message="Agents synced successfully",
        agents_added=agents_added_list,
    )
