from typing import List

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def collect_agent_vulnerabilities(agent_id: str):
    """
    Collect agent vulnerabilities from Wazuh Manager.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentVulnerabilitiesResponse: An object containing the collected vulnerabilities.

    Raises:
        HTTPException: If there is an error collecting the vulnerabilities.
    """
    logger.info(f"Collecting agent {agent_id} vulnerabilities from Wazuh Manager")
    agent_vulnerabilities = await send_get_request(endpoint=f"/vulnerability/{agent_id}")
    if agent_vulnerabilities["success"] is False:
        raise HTTPException(status_code=500, detail=agent_vulnerabilities["message"])

    processed_vulnerabilities = process_agent_vulnerabilities(agent_vulnerabilities["data"])
    return WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=processed_vulnerabilities,
        success=True,
        message="Vulnerabilities collected successfully",
    )


from typing import List


def process_agent_vulnerabilities(agent_vulnerabilities: dict) -> List[WazuhAgentVulnerabilities]:
    """
    Process agent vulnerabilities and return a list of WazuhAgentVulnerabilities objects.

    Args:
        agent_vulnerabilities (dict): A dictionary containing agent vulnerabilities data.

    Returns:
        List[WazuhAgentVulnerabilities]: A list of WazuhAgentVulnerabilities objects.

    Raises:
        HTTPException: If there is an error processing the agent vulnerabilities.
    """
    try:
        vulnerabilities = agent_vulnerabilities.get("data", {}).get("affected_items", [])
        return [WazuhAgentVulnerabilities(**vuln) for vuln in vulnerabilities]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process agent vulnerabilities: {e}")
