from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger

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


def get_index_names() -> List[str]:
    indices = collect_indices()
    return indices.indices_list


def verify_index_name(index_alerts_search_body: IndexAlertsSearchBody) -> IndexAlertsSearchBody:
    # Remove any extra spaces from index_name
    index_alerts_search_body.index_name = index_alerts_search_body.index_name.strip()

    managed_index_names = get_index_names()
    if index_alerts_search_body.index_name not in managed_index_names:
        raise HTTPException(
            status_code=400,
            detail=f"Index name '{index_alerts_search_body.index_name}' is not managed by Wazuh Indexer or no longer exists.",
        )
    return index_alerts_search_body


@wazuh_indexer_alerts_router.post("", response_model=AlertsSearchResponse, description="Get all alerts")
async def get_all_alerts(alerts_search_body: AlertsSearchBody) -> AlertsSearchResponse:
    logger.info(f"Fetching all alerts")
    return get_alerts(alerts_search_body)


@wazuh_indexer_alerts_router.post("/host", response_model=HostAlertsSearchResponse, description="Get all alerts for a host")
async def get_all_alerts_for_host(host_alerts_search_body: HostAlertsSearchBody) -> HostAlertsSearchResponse:
    logger.info(f"Fetching all alerts for host {host_alerts_search_body.agent_name}")
    return get_host_alerts(host_alerts_search_body)


@wazuh_indexer_alerts_router.post("/index", response_model=IndexAlertsSearchResponse, description="Get all alerts for an index")
async def get_all_alerts_for_index(
    index_alerts_search_body: IndexAlertsSearchBody = Depends(verify_index_name),
) -> IndexAlertsSearchResponse:
    logger.info(f"Fetching all alerts for index {index_alerts_search_body.index_name}")
    return get_index_alerts(index_alerts_search_body)


@wazuh_indexer_alerts_router.post("/hosts/all", response_model=AlertsByHostResponse, description="Get number of all alerts for all hosts")
async def get_all_alerts_by_host(alerts_search_body: AlertsSearchBody) -> AlertsByHostResponse:
    logger.info(f"Fetching number of all alerts for all hosts")
    return get_alerts_by_host(alerts_search_body)


@wazuh_indexer_alerts_router.post("/rules/all", response_model=AlertsByRuleResponse, description="Get number of all alerts for all rules")
async def get_all_alerts_by_rule(alerts_search_body: AlertsSearchBody) -> AlertsByRuleResponse:
    logger.info(f"Fetching number of all alerts for all rules")
    return get_alerts_by_rule(alerts_search_body)


@wazuh_indexer_alerts_router.post(
    "/rules/hosts/all",
    response_model=AlertsByRulePerHostResponse,
    description="Get number of all alerts for all rules per host",
)
async def get_all_alerts_by_rule_per_host(alerts_search_body: AlertsSearchBody) -> AlertsByRulePerHostResponse:
    """
    Get number of all alerts for all rules per host

    Args:
        alerts_search_body (AlertsSearchBody): _description_

    Returns:
        AlertsByRulePerHostResponse: _description_
    """
    logger.info(f"Fetching number of all alerts for all rules per host")
    return get_alerts_by_rule_per_host(alerts_search_body)
