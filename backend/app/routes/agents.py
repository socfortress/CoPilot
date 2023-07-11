from flask import Blueprint
from flask import jsonify

from app.services.agents.agents import AgentService
from app.services.agents.agents import AgentSyncService
from app.services.WazuhManager.agent import WazuhManagerAgentService
from app.services.WazuhManager.universal import UniversalService
from app.services.WazuhManager.vulnerability import VulnerabilityService

# from loguru import logger


bp = Blueprint("agents", __name__)


@bp.route("/agents", methods=["GET"])
def get_agents():
    """
    Endpoint to list all available agents.
    It processes each agent to verify the connection and returns the results.

    Returns:
        json: A JSON response containing the list of all available agents along with their connection
        verification status.
    """
    service = AgentService()
    agents = service.get_all_agents()
    return agents


@bp.route("/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id):
    """
    Endpoint to get the details of a agent.

    Args:
        id (str): The id of the agent to be fetched.

    Returns:
        json: A JSON response containing the details of the agent.
    """
    service = AgentService()
    agent = service.get_agent(agent_id=agent_id)
    return agent


@bp.route("/agents/<agent_id>/critical", methods=["POST"])
def mark_as_critical(agent_id):
    """
    Endpoint to mark a agent as critical.

    Args:
        id (str): The id of the agent to be marked as critical.

    Returns:
        json: A JSON response containing the updated agent information.
    """
    service = AgentService()
    result = service.mark_agent_as_critical(agent_id=agent_id)
    return result


@bp.route("/agents/<agent_id>/noncritical", methods=["POST"])
def unmark_agent_critical(agent_id):
    """
    Endpoint to unmark a agent as critical.

    Args:
        id (str): The id of the agent to be unmarked as critical.

    Returns:
        json: A JSON response containing the updated agent information.
    """
    service = AgentService()
    result = service.mark_agent_as_non_critical(agent_id=agent_id)
    return result


@bp.route("/agents/sync", methods=["POST"])
def sync_agents():
    """
    Endpoint to sync all agents.

    Returns:
        json: A JSON response containing the updated agent information.
    """
    service = AgentSyncService()
    result = service.sync_agents()
    return jsonify(result)


@bp.route("/agents/<agent_id>/delete", methods=["POST"])
def delete_agent(agent_id):
    """
    Endpoint to delete a agent.

    Args:
        id (str): The id of the agent to be deleted.

    Returns:
        json: A JSON response containing the updated agent information.
    """
    service = AgentService()
    result = service.delete_agent_db(agent_id=agent_id)

    # Delete from WazuhManager
    # Create instance of UniversalService
    universal_service = UniversalService()

    # Pass universal_service to WazuhManagerAgentService
    agent_service = WazuhManagerAgentService(universal_service)
    agent_service.delete_agent(agent_id=agent_id)

    return result


@bp.route("/agents/<agent_id>/vulnerabilities", methods=["GET"])
def get_agent_vulnerabilities(agent_id):
    """
    Endpoint to get the vulnerabilities of a agent.

    Args:
        id (str): The id of the agent to be fetched.

    Returns:
        json: A JSON response containing the vulnerabilities of the agent.
    """
    # Create instance of UniversalService
    universal_service = UniversalService()

    # Pass universal_service to VulnerabilityService
    vulnerability_service = VulnerabilityService(universal_service)

    agent_vulnerabilities = vulnerability_service.agent_vulnerabilities(agent_id=agent_id)
    return agent_vulnerabilities
