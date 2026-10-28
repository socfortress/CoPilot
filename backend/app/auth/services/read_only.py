"""Read-only portal users (#1312).

A ``customer_user`` whose ``user_customer_access`` row for a customer has ``read_only`` sees
everything the portal shows for that customer and changes nothing of it: every write on that
customer's data (alert and case status, comments, cases, links, files, assignees, reports, asset
criticality, AI analyses, questions to the SOC) answers 403 ``READ_ONLY``. What is the user's own
stays theirs: password, 2FA, language, notification choices and saved searches.

The flag is per customer, like ``is_customer_admin``: a user may only read one of their customers
and work on another. So the check sits where a write knows whose data it changes, after the
tenant check that resolved it (``ensure_may_write``), never on the route alone.
"""

from typing import Dict
from typing import FrozenSet
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess

READ_ONLY = "Your account can view this customer's data but not change it."

# Memoized per request, like the accessible customers (``session.info`` lives with the session).
_INFO_KEY = "read_only_customer_codes"


def _memo(session: AsyncSession) -> Optional[Dict[int, FrozenSet[str]]]:
    info = getattr(session, "info", None)
    return info.setdefault(_INFO_KEY, {}) if isinstance(info, dict) else None


async def read_only_customer_codes(user: User, session: AsyncSession) -> FrozenSet[str]:
    """The customers ``user`` may only read: none unless they are a ``customer_user``."""
    if user is None or user.role_id != RoleEnum.customer_user.value:
        return frozenset()
    memo = _memo(session)
    if memo is not None and user.id in memo:
        return memo[user.id]
    result = await session.execute(
        select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user.id, UserCustomerAccess.read_only.is_(True)),
    )
    codes = frozenset(result.scalars().all())
    if memo is not None:
        memo[user.id] = codes
    return codes


def forget_read_only(session: AsyncSession, user_id: int) -> None:
    """Drop the memo after a change to ``user_id``'s flags in this request."""
    memo = _memo(session)
    if memo is not None:
        memo.pop(user_id, None)


async def is_read_only_for(user: User, customer_code: Optional[str], session: AsyncSession) -> bool:
    return bool(customer_code) and customer_code in await read_only_customer_codes(user, session)


async def ensure_may_write(user: User, customer_code: Optional[str], session: AsyncSession) -> None:
    """403 ``READ_ONLY`` when ``user`` may only read ``customer_code``'s data.

    Called after the tenant check that resolved ``customer_code`` from the object written, so it
    never decides who may see what: only whether a portal user who may see it may change it.
    """
    if await is_read_only_for(user, customer_code, session):
        raise HTTPException(status_code=403, detail=READ_ONLY)
