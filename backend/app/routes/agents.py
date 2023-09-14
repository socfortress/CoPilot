from typing import Any

from flask import Blueprint
from flask import jsonify
from loguru import logger

from app.models.agents import agent_metadata_schema
from app.services.agents.agents import AgentService
from app.services.agents.agents import AgentSyncService
from app.services.wazuh_manager.agent import WazuhManagerAgentService
from app.services.wazuh_manager.universal import UniversalService
from app.services.wazuh_manager.vulnerability import VulnerabilityService

bp = Blueprint("agents", __name__)


@bp.route("/agents", methods=["GET"])
def get_agents() -> Any:
    """
    Endpoint to get a list of all agents. It processes each agent and returns the results.
    Returns:
        json: A JSON response containing the list of all available agents along with their connection verification status.
    """
    service = AgentService()
    agents = service.get_all_agents()
    return jsonify(agents)


@bp.route("/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id: str) -> Any:
    """
    Endpoint to get the details of a specific agent.
    Args:
        agent_id (str): The ID of the agent to retrieve.
    Returns:
        json: A JSON response containing the details of the agent.
    """
    service = AgentService()
    agent = service.get_agent(agent_id=agent_id)
    if agent is None:
        return jsonify({"message": "Agent not found", "success": False}), 404
    else:
        try:
            agent_dict = agent_metadata_schema.dump(agent)
            return {"agent": agent_dict, "success": True, "message": "Agent found"}
        except Exception as e:
            logger.error(f"Error returning agent: {e}")
            return jsonify({"message": "Error returning agent", "success": False}), 500


@bp.route("/agents/<agent_id>/critical", methods=["POST"])
def mark_as_critical(agent_id: str) -> Any:
    """
    Endpoint to mark an agent as critical.
    Args:
        agent_id (str): The ID of the agent to mark as critical.
    Returns:
        json: A JSON response containing the updated agent information after being marked as critical.
    """
    service = AgentService()
    result = service.mark_agent_criticality(agent_id=agent_id, critical=True)
    return jsonify(result)


@bp.route("/agents/<agent_id>/noncritical", methods=["POST"])
def unmark_agent_critical(agent_id: str) -> Any:
    """
    Endpoint to unmark an agent as critical.
    Args:
        agent_id (str): The ID of the agent to unmark as critical.
    Returns:
        json: A JSON response containing the updated agent information after being unmarked as critical.
    """
    service = AgentService()
    result = service.mark_agent_criticality(agent_id=agent_id, critical=False)
    return jsonify(result)


@bp.route("/agents/sync", methods=["POST"])
def sync_agents() -> Any:
    """
    Endpoint to synchronize all agents.
    Returns:
        json: A JSON response containing the updated information of all synchronized agents.
    """
    service = AgentSyncService()
    result = service.sync_agents()
    return jsonify(result)


@bp.route("/agents/<agent_id>/delete", methods=["DELETE"])
def delete_agent(agent_id: str) -> Any:
    """
    Endpoint to delete an agent.
    Args:
        agent_id (str): The ID of the agent to be deleted.
    Returns:
        json: A JSON response indicating whether the deletion was successful.
    """
    service = AgentService()
    result = service.delete_agent_db(agent_id=agent_id)

    universal_service = UniversalService()
    agent_service = WazuhManagerAgentService(universal_service)
    agent_service.delete_agent(agent_id=agent_id)

    return jsonify(result)


@bp.route("/agents/<agent_id>/vulnerabilities", methods=["GET"])
def get_agent_vulnerabilities(agent_id: str) -> Any:
    """
    Endpoint to get the vulnerabilities of a specific agent.
    Args:
        agent_id (str): The ID of the agent whose vulnerabilities are to be fetched.
    Returns:
        json: A JSON response containing the vulnerabilities of the agent.
    """
    universal_service = UniversalService()
    vulnerability_service = VulnerabilityService(universal_service)

    agent_vulnerabilities = vulnerability_service.agent_vulnerabilities(
        agent_id=agent_id,
    )
    return jsonify(agent_vulnerabilities)


@bp.route("/agents/wazuh/outdated", methods=["GET"])
def get_outdated_wazuh_agents() -> Any:
    """
    Endpoint to get the outdated Wazuh agents.
    Returns:
        json: A JSON response containing the list of outdated Wazuh agents.
    """
    service = AgentService()
    agents = service.get_outdated_agents_wazuh()
    return jsonify(agents)


@bp.route("/agents/velociraptor/outdated", methods=["GET"])
def get_outdated_velociraptor_agents() -> Any:
    """
    Endpoint to get the outdated Velociraptor agents.
    Returns:
        json: A JSON response containing the list of outdated Velociraptor agents.
    """
    service = AgentService()
    agents = service.get_outdated_agents_velociraptor()
    return jsonify(agents)
