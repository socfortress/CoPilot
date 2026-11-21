"""Event sources: the indices a customer's Event Search and SIEM dashboards read.

An event source's ``index_pattern`` is the tenant boundary for every search that goes through it.
CoPilot adds no customer filter to those queries, and the Customer Portal's Event Search and
dashboards read the same sources. A pattern that reaches another customer's indices therefore shows
that customer's events to whoever reads the source, the portal's users included. So only an admin
sets a pattern (adding a source, or changing its pattern), and an analyst edits the other fields of
their own customers' sources only.
"""

from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.db.universal_models import EventSources
from app.middleware.customer_access import enforce_owned_object_access
from app.siem.schema.event_sources import EventSourceCreate
from app.siem.schema.event_sources import EventSourceUpdate

ADMIN_ONLY_CREATE = "Only an admin can add an event source"
ADMIN_ONLY_PATTERN = "Only an admin can change an event source's index pattern"


def is_admin(user: User) -> bool:
    """By the database role, not the token's scopes: a demoted admin's token says "admin" until it expires."""
    return user.role_id == RoleEnum.admin


def changes_index_pattern(event_source: EventSources, update_data: EventSourceUpdate) -> bool:
    """Whether the update moves the pattern. The edit form sends the unchanged pattern with every save."""
    return "index_pattern" in update_data.model_fields_set and update_data.index_pattern != event_source.index_pattern


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
    current_user: User,
) -> EventSources:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail=ADMIN_ONLY_CREATE)
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

    db_event_source = EventSources(**event_source_data.model_dump())
    db.add(db_event_source)
    await db.flush()
    await db.refresh(db_event_source)
    await db.commit()
    return db_event_source


async def update_event_source(
    event_source_id: int,
    update_data: EventSourceUpdate,
    db: AsyncSession,
    current_user: User,
) -> EventSources:
    event_source = await get_event_source_by_id(event_source_id, db)
    # The id alone reaches any customer's source, so the source's own customer is what is checked.
    await enforce_owned_object_access(current_user, event_source.customer_code, db, subject=f"event source {event_source_id}")
    if changes_index_pattern(event_source, update_data) and not is_admin(current_user):
        raise HTTPException(status_code=403, detail=ADMIN_ONLY_PATTERN)
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
