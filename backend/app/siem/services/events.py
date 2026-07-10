import fnmatch

from elasticsearch7.exceptions import NotFoundError
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import EventSources
from app.siem.schema.events import EventDocumentResponse
from app.siem.schema.events import EventsQueryParams
from app.siem.schema.events import EventsQueryResponse
from app.siem.schema.events import FieldMapping
from app.siem.schema.events import FieldMappingsResponse


def _event_from_hit(hit: dict) -> dict:
    return {**hit["_source"], "_id": hit["_id"], "_index": hit["_index"]}


def _index_matches_pattern(index_name: str, index_pattern: str) -> bool:
    # ponytail: fnmatch only — ES comma/exclusion patterns need a richer matcher later.
    return fnmatch.fnmatchcase(index_name, index_pattern)


async def get_event_source_by_customer_and_name(
    customer_code: str,
    source_name: str,
    db: AsyncSession,
) -> EventSources:
    result = await db.execute(
        select(EventSources).where(
            EventSources.customer_code == customer_code,
            EventSources.name == source_name,
        ),
    )
    event_source = result.scalars().first()
    if not event_source:
        raise HTTPException(
            status_code=404,
            detail=f"Event source '{source_name}' not found for customer {customer_code}",
        )
    if not event_source.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Event source '{source_name}' is disabled",
        )
    return event_source


async def query_events(
    customer_code: str,
    source_name: str,
    params: EventsQueryParams,
    db: AsyncSession,
) -> EventsQueryResponse:
    logger.info(f"Querying events for customer {customer_code}, source {source_name}")

    # If a scroll_id is provided, continue scrolling
    if params.scroll_id:
        return await _scroll_next_page(params.scroll_id)

    # Look up event source to get index_pattern and time_field
    event_source = await get_event_source_by_customer_and_name(customer_code, source_name, db)

    return await _initial_search(
        index_pattern=event_source.index_pattern,
        time_field=event_source.time_field,
        timerange=params.timerange,
        page_size=params.page_size,
        query=params.query,
        time_from=params.time_from,
        time_to=params.time_to,
    )


async def _initial_search(
    index_pattern: str,
    time_field: str,
    timerange: str,
    page_size: int,
    query: str = None,
    time_from: str = None,
    time_to: str = None,
) -> EventsQueryResponse:
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        query_builder = AlertsQueryBuilder()
        if time_from and time_to:
            query_builder.add_absolute_time_range(time_from=time_from, time_to=time_to, timestamp_field=time_field)
        else:
            query_builder.add_time_range(timerange=timerange, timestamp_field=time_field)
        query_builder.add_sort(time_field, order="desc")

        # Add Lucene query_string if provided
        if query:
            query_builder.query["query"]["bool"]["must"].append(
                {"query_string": {"query": query, "default_operator": "AND"}},
            )

        query = query_builder.build()

        response = await es_client.search(
            index=index_pattern,
            body=query,
            size=page_size,
            scroll="5m",
        )

        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"]
        scroll_id = response.get("_scroll_id")

        # If all results fit in one page, clear the scroll context
        if len(hits) >= total:
            if scroll_id:
                await _clear_scroll(es_client, scroll_id)
                scroll_id = None

        return EventsQueryResponse(
            events=[_event_from_hit(hit) for hit in hits],
            total=total,
            scroll_id=scroll_id,
            page_size=page_size,
            success=True,
            message=f"Retrieved {len(hits)} of {total} events",
        )
    except Exception as e:
        logger.error(f"Error querying events: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying events: {e}")
    finally:
        await es_client.close()


async def _scroll_next_page(scroll_id: str) -> EventsQueryResponse:
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        response = await es_client.scroll(scroll_id=scroll_id, scroll="5m")
        hits = response["hits"]["hits"]
        total = response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"]
        new_scroll_id = response.get("_scroll_id")

        # If no more results, clear the scroll context
        if not hits:
            if new_scroll_id:
                await _clear_scroll(es_client, new_scroll_id)
            return EventsQueryResponse(
                events=[],
                total=total,
                scroll_id=None,
                page_size=0,
                success=True,
                message="No more results",
            )

        return EventsQueryResponse(
            events=[_event_from_hit(hit) for hit in hits],
            total=total,
            scroll_id=new_scroll_id,
            page_size=len(hits),
            success=True,
            message=f"Retrieved {len(hits)} of {total} events",
        )
    except Exception as e:
        logger.error(f"Error scrolling events: {e}")
        raise HTTPException(status_code=500, detail=f"Error scrolling events: {e}")
    finally:
        await es_client.close()


async def _clear_scroll(es_client, scroll_id: str) -> None:
    try:
        await es_client.clear_scroll(scroll_id=scroll_id)
    except Exception as e:
        logger.warning(f"Failed to clear scroll context: {e}")


async def get_event_document(
    customer_code: str,
    source_name: str,
    index_name: str,
    event_id: str,
    db: AsyncSession,
) -> EventDocumentResponse:
    event_source = await get_event_source_by_customer_and_name(customer_code, source_name, db)
    if not _index_matches_pattern(index_name, event_source.index_pattern):
        raise HTTPException(
            status_code=400,
            detail=f"Index '{index_name}' does not match event source pattern '{event_source.index_pattern}'",
        )

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        doc = await es_client.get(index=index_name, id=event_id)
        return EventDocumentResponse(
            event=_event_from_hit(doc),
            success=True,
            message="Event retrieved",
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_id}' not found in index '{index_name}'",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event document: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching event: {e}")
    finally:
        await es_client.close()


async def get_field_mappings(
    customer_code: str,
    source_name: str,
    db: AsyncSession,
) -> FieldMappingsResponse:
    """Retrieve index field name mappings for a customer's event source."""
    event_source = await get_event_source_by_customer_and_name(customer_code, source_name, db)
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        mapping_response = await es_client.indices.get_mapping(index=event_source.index_pattern)

        # Flatten nested mappings into dot-notation field list
        fields = []
        for index_name in mapping_response:
            properties = mapping_response[index_name].get("mappings", {}).get("properties", {})
            _flatten_properties(properties, "", fields)
            break  # All indices matching pattern share the same mapping

        # Deduplicate and sort
        seen = set()
        unique_fields = []
        for f in fields:
            if f.field not in seen:
                seen.add(f.field)
                unique_fields.append(f)
        unique_fields.sort(key=lambda x: x.field)

        return FieldMappingsResponse(
            fields=unique_fields,
            total=len(unique_fields),
            index_pattern=event_source.index_pattern,
            success=True,
            message=f"Retrieved {len(unique_fields)} field mappings",
        )
    except Exception as e:
        logger.error(f"Error retrieving field mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving field mappings: {e}")
    finally:
        await es_client.close()


def _assert_event_helpers() -> None:
    hit = {"_id": "doc-1", "_index": "wazuh-alerts-4", "_source": {"id": "evt-1"}}
    event = _event_from_hit(hit)
    assert event["_id"] == "doc-1" and event["id"] == "evt-1"
    assert _index_matches_pattern("wazuh-alerts-4-2026.07.10", "wazuh-alerts-*")
    assert not _index_matches_pattern("office365-foo", "wazuh-alerts-*")


def _flatten_properties(properties: dict, prefix: str, fields: list) -> None:
    """Recursively flatten OpenSearch mapping properties into FieldMapping objects."""
    for field_name, field_info in properties.items():
        full_name = f"{prefix}{field_name}" if not prefix else f"{prefix}_{field_name}"
        field_type = field_info.get("type")
        if field_type:
            fields.append(FieldMapping(field=full_name, type=field_type))
        # Recurse into nested properties
        if "properties" in field_info:
            _flatten_properties(field_info["properties"], full_name, fields)
