from typing import List
from loguru import logger
from app.db.db_session import session
from app.db.universal_models import Agents
import app.agents.wazuh.services.agents as wazuh_services
import app.agents.velociraptor.services.agents as velociraptor_services
from app.agents.schema.agents import SyncedAgentsResponse, SyncedAgent
from app.agents.wazuh.schema.agents import WazuhAgent, WazuhAgentsList
from app.agents.velociraptor.schema.agents import VelociraptorAgent

def fetch_wazuh_agents() -> WazuhAgentsList:
    """Fetch agents from Wazuh service."""
    collected_wazuh_agents = wazuh_services.collect_wazuh_agents()
    return WazuhAgentsList(
        agents=collected_wazuh_agents.agents,
        success=collected_wazuh_agents.success,
        message=collected_wazuh_agents.message,
    )

def fetch_velociraptor_agent(agent_name: str) -> VelociraptorAgent:
    """Fetch agent details from Velociraptor service."""
    return velociraptor_services.collect_velociraptor_agent(agent_name)

def add_agent_to_db(agent: WazuhAgent, client: VelociraptorAgent, customer_code: str):
    """Add new agent to database."""
    new_agent = Agents.create_from_model(agent, client, customer_code)
    session.add(new_agent)
    session.commit()
    logger.info(f"Agent {agent.agent_name} added to the database")

def update_agent_in_db(existing_agent: Agents, agent: WazuhAgent, client: VelociraptorAgent, customer_code: str):
    """Update existing agent in database."""
    existing_agent.update_from_model(agent, client, customer_code)
    session.commit()
    logger.info(f"Agent {agent.agent_name} updated in the database")

def extract_customer_code(customer_code: str):
    """Extract customer code from agent label."""
    parts = customer_code.split("_")
    return parts[1] if len(parts) > 1 else None

def sync_agents() -> SyncedAgentsResponse:
    """Synchronize agents from Wazuh and Velociraptor services."""
    wazuh_agents_list = fetch_wazuh_agents()
    logger.info(f"Collected Wazuh Agents: {wazuh_agents_list}")

    agents_added_list: List[WazuhAgent] = []

    for wazuh_agent in wazuh_agents_list.agents:
        logger.info(f"Collecting Velociraptor Agent for {wazuh_agent.agent_name}")
        
        velociraptor_agent = fetch_velociraptor_agent(wazuh_agent.agent_name)

        customer_code = extract_customer_code(wazuh_agent.agent_label)

        existing_agent = session.query(Agents).filter(Agents.hostname == wazuh_agent.agent_name).first()

        if existing_agent:
            update_agent_in_db(existing_agent, wazuh_agent, velociraptor_agent, customer_code)
        else:
            add_agent_to_db(wazuh_agent, velociraptor_agent, customer_code)

        # Combine the wazuh agent and velociraptor agent into one object
        synced_agent = SyncedAgent(**wazuh_agent.dict(), **velociraptor_agent.dict())
        agents_added_list.append(synced_agent)
        


    logger.info(f"Agents Added List: {agents_added_list}")
    return SyncedAgentsResponse(success=True, message="Agents synced successfully", agents_added=agents_added_list)
