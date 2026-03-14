from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import EventSources
from app.siem.schema.event_sources import EventSourceCreate
from app.siem.schema.event_sources import EventSourceUpdate


async def get_event_sources_by_customer(
    customer_code: str,
    db: AsyncSession,
) -> List[EventSources]:
    logger.info(f"Fetching event sources for customer {customer_code}")
    result = await db.execute(
        select(EventSources).where(EventSources.customer_code == customer_code),
    )
    return result.scalars().all()


async def get_event_source_by_id(
    event_source_id: int,
    db: AsyncSession,
) -> EventSources:
    result = await db.execute(
        select(EventSources).where(EventSources.id == event_source_id),
    )
    event_source = result.scalars().first()
    if not event_source:
        raise HTTPException(status_code=404, detail="Event source not found")
    return event_source


async def create_event_source(
    event_source_data: EventSourceCreate,
    db: AsyncSession,
) -> EventSources:
    logger.info(f"Creating event source '{event_source_data.name}' for customer {event_source_data.customer_code}")
    # Check for duplicate name within the same customer
    result = await db.execute(
        select(EventSources).where(
            EventSources.customer_code == event_source_data.customer_code,
            EventSources.name == event_source_data.name,
        ),
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Event source '{event_source_data.name}' already exists for customer {event_source_data.customer_code}",
        )

    db_event_source = EventSources(**event_source_data.dict())
    db.add(db_event_source)
    await db.flush()
    await db.refresh(db_event_source)
    await db.commit()
    return db_event_source


async def update_event_source(
    event_source_id: int,
    update_data: EventSourceUpdate,
    db: AsyncSession,
) -> EventSources:
    event_source = await get_event_source_by_id(event_source_id, db)
    event_source.update_from_model(update_data)
    await db.commit()
    await db.refresh(event_source)
    return event_source


async def delete_event_source(
    event_source_id: int,
    db: AsyncSession,
) -> None:
    event_source = await get_event_source_by_id(event_source_id, db)
    await db.delete(event_source)
    await db.commit()
    logger.info(f"Deleted event source {event_source_id}")
