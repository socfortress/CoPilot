from typing import List
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import Customers


async def build_customer_index_matchers(session: AsyncSession, customer_codes: List[str]) -> List[str]:
    result = await session.execute(
        select(Customers.customer_code, Customers.customer_name).where(
            Customers.customer_code.in_(customer_codes),
        ),
    )
    matchers: set[str] = set()
    for code, name in result.all():
        matchers.add(code.lower())
        if name:
            normalized = name.lower()
            matchers.add(normalized)
            matchers.add(normalized.replace(" ", "_"))
            matchers.add(normalized.replace(" ", "-"))
    return list(matchers)


def index_matches_customer(index_name: Optional[str], matchers: List[str]) -> bool:
    if not index_name or not matchers:
        return False
    index_lower = index_name.lower()
    return any(matcher in index_lower for matcher in matchers)


async def filter_index_dicts_by_customers(
    indices: List[dict],
    customer_codes: Optional[List[str]],
    session: AsyncSession,
) -> List[dict]:
    if customer_codes is None:
        return indices
    if not customer_codes:
        return []

    matchers = await build_customer_index_matchers(session, customer_codes)
    if not matchers:
        return []

    return [index for index in indices if index_matches_customer(index.get("index"), matchers)]
