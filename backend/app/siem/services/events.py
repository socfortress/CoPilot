import fnmatch
import re
from typing import List
from typing import Optional
from typing import Sequence

from elasticsearch7.exceptions import NotFoundError
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
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
from app.siem.schema.events import MultiSourceEventsQuery
from app.siem.utils.scroll_token import open_multi_scroll
from app.siem.utils.scroll_token import open_scroll
from app.siem.utils.scroll_token import sign_multi_scroll
from app.siem.utils.scroll_token import sign_scroll

DATE_TYPES = {"date", "date_nanos"}
NO_LONGER_VALID = "These results are no longer valid: run the search again"
_GLOB = re.compile(r"[*?]")


def _event_from_hit(hit: dict) -> dict:
    return {**hit["_source"], "_id": hit["_id"], "_index": hit["_index"]}


def _pattern_parts(index_pattern: str) -> List[str]:
    return [part.strip() for part in (index_pattern or "").split(",") if part.strip()]


def index_in_pattern(index_name: str, index_pattern: str) -> bool:
    """Whether the indexer would search ``index_name`` for ``index_pattern``.

    A pattern is a comma list of globs, read left to right: a part starting with ``-`` removes
    what the parts before it matched, and a later part can add an index back. The frontend's
    ``eventSearch.helpers.ts:indexMatchesPattern`` applies the same rule.
    """
    included = False
    for part in _pattern_parts(index_pattern):
        if part.startswith("-"):
            if included and fnmatch.fnmatchcase(index_name, part[1:]):
                included = False
        elif fnmatch.fnmatchcase(index_name, part):
            included = True
    return included


def _index_matches_pattern(index_name: str, index_pattern: str) -> bool:
    return index_in_pattern(index_name, index_pattern)


def _specificity(index_name: str, index_pattern: str) -> int:
    """How literally a pattern names an index: the literal length of its longest part matching it."""
    return max(
        (
            len(_GLOB.sub("", part))
            for part in _pattern_parts(index_pattern)
            if not part.startswith("-") and fnmatch.fnmatchcase(index_name, part)
        ),
        default=-1,
    )


def source_for_index(index_name: str, sources: Sequence[EventSources]) -> Optional[EventSources]:
    """The source an event of ``index_name`` came from: the one whose pattern names it most literally.

    Two sources' patterns can both match an index (``fortigate-acme*`` and a catch-all ``*-acme*``);
    the most specific wins, the first one asked for on a tie.
    """
    candidates = [source for source in sources if index_in_pattern(index_name, source.index_pattern)]
    if not candidates:
        return None
    return max(candidates, key=lambda source: _specificity(index_name, source.index_pattern))


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

    # Look up event source to get index_pattern and time_field. A next page needs it too:
    # a source disabled or removed since the first page stops there.
    event_source = await get_event_source_by_customer_and_name(customer_code, source_name, db)
    secret = AuthHandler().secret

    if params.scroll_id:
        # Only a token issued for this customer and source continues: the route checked the
        # caller may see the customer, and the token is what ties the scroll to it.
        scroll_id = open_scroll(params.scroll_id, customer_code, source_name, secret)
        if scroll_id is None:
            raise HTTPException(status_code=400, detail=NO_LONGER_VALID)
        response = await _scroll_next_page(scroll_id)
    else:
        response = await _initial_search(
            index_pattern=event_source.index_pattern,
            time_field=event_source.time_field,
            timerange=params.timerange,
            page_size=params.page_size,
            query=params.query,
            time_from=params.time_from,
            time_to=params.time_to,
        )

    response.scroll_id = sign_scroll(response.scroll_id, customer_code, source_name, secret)
    return response


def _shard_warnings(response: dict) -> List[str]:
    """What the indexer said about a page it could only partly answer."""
    shards = response.get("_shards") or {}
    failed = shards.get("failed") or 0
    if not failed:
        return []
    return [f"{failed} of {shards.get('total', failed)} shards could not answer: the results may be incomplete"]


async def _initial_search(
    index_pattern: str,
    time_field: str,
    timerange: str,
    page_size: int,
    query: str = None,
    time_from: str = None,
    time_to: str = None,
    unmapped_sort: bool = False,
) -> EventsQueryResponse:
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        query_builder = AlertsQueryBuilder()
        if time_from and time_to:
            query_builder.add_absolute_time_range(time_from=time_from, time_to=time_to, timestamp_field=time_field)
        else:
            query_builder.add_time_range(timerange=timerange, timestamp_field=time_field)
        query_builder.add_sort(time_field, order="desc")
        if unmapped_sort:
            # Several sources' indices: one that doesn't map the time field sorts last instead of
            # failing its shards.
            query_builder.query["sort"] = [{time_field: {"order": "desc", "unmapped_type": "date"}}]

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
            warnings=_shard_warnings(response),
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
            warnings=_shard_warnings(response),
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
    """Retrieve the field names available across a customer's event source.

    Uses `_field_caps` rather than `_mapping` because an event source pattern routinely
    spans many indices whose mappings diverge: a quiet period or a dynamically-mapped
    field means one index can be missing fields another has, so reading a single index's
    mapping under-reports the source (#1114). `_field_caps` answers exactly this question
    -- the union of fields over every matching index -- in one response instead of a full
    mapping per index, and it echoes each field path as the mapping declares it, so no
    path is re-derived here and already-configured columns keep resolving.
    """
    event_source = await get_event_source_by_customer_and_name(customer_code, source_name, db)
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        response = await es_client.field_caps(
            index=event_source.index_pattern,
            fields="*",
            ignore_unavailable=True,
            allow_no_indices=True,
        )
        fields = _fields_from_field_caps(response.get("fields", {}))

        return FieldMappingsResponse(
            fields=fields,
            total=len(fields),
            index_pattern=event_source.index_pattern,
            success=True,
            message=f"Retrieved {len(fields)} field mappings",
        )
    except Exception as e:
        logger.error(f"Error retrieving field mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving field mappings: {e}")
    finally:
        await es_client.close()


def _fields_from_field_caps(field_caps: dict) -> list:
    """Project a `_field_caps` `fields` object into a sorted FieldMapping list.

    Three kinds of entry are dropped as noise in a column picker: metadata fields
    (`_id`, `_index`, ...), container fields (`object`/`nested`, which hold no value of
    their own -- the previous `_mapping` walk skipped them for the same reason), and
    multi-field subfields whose parent leaf is also present (`full_log.keyword` when
    `full_log` exists). A field mapped with conflicting types across indices reports
    every type rather than silently picking a winner.
    """
    leaf_names = {name for name, caps in field_caps.items() if _leaf_types(caps)}

    fields = []
    for field_name, caps_by_type in field_caps.items():
        types = _leaf_types(caps_by_type)
        if not types:
            continue
        if any(caps.get("metadata_field") for caps in caps_by_type.values() if isinstance(caps, dict)):
            continue
        # A dotted name whose parent is itself a leaf field can only be a multi-field
        # (an object's children have an object-typed parent, so they survive this test).
        parent, _, _ = field_name.rpartition(".")
        if parent and parent in leaf_names:
            continue
        fields.append(FieldMapping(field=field_name, type=", ".join(sorted(types)), conflict=len(types) > 1))

    fields.sort(key=lambda f: f.field)
    return fields


def _leaf_types(caps_by_type) -> set:
    """Type names under one `_field_caps` entry, excluding the container types."""
    if not isinstance(caps_by_type, dict):
        return set()
    return {field_type for field_type in caps_by_type if field_type not in ("object", "nested")}


# ── one search across several sources (#1356) ────────────────────────────────
#
# The sources are the customer's own (looked up by the path's customer, which the route checked),
# so their patterns are what bounds the search, as for one source: only an admin sets a pattern.
# One query runs over the patterns together, sorted on the time field they share. What makes that
# safe is checked before the indexer is asked: one time field name, mapped as a date in every index
# (a date in one index and a keyword in another makes the whole search fail; one name holding epoch
# milliseconds in one source and ISO text in another sorts one source after the other).


async def _sources(customer_code: str, names: Sequence[str], db: AsyncSession) -> List[EventSources]:
    return [await get_event_source_by_customer_and_name(customer_code, name, db) for name in names]


def _excludes(index_pattern: str) -> bool:
    return any(part.startswith("-") for part in _pattern_parts(index_pattern))


def combined_pattern(sources: Sequence[EventSources]) -> str:
    """The sources' index patterns as one, in the order asked for, a pattern with an exclusion first.

    The indexer applies an exclusion (``-fortigate-acme-old*``) to every part before it, so a
    source's exclusion placed after another source would also remove that source's indices. First,
    it removes only its own. Two sources with exclusions can still narrow each other's indices;
    the search never covers an index that none of the sources covers on its own.
    """
    ordered = sorted(sources, key=lambda source: not _excludes(source.index_pattern))
    return ",".join(source.index_pattern for source in ordered)


def shared_time_field(sources: Sequence[EventSources]) -> str:
    fields = {source.time_field for source in sources}
    if len(fields) > 1:
        named = ", ".join(f"{source.name}: {source.time_field}" for source in sources)
        raise HTTPException(
            status_code=400,
            detail=f"These sources use different time fields ({named}). Search them one at a time, or give them the same time field.",
        )
    return sources[0].time_field


async def check_time_field_is_a_date(index_pattern: str, time_field: str) -> None:
    """400 unless every index of ``index_pattern`` that maps ``time_field`` maps it as a date."""
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        response = await es_client.field_caps(index=index_pattern, fields=time_field, ignore_unavailable=True, allow_no_indices=True)
    except Exception as e:
        logger.error(f"Could not read the type of {time_field} in {index_pattern}: {e}")
        raise HTTPException(status_code=502, detail="Could not check these sources' time field: try again")
    finally:
        await es_client.close()
    types = set((response.get("fields") or {}).get(time_field, {}))
    if types - DATE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"These sources can't be searched together: their time field {time_field} is not a date in every index "
                f"({', '.join(sorted(types))}). Search them one at a time."
            ),
        )


def _tagged(response: EventsQueryResponse, sources: Sequence[EventSources]) -> EventsQueryResponse:
    """Each event names the source it came from (``_source_name``), so the results can say so."""
    for event in response.events:
        source = source_for_index(str(event.get("_index", "")), sources)
        event["_source_name"] = source.name if source is not None else None
    return response


async def query_events_multi(customer_code: str, request: MultiSourceEventsQuery, db: AsyncSession) -> EventsQueryResponse:
    """A page of events from several of a customer's sources at once, newest first."""
    sources = await _sources(customer_code, request.sources, db)
    names = [source.name for source in sources]
    logger.info(f"Querying events for customer {customer_code}, sources {names}")
    secret = AuthHandler().secret

    if request.scroll_id:
        # As for one source: the token continues only the search it was issued for, and the
        # sources are looked up again first, so one disabled since stops the paging there.
        scroll_id = open_multi_scroll(request.scroll_id, customer_code, names, secret)
        if scroll_id is None:
            raise HTTPException(status_code=400, detail=NO_LONGER_VALID)
        response = await _scroll_next_page(scroll_id)
    else:
        time_field = shared_time_field(sources)
        index_pattern = combined_pattern(sources)
        await check_time_field_is_a_date(index_pattern, time_field)
        response = await _initial_search(
            index_pattern=index_pattern,
            time_field=time_field,
            timerange=request.timerange,
            page_size=request.page_size,
            query=request.query,
            time_from=request.time_from,
            time_to=request.time_to,
            unmapped_sort=True,
        )

    response.scroll_id = sign_multi_scroll(response.scroll_id, customer_code, names, secret)
    return _tagged(response, sources)


async def get_field_mappings_multi(customer_code: str, names: Sequence[str], db: AsyncSession) -> FieldMappingsResponse:
    """The fields of several sources together; a field their indices type differently is marked ``conflict``."""
    sources = await _sources(customer_code, names, db)
    index_pattern = combined_pattern(sources)
    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    try:
        response = await es_client.field_caps(index=index_pattern, fields="*", ignore_unavailable=True, allow_no_indices=True)
        fields = _fields_from_field_caps(response.get("fields", {}))
        return FieldMappingsResponse(
            fields=fields,
            total=len(fields),
            index_pattern=index_pattern,
            success=True,
            message=f"Retrieved {len(fields)} field mappings",
        )
    except Exception as e:
        logger.error(f"Error retrieving field mappings: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving field mappings")
    finally:
        await es_client.close()
