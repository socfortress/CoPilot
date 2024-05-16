from typing import List

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.schema.agents import WazuhAgentScaPolicyResults
from app.agents.wazuh.schema.agents import WazuhAgentScaPolicyResultsResponse
from app.agents.wazuh.schema.agents import WazuhAgentScaResponse
from app.agents.wazuh.schema.agents import WazuhAgentScaResults
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def collect_agent_sca(agent_id: str):
    """
    Collect agent sca from Wazuh Manager.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentVulnerabilitiesResponse: An object containing the collected sca.

    Raises:
        HTTPException: If there is an error collecting the sca.
    """
    logger.info(f"Collecting agent {agent_id} sca from Wazuh Manager")
    agent_sca = await send_get_request(
        endpoint=f"/sca/{agent_id}",
    )
    if agent_sca["success"] is False:
        raise HTTPException(status_code=500, detail=agent_sca["message"])

    processed_sca = process_agent_sca(
        agent_sca["data"],
    )
    logger.info(f"{processed_sca}")
    return WazuhAgentScaResponse(
        sca=processed_sca,
        success=True,
        message="SCA collected successfully",
    )


def process_agent_sca(
    agent_sca: dict,
) -> List[WazuhAgentScaResults]:
    """
    Process agent sca and return a list of WazuhAgentScaResults objects.

    Args:
        agent_sca (dict): A dictionary containing agent sca data.

    Returns:
        List[WazuhAgentScaResults]: A list of WazuhAgentScaResults objects.

    Raises:
        HTTPException: If there is an error processing the agent sca.
    """
    try:
        sca = agent_sca.get("data", {}).get(
            "affected_items",
            [],
        )
        return [WazuhAgentScaResults(**sca) for sca in sca]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process agent sca: {e}",
        )


########## ! SCA POLICY RESULTS ! #########
async def collect_agent_sca_policy_results(agent_id: str, policy_id: str):
    """
    Collect agent sca from Wazuh Manager.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentScaPolicyResultsResponse: An object containing the collected sca.

    Raises:
        HTTPException: If there is an error collecting the sca.
    """
    logger.info(f"Collecting agent {agent_id} sca from Wazuh Manager")
    agent_sca_policy_results = await send_get_request(
        endpoint=f"/sca/{agent_id}/checks/{policy_id}",
    )
    if agent_sca_policy_results["success"] is False:
        raise HTTPException(status_code=500, detail=agent_sca_policy_results["message"])

    processed_sca_policy_results = process_agent_sca_policy_results(
        agent_sca_policy_results["data"],
    )
    logger.info(f"{processed_sca_policy_results}")
    return WazuhAgentScaPolicyResultsResponse(
        sca_policy_results=processed_sca_policy_results,
        success=True,
        message="SCA Policy results collected successfully",
    )


def process_agent_sca_policy_results(
    agent_sca: dict,
) -> List[WazuhAgentScaPolicyResults]:
    """
    Process agent sca and return a list of WazuhAgentScaPolicyResults objects.

    Args:
        agent_sca (dict): A dictionary containing agent sca data.

    Returns:
        List[WazuhAgentScaPolicyResults]: A list of WazuhAgentScaPolicyResults objects.

    Raises:
        HTTPException: If there is an error processing the agent sca.
    """
    try:
        sca = agent_sca.get("data", {}).get(
            "affected_items",
            [],
        )
        return [WazuhAgentScaPolicyResults(**sca) for sca in sca]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process agent sca: {e}",
        )
