from datetime import datetime
from datetime import timedelta
from typing import Optional
from typing import Type

from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_indexer.utils.universal import LogsQueryBuilder
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.healthchecks.agents.schema.agents import AgentHealthCheckResponse
from app.healthchecks.agents.schema.agents import AgentModel
from app.healthchecks.agents.schema.agents import CollectLogsResponse
from app.healthchecks.agents.schema.agents import ExtendedAgentModel
from app.healthchecks.agents.schema.agents import HostLogsSearchBody
from app.healthchecks.agents.schema.agents import HostLogsSearchResponse
from app.healthchecks.agents.schema.agents import LogsSearchBody
from app.healthchecks.agents.schema.agents import TimeCriteriaModel


def is_wazuh_agent_unhealthy(
    agent: AgentModel,
    time_criteria: TimeCriteriaModel,
) -> ExtendedAgentModel:
    """
    Checks if a Wazuh agent is unhealthy based on the last seen time and time criteria.

    Args:
        agent (AgentModel): The agent to check.
        time_criteria (TimeCriteriaModel): The time criteria for determining agent health.

    Returns:
        ExtendedAgentModel: An extended agent model with the unhealthy status updated.
    """
    current_time = datetime.now()
    wazuh_last_seen = agent.wazuh_last_seen

    if wazuh_last_seen > current_time:
        logger.info(
            f"Agent {agent} has a wazuh_last_seen time in the future: {wazuh_last_seen}",
        )
        return ExtendedAgentModel(**agent.dict(), unhealthy_wazuh_agent=True)

    # Calculate the total time delta based on the criteria
    total_minutes = time_criteria.minutes + time_criteria.hours * 60 + time_criteria.days * 24 * 60
    time_delta = timedelta(minutes=total_minutes)

    is_unhealthy = (current_time - wazuh_last_seen) > time_delta
    return ExtendedAgentModel(**agent.dict(), unhealthy_wazuh_agent=is_unhealthy)


def is_velociraptor_agent_unhealthy(
    agent: AgentModel,
    time_criteria: TimeCriteriaModel,
) -> ExtendedAgentModel:
    """
    Checks if a velociraptor agent is unhealthy based on the last seen time and time criteria.

    Args:
        agent (AgentModel): The agent to check.
        time_criteria (TimeCriteriaModel): The time criteria for determining agent health.

    Returns:
        ExtendedAgentModel: An extended agent model with the unhealthy_velociraptor_agent flag set.
    """
    current_time = datetime.now()
    velociraptor_last_seen = agent.velociraptor_last_seen

    if velociraptor_last_seen > current_time:
        logger.info(
            f"Agent {agent} has a velociraptor_last_seen time in the future: {velociraptor_last_seen}",
        )
        return ExtendedAgentModel(**agent.dict(), unhealthy_velociraptor_agent=True)

    # Calculate the total time delta based on the criteria
    total_minutes = time_criteria.minutes + time_criteria.hours * 60 + time_criteria.days * 24 * 60
    time_delta = timedelta(minutes=total_minutes)

    is_unhealthy = (current_time - velociraptor_last_seen) > time_delta
    return ExtendedAgentModel(**agent.dict(), unhealthy_velociraptor_agent=is_unhealthy)


async def wazuh_agents_healthcheck(
    agents: list,
    time_criteria: TimeCriteriaModel,
) -> AgentHealthCheckResponse:
    """
    Perform a health check on Wazuh agents.

    Args:
        agents (list): List of agents to perform health check on.
        time_criteria (TimeCriteriaModel): Time criteria for determining agent health.

    Returns:
        AgentHealthCheckResponse: Response object containing the results of the health check.
    """
    healthy_wazuh_agents = []
    unhealthy_wazuh_agents = []
    for agent in agents:
        # If agent_id is `000` skip it because this is the Wazuh manager
        if agent.agent_id == "000":
            continue
        logger.info(f"Checking agent {agent} for health")
        extended_agent = is_wazuh_agent_unhealthy(agent, time_criteria)
        logger.info(f"Extended agent: {extended_agent}")
        if extended_agent.unhealthy_wazuh_agent:
            unhealthy_wazuh_agents.append(extended_agent)
        else:
            healthy_wazuh_agents.append(extended_agent)

    return AgentHealthCheckResponse(
        healthy_wazuh_agents=healthy_wazuh_agents,
        unhealthy_wazuh_agents=unhealthy_wazuh_agents,
        success=True,
        message="Wazuh agent healthcheck fetched successfully",
    )


async def wazuh_agent_healthcheck(
    agent: AgentModel,
    time_criteria: TimeCriteriaModel,
) -> AgentHealthCheckResponse:
    """
    Performs a health check on a Wazuh agent.

    Args:
        agent (AgentModel): The agent to perform the health check on.
        time_criteria (TimeCriteriaModel): The time criteria for the health check.

    Returns:
        AgentHealthCheckResponse: The health check response containing the results of the health check.
    """
    extended_agent = is_wazuh_agent_unhealthy(agent, time_criteria)
    if extended_agent.unhealthy_wazuh_agent:
        return AgentHealthCheckResponse(
            healthy_wazuh_agents=[],
            unhealthy_wazuh_agents=[extended_agent],
            success=True,
            message="Wazuh agent healthcheck fetched successfully",
        )
    else:
        return AgentHealthCheckResponse(
            healthy_wazuh_agents=[extended_agent],
            unhealthy_wazuh_agents=[],
            success=True,
            message="Wazuh agent healthcheck fetched successfully",
        )


async def velociraptor_agents_healthcheck(
    agents: list,
    time_criteria: TimeCriteriaModel,
) -> AgentHealthCheckResponse:
    """
    Perform health check on Velociraptor agents.

    Args:
        agents (list): List of agents to perform health check on.
        time_criteria (TimeCriteriaModel): Time criteria for determining agent health.

    Returns:
        AgentHealthCheckResponse: Response object containing healthy and unhealthy agents.
    """
    healthy_velociraptor_agents = []
    unhealthy_velociraptor_agents = []

    for agent in agents:
        # If agent_id is `000` skip it because this is the Wazuh manager
        if agent.agent_id == "000":
            continue
        logger.info(f"Checking agent {agent} for health")
        extended_agent = is_velociraptor_agent_unhealthy(agent, time_criteria)
        logger.info(f"Extended agent: {extended_agent}")
        if extended_agent.unhealthy_velociraptor_agent:
            unhealthy_velociraptor_agents.append(extended_agent)
        else:
            healthy_velociraptor_agents.append(extended_agent)

    return AgentHealthCheckResponse(
        healthy_velociraptor_agents=healthy_velociraptor_agents,
        unhealthy_velociraptor_agents=unhealthy_velociraptor_agents,
        success=True,
        message="Velociraptor agent healthcheck fetched successfully",
    )


async def velociraptor_agent_healthcheck(
    agent: AgentModel,
    time_criteria: TimeCriteriaModel,
) -> AgentHealthCheckResponse:
    """
    Perform a health check on a Velociraptor agent.

    Args:
        agent (AgentModel): The agent to perform the health check on.
        time_criteria (TimeCriteriaModel): The time criteria for the health check.

    Returns:
        AgentHealthCheckResponse: The health check response containing the status of the Velociraptor agent.
    """
    extended_agent = is_velociraptor_agent_unhealthy(agent, time_criteria)
    if extended_agent.unhealthy_velociraptor_agent:
        return AgentHealthCheckResponse(
            healthy_velociraptor_agents=[],
            unhealthy_velociraptor_agents=[extended_agent],
            success=True,
            message="Velociraptor agent healthcheck fetched successfully",
        )
    else:
        return AgentHealthCheckResponse(
            healthy_velociraptor_agents=[extended_agent],
            unhealthy_velociraptor_agents=[],
            success=True,
            message="Velociraptor agent healthcheck fetched successfully",
        )


async def host_logs(search_body: HostLogsSearchBody) -> HostLogsSearchResponse:
    """
    Search for host logs based on the provided search criteria.

    Args:
        search_body (HostLogsSearchBody): The search criteria for host logs.

    Returns:
        HostLogsSearchResponse: The response containing the search result and status information.
    """
    result = await get_logs_generic(search_body, is_host_specific=True)
    logger.info(f"Host logs search result: {result}")

    # Initialize variable to keep track of total logs
    total_logs = 0

    # Loop through each item in logs_summary to count total logs
    for log_summary in result["logs_summary"]:
        total_logs += log_summary["total_logs"]

    # Check if there are any logs
    if total_logs > 0:
        return HostLogsSearchResponse(
            success=True,
            healthy=True,
            message=f"Host is healthy. At least one log was found within the specified time range of {search_body.timerange}",
        )
    else:
        return HostLogsSearchResponse(
            success=True,
            healthy=False,
            message=f"Host is unhealthy. No logs were found within the specified time range of {search_body.timerange}",
        )


async def get_logs_generic(
    search_body: Type[LogsSearchBody],
    is_host_specific: bool = False,
    index_name: Optional[str] = None,
):
    """
    Retrieves logs based on the provided search criteria.

    Args:
        search_body (Type[LogsSearchBody]): The search criteria for the logs.
        is_host_specific (bool, optional): Specifies if the search is host-specific. Defaults to False.
        index_name (str, optional): The name of the index to search in. If not provided, all indices will be searched.

    Returns:
        dict: A dictionary containing the logs summary, success status, and message.
    """
    logger.info(
        f"Collecting Wazuh Indexer alerts for host {search_body.agent_name if is_host_specific else ''}",
    )
    logs_summary = []
    indices = await collect_indices()
    index_list = [index_name] if index_name else indices.indices_list  # Use the provided index_name or get all indices

    for index_name in index_list:
        try:
            logs = await collect_logs_generic(
                index_name,
                body=search_body,
                is_host_specific=is_host_specific,
            )
            if logs.success and len(logs.logs) > 0:
                logs_summary.append(
                    {
                        "index_name": index_name,
                        "total_logs": len(logs.logs),
                        "logs": logs.logs,
                    },
                )
                break  # Only collect logs from the first index that has logs
        except HTTPException as e:
            logger.warning(
                f"An error occurred while processing index {index_name}: {e.detail}",
            )

    if len(logs_summary) == 0:
        message = "No logs found"
    else:
        message = f"Succesfully collected top {search_body.size} logs for each index"

    return {
        "logs_summary": logs_summary,
        "success": len(logs_summary) > 0,
        "message": message,
    }


async def collect_logs_generic(
    index_name: str,
    body: LogsSearchBody,
    is_host_specific: bool = False,
) -> CollectLogsResponse:
    """
    Collects logs from Elasticsearch based on the specified parameters.

    Args:
        index_name (str): The name of the Elasticsearch index to search.
        body (LogsSearchBody): The search body containing the timerange, log field, log value, and other parameters.
        is_host_specific (bool, optional): Specifies whether the search should be limited to a specific agent. Defaults to False.

    Returns:
        CollectLogsResponse: The response object containing the collected logs, success status, and message.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    query_builder = LogsQueryBuilder()
    query_builder.add_time_range(
        timerange=body.timerange,
        timestamp_field=body.timestamp_field,
    )
    query_builder.add_matches(matches=[(body.log_field, body.log_value)])
    query_builder.add_sort(body.timestamp_field)

    if is_host_specific:
        query_builder.add_match_phrase(matches=[("agent_name", body.agent_name)])

    query = query_builder.build()

    try:
        logs = es_client.search(index=index_name, body=query, size=body.size)
        logger.info(f"logs collected: {logs}")
        logs_list = [log for log in logs["hits"]["hits"]]
        logger.info(f"logs collected: {logs_list}")
        return CollectLogsResponse(
            logs=logs_list,
            success=True,
            message="logs collected successfully",
        )
    except Exception as e:
        logger.debug(f"Failed to collect logs: {e}")
        return CollectLogsResponse(
            logs=[],
            success=False,
            message=f"Failed to collect logs: {e}",
        )
