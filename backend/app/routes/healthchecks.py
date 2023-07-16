from typing import Any

from flask import Blueprint
from flask import jsonify
from loguru import logger

from app.models.agents import agent_metadata_schema
from app.services.agents.agents import AgentService
from app.services.agents.agents import AgentSyncService
from app.services.WazuhManager.agent import WazuhManagerAgentService
from app.services.WazuhManager.universal import UniversalService
from app.services.WazuhManager.vulnerability import VulnerabilityService
from app.services.Healthchecks.agents import HealthcheckAgentsService

bp = Blueprint("healthchecks", __name__)

@bp.route("/healthcheck/agent/full", methods=["GET"])
def get_agents_full() -> Any:
    """
    Endpoint to get a list of all agents who have sent logs within the last 15 minutes. Also returns a list of agents who have not sent logs within the last 15 minutes.
    Returns:
        json: A JSON response containing the list of all available agents along with their log existence status.
    """
    agent_service = AgentService()
    agents = agent_service.get_all_agents()
    healthcheck_service = HealthcheckAgentsService()
    agent_health = healthcheck_service.perform_healthcheck_full(agents, check_logs=True)
    return jsonify(agent_health)

@bp.route("/healthcheck/agent/<agent_id>/full", methods=["GET"])
def get_agent_full(agent_id: str) -> Any:
    """
    Endpoint to get the log existence status of a specific agent.
    Args:
        agent_id (str): The ID of the agent.
    Returns:
        json: A JSON response containing the log existence status of the agent.
    """
    # Query the `agent_metadata` table for the agent to get the hostname
    agent_service = AgentService()
    healthcheck_service = HealthcheckAgentsService()
    agent = agent_service.get_agent(agent_id=agent_id)
    if agent is None:
        return jsonify({"success": False, "message": "Agent not found."}), 404
    agent = agent_metadata_schema.dump(agent)
    agent_health = healthcheck_service.perform_healthcheck_full([agent], check_logs=True)
    return jsonify(agent_health)

@bp.route("/healthcheck/agent/wazuh", methods=["GET"])
def get_agents_wazuh() -> Any:
    """
    Endpoint to get a list of all agents whose Wazuh-Agent is running. Also returns a list of agents whose Wazuh-Agent is not running.
    Returns:
        json: A JSON response containing the list of all available agents along with their Wazuh-Agent status.
    """
    agent_service = AgentService()
    agents = agent_service.get_all_agents()
    healthcheck_service = HealthcheckAgentsService()
    agent_health = healthcheck_service.perform_healthcheck_wazuh(agents)
    return jsonify(agent_health)

@bp.route("/healthcheck/agent/<agent_id>/wazuh", methods=["GET"])
def get_agent_wazuh(agent_id: str) -> Any:
    """
    Endpoint to get the Wazuh-Agent status of a specific agent.
    Args:
        agent_id (str): The ID of the agent.
    Returns:
        json: A JSON response containing the Wazuh-Agent status of the agent.
    """
    # Query the `agent_metadata` table for the agent to get the hostname
    agent_service = AgentService()
    healthcheck_service = HealthcheckAgentsService()
    agent = agent_service.get_agent(agent_id=agent_id)
    if agent is None:
        return jsonify({"success": False, "message": "Agent not found."}), 404
    agent = agent_metadata_schema.dump(agent)
    logger.info(f"Checking Wazuh-Agent status for agent {agent}.")
    health = healthcheck_service.perform_healthcheck_wazuh(agent)
    return jsonify(health)

@bp.route("/healthcheck/agent/velociraptor", methods=["GET"])
def get_agents_velociraptor() -> Any:
    """
    Endpoint to get a list of all agents whose Velociraptor service is running. Also returns a list of agents whose Velociraptor service is not running.
    Returns:
        json: A JSON response containing the list of all available agents along with their Velociraptor service status.
    """
    agent_service = AgentService()
    agents = agent_service.get_all_agents()
    healthcheck_service = HealthcheckAgentsService()
    agent_health = healthcheck_service.perform_healthcheck_velociraptor(agents)
    return jsonify(agent_health)

@bp.route("/healthcheck/agent/<agent_id>/velociraptor", methods=["GET"])
def get_agent_velociraptor(agent_id: str) -> Any:
    """
    Endpoint to get the Velociraptor service status of a specific agent.
    Args:
        agent_id (str): The ID of the agent.
    Returns:
        json: A JSON response containing the Velociraptor service status of the agent.
    """
    # Query the `agent_metadata` table for the agent to get the hostname
    agent_service = AgentService()
    healthcheck_service = HealthcheckAgentsService()
    agent = agent_service.get_agent(agent_id=agent_id)
    if agent is None:
        return jsonify({"success": False, "message": "Agent not found."}), 404
    agent = agent_metadata_schema.dump(agent)
    logger.info(f"Checking Velociraptor service status for agent {agent}.")
    health = healthcheck_service.perform_healthcheck_velociraptor(agent)
    return jsonify(health)
