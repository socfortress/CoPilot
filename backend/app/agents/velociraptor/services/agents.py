import json
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests
import xmltodict
from loguru import logger

from app.agents.schema.agents import AgentsResponse
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.agents.velociraptor.utils.universal import parse_date
from app.connectors.velociraptor.services.artifacts import ArtifactsService
from app.connectors.velociraptor.utils.universal import UniversalService
from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse


def collect_velociraptor_agent(agent_name: str) -> VelociraptorAgent:
    """
    Retrieves the client ID, last_seen_at and client version based on the agent name from Velociraptor.

    Args:
        agent_name (str): The name of the agent.

    Returns:
        str: The client ID if found, None otherwise.
        str: The last seen at timestamp if found, Default timsetamp otherwise.
    """
    logger.info(f"Collecting agent {agent_name} from Velociraptor")
    try:
        client_id = UniversalService().get_client_id(agent_name)["results"][0]["client_id"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to get client ID for {agent_name}. Error: {e}")
        return VelociraptorAgent(client_id="Unknown", client_last_seen="Unknown", client_version="Unknown")

    try:
        vql_last_seen_at = f"select last_seen_at from clients(search='host:{agent_name}')"
        last_seen_at = UniversalService()._get_last_seen_timestamp(vql_last_seen_at)
        client_last_seen = datetime.fromtimestamp(
            int(last_seen_at) / 1000000,
        ).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00",
        )  # Converting to string format
    except Exception as e:
        logger.error(f"Failed to get or convert last seen at for {agent_name}. Error: {e}")
        client_last_seen = "1970-01-01T00:00:00+00:00"

    try:
        vql_client_version = f"select * from clients(search='host:{agent_name}')"
        client_version = UniversalService()._get_client_version(vql_client_version)
    except Exception as e:
        logger.error(f"Failed to get client version for {agent_name}. Error: {e}")
        client_version = "Unknown"

    return VelociraptorAgent(client_id=client_id, client_last_seen=client_last_seen, client_version=client_version)


def delete_agent_velociraptor(client_id: str) -> AgentsResponse:
    """
    Deletes an agent from Velociraptor.

    Args:
        client_id (str): The client ID of the agent to delete.

    Returns:
        AgentsResponse: The response object.
    """
    logger.info(f"Deleting agent {client_id} from Velociraptor")
    try:
        ArtifactsService().delete_client(client_id=client_id)
        return AgentsResponse(success=True, message="Agent deleted successfully")
    except Exception as e:
        logger.error(f"Failed to delete agent {client_id}. Error: {e}")
        return AgentsResponse(success=False, message="Failed to delete agent")
