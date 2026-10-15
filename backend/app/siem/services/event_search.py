"""Event search's memory (#1258): saved queries, recent ones and picked columns, kept per
user and customer so the user finds them on any device.

Every write locks the user's row first, so two tabs or devices acting at once cannot
both take the last saved slot, nor trim the recent list from under each other. Each
write returns the whole memory, which the client takes as is.
"""

from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.siem.models.event_search import EventSearchColumns
from app.siem.models.event_search import EventSearchRecentQuery
from app.siem.models.event_search import EventSearchSavedQuery
from app.siem.schema.event_search import EventSearchColumn
from app.siem.schema.event_search import EventSearchMemory
from app.siem.schema.event_search import EventSearchState
from app.siem.schema.event_search import RecentQueryOut
from app.siem.schema.event_search import SavedQueryOut
from app.siem.schema.event_search import SaveQueryRequest
from app.siem.schema.event_search import SetColumnsRequest
from app.siem.utils.event_search import RECENT_LIMIT
from app.siem.utils.event_search import SAVED_LIMIT
from app.siem.utils.event_search import same_search
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

STATE_FIELDS = ("source_name", "query", "time_mode", "time_amount", "time_unit", "time_from", "time_to", "page_size")


def _state_values(state: EventSearchState) -> dict:
    values = {field: getattr(state, field) for field in STATE_FIELDS}
    values["time_from"] = to_naive_utc(values["time_from"])
    values["time_to"] = to_naive_utc(values["time_to"])
    return values


async def _lock_owner(session: AsyncSession, user_id: int) -> None:
    """Serialises the user's writes on their own row.

    The lock opens a fresh transaction: under MySQL's REPEATABLE READ a transaction reads
    the snapshot taken at its first plain read, and the route has already read (the
    customer-access check). Without the commit, the count after the lock would not see
    what the previous holder saved, and two devices could both take the last slot.
    """
    await session.commit()
    await session.execute(select(User.id).where(User.id == user_id).with_for_update())


async def load_memory(session: AsyncSession, user_id: int, customer_code: str) -> EventSearchMemory:
    saved = await session.execute(
        select(EventSearchSavedQuery)
        .where(EventSearchSavedQuery.user_id == user_id, EventSearchSavedQuery.customer_code == customer_code)
        .order_by(EventSearchSavedQuery.updated_at.desc(), EventSearchSavedQuery.id.desc()),
    )
    recent = await session.execute(
        select(EventSearchRecentQuery)
        .where(EventSearchRecentQuery.user_id == user_id, EventSearchRecentQuery.customer_code == customer_code)
        .order_by(EventSearchRecentQuery.ran_at.desc(), EventSearchRecentQuery.id.desc()),
    )
    columns = await session.execute(
        select(EventSearchColumns).where(EventSearchColumns.user_id == user_id, EventSearchColumns.customer_code == customer_code),
    )
    return EventSearchMemory(
        saved=[SavedQueryOut.model_validate(row) for row in saved.scalars()],
        recent=[RecentQueryOut.model_validate(row) for row in recent.scalars()],
        columns={row.source_name: [EventSearchColumn.model_validate(c) for c in row.columns] for row in columns.scalars()},
    )


async def save_query(
    session: AsyncSession,
    user_id: int,
    customer_code: str,
    request: SaveQueryRequest,
) -> Tuple[EventSearchMemory, bool]:
    """Saves the search under its name; a name already used is updated, not duplicated.

    "Already used" is decided by the database's collation (case- and accent-insensitive by
    default), the same rule its unique key enforces.
    """
    await _lock_owner(session, user_id)
    existing = (
        (
            await session.execute(
                select(EventSearchSavedQuery).where(
                    EventSearchSavedQuery.user_id == user_id,
                    EventSearchSavedQuery.customer_code == customer_code,
                    EventSearchSavedQuery.name == request.name,
                ),
            )
        )
        .scalars()
        .first()
    )
    now = to_naive_utc(now_utc())
    if existing:
        for field, value in _state_values(request).items():
            setattr(existing, field, value)
        existing.name = request.name
        existing.updated_at = now
    else:
        count = await session.scalar(
            select(func.count())
            .select_from(EventSearchSavedQuery)
            .where(EventSearchSavedQuery.user_id == user_id, EventSearchSavedQuery.customer_code == customer_code),
        )
        if count >= SAVED_LIMIT:
            raise HTTPException(
                status_code=409,
                detail=f"You have {SAVED_LIMIT} saved queries for this customer: delete one to save another",
            )
        session.add(
            EventSearchSavedQuery(
                user_id=user_id,
                customer_code=customer_code,
                name=request.name,
                created_at=now,
                updated_at=now,
                **_state_values(request),
            ),
        )
    await session.commit()
    return await load_memory(session, user_id, customer_code), existing is not None


async def delete_query(session: AsyncSession, user_id: int, customer_code: str, query_id: int) -> EventSearchMemory:
    result = await session.execute(
        delete(EventSearchSavedQuery).where(
            EventSearchSavedQuery.id == query_id,
            EventSearchSavedQuery.user_id == user_id,
            EventSearchSavedQuery.customer_code == customer_code,
        ),
    )
    if result.rowcount == 0:
        # Someone else's query, or one already deleted: both read as missing.
        await session.rollback()
        raise HTTPException(status_code=404, detail="Saved query not found")
    await session.commit()
    return await load_memory(session, user_id, customer_code)


async def remember(session: AsyncSession, user_id: int, customer_code: str, state: EventSearchState) -> EventSearchMemory:
    """Records a search just run: on top, once, keeping the last `RECENT_LIMIT`."""
    await _lock_owner(session, user_id)
    rows = (
        (
            await session.execute(
                select(EventSearchRecentQuery)
                .where(EventSearchRecentQuery.user_id == user_id, EventSearchRecentQuery.customer_code == customer_code)
                .order_by(EventSearchRecentQuery.ran_at.desc(), EventSearchRecentQuery.id.desc()),
            )
        )
        .scalars()
        .all()
    )
    kept = [row for row in rows if not same_search(row, state)]
    for row in [row for row in rows if row not in kept] + kept[RECENT_LIMIT - 1 :]:
        await session.delete(row)
    session.add(
        EventSearchRecentQuery(user_id=user_id, customer_code=customer_code, ran_at=to_naive_utc(now_utc()), **_state_values(state)),
    )
    await session.commit()
    return await load_memory(session, user_id, customer_code)


async def clear_recent(session: AsyncSession, user_id: int, customer_code: str) -> EventSearchMemory:
    await session.execute(
        delete(EventSearchRecentQuery).where(
            EventSearchRecentQuery.user_id == user_id,
            EventSearchRecentQuery.customer_code == customer_code,
        ),
    )
    await session.commit()
    return await load_memory(session, user_id, customer_code)


async def set_columns(session: AsyncSession, user_id: int, customer_code: str, request: SetColumnsRequest) -> EventSearchMemory:
    """The user's columns for a source; none goes back to the source's layout."""
    await _lock_owner(session, user_id)
    existing: Optional[EventSearchColumns] = (
        (
            await session.execute(
                select(EventSearchColumns).where(
                    EventSearchColumns.user_id == user_id,
                    EventSearchColumns.customer_code == customer_code,
                    EventSearchColumns.source_name == request.source_name,
                ),
            )
        )
        .scalars()
        .first()
    )
    columns = [column.model_dump() for column in request.columns or []]
    if not columns:
        if existing:
            await session.delete(existing)
    elif existing:
        existing.columns = columns
        existing.updated_at = to_naive_utc(now_utc())
    else:
        session.add(
            EventSearchColumns(
                user_id=user_id,
                customer_code=customer_code,
                source_name=request.source_name,
                columns=columns,
                updated_at=to_naive_utc(now_utc()),
            ),
        )
    await session.commit()
    return await load_memory(session, user_id, customer_code)
