import asyncio
from typing import List

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload

# Resolved server-side by the indexer — cheaper and shorter than enumerating the
# concrete indices client-side (see `collect_indices`).
VULNERABILITY_STATES_INDEX_PATTERN = "wazuh-states-vulnerabilities-*"


async def collect_agent_vulnerabilities(agent_id: str, vulnerability_severity: str):
    """
    Collect agent vulnerabilities from Wazuh Manager.
    Used when Wazuh Manager is below 4.8.0

    Args:
        agent_id (str): The ID of the agent.
        vulnerability_severity (str): The severity of the vulnerabilities to collect.

    Returns:
        WazuhAgentVulnerabilitiesResponse: An object containing the collected vulnerabilities.

    Raises:
        HTTPException: If there is an error collecting the vulnerabilities.
    """
    logger.info(f"Collecting agent {agent_id} vulnerabilities from Wazuh Manager")

    severities = ["Low", "Medium", "High", "Critical"] if vulnerability_severity == "All" else [vulnerability_severity]

    agent_vulnerabilities = []
    for severity in severities:
        response = await send_get_request(
            endpoint=f"/vulnerability/{agent_id}",
            params={"severity": severity},
        )
        if response["success"] is False:
            raise HTTPException(status_code=500, detail=response["message"])
        # Navigate through the nested 'data' structure to get 'affected_items'
        affected_items = response.get("data", {}).get("data", {}).get("affected_items", [])
        agent_vulnerabilities.extend(affected_items)

    processed_vulnerabilities = process_agent_vulnerabilities(agent_vulnerabilities)

    return WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=processed_vulnerabilities,
        success=True,
        message="Vulnerabilities collected successfully",
    )


def process_agent_vulnerabilities(
    agent_vulnerabilities: List[dict],
) -> List[WazuhAgentVulnerabilities]:
    """
    Process agent vulnerabilities and return a list of WazuhAgentVulnerabilities objects.

    Args:
        agent_vulnerabilities (List[dict]): A list of dictionaries containing agent vulnerabilities data.

    Returns:
        List[WazuhAgentVulnerabilities]: A list of WazuhAgentVulnerabilities objects.

    Raises:
        HTTPException: If there is an error processing the agent vulnerabilities.
    """
    try:
        return [WazuhAgentVulnerabilities(**vuln) for vuln in agent_vulnerabilities]
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


async def collect_agent_vulnerability_by_cve(
    agent_id: str,
    cve: str,
    package_name: str = None,
    package_version: str = None,
    wazuh_new: bool = True,
) -> WazuhAgentVulnerabilitiesResponse:
    """
    Collect a single vulnerability of an agent, identified by its CVE (plus the
    affected package when the same CVE hits more than one package on the agent).

    The severity-based endpoints scroll every vulnerability document of the agent
    across all ``wazuh-states-vulnerabilities-*`` indices, which takes minutes on
    real deployments. The detail view only needs one document, so this issues a
    single filtered search instead.

    ``wazuh_new`` is the caller's ``check_wazuh_manager_version()`` result (the
    helper lives in the routes module — importing it here would be circular).
    When False we fall back to the Wazuh Manager API and filter by CVE in Python,
    since the indexer-backed states indices don't exist before manager 4.8.0.
    """
    logger.info(f"Collecting agent {agent_id} vulnerability {cve}")

    if wazuh_new is not True:
        # legacy path: the manager API has no CVE filter, so fetch and filter here
        response = await collect_agent_vulnerabilities(agent_id, "All")
        matches = [vuln for vuln in response.vulnerabilities if vuln.cve == cve]
        return _single_vulnerability_response(matches, cve, package_name, package_version)

    es = await create_wazuh_indexer_client("Wazuh-Indexer")

    must = [
        {"match": {"agent.id": agent_id}},
        {"match": {"vulnerability.id": cve}},
    ]
    if package_name:
        must.append({"match": {"package.name": package_name}})
    if package_version:
        must.append({"match": {"package.version": package_version}})

    query = {"query": {"bool": {"must": must}}}

    # let the indexer resolve the pattern server-side rather than enumerating indices
    response = es.search(
        index=VULNERABILITY_STATES_INDEX_PATTERN,
        body=query,
        size=10,
        ignore_unavailable=True,
        allow_no_indices=True,
    )

    hits = [hit["_source"] for hit in response["hits"]["hits"]]
    matches = process_agent_vulnerabilities_new(hits)

    return _single_vulnerability_response(matches, cve, package_name, package_version)


def _single_vulnerability_response(
    matches: List[WazuhAgentVulnerabilities],
    cve: str,
    package_name: str = None,
    package_version: str = None,
) -> WazuhAgentVulnerabilitiesResponse:
    """Narrow the matches down to the requested package, keeping the first hit as fallback."""
    if not matches:
        raise HTTPException(status_code=404, detail=f"Vulnerability {cve} not found for this agent")

    exact = next(
        (
            vuln
            for vuln in matches
            if (not package_name or vuln.name == package_name) and (not package_version or vuln.version == package_version)
        ),
        None,
    )

    return WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=[exact or matches[0]],
        success=True,
        message="Vulnerability collected successfully",
    )


def filter_vulnerabilities_indices(indices_list):
    return [index for index in indices_list if index.startswith("wazuh-states-vulnerabilities")]


def filter_vulnerabilities_indices_sync(indices_list, customer_code):
    """
    Filter the indices list to only include the vulnerability indices which are relevant to the customer.
    Notice the missing `states` in the index name.
    """
    # ! Make the customer code lowercase ! #
    return [index for index in indices_list if index.startswith(f"wazuh-vulnerabilities-{customer_code.lower()}")]


async def collect_vulnerabilities(es, vulnerabilities_indices, agent_id, vulnerability_severity="Critical"):
    agent_vulnerabilities = []
    for index in vulnerabilities_indices:
        if vulnerability_severity == "All":
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"agent.id": agent_id}},
                            {"terms": {"vulnerability.severity": ["Low", "Medium", "High", "Critical"]}},
                        ],
                    },
                },
            }
        else:
            query = {
                "query": {
                    "bool": {"must": [{"match": {"agent.id": agent_id}}, {"match": {"vulnerability.severity": vulnerability_severity}}]},
                },
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


async def collect_vulnerabilities_sync(es, vulnerabilities_indices, agent_name, vulnerability_severity="All"):
    agent_vulnerabilities = []
    for index in vulnerabilities_indices:
        if vulnerability_severity == "All":
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"agent.name": agent_name}},
                            {"terms": {"vulnerability.severity": ["Low", "Medium", "High", "Critical"]}},
                        ],
                    },
                },
            }
        else:
            query = {
                "query": {
                    "bool": {
                        "must": [{"match": {"agent.name": agent_name}}, {"match": {"vulnerability.severity": vulnerability_severity}}],
                    },
                },
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


async def collect_vulnerabilities_async(es, vulnerabilities_indices, agent_name, vulnerability_severity="All"):
    agent_vulnerabilities = []
    for index in vulnerabilities_indices:
        if vulnerability_severity == "All":
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"agent.name": agent_name}},
                            {"terms": {"vulnerability.severity": ["Low", "Medium", "High", "Critical"]}},
                        ],
                    },
                },
            }
        else:
            query = {
                "query": {
                    "bool": {
                        "must": [{"match": {"agent.name": agent_name}}, {"match": {"vulnerability.severity": vulnerability_severity}}],
                    },
                },
            }

        page = await es.search(index=index, body=query, scroll="2m")
        sid = page["_scroll_id"]
        scroll_size = len(page["hits"]["hits"])

        while scroll_size > 0:
            for hit in page["hits"]["hits"]:
                vulnerability = hit["_source"]
                agent_vulnerabilities.append(vulnerability)

            page = await es.scroll(scroll_id=sid, scroll="2m")
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


async def check_vulnerability_exists_async(es, vulnerability_cve, agent_name, index_prefix):
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"agent_name": agent_name}},
                    {"match": {"cve": vulnerability_cve}},
                ],
            },
        },
    }
    index_pattern = f"{index_prefix}*"
    response = await es.search(index=index_pattern, body=query)
    return response["hits"]["total"]["value"] > 0


async def sync_agent_vulnerabilities(agent_name: str, customer_code: str):
    """
    1. Loops through all agents in the database to collect their agent_name and customer code.
    2. Queries the `wazuh-states-vulnerabilities-*` index in Wazuh Indexer to get vulnerabilities based on the agent_name.
    3. Checks the `wazuh-vulnerabilities-*customer_code*` index in Wazuh Indexer to get vulnerabilities based on the
        agent_name and checks to see if a vulnerability_id already exists.
    4. If the vulnerability_id does not exist, it is sent to the Graylog GELF Input.
    """
    logger.info(f"Syncing agent {agent_name} with customer code {customer_code} vulnerabilities")

    es = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    indices = await collect_indices(all_indices=True)

    vulnerabilities_indices = filter_vulnerabilities_indices(indices.indices_list)

    agent_vulnerabilities = await collect_vulnerabilities_async(es, vulnerabilities_indices, agent_name, vulnerability_severity="All")

    processed_vulnerabilities = process_agent_vulnerabilities_new(agent_vulnerabilities)

    customer_vulnerabilities_indices = filter_vulnerabilities_indices_sync(indices.indices_list, customer_code)

    if customer_vulnerabilities_indices:
        logger.info("Customer vulnerabilities index already exists")
        # Create a list of tasks for checking vulnerabilities
        tasks = [
            check_vulnerability_exists_async(
                es,
                vulnerability_cve=vulnerability.cve,
                agent_name=agent_name,
                index_prefix=f"wazuh-vulnerabilities-{customer_code}",
            )
            for vulnerability in processed_vulnerabilities
        ]

        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Process the results
        for vulnerability, vulnerability_exists in zip(processed_vulnerabilities, results):
            if not vulnerability_exists:
                logger.info(
                    f"Vulnerability {vulnerability.cve} does not exist in customer index for agent {agent_name}, sending to Graylog",
                )
                await event_shipper(
                    EventShipperPayload(
                        integration="vulnerabilities",
                        customer_code=customer_code,
                        agent_name=agent_name,
                        **vulnerability.model_dump(),
                    ),
                )
        return True

    logger.info("Customer vulnerabilities index does not exist")
    # ! Send all vulnerabilities to Graylog ! #
    for vulnerability in processed_vulnerabilities:
        await event_shipper(
            EventShipperPayload(
                integration="vulnerabilities",
                customer_code=customer_code,
                agent_name=agent_name,
                **vulnerability.model_dump(),
            ),
        )
    return True
