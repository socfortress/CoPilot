from typing import List

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import app.agents.velociraptor.services.agents as velociraptor_services
import app.agents.wazuh.services.agents as wazuh_services
from app.agents.schema.agents import SyncedAgent
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.db.universal_models import Agents


async def fetch_wazuh_agents() -> WazuhAgentsList:
    """Fetch agents from Wazuh service."""
    collected_wazuh_agents = await wazuh_services.collect_wazuh_agents()
    return WazuhAgentsList(
        agents=collected_wazuh_agents.agents,
        success=collected_wazuh_agents.success,
        message=collected_wazuh_agents.message,
    )


async def fetch_velociraptor_agent(agent_name: str) -> VelociraptorAgent:
    """Fetch agent details from Velociraptor service."""
    return await velociraptor_services.collect_velociraptor_agent(agent_name)


async def add_agent_to_db(session: AsyncSession, agent: WazuhAgent, client: VelociraptorAgent, customer_code: str):
    """Add new agent to database."""
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
    """Update existing agent in database."""
    existing_agent.update_from_model(agent, client, customer_code)
    await session.commit()  # Use the await keyword to commit asynchronously
    logger.info(f"Agent {agent.agent_name} updated in the database")


def extract_customer_code(customer_code: str):
    """Extract customer code from agent label."""
    parts = customer_code.split("_")
    return parts[1] if len(parts) > 1 else None


async def sync_agents(session: AsyncSession) -> SyncedAgentsResponse:
    """Synchronize agents from Wazuh and Velociraptor services."""
    wazuh_agents_list = await fetch_wazuh_agents()
    logger.info(f"Collected Wazuh Agents: {wazuh_agents_list}")

    agents_added_list: List[WazuhAgent] = []

    for wazuh_agent in wazuh_agents_list.agents:
        logger.info(f"Collecting Velociraptor Agent for {wazuh_agent.agent_name}")

        velociraptor_agent = await fetch_velociraptor_agent(wazuh_agent.agent_name)

        customer_code = extract_customer_code(wazuh_agent.agent_label)

        # Asynchronously fetch the existing agent
        existing_agent_query = select(Agents).filter(Agents.hostname == wazuh_agent.agent_name)
        result = await session.execute(existing_agent_query)
        existing_agent = result.scalars().first()

        if existing_agent:
            await update_agent_in_db(session, existing_agent, wazuh_agent, velociraptor_agent, customer_code)
        else:
            await add_agent_to_db(session, wazuh_agent, velociraptor_agent, customer_code)

        # Combine the wazuh agent and velociraptor agent into one object
        synced_agent = SyncedAgent(**wazuh_agent.dict(), **velociraptor_agent.dict())
        agents_added_list.append(synced_agent)

    logger.info(f"Agents Added List: {agents_added_list}")
    return SyncedAgentsResponse(success=True, message="Agents synced successfully", agents_added=agents_added_list)
