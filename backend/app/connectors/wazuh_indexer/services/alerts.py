import asyncio
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type

from elasticsearch7 import AsyncElasticsearch
from elasticsearch7.exceptions import NotFoundError
from elasticsearch7.exceptions import RequestError
from fastapi import HTTPException
from loguru import logger

# from app.connectors.wazuh_indexer.schema.alerts import Alert
from app.connectors.wazuh_indexer.schema.alerts import AlertNotFound
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHost
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRule
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHost
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRuleResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import CollectAlertsResponse
from app.connectors.wazuh_indexer.schema.alerts import GraylogAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import SkippableWazuhIndexerClientErrors
from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)


async def collect_and_aggregate_alerts(
    field_names: List[str],
    search_body: AlertsSearchBody,
) -> Dict[str, int]:
    """
    Collects and aggregates alerts based on the specified field names and search body.

    Args:
        field_names (List[str]): The list of field names to use for aggregation.
        search_body (AlertsSearchBody): The search body to filter alerts.

    Returns:
        Dict[str, int]: A dictionary containing the aggregated alerts, where the keys are composite keys
        based on the specified field names, and the values are the count of alerts for each composite key.
    """
    indices = await collect_indices()
    aggregated_alerts_dict = {}

    for index_name in indices.indices_list:
        try:
            alerts_response = await collect_alerts_generic(index_name, body=search_body)
            if alerts_response.success:
                for alert in alerts_response.alerts:
                    composite_key = tuple(alert["_source"][field] for field in field_names)
                    aggregated_alerts_dict[composite_key] = aggregated_alerts_dict.get(composite_key, 0) + 1
        except HTTPException as e:
            detail_str = str(e.detail)  # Convert to string to make sure it's comparable
            if any(err.value in detail_str for err in SkippableWazuhIndexerClientErrors):
                logger.warning(
                    f"Skipping index {index_name} due to specific error: {e.detail}",
                )
                continue  # Skip this index and continue with the next one
            else:
                logger.warning(
                    f"An error occurred while processing index {index_name}: {e.detail}",
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"An error occurred while processing index {index_name}: {e.detail}",
                )

    return aggregated_alerts_dict


async def collect_alerts_generic(
    index_name: str,
    body: AlertsSearchBody,
    is_host_specific: bool = False,
) -> CollectAlertsResponse:
    """
    Collects alerts from the specified index based on the provided search criteria.

    Args:
        index_name (str): The name of the index to search for alerts.
        body (AlertsSearchBody): The search criteria for filtering alerts.
        is_host_specific (bool, optional): Flag indicating whether the search should be limited to a specific host.
            Defaults to False.

    Returns:
        CollectAlertsResponse: The response containing the collected alerts.

    Raises:
        HTTPException: If an error occurs while collecting alerts.

    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    query_builder = AlertsQueryBuilder()

    try:
        query_builder.add_time_range(
            timerange=body.timerange,
            timestamp_field=body.timestamp_field,
        )
        query_builder.add_matches(matches=[(body.alert_field, body.alert_value)])
        query_builder.add_sort(body.timestamp_field)

        if is_host_specific:
            query_builder.add_match_phrase(matches=[("agent_name", body.agent_name)])

        query = query_builder.build()

        alerts = es_client.search(index=index_name, body=query, size=body.size)
    except RequestError as e:
        logger.warning(f"An error occurred while collecting alerts: {e}")
        if "No mapping found for [timestamp_utc] in order to sort on" in str(e):
            logger.warning("Retrying with timestamp field set to 'timestamp'")
            body.timestamp_field = "timestamp"
            try:
                return await collect_alerts_generic(index_name, body, is_host_specific)
            except RequestError as e:
                if "No mapping found for [timestamp] in order to sort on" in str(e):
                    logger.warning("Retrying with timestamp field set to '@timestamp'")
                    body.timestamp_field = "@timestamp"
                    return await collect_alerts_generic(index_name, body, is_host_specific)
        else:
            logger.warning(f"An error occurred while collecting alerts: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while collecting alerts: {e}",
            )

    logger.info(f"Alerts collected: {alerts}")
    alerts_list = [alert for alert in alerts["hits"]["hits"]]
    logger.info(f"Alerts collected: {alerts_list}")
    return CollectAlertsResponse(
        alerts=alerts_list,
        success=True,
        message="Alerts collected successfully",
    )


async def get_alerts_generic(
    search_body: Type[AlertsSearchBody],
    is_host_specific: bool = False,
    index_name: Optional[str] = None,
):
    """
    Retrieves alerts from the Wazuh Indexer based on the provided search criteria.

    Args:
        search_body (Type[AlertsSearchBody]): The search criteria for the alerts.
        is_host_specific (bool, optional): Specifies whether the search is host-specific. Defaults to False.
        index_name (str, optional): The name of the index to search in. If not provided, all indices will be searched.

    Returns:
        dict: A dictionary containing the alerts summary, success status, and a message.
    """
    logger.info(
        f"Collecting Wazuh Indexer alerts for host {search_body.agent_name if is_host_specific else ''}",
    )
    alerts_summary = []
    indices = await collect_indices()
    index_list = [index_name] if index_name else indices.indices_list  # Use the provided index_name or get all indices

    for index_name in index_list:
        try:
            alerts = await collect_alerts_generic(
                index_name,
                body=search_body,
                is_host_specific=is_host_specific,
            )
            if alerts.success and len(alerts.alerts) > 0:
                alerts_summary.append(
                    {
                        "index_name": index_name,
                        "total_alerts": len(alerts.alerts),
                        "alerts": alerts.alerts,
                    },
                )
        except HTTPException as e:
            detail_str = str(e.detail)  # Convert to string to make sure it's comparable
            if any(err.value in detail_str for err in SkippableWazuhIndexerClientErrors):
                logger.warning(
                    f"Skipping index {index_name} due to specific error: {e.detail}",
                )
                continue  # Skip this index and continue with the next one
            else:
                logger.warning(
                    f"An error occurred while processing index {index_name}: {e.detail}",
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"An error occurred while processing index {index_name}: {e.detail}",
                )

    if len(alerts_summary) == 0:
        message = "No alerts found"
    else:
        message = f"Succesfully collected top {search_body.size} alerts for each index"

    return {
        "alerts_summary": alerts_summary,
        "success": len(alerts_summary) > 0,
        "message": message,
    }


async def get_alerts(search_body: AlertsSearchBody) -> AlertsSearchResponse:
    """
    Retrieves alerts based on the provided search criteria.

    Args:
        search_body (AlertsSearchBody): The search criteria for retrieving alerts.

    Returns:
        AlertsSearchResponse: The response containing the retrieved alerts.
    """
    result = await get_alerts_generic(search_body)
    return AlertsSearchResponse(**result)


async def get_host_alerts(
    search_body: HostAlertsSearchBody,
) -> HostAlertsSearchResponse:
    """
    Retrieves alerts specific to a host.

    Args:
        search_body (HostAlertsSearchBody): The search criteria for retrieving host alerts.

    Returns:
        HostAlertsSearchResponse: The response containing the host alerts.
    """
    result = await get_alerts_generic(search_body, is_host_specific=True)
    return HostAlertsSearchResponse(**result)


async def get_index_alerts(
    search_body: IndexAlertsSearchBody,
) -> IndexAlertsSearchResponse:
    """
    Retrieves alerts from the specified index based on the search criteria.

    Args:
        search_body (IndexAlertsSearchBody): The search criteria for retrieving alerts.

    Returns:
        IndexAlertsSearchResponse: The response containing the retrieved alerts.
    """
    result = await get_alerts_generic(search_body, index_name=search_body.index_name)
    return IndexAlertsSearchResponse(**result)


async def get_alerts_by_host(search_body: AlertsSearchBody) -> AlertsByHostResponse:
    """
    Retrieves alerts grouped by host.

    Args:
        search_body (AlertsSearchBody): The search criteria for retrieving alerts.

    Returns:
        AlertsByHostResponse: The response containing alerts grouped by host.

    """
    aggregated_by_host = await collect_and_aggregate_alerts(["agent_name"], search_body)
    alerts_by_host_list: List[AlertsByHost] = [
        AlertsByHost(
            agent_name=host[0],
            number_of_alerts=count,
        )  # host[0] because host is now a tuple
        for host, count in aggregated_by_host.items()
    ]
    return AlertsByHostResponse(
        alerts_by_host=alerts_by_host_list,
        success=bool(alerts_by_host_list),
        message="Successfully collected alerts by host",
    )


async def get_alerts_by_rule(search_body: AlertsSearchBody) -> AlertsByRuleResponse:
    """
    Retrieves alerts grouped by rule based on the provided search criteria.

    Args:
        search_body (AlertsSearchBody): The search criteria for retrieving alerts.

    Returns:
        AlertsByRuleResponse: The response containing the alerts grouped by rule.

    """
    aggregated_by_rule = await collect_and_aggregate_alerts(
        ["rule_description"],
        search_body,
    )
    alerts_by_rule_list: List[AlertsByRule] = [
        AlertsByRule(
            rule=rule[0],
            number_of_alerts=count,
        )  # rule[0] because rule is now a tuple
        for rule, count in aggregated_by_rule.items()
    ]
    return AlertsByRuleResponse(
        alerts_by_rule=alerts_by_rule_list,
        success=bool(alerts_by_rule_list),
        message="Successfully collected alerts by rule",
    )


async def get_alerts_by_rule_per_host(
    search_body: AlertsSearchBody,
) -> AlertsByRulePerHostResponse:
    """
    Retrieves alerts grouped by rule per host based on the provided search criteria.

    Args:
        search_body (AlertsSearchBody): The search criteria for retrieving alerts.

    Returns:
        AlertsByRulePerHostResponse: The response containing the alerts grouped by rule per host.

    """
    aggregated_by_rule_per_host = await collect_and_aggregate_alerts(
        ["agent_name", "rule_description"],
        search_body,
    )
    alerts_by_rule_per_host_list: List[AlertsByRulePerHost] = [
        AlertsByRulePerHost(agent_name=agent_name, rule=rule, number_of_alerts=count)
        for (agent_name, rule), count in aggregated_by_rule_per_host.items()
    ]

    return AlertsByRulePerHostResponse(
        alerts_by_rule_per_host=alerts_by_rule_per_host_list,
        success=bool(alerts_by_rule_per_host_list),
        message="Successfully collected alerts by rule per host",
    )


def parse_timerange(timerange: str) -> str:
    """
    Parses the timerange string and returns the corresponding datetime string for Elasticsearch.
    """
    unit = timerange[-1]
    amount = int(timerange[:-1])

    if unit == "h":
        delta = timedelta(hours=amount)
    elif unit == "d":
        delta = timedelta(days=amount)
    elif unit == "w":
        delta = timedelta(weeks=amount)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid timerange unit. Must be one of 'h', 'd', or 'w'.",
        )

    start_time = datetime.utcnow() - delta
    return start_time.isoformat() + "Z"


async def get_original_alert_id(origin_context: str) -> Tuple[str, str]:
    """
    Extracts the index name and id from the origin_context field of an alert.

    Args:
        origin_context (str): The origin_context field of an alert.

    Returns:
        Tuple[str, str]: A tuple containing the index name and id of the alert.
    """
    index_name, index_id = origin_context.split(":")[-2:]
    return index_name, index_id


# ! THIS IS OLD WITH ASYNC OPERATIONS ! #
# async def get_single_alert_details(
#     index_name: str,
#     index_id: str,
# ) -> Dict:
#     """
#     Retrieves the details of a single alert based on the index name and id.

#     Args:
#         es_client: The Elasticsearch client.
#         index_name (str): The name of the index to search for the alert.
#         index_id (str): The id of the alert to retrieve.

#     Returns:
#         dict: The details of the alert.
#     """
#     es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
#     try:
#         alert = es_client.get(index=index_name, id=index_id)
#         return alert
#     except NotFoundError:
#         logger.warning(f"Alert not found for index {index_name} and id {index_id}")
#         return AlertNotFound(_index=index_name, _id=index_id, _source={"message": "alert not found"}).to_dict()


# async def fetch_alerts_from_graylog(index_prefix: str, size: int, timerange: str) -> List[Dict]:
#     """
#     Fetches alerts from the Graylog Alert Index.

#     Args:
#         es_client: The Elasticsearch client.
#         index_prefix (str): The prefix of the index to search for alerts.
#         size (int): The number of alerts to retrieve.

#     Returns:
#         List[Dict]: A list of alerts.
#     """
#     es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
#     es_query = {
#         "size": size,
#         "query": {
#             "bool": {
#                 "must": [
#                     {
#                         "range": {
#                             "timestamp": {
#                                 "gte": parse_timerange(timerange),
#                                 "format": "strict_date_optional_time",
#                             },
#                         },
#                     },
#                 ],
#             },
#         },
#     }
#     response = await es_client.search(index=index_prefix, body=es_query)
#     logger.info(f"Graylog alerts response: {response}")
#     return response["hits"]["hits"]


# async def process_alert_hits(hits: List[Dict]) -> List[Dict]:
#     """
#     Processes the hits from the Graylog alert search response.

#     Args:
#         es_client: The Elasticsearch client.
#         hits (List[Dict]): The hits from the search response.

#     Returns:
#         List[Dict]: A list of detailed alerts.
#     """
#     alerts_dict = defaultdict(lambda: {"total_alerts": 0, "alerts": []})

#     for hit in hits:
#         origin_context = hit["_source"]["origin_context"]
#         index_name, index_id = await get_original_alert_id(origin_context)
#         logger.info(f"Fetching alert details for index {index_name} and id {index_id}")
#         alert_details = await get_single_alert_details(index_name, index_id)
#         logger.info(f"Alert details: {alert_details}")

#         alerts_dict[index_name]["total_alerts"] += 1
#         alerts_dict[index_name]["alerts"].append(alert_details)

#     alerts = [
#         Alert(index_name=index_name, total_alerts=data["total_alerts"], alerts=data["alerts"]) for index_name, data in alerts_dict.items()
#     ]

#     return alerts


# async def get_graylog_alerts(
#     request: GraylogAlertsSearchBody,
# ) -> AlertsSearchResponse:
#     """
#     Retrieves alerts from the Graylog Alert Index.
#     Looks up the actual alert details via the origin_context field.
#     Strips out the index name and id from the origin_context field.
#     Example: urn:graylog:message:es:huntress_00002_0:b4d2c721-f690-11ee-ac73-8600007a2218
#     Looks up each alert by the index name and id.
#     Adds each alert to the response.
#     """
#     logger.info(f"Fetching Graylog alerts for request: {request}")

#     hits = await fetch_alerts_from_graylog(request.index_prefix, request.size, request.timerange)
#     alerts = await process_alert_hits(hits)

#     return alerts

# ! ^^THIS IS OLD WITH ASYNC OPERATIONS^^ ! #


async def get_single_alert_details(
    es_client: AsyncElasticsearch,
    index_name: str,
    index_id: str,
) -> Dict:
    """
    Retrieves the details of a single alert based on the index name and id.

    Args:
        es_client: The Elasticsearch client.
        index_name (str): The name of the index to search for the alert.
        index_id (str): The id of the alert to retrieve.

    Returns:
        dict: The details of the alert.
    """
    try:
        alert = await es_client.get(index=index_name, id=index_id)
        return alert
    except NotFoundError:
        logger.warning(f"Alert not found for index {index_name} and id {index_id}")
        return AlertNotFound(_index=index_name, _id=index_id, _source={"message": "alert not found"}).to_dict()


async def fetch_alerts_from_graylog(index_prefix: str, size: int, timerange: str) -> List[Dict]:
    """
    Fetches alerts from the Graylog Alert Index.

    Args:
        es_client: The Elasticsearch client.
        index_prefix (str): The prefix of the index to search for alerts.
        size (int): The number of alerts to retrieve.

    Returns:
        List[Dict]: A list of alerts.
    """
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    es_query = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "timestamp": {
                                "gte": parse_timerange(timerange),
                                "format": "strict_date_optional_time",
                            },
                        },
                    },
                ],
            },
        },
    }
    response = await es_client.search(index=index_prefix, body=es_query)
    logger.info(f"Graylog alerts response: {response}")
    return response["hits"]["hits"]


async def process_alert_hits(hits: List[Dict], es_client: AsyncElasticsearch) -> List[Dict]:
    """
    Processes the hits from the Graylog alert search response.

    Args:
        es_client: The Elasticsearch client.
        hits (List[Dict]): The hits from the search response.

    Returns:
        List[Dict]: A list of detailed alerts.
    """
    alerts_dict = defaultdict(lambda: {"total_alerts": 0, "alerts": []})

    tasks = []
    for hit in hits:
        origin_context = hit["_source"]["origin_context"]
        index_name, index_id = await get_original_alert_id(origin_context)
        logger.info(f"Fetching alert details for index {index_name} and id {index_id}")
        task = get_single_alert_details(es_client, index_name, index_id)
        tasks.append(task)

    alert_details_list = await asyncio.gather(*tasks)

    for alert_details in alert_details_list:
        index_name = alert_details["_index"]
        alerts_dict[index_name]["total_alerts"] += 1
        alerts_dict[index_name]["alerts"].append(alert_details)

    alerts = [
        {"index_name": index_name, "total_alerts": data["total_alerts"], "alerts": data["alerts"]}
        for index_name, data in alerts_dict.items()
    ]

    logger.info(f"Processed alerts: {alerts}")

    return alerts


async def get_graylog_alerts(
    request: GraylogAlertsSearchBody,
) -> AlertsSearchResponse:
    """
    Retrieves alerts from the Graylog Alert Index.
    Looks up the actual alert details via the origin_context field.
    Strips out the index name and id from the origin_context field.
    Example: urn:graylog:message:es:huntress_00002_0:b4d2c721-f690-11ee-ac73-8600007a2218
    Looks up each alert by the index name and id.
    Adds each alert to the response.
    """
    logger.info(f"Fetching Graylog alerts for request: {request}")

    hits = await fetch_alerts_from_graylog(request.index_prefix, request.size, request.timerange)
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

    return await process_alert_hits(hits, es_client)
