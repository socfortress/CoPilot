from typing import List
from loguru import logger
from app.db.db_session import session
from app.db.universal_models import Agents
from app.agents.schema.agents import OutdatedWazuhAgentsResponse, OutdatedVelociraptorAgentsResponse
from app.connectors.velociraptor.utils.universal import (
    UniversalService
)


def get_agent(agent_id: str) -> List[Agents]:
        """
        Retrieves a specific agent from the database using its ID.

        Args:
            agent_id (str): The ID of the agent to retrieve.

        Returns:
            AgentMetadata: The agent object if found, otherwise None.
        """
        return session.query(Agents).filter(Agents.agent_id == agent_id).first()

def get_outdated_agents_wazuh() -> OutdatedWazuhAgentsResponse:
    """
    Retrieves all agents with outdated Wazuh agent versions from the database.

    Returns:
        List[dict]: A list of dictionaries where each dictionary represents the serialized data of an outdated agent.
    """
    wazuh_manager = get_agent("000")
    if wazuh_manager is None:
        logger.error("Wazuh Manager with agent_id '000' not found.")
        return {"message": "Wazuh Manager with agent_id '000' not found.", "success": False}

    outdated_wazuh_agents = session.query(Agents).filter(Agents.agent_id != "000", Agents.wazuh_agent_version != wazuh_manager.wazuh_agent_version).all()
    return {"message": "Outdated Wazuh agents fetched successfully.", "success": True, "outdated_wazuh_agents": outdated_wazuh_agents}

def get_outdated_agents_velociraptor() -> OutdatedVelociraptorAgentsResponse:
    """
    Retrieves all agents with outdated Velociraptor client versions from the database.

    Returns:
        List[dict]: A list of dictionaries where each dictionary represents the serialized data of an outdated agent.
    """
    outdated_velociraptor_agents = []
    vql_server_version = "select * from config"
    server_version = UniversalService()._get_server_version(vql_server_version)
    agents = session.query(Agents).all()
    for agent in agents:
        if agent.velociraptor_agent_version != server_version:
            outdated_velociraptor_agents.append(agent)
    return {"message": "Outdated Velociraptor agents fetched successfully.", "success": True, "outdated_velociraptor_agents": outdated_velociraptor_agents}


