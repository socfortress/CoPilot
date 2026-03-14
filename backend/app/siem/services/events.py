from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client_async
from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.db.universal_models import EventSources
from app.siem.schema.events import EventsQueryParams
from app.siem.schema.events import EventsQueryResponse


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
    )


async def _initial_search(
    index_pattern: str,
    time_field: str,
    timerange: str,
    page_size: int,
) -> EventsQueryResponse:
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        query_builder = AlertsQueryBuilder()
        query_builder.add_time_range(timerange=timerange, timestamp_field=time_field)
        query_builder.add_sort(time_field, order="desc")
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
            events=[hit["_source"] for hit in hits],
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
            events=[hit["_source"] for hit in hits],
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
