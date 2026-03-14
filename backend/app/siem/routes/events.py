from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.siem.schema.events import EventsQueryParams
from app.siem.schema.events import EventsQueryResponse
from app.siem.services.events import query_events

siem_events_router = APIRouter()


@siem_events_router.get(
    "/{customer_code}/{source_name}",
    response_model=EventsQueryResponse,
    description="Query events from a customer's event source with scroll-based pagination",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def query_events_endpoint(
    customer_code: str,
    source_name: str,
    timerange: str = Query("24h", description="Time range (e.g. '1h', '24h', '7d', '1w')"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of results per page"),
    scroll_id: Optional[str] = Query(None, description="Scroll ID for fetching the next page"),
    db: AsyncSession = Depends(get_db),
) -> EventsQueryResponse:
    logger.info(f"Querying events for customer {customer_code}, source {source_name}")
    params = EventsQueryParams(
        timerange=timerange,
        page_size=page_size,
        scroll_id=scroll_id,
    )
    return await query_events(customer_code, source_name, params, db)
