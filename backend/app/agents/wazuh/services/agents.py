from fastapi import HTTPException
from loguru import logger

from app.agents.schema.agents import AgentModifyResponse
from app.agents.wazuh.schema.agents import WazuhAgent
from app.agents.wazuh.schema.agents import WazuhAgentsList
from app.connectors.wazuh_manager.utils.universal import send_delete_request
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def collect_wazuh_agents() -> WazuhAgentsList:
    """
    Collects all agents from Wazuh Manager.

    Returns:
        WazuhAgentsList: A list of WazuhAgent objects representing the collected agents.
    """
    logger.info("Collecting all agents from Wazuh Manager")
    agents_collected = await send_get_request(
        endpoint="/agents",
        params={"limit": 1000},
    )

    if agents_collected.get("success") is False:
        raise HTTPException(
            status_code=500,
            detail=agents_collected.get("message", "Unknown error"),
        )
    try:
        if agents_collected.get("success"):
            wazuh_agents_list = []
            for agent in agents_collected.get("data", {}).get("data", {}).get("affected_items", []):
                os_name = agent.get("os", {}).get("name", "Unknown")
                last_keep_alive = agent.get("lastKeepAlive", "Unknown")
                agent_group_list = agent.get("group", [])
                agent_group = agent_group_list[0] if agent_group_list else "Unknown"

                wazuh_agent = WazuhAgent(
                    agent_id=agent.get("id", "Unknown"),
                    agent_name=agent.get("name", "Unknown"),
                    agent_ip=agent.get("ip", "Unknown"),
                    agent_os=os_name,
                    agent_label=agent_group,
                    agent_last_seen=last_keep_alive,
                    wazuh_agent_version=agent.get("version", "n/a"),
                )
                wazuh_agents_list.append(wazuh_agent)

            return WazuhAgentsList(
                agents=wazuh_agents_list,
                success=True,
                message="Agents collected successfully",
            )

    except (KeyError, IndexError, HTTPException) as e:
        # Handle or log the error as needed
        logger.error(f"An error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect agents: {e}",
        )

    except Exception as e:
        # Catch-all for other exceptions
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect agents: {e}",
        )


def handle_agent_deletion_response(agent_deleted: dict, agent_id: str):
    """
    Handles the response of agent deletion from the Wazuh Manager.

    Args:
        agent_deleted (dict): The response of agent deletion.
        agent_id (str): The ID of the agent.

    Returns:
        AgentModifyResponse: An instance of AgentModifyResponse if the agent is deleted successfully.

    Raises:
        HTTPException: If the agent deletion fails, an HTTPException is raised with the appropriate error message.
    """
    if agent_deleted["success"]:
        return AgentModifyResponse(success=True, message="Agent deleted successfully")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete agent {agent_id} from Wazuh Manager: {agent_deleted.get('message', 'Unknown error')}",
        )


async def delete_agent_wazuh(agent_id: str) -> AgentModifyResponse:
    """Delete agent from Wazuh Manager.

    Args:
        agent_id (str): The ID of the agent to be deleted.

    Returns:
        AgentModifyResponse: The response indicating the status of the agent deletion.

    Raises:
        HTTPException: If there is an HTTP error during the deletion process.
    """
    logger.info(f"Deleting agent {agent_id} from Wazuh Manager")

    params = {
        "purge": True,
        "agents_list": [agent_id],
        "status": "all",
        "older_than": "0s",
    }

    try:
        agent_deleted = await send_delete_request(endpoint="/agents", params=params)
        return handle_agent_deletion_response(agent_deleted, agent_id)

    except HTTPException as http_e:
        # * Catch any HTTPException and re-raise it
        raise http_e

    except Exception as e:
        # * Catch-all for other exceptions
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete agent {agent_id} from Wazuh Manager: {e}",
        )
