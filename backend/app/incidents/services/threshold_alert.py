"""
Service functions for threshold alert event resolution and timeline retrieval.

When a Graylog threshold alert fires, there is no individual event _index/_id available.
This module uses the replay_info (Lucene query + timerange) and group_by_fields from the
Graylog webhook to find the first matching event in OpenSearch, and provides timeline
retrieval for threshold alerts using stored metadata.
"""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.incidents.config.threshold_index_mapping import get_index_config_for_source
from app.incidents.models import AssetFieldName
from app.incidents.models import ThresholdAlertMetadata


def _format_datetime(dt: datetime) -> str:
    """Format a datetime for OpenSearch range queries, matching the index time format."""
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


async def resolve_threshold_event(
    replay_query: str,
    timerange_start: datetime,
    timerange_end: datetime,
    group_by_fields: Dict[str, str],
    source: str,
) -> Tuple[str, str]:
    """
    Query OpenSearch to find the first event matching a threshold alert's conditions.

    Uses the replay_info from the Graylog webhook to reconstruct the search and find
    the actual underlying event that contributed to the threshold count.

    Args:
        replay_query: Lucene query string from replay_info.query (e.g. "rule_id:5503").
        timerange_start: Start of the threshold evaluation window.
        timerange_end: End of the threshold evaluation window.
        group_by_fields: Group-by field values from the threshold event (e.g. {"data_dstuser": "taylor"}).
        source: The SOURCE field from the Graylog alert (e.g. "wazuh").

    Returns:
        Tuple of (index_name, index_id) from the first matching hit,
        or ("not_applicable", "not_applicable") if no event is found or source is unmapped.
    """
    try:
        index_pattern, time_field = get_index_config_for_source(source)
    except ValueError:
        return ("not_applicable", "not_applicable")

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        must_clauses: List[Dict[str, Any]] = [
            {"query_string": {"query": replay_query, "default_operator": "AND"}},
            {
                "range": {
                    time_field: {
                        "gte": _format_datetime(timerange_start),
                        "lte": _format_datetime(timerange_end),
                    },
                },
            },
        ]

        # Add match clauses for each group_by_fields entry
        for field_name, field_value in group_by_fields.items():
            if field_value:
                must_clauses.append({"match": {field_name: field_value}})

        query = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{time_field: {"order": "asc"}}],
        }

        logger.info(
            f"Resolving threshold event for source '{source}' in index '{index_pattern}' "
            f"with query: {replay_query}, group_by: {group_by_fields}, "
            f"timerange: {timerange_start} -> {timerange_end}",
        )

        response = await es_client.search(index=index_pattern, body=query, size=1)
        hits = response["hits"]["hits"]

        if hits:
            hit = hits[0]
            resolved_index = hit["_index"]
            resolved_id = hit["_id"]
            logger.info(f"Resolved threshold event: index={resolved_index}, id={resolved_id}")
            return (resolved_index, resolved_id)

        logger.warning(
            f"No matching event found for threshold alert in '{index_pattern}' "
            f"with query '{replay_query}' and group_by {group_by_fields}",
        )
        return ("not_applicable", "not_applicable")

    except Exception as e:
        logger.error(f"Error resolving threshold event: {e}")
        return ("not_applicable", "not_applicable")
    finally:
        await es_client.close()


async def resolve_threshold_asset(
    index_name: str,
    index_id: str,
    source: str,
    session: AsyncSession,
) -> str:
    """
    Fetch the resolved event document from OpenSearch and resolve the asset name
    using the AssetFieldName configuration for the given source.

    Args:
        index_name: The OpenSearch index name of the resolved event.
        index_id: The OpenSearch document ID of the resolved event.
        source: The source type (e.g. "wazuh").
        session: Database session for looking up asset field names.

    Returns:
        The resolved asset name, or "No asset found" if resolution fails.
    """
    if index_name == "not_applicable" or index_id == "not_applicable":
        return "No asset found"

    # Look up asset field names for this source from the database
    result = await session.execute(
        select(AssetFieldName.field_name).where(AssetFieldName.source == source).distinct(),
    )
    asset_field_name = result.scalars().first()
    if not asset_field_name:
        logger.warning(f"No asset field name configured for source '{source}'")
        return "No asset found"

    possible_fields = [f.strip() for f in asset_field_name.split(",")]
    logger.info(f"Asset field candidates for source '{source}': {possible_fields}")

    # Fetch the event document from OpenSearch
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        doc = await es_client.get(index=index_name, id=index_id)
        event_source = doc.get("_source", {})

        for field in possible_fields:
            if field in event_source and event_source[field]:
                logger.info(f"Resolved threshold asset name '{event_source[field]}' from field '{field}'")
                return event_source[field]

        logger.warning(f"No asset name found in event for fields: {possible_fields}")
        return "No asset found"
    except Exception as e:
        logger.error(f"Error fetching event for asset resolution: {e}")
        return "No asset found"
    finally:
        await es_client.close()


async def save_threshold_metadata(
    alert_id: int,
    event_definition_id: str,
    replay_query: str,
    timerange_start: datetime,
    timerange_end: datetime,
    group_by_fields: Dict[str, str],
    source_streams: List[str],
    source: str,
    resolved_index_name: str,
    resolved_index_id: str,
    session: AsyncSession,
) -> ThresholdAlertMetadata:
    """
    Persist threshold alert metadata to the database for later timeline retrieval.

    Args:
        alert_id: The CoPilot alert ID returned by create_alert_full.
        event_definition_id: The Graylog event definition ID.
        replay_query: Lucene query from replay_info.query.
        timerange_start: Start of the threshold evaluation window.
        timerange_end: End of the threshold evaluation window.
        group_by_fields: Group-by field key/value pairs.
        source_streams: Graylog source stream IDs.
        source: The SOURCE field value (e.g. "wazuh").
        resolved_index_name: OpenSearch index name of the resolved event.
        resolved_index_id: OpenSearch document ID of the resolved event.
        session: Database session.

    Returns:
        The created ThresholdAlertMetadata record.
    """
    metadata = ThresholdAlertMetadata(
        alert_id=alert_id,
        event_definition_id=event_definition_id,
        replay_query=replay_query,
        timerange_start=timerange_start,
        timerange_end=timerange_end,
        group_by_fields=group_by_fields,
        source_streams=source_streams,
        source=source,
        resolved_index_name=resolved_index_name,
        resolved_index_id=resolved_index_id,
    )
    session.add(metadata)
    await session.commit()
    logger.info(f"Saved threshold alert metadata for alert ID {alert_id}")
    return metadata


async def retrieve_threshold_alert_timeline(
    alert_id: int,
    session: AsyncSession,
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve the timeline for a threshold alert using stored metadata.

    Queries OpenSearch using the stored replay_query, group_by_fields, and timerange
    from the ThresholdAlertMetadata table.

    Args:
        alert_id: The CoPilot alert ID.
        session: Database session.

    Returns:
        List of OpenSearch hit dicts if this is a threshold alert, or None if no
        threshold metadata exists for this alert_id (meaning it's not a threshold alert).
    """
    result = await session.execute(
        select(ThresholdAlertMetadata).where(ThresholdAlertMetadata.alert_id == alert_id),
    )
    metadata = result.scalars().first()

    if metadata is None:
        return None

    try:
        index_pattern, time_field = get_index_config_for_source(metadata.source)
    except ValueError:
        logger.warning(f"Cannot retrieve threshold timeline: source '{metadata.source}' is not mapped")
        return []

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        must_clauses: List[Dict[str, Any]] = [
            {"query_string": {"query": metadata.replay_query, "default_operator": "AND"}},
            {
                "range": {
                    time_field: {
                        "gte": _format_datetime(metadata.timerange_start),
                        "lte": _format_datetime(metadata.timerange_end),
                    },
                },
            },
        ]

        group_by = metadata.group_by_fields or {}
        for field_name, field_value in group_by.items():
            if field_value:
                must_clauses.append({"match": {field_name: field_value}})

        query = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{time_field: {"order": "asc"}}],
        }

        logger.info(
            f"Fetching threshold alert timeline for alert ID {alert_id} "
            f"in index '{index_pattern}' with query: {metadata.replay_query}",
        )

        response = await es_client.search(index=index_pattern, body=query, size=50)
        return response["hits"]["hits"]

    except Exception as e:
        logger.error(f"Error fetching threshold alert timeline for alert ID {alert_id}: {e}")
        return []
    finally:
        await es_client.close()
