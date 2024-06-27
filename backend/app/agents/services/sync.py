from datetime import datetime
from datetime import timezone
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import app.agents.velociraptor.services.agents as velociraptor_services
import app.agents.wazuh.services.agents as wazuh_services
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.schema.agents import SyncedWazuhAgent
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.velociraptor.schema.agents import VelociraptorClients
from app.agents.velociraptor.schema.agents import VelociraptorOrganizations
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.connectors.models import Connectors
from app.db.db_session import get_db_session
from app.db.universal_models import Agents


async def fetch_wazuh_agents() -> WazuhAgentsList:
    """
    Fetch agents from Wazuh service.

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


async def fetch_velociraptor_clients(org_id: str) -> VelociraptorClients:
    """
    Fetches clients from Velociraptor service.

    Args:
        None

    Returns:
        VelociraptorClientsList: The fetched clients.
    """
    collected_velociraptor_agents = await velociraptor_services.collect_velociraptor_clients(org_id=org_id)
    return VelociraptorClients(
        clients=collected_velociraptor_agents,
    )


async def fetch_velociraptor_organizations() -> VelociraptorOrganizations:
    """
    Fetches organizations from Velociraptor service.

    Args:
        None

    Returns:
        VelociraptorOrgsList: The fetched orgs.
    """
    collected_velociraptor_orgs = await velociraptor_services.collect_velociraptor_organizations()
    logger.info(f"Collected Velociraptor Orgs: {collected_velociraptor_orgs}")
    return VelociraptorOrganizations(
        organizations=collected_velociraptor_orgs,
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


async def fetch_velociraptor_agent_via_client_id(client_id: str) -> VelociraptorAgent:
    """
    Fetches agent details from Velociraptor service.

    Args:
        client_id (str): The client_id of the agent to fetch.

    Returns:
        VelociraptorAgent: The fetched agent details.
    """
    return await velociraptor_services.collect_velociraptor_agent_via_client_id(client_id)


async def add_wazuh_agent_in_db(
    session: AsyncSession,
    agent: WazuhAgent,
    customer_code: str,
):
    """Add new agent to database.

    Args:
        session (AsyncSession): The asynchronous session object for database operations.
        agent (WazuhAgent): The Wazuh agent object to be added.
        customer_code (str): The customer code for the agent.

    Returns:
        None

    """
    new_agent = Agents.create_wazuh_agent_from_model(agent, customer_code)
    session.add(new_agent)
    logger.info(f"Adding agent {agent.agent_name} to the database")
    try:
        await session.commit()  # Use the await keyword to commit asynchronously
    except Exception as e:
        logger.error(f"Failed to add agent {agent.agent_name} to the database: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    logger.info(f"Agent {agent.agent_name} added to the database")


async def update_wazuh_agent_in_db(
    session: AsyncSession,
    existing_agent: Agents,
    agent: WazuhAgent,
    customer_code: str,
):
    """Update existing agent in database.

    Args:
        session (AsyncSession): The async session object for database operations.
        existing_agent (Agents): The existing agent object in the database.
        agent (WazuhAgent): The updated agent object.
        customer_code (str): The customer code associated with the agent.

    Returns:
        None

    """
    existing_agent.update_wazuh_agent_from_model(agent, customer_code)
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


async def get_velociraptor_agent_by_client_id(client_id):
    """
    Retrieves a Velociraptor agent with the specified client_id.

    Args:
        client_id (str): The client_id of the agent to retrieve.

    Returns:
        VelociraptorAgent: The retrieved Velociraptor agent, or None if retrieval fails.
    """
    try:
        return await fetch_velociraptor_agent_via_client_id(client_id)
    except Exception as e:
        logger.error(f"Failed to collect Velociraptor Agent for {client_id}: {e}")
        return None


async def process_velociraptor_agent(session, agent, client_id=None):
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
            velociraptor_agent = await get_velociraptor_agent(agent)
            if client_id is not None:
                velociraptor_agent = await get_velociraptor_agent_by_client_id(client_id)
        else:
            velociraptor_agent = VelociraptorAgent(
                client_id="Unknown",
                client_last_seen="1970-01-01T00:00:00+00:00",
                client_version="Unknown",
            )
        return velociraptor_agent
    except Exception as e:
        logger.error(f"Failed to process agent {agent}: {e}")
        return None


async def sync_agents_wazuh() -> SyncedAgentsResponse:
    wazuh_agents_list = await fetch_wazuh_agents()
    logger.info(f"Collected Wazuh Agents: {wazuh_agents_list}")

    agents_added_list: List[WazuhAgent] = []

    async with get_db_session() as session:  # Create a new session here
        for wazuh_agent in wazuh_agents_list.agents:
            customer_code = extract_customer_code(wazuh_agent.agent_label)

            existing_agent_query = select(Agents).filter(
                Agents.hostname == wazuh_agent.agent_name,
            )
            result = await session.execute(existing_agent_query)
            existing_agent = result.scalars().first()

            if existing_agent:
                await update_wazuh_agent_in_db(session, existing_agent, wazuh_agent, customer_code)
            else:
                await add_wazuh_agent_in_db(session, wazuh_agent, customer_code)

            synced_wazuh_agent = SyncedWazuhAgent(**wazuh_agent.dict())
            agents_added_list.append(synced_wazuh_agent)

    logger.info(f"Agents Added List: {agents_added_list}")

    # Close the session
    await session.close()

    return SyncedAgentsResponse(
        success=True,
        message="Agents synced successfully",
    )


async def update_agent_with_velociraptor_in_db(
    session: AsyncSession,
    agent: Agents,
    velociraptor_agent: VelociraptorAgent,
):
    """Update existing agent in database with Velociraptor details.

    Args:
        session (AsyncSession): The async session object for database operations.
        agent (Agents): The existing agent object in the database.
        client (VelociraptorAgent): The updated client object.

    Returns:
        None

    """
    logger.info(f"Updating agent {agent.hostname} with Velociraptor details in the database")
    agent.update_velociraptor_details(velociraptor_agent)
    session.add(agent)  # Add the updated agent back to the session
    await session.commit()  # Use the await keyword to commit asynchronously
    logger.info("Agent updated with Velociraptor details in the database")


async def sync_agents_velociraptor() -> SyncedAgentsResponse:
    """
    Syncronizes the agents with Velociraptor. This function retrieves all the
    agents from the `Agents` table and invokes the velociraptor API with the
    hostname. If the hostname cannot be found within Velociraptor, and the agent's
    `velociraptor_id` is not None, invoke the Velociraptor API and pass it the
    `velociraptor_id`.

    :param session: The database session to use for querying and updating agents.
    :type session: AsyncSession
    :return: The response indicating the success of the synchronization operation and the list of agents added.
    :rtype: SyncedAgentsResponse
    """
    agents_added_list: List[VelociraptorAgent] = []
    velo_orgs = await fetch_velociraptor_organizations()
    logger.info(f"Collected Velociraptor Orgs: {velo_orgs}")
    for org in velo_orgs.organizations:
        velociraptor_clients = await fetch_velociraptor_clients(org_id=org.OrgId)
        logger.info(f"Collected Velociraptor Clients: {velociraptor_clients}")
        velociraptor_clients = velociraptor_clients.clients if hasattr(velociraptor_clients, "clients") else []

        async with get_db_session() as session:  # Create a new session here
            existing_agents_query = select(Agents)
            result = await session.execute(existing_agents_query)
            existing_agents = result.scalars().all()

            for agent in existing_agents:
                logger.info(f"Collecting Velociraptor Agent for {agent.hostname}")

                try:
                    # Build the velociraptor_agent where the hostname or `client_id` is that equal to the `agents`
                    velociraptor_agent = next(
                        (
                            client
                            for client in velociraptor_clients
                            if client.os_info.hostname == agent.hostname or client.client_id == agent.velociraptor_id
                        ),
                        None,
                    )
                    # Convert Unix epoch timestamp to datetime
                    last_seen_at = datetime.fromtimestamp(
                        int(velociraptor_agent.last_seen_at) / 1e6,
                    )  # Divide by 1e6 to convert from microseconds to seconds
                    # Convert datetime to ISO 8601 format without fractional seconds
                    last_seen_at_iso = last_seen_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
                    velociraptor_agent = VelociraptorAgent(
                        velociraptor_id=velociraptor_agent.client_id,
                        velociraptor_last_seen=last_seen_at_iso,
                        velociraptor_agent_version=velociraptor_agent.agent_information.version,
                        velociraptor_org=org.OrgId,
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to collect Velociraptor Agent for {agent.hostname}: {e}",
                    )
                    continue

                if velociraptor_agent:
                    # Update the agent with the Velociraptor client's details
                    await update_agent_with_velociraptor_in_db(session, agent, velociraptor_agent)
                    agents_added_list.append(velociraptor_agent)

        # Close the session
        await session.close()

    logger.info(f"Agents Added List: {agents_added_list}")
    return SyncedAgentsResponse(
        success=True,
        message="Agents synced successfully",
        agents_added=agents_added_list,
    )
