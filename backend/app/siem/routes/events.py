from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler
from app.siem.schema.events import EventDocumentResponse
from app.siem.schema.events import EventsQueryParams
from app.siem.schema.events import EventsQueryResponse
from app.siem.schema.events import FieldMappingsResponse
from app.siem.schema.events import MultiSourceEventsQuery
from app.siem.schema.events import MultiSourceFieldsQuery
from app.siem.services.events import get_event_document
from app.siem.services.events import get_field_mappings
from app.siem.services.events import get_field_mappings_multi
from app.siem.services.events import query_events
from app.siem.services.events import query_events_multi

siem_events_router = APIRouter()


# Several sources of one customer at once (#1356). POST, so the routes never collide with
# ``GET /{customer_code}/{source_name}`` (a source may be called "search" or "fields") and the
# query stays out of the URL. Only the SOC's: the Customer Portal searches one source at a time.


@siem_events_router.post(
    "/{customer_code}/search",
    response_model=EventsQueryResponse,
    description="Query events across several of a customer's event sources at once (each event names its source in _source_name)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def query_events_multi_endpoint(
    customer_code: str,
    request: MultiSourceEventsQuery,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventsQueryResponse:
    logger.info(f"Querying events for customer {customer_code}, {len(request.sources)} sources")
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
    return await query_events_multi(customer_code, request, db)


@siem_events_router.post(
    "/{customer_code}/fields",
    response_model=FieldMappingsResponse,
    description="Get the fields of several of a customer's event sources together; a field typed differently across them is marked conflict",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_field_mappings_multi_endpoint(
    customer_code: str,
    request: MultiSourceFieldsQuery,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FieldMappingsResponse:
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
    return await get_field_mappings_multi(customer_code, request.sources, db)


@siem_events_router.get(
    "/{customer_code}/{source_name}",
    response_model=EventsQueryResponse,
    description="Query events from a customer's event source with scroll-based pagination and optional Lucene query",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def query_events_endpoint(
    customer_code: str,
    source_name: str,
    timerange: str = Query("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of results per page"),
    scroll_id: Optional[str] = Query(None, description="Scroll ID for fetching the next page"),
    query: Optional[str] = Query(None, description="Lucene query string (e.g. 'agent_name:piHole AND agent_id:088')"),
    time_from: Optional[str] = Query(None, description="Absolute start time in ISO format. Overrides timerange."),
    time_to: Optional[str] = Query(None, description="Absolute end time in ISO format. Overrides timerange."),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventsQueryResponse:
    logger.info(f"Querying events for customer {customer_code}, source {source_name}")

    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

    params = EventsQueryParams(
        timerange=timerange,
        page_size=page_size,
        scroll_id=scroll_id,
        query=query,
        time_from=time_from,
        time_to=time_to,
    )
    return await query_events(customer_code, source_name, params, db)


@siem_events_router.get(
    "/{customer_code}/{source_name}/document",
    response_model=EventDocumentResponse,
    description="Get a single event document by OpenSearch index name and document id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_event_document_endpoint(
    customer_code: str,
    source_name: str,
    index_name: str = Query(..., description="Concrete OpenSearch index name containing the event"),
    event_id: str = Query(..., description="OpenSearch document _id"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventDocumentResponse:
    logger.info(f"Fetching event {event_id} from index {index_name} for customer {customer_code}, source {source_name}")

    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

    return await get_event_document(customer_code, source_name, index_name, event_id, db)


@siem_events_router.get(
    "/{customer_code}/{source_name}/fields",
    response_model=FieldMappingsResponse,
    description="Get index field name mappings for a customer's event source to assist with building queries",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_field_mappings_endpoint(
    customer_code: str,
    source_name: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FieldMappingsResponse:
    logger.info(f"Getting field mappings for customer {customer_code}, source {source_name}")

    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

    return await get_field_mappings(customer_code, source_name, db)
