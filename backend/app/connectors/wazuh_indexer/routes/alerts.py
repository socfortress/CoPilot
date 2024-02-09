from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRuleResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchResponse
from app.connectors.wazuh_indexer.services.alerts import get_alerts
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_host
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule_per_host
from app.connectors.wazuh_indexer.services.alerts import get_host_alerts
from app.connectors.wazuh_indexer.services.alerts import get_index_alerts
from app.connectors.wazuh_indexer.utils.universal import collect_indices

# App specific imports


wazuh_indexer_alerts_router = APIRouter()


async def get_index_names() -> List[str]:
    """
    Retrieves a list of index names.

    Returns:
        A list of index names.
    """
    indices = await collect_indices()
    return indices.indices_list


async def verify_index_name(
    index_alerts_search_body: IndexAlertsSearchBody,
) -> IndexAlertsSearchBody:
    """
    Verifies if the given index name is managed by Wazuh Indexer or still exists.

    Args:
        index_alerts_search_body (IndexAlertsSearchBody): The search body containing the index name.

    Raises:
        HTTPException: If the index name is not managed by Wazuh Indexer or no longer exists.

    Returns:
        IndexAlertsSearchBody: The search body with the verified index name.
    """
    # Remove any extra spaces from index_name
    index_alerts_search_body.index_name = index_alerts_search_body.index_name.strip()

    managed_index_names = await get_index_names()
    if index_alerts_search_body.index_name not in managed_index_names:
        raise HTTPException(
            status_code=400,
            detail=f"Index name '{index_alerts_search_body.index_name}' is not managed by Wazuh Indexer or no longer exists.",
        )
    return index_alerts_search_body


@wazuh_indexer_alerts_router.post(
    "",
    response_model=AlertsSearchResponse,
    description="Get all alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts(alerts_search_body: AlertsSearchBody) -> AlertsSearchResponse:
    """
    Get all alerts.

    Args:
        alerts_search_body (AlertsSearchBody): The search body containing filters and query parameters.

    Returns:
        AlertsSearchResponse: The response containing the search results.
    """
    logger.info("Fetching all alerts")
    return await get_alerts(alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/host",
    response_model=HostAlertsSearchResponse,
    description="Get all alerts for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_for_host(
    host_alerts_search_body: HostAlertsSearchBody,
) -> HostAlertsSearchResponse:
    """
    Get all alerts for a specific host.

    Args:
        host_alerts_search_body (HostAlertsSearchBody): The request body containing the agent name.

    Returns:
        HostAlertsSearchResponse: The response containing the host alerts.
    """
    logger.info(f"Fetching all alerts for host {host_alerts_search_body.agent_name}")
    return await get_host_alerts(host_alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/index",
    response_model=IndexAlertsSearchResponse,
    description="Get all alerts for an index",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_for_index(
    index_alerts_search_body: IndexAlertsSearchBody = Depends(verify_index_name),
) -> IndexAlertsSearchResponse:
    """
    Fetches all alerts for a given index.

    Args:
        index_alerts_search_body (IndexAlertsSearchBody): The request body containing the index name.

    Returns:
        IndexAlertsSearchResponse: The response containing the alerts for the index.
    """
    logger.info(f"Fetching all alerts for index {index_alerts_search_body.index_name}")
    return await get_index_alerts(index_alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/hosts/all",
    response_model=AlertsByHostResponse,
    description="Get number of all alerts for all hosts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_by_host(
    alerts_search_body: AlertsSearchBody,
) -> AlertsByHostResponse:
    """
    Fetches the number of all alerts for all hosts.

    Args:
        alerts_search_body (AlertsSearchBody): The search body containing the filters for the alerts.

    Returns:
        AlertsByHostResponse: The response containing the number of alerts for each host.
    """
    logger.info("Fetching number of all alerts for all hosts")
    return await get_alerts_by_host(alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/rules/all",
    response_model=AlertsByRuleResponse,
    description="Get number of all alerts for all rules",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_by_rule(
    alerts_search_body: AlertsSearchBody,
) -> AlertsByRuleResponse:
    """
    Fetches the number of all alerts for all rules.

    Args:
        alerts_search_body (AlertsSearchBody): The search body containing the filters for the alerts.

    Returns:
        AlertsByRuleResponse: The response containing the number of alerts for each rule.
    """
    logger.info("Fetching number of all alerts for all rules")
    return await get_alerts_by_rule(alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/rules/hosts/all",
    response_model=AlertsByRulePerHostResponse,
    description="Get number of all alerts for all rules per host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_by_rule_per_host(
    alerts_search_body: AlertsSearchBody,
) -> AlertsByRulePerHostResponse:
    """
    Get number of all alerts for all rules per host

    Args:
        alerts_search_body (AlertsSearchBody): _description_

    Returns:
        AlertsByRulePerHostResponse: _description_
    """
    logger.info("Fetching number of all alerts for all rules per host")
    return await get_alerts_by_rule_per_host(alerts_search_body)
