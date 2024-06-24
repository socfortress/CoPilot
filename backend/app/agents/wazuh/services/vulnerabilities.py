from typing import List

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def collect_agent_vulnerabilities(agent_id: str, vulnerability_severity: str):
    """
    Collect agent vulnerabilities from Wazuh Manager.
    Used when Wazuh Manager is below 4.8.0

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentVulnerabilitiesResponse: An object containing the collected vulnerabilities.

    Raises:
        HTTPException: If there is an error collecting the vulnerabilities.
    """
    logger.info(f"Collecting agent {agent_id} vulnerabilities from Wazuh Manager")
    agent_vulnerabilities = await send_get_request(
        endpoint=f"/vulnerability/{agent_id}",
        params={"severity": vulnerability_severity},
    )
    if agent_vulnerabilities["success"] is False:
        raise HTTPException(status_code=500, detail=agent_vulnerabilities["message"])

    processed_vulnerabilities = process_agent_vulnerabilities(
        agent_vulnerabilities["data"],
    )
    return WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=processed_vulnerabilities,
        success=True,
        message="Vulnerabilities collected successfully",
    )


def process_agent_vulnerabilities(
    agent_vulnerabilities: dict,
) -> List[WazuhAgentVulnerabilities]:
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
        vulnerabilities = agent_vulnerabilities.get("data", {}).get(
            "affected_items",
            [],
        )
        return [WazuhAgentVulnerabilities(**vuln) for vuln in vulnerabilities]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process agent vulnerabilities: {e}",
        )


async def collect_agent_vulnerabilities_new(agent_id: str, vulnerability_severity: str):
    """
    Collects vulnerabilities for a specific agent from the Wazuh Indexer Index.
    Used when Wazuh-Manager is 4.8.0 or above.

    Args:
        agent_id (str): The ID of the agent for which to collect vulnerabilities.

    Returns:
        WazuhAgentVulnerabilitiesResponse: An object containing the collected vulnerabilities,
        along with a success flag and a message indicating the success status.
    """
    logger.info(f"Collecting agent {agent_id} vulnerabilities from Wazuh Indexer Index")
    es = await create_wazuh_indexer_client("Wazuh-Indexer")
    indices = await collect_indices(all_indices=True)
    logger.info(f"Indices collect: {indices}")

    vulnerabilities_indices = filter_vulnerabilities_indices(indices.indices_list)

    agent_vulnerabilities = await collect_vulnerabilities(es, vulnerabilities_indices, agent_id, vulnerability_severity)

    processed_vulnerabilities = process_agent_vulnerabilities_new(agent_vulnerabilities)

    return WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=processed_vulnerabilities,
        success=True,
        message="Vulnerabilities collected successfully",
    )


def filter_vulnerabilities_indices(indices_list):
    return [index for index in indices_list if index.startswith("wazuh-states-vulnerabilities")]


async def collect_vulnerabilities(es, vulnerabilities_indices, agent_id, vulnerability_severity="Critical"):
    agent_vulnerabilities = []
    for index in vulnerabilities_indices:
        query = {
            "query": {"bool": {"must": [{"match": {"agent.id": agent_id}}, {"match": {"vulnerability.severity": vulnerability_severity}}]}},
        }
        page = es.search(index=index, body=query, scroll="2m")
        sid = page["_scroll_id"]
        scroll_size = len(page["hits"]["hits"])

        while scroll_size > 0:
            for hit in page["hits"]["hits"]:
                vulnerability = hit["_source"]
                agent_vulnerabilities.append(vulnerability)

            page = es.scroll(scroll_id=sid, scroll="2m")
            sid = page["_scroll_id"]
            scroll_size = len(page["hits"]["hits"])

    return agent_vulnerabilities


def process_agent_vulnerabilities_new(agent_vulnerabilities: List[dict]) -> List[WazuhAgentVulnerabilities]:
    logger.info(f"Processing agent vulnerabilities: {agent_vulnerabilities}")

    processed_vulnerabilities = []
    for vulnerability in agent_vulnerabilities:
        processed_vulnerability = process_single_vulnerability(vulnerability)
        processed_vulnerabilities.append(processed_vulnerability)

    return processed_vulnerabilities


def process_single_vulnerability(vulnerability):
    external_references = ensure_list(vulnerability.get("vulnerability").get("reference"))
    return WazuhAgentVulnerabilities(
        severity=vulnerability.get("vulnerability").get("severity"),
        version=vulnerability.get("package").get("version"),
        type=vulnerability.get("package").get("type"),
        name=vulnerability.get("package").get("name"),
        external_references=external_references,
        detection_time=vulnerability.get("vulnerability").get("detected_at"),
        cvss3_score=vulnerability.get("vulnerability").get("score").get("base"),
        published=vulnerability.get("vulnerability").get("published_at"),
        architecture=vulnerability.get("package").get("architecture"),
        cve=vulnerability.get("vulnerability").get("id"),
        status=vulnerability.get("status"),
        title=vulnerability.get("vulnerability").get("description"),
    )


def ensure_list(value):
    if not isinstance(value, list):
        return [value]
    return value
