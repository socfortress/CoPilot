from loguru import logger

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.connectors.wazuh_indexer.utils.universal import (
    return_graylog_events_index_names,
)
from app.incidents.schema.alert_collection import AlertPayloadItem
from app.incidents.schema.alert_collection import AlertsPayload
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import IndexNamesResponse


async def get_graylog_event_indices() -> IndexNamesResponse:
    """
    Get the Graylog event indices. Get the Graylog event indices for the Graylog events.

    Returns:
        List[str]: The list of Graylog event indices.
    """
    # return await return_graylog_events_index_names()
    return IndexNamesResponse(index_names=await return_graylog_events_index_names(), success=True, message="Success")


async def construct_query():
    """
    Constructs the query to find alerts where `fields.COPILOT_ALERT_ID` is NONE.
    """
    return {"query": {"bool": {"must": [{"term": {"fields.COPILOT_ALERT_ID": "NONE"}}]}}}


async def fetch_alerts_for_index(es_client, index, query):
    """
    Fetches alerts for a given index that match the query using the Elasticsearch scroll API.
    """
    # Start the initial search request
    response = es_client.search(
        index=index,
        body=query,
        scroll="2m",
        size=1000,  # Keep the search context open for 2 minutes  # Number of results per "page"
    )
    scroll_id = response["_scroll_id"]
    hits = response["hits"]["hits"]

    # Keep fetching results while there are still results to fetch
    while len(response["hits"]["hits"]):
        response = es_client.scroll(scroll_id=scroll_id, scroll="2m")  # Extend the scroll context for another 2 minutes
        # Update the scroll ID in case it changes
        scroll_id = response["_scroll_id"]
        hits.extend(response["hits"]["hits"])

    # Close the scroll context
    es_client.clear_scroll(scroll_id=scroll_id)

    return [AlertPayloadItem(**hit) for hit in hits]


async def get_alerts_not_created_in_copilot() -> AlertsPayload:
    """
    Get the Graylog event indices. Then get all the results from the list of indices, where `copilot_alert_id` does not exist.
    """
    indices = await return_graylog_events_index_names()
    logger.info(f"Indices: {indices}")
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    query = await construct_query()

    alerts_not_created = []
    for index in indices:
        alerts = await fetch_alerts_for_index(es_client, index, query)
        alerts_not_created.extend(alerts)

    logger.info(f"Alerts not created: {len(alerts_not_created)} alerts found")
    return AlertsPayload(alerts=alerts_not_created)


async def get_original_alert_id(origin_context: str):
    """
    Get the original alert id from the origin context.
    """
    # Assuming the ID is the last part after the last colon and before the last underscore
    try:
        return origin_context.split(":")[-1].split("_")[-1]
    except IndexError:  # In case the origin_context does not follow the expected pattern
        return None


async def get_original_alert_index_name(origin_context: str):
    """
    Get the original alert index name from the origin context.
    """
    # Assuming the index name is the part after 'es:' and before the next colon
    try:
        return origin_context.split("es:")[-1].split(":")[0]
    except IndexError:  # In case the origin_context does not follow the expected pattern
        return None


async def add_copilot_alert_id(index_data: CreateAlertRequest, alert_id: int):
    """
    Add the CoPilot alert ID to the Graylog event.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    body = {"doc": {"fields": {"COPILOT_ALERT_ID": f"{alert_id}"}}}
    try:
        es_client.update(index=index_data.index_name, id=index_data.alert_id, body=body)
        logger.info(f"Added CoPilot alert ID {alert_id} to Graylog event {index_data.alert_id} in index {index_data.index_name}")
    except Exception as e:
        logger.error(
            f"Failed to add CoPilot alert ID {alert_id} to Graylog event {index_data.alert_id} in index {index_data.index_name}: {e}",
        )

        # Attempt to remove read-only block
        try:
            es_client.indices.put_settings(index=index_data.index_name, body={"index.blocks.write": None})
            logger.info(f"Removed read-only block from index {index_data.index_name}. Retrying update.")

            # Retry the update operation
            es_client.update(index=index_data.index_name, id=index_data.alert_id, body=body)
            logger.info(
                f"Added CoPilot alert ID {alert_id} to Graylog event {index_data.alert_id} in index {index_data.index_name} after removing read-only block",
            )

            # Re-enable the write block
            es_client.indices.put_settings(index=index_data.index_name, body={"index.blocks.write": True})
        except Exception as e2:
            logger.error(f"Failed to remove read-only block from index {index_data.index_name}: {e2}")

    return None
