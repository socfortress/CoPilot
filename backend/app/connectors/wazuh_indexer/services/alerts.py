from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

import requests
from elasticsearch7 import Elasticsearch
from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session
from sqlmodel import select

from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse
from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHost
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRule
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHost
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRuleResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import CollectAlertsResponse
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.indices import IndexConfigModel
from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import format_indices_stats
from app.connectors.wazuh_indexer.utils.universal import format_node_allocation
from app.connectors.wazuh_indexer.utils.universal import format_shards
from app.db.db_session import engine

# def collect_and_aggregate_alerts(field_name: str, search_body: AlertsSearchBody) -> Dict[str, int]:
#     indices = collect_indices()
#     aggregated_alerts_dict = {}

#     for index_name in indices.indices_list:
#         try:
#             alerts_response = collect_alerts_generic(index_name, body=search_body)
#             if alerts_response.success:
#                 for alert in alerts_response.alerts:
#                     field_value = alert["_source"][field_name]
#                     aggregated_alerts_dict[field_value] = aggregated_alerts_dict.get(field_value, 0) + 1
#         except HTTPException as e:
#             logger.warning(f"An error occurred while processing index {index_name}: {e.detail}")

#     return aggregated_alerts_dict


def collect_and_aggregate_alerts(field_names: List[str], search_body: AlertsSearchBody) -> Dict[str, int]:
    indices = collect_indices()
    aggregated_alerts_dict = {}

    for index_name in indices.indices_list:
        try:
            alerts_response = collect_alerts_generic(index_name, body=search_body)
            if alerts_response.success:
                for alert in alerts_response.alerts:
                    composite_key = tuple(alert["_source"][field] for field in field_names)
                    aggregated_alerts_dict[composite_key] = aggregated_alerts_dict.get(composite_key, 0) + 1
        except HTTPException as e:
            logger.warning(f"An error occurred while processing index {index_name}: {e.detail}")

    return aggregated_alerts_dict


def collect_alerts_generic(index_name: str, body: AlertsSearchBody, is_host_specific: bool = False) -> CollectAlertsResponse:
    es_client = create_wazuh_indexer_client("Wazuh-Indexer")
    query_builder = AlertsQueryBuilder()
    query_builder.add_time_range(timerange=body.timerange, timestamp_field=body.timestamp_field)
    query_builder.add_matches(matches=[(body.alert_field, body.alert_value)])
    query_builder.add_sort(body.timestamp_field)

    if is_host_specific:
        query_builder.add_match_phrase(matches=[("agent_name", body.agent_name)])

    query = query_builder.build()

    try:
        alerts = es_client.search(index=index_name, body=query, size=body.size)
        logger.info(f"Alerts collected: {alerts}")
        alerts_list = [alert for alert in alerts["hits"]["hits"]]
        logger.info(f"Alerts collected: {alerts_list}")
        return CollectAlertsResponse(alerts=alerts_list, success=True, message="Alerts collected successfully")
    except Exception as e:
        logger.debug(f"Failed to collect alerts: {e}")
        return CollectAlertsResponse(alerts=[], success=False, message=f"Failed to collect alerts: {e}")


def get_alerts_generic(search_body: Type[AlertsSearchBody], is_host_specific: bool = False, index_name: Optional[str] = None):
    logger.info(f"Collecting Wazuh Indexer alerts for host {search_body.agent_name if is_host_specific else ''}")
    alerts_summary = []
    indices = collect_indices()
    index_list = [index_name] if index_name else indices.indices_list  # Use the provided index_name or get all indices

    for index_name in index_list:
        try:
            alerts = collect_alerts_generic(index_name, body=search_body, is_host_specific=is_host_specific)
            if alerts.success and len(alerts.alerts) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts.alerts),
                        "alerts": alerts.alerts,
                    },
                )
        except HTTPException as e:
            logger.warning(f"An error occurred while processing index {index_name}: {e.detail}")

    if len(alerts_summary) == 0:
        message = "No alerts found"
    else:
        message = f"Succesfully collected top {search_body.size} alerts for each index"

    return {"alerts_summary": alerts_summary, "success": len(alerts_summary) > 0, "message": message}


def get_alerts(search_body: AlertsSearchBody) -> AlertsSearchResponse:
    result = get_alerts_generic(search_body)
    return AlertsSearchResponse(**result)


def get_host_alerts(search_body: HostAlertsSearchBody) -> HostAlertsSearchResponse:
    result = get_alerts_generic(search_body, is_host_specific=True)
    return HostAlertsSearchResponse(**result)


def get_index_alerts(search_body: IndexAlertsSearchBody) -> IndexAlertsSearchResponse:
    result = get_alerts_generic(search_body, index_name=search_body.index_name)
    return IndexAlertsSearchResponse(**result)


def get_alerts_by_host(search_body: AlertsSearchBody) -> AlertsByHostResponse:
    aggregated_by_host = collect_and_aggregate_alerts(["agent_name"], search_body)
    alerts_by_host_list: List[AlertsByHost] = [
        AlertsByHost(agent_name=host[0], number_of_alerts=count)  # host[0] because host is now a tuple
        for host, count in aggregated_by_host.items()
    ]
    return AlertsByHostResponse(
        alerts_by_host=alerts_by_host_list,
        success=bool(alerts_by_host_list),
        message="Successfully collected alerts by host",
    )


def get_alerts_by_rule(search_body: AlertsSearchBody) -> AlertsByRuleResponse:
    aggregated_by_rule = collect_and_aggregate_alerts(["rule_description"], search_body)
    alerts_by_rule_list: List[AlertsByRule] = [
        AlertsByRule(rule=rule[0], number_of_alerts=count)  # rule[0] because rule is now a tuple
        for rule, count in aggregated_by_rule.items()
    ]
    return AlertsByRuleResponse(
        alerts_by_rule=alerts_by_rule_list,
        success=bool(alerts_by_rule_list),
        message="Successfully collected alerts by rule",
    )


def get_alerts_by_rule_per_host(search_body: AlertsSearchBody) -> AlertsByRulePerHostResponse:
    aggregated_by_rule_per_host = collect_and_aggregate_alerts(["agent_name", "rule_description"], search_body)
    alerts_by_rule_per_host_list: List[AlertsByRulePerHost] = [
        AlertsByRulePerHost(agent_name=agent_name, rule=rule, number_of_alerts=count)
        for (agent_name, rule), count in aggregated_by_rule_per_host.items()
    ]

    return AlertsByRulePerHostResponse(
        alerts_by_rule_per_host=alerts_by_rule_per_host_list,
        success=bool(alerts_by_rule_per_host_list),
        message="Successfully collected alerts by rule per host",
    )
