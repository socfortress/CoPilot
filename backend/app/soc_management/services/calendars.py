"""Reading and writing business-hours calendars (global, or per customer).

Like the policy table, the calendar table is tiny and read whole: one indexed read per
question, resolution in ``domain/calendar.py:CalendarBook``.
"""

from __future__ import annotations

from typing import Iterable
from typing import List
from typing import Optional

from sqlalchemy import delete
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.soc_management.clock import utc_now
from app.soc_management.domain.calendar import BusinessCalendar
from app.soc_management.domain.calendar import CalendarBook
from app.soc_management.models.sla import SlaCalendar
from app.soc_management.schema.calendar import CalendarIn
from app.soc_management.schema.calendar import CalendarOut


def _to_domain(row: SlaCalendar) -> BusinessCalendar:
    return BusinessCalendar.from_dict({"timezone": row.timezone, "week": row.week, "holidays": row.holidays})


async def load_book(session: AsyncSession, customer_codes: Optional[Iterable[str]] = None) -> CalendarBook:
    """The global calendar plus those of ``customer_codes`` (every customer's when ``None``)."""
    query = select(SlaCalendar)
    if customer_codes is not None:
        codes = [code for code in customer_codes if code]
        scope = SlaCalendar.customer_code.is_(None)
        if codes:
            scope = or_(scope, SlaCalendar.customer_code.in_(codes))
        query = query.where(scope)
    rows = (await session.execute(query)).scalars().all()
    global_calendar = next((_to_domain(row) for row in rows if row.customer_code is None), None)
    return CalendarBook(
        global_calendar=global_calendar,
        by_customer={row.customer_code: _to_domain(row) for row in rows if row.customer_code is not None},
    )


async def get_calendar(session: AsyncSession, customer_code: Optional[str]) -> CalendarOut:
    """The calendar a scope runs on, labelled with where it comes from."""
    book = await load_book(session, [customer_code] if customer_code else [])
    calendar = book.for_customer(customer_code)
    source = book.source(customer_code) if customer_code else ("global" if book.global_calendar else "default")
    return CalendarOut(customer_code=customer_code, source=source, **calendar.to_dict())


async def replace_calendar(session: AsyncSession, payload: CalendarIn, actor: Optional[str]) -> CalendarOut:
    """Store a scope's calendar (replacing any previous one). Does not commit."""
    calendar = payload.to_domain()
    await session.execute(delete(SlaCalendar).where(_scope(payload.customer_code)))
    stored = calendar.to_dict()
    session.add(
        SlaCalendar(
            customer_code=payload.customer_code,
            timezone=calendar.timezone,
            week=stored["week"],
            holidays=stored["holidays"],
            updated_at=utc_now(),
            updated_by=actor,
        ),
    )
    await session.flush()
    return await get_calendar(session, payload.customer_code)


async def clear_calendar(session: AsyncSession, customer_code: str) -> int:
    """Remove a customer's calendar; it falls back to the global one."""
    result = await session.execute(delete(SlaCalendar).where(SlaCalendar.customer_code == customer_code))
    return result.rowcount or 0


async def customers_with_calendar(session: AsyncSession, customer_codes: Optional[List[str]] = None) -> List[str]:
    query = select(SlaCalendar.customer_code).where(SlaCalendar.customer_code.is_not(None))
    if customer_codes is not None:
        if not customer_codes:
            return []
        query = query.where(SlaCalendar.customer_code.in_(customer_codes))
    return sorted((await session.execute(query)).scalars().all())


def _scope(customer_code: Optional[str]):
    return SlaCalendar.customer_code.is_(None) if customer_code is None else SlaCalendar.customer_code == customer_code
