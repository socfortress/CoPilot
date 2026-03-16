from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler
from app.db.universal_models import Customers
from app.siem.schema.event_sources import EventSourceCreate
from app.siem.schema.event_sources import EventSourceDeleteResponse
from app.siem.schema.event_sources import EventSourceOperationResponse
from app.siem.schema.event_sources import EventSourceResponse
from app.siem.schema.event_sources import EventSourcesListResponse
from app.siem.schema.event_sources import EventSourceUpdate
from app.siem.services.event_sources import create_event_source
from app.siem.services.event_sources import delete_event_source
from app.siem.services.event_sources import get_event_sources_by_customer
from app.siem.services.event_sources import update_event_source

event_sources_router = APIRouter()


async def verify_customer_exists(customer_code: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )


@event_sources_router.get(
    "/{customer_code}",
    response_model=EventSourcesListResponse,
    description="Get all event sources for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_event_sources_endpoint(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourcesListResponse:
    logger.info(f"Getting event sources for customer {customer_code}")
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
    await verify_customer_exists(customer_code, db)
    event_sources = await get_event_sources_by_customer(customer_code, db)
    return EventSourcesListResponse(
        event_sources=[EventSourceResponse.from_orm(es) for es in event_sources],
        success=True,
        message="Event sources retrieved successfully",
    )


@event_sources_router.post(
    "",
    response_model=EventSourceOperationResponse,
    description="Create a new event source for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_event_source_endpoint(
    event_source: EventSourceCreate,
    db: AsyncSession = Depends(get_db),
) -> EventSourceOperationResponse:
    logger.info(f"Creating event source for customer {event_source.customer_code}")
    await verify_customer_exists(event_source.customer_code, db)
    created = await create_event_source(event_source, db)
    return EventSourceOperationResponse(
        event_source=EventSourceResponse.from_orm(created),
        success=True,
        message="Event source created successfully",
    )


@event_sources_router.put(
    "/{event_source_id}",
    response_model=EventSourceOperationResponse,
    description="Update an existing event source",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_event_source_endpoint(
    event_source_id: int,
    update_data: EventSourceUpdate,
    db: AsyncSession = Depends(get_db),
) -> EventSourceOperationResponse:
    logger.info(f"Updating event source {event_source_id}")
    updated = await update_event_source(event_source_id, update_data, db)
    return EventSourceOperationResponse(
        event_source=EventSourceResponse.from_orm(updated),
        success=True,
        message="Event source updated successfully",
    )


@event_sources_router.delete(
    "/{event_source_id}",
    response_model=EventSourceDeleteResponse,
    description="Delete an event source",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_event_source_endpoint(
    event_source_id: int,
    db: AsyncSession = Depends(get_db),
) -> EventSourceDeleteResponse:
    logger.info(f"Deleting event source {event_source_id}")
    await delete_event_source(event_source_id, db)
    return EventSourceDeleteResponse(
        success=True,
        message="Event source deleted successfully",
    )
