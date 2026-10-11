"""Which customers a user is assigned to, and the rules every write of them follows (#1219).

Analysts and responders see exactly the customers assigned to them, so they are never
left with none: creating one, changing a user's role to one, and replacing their
assignments all require at least one customer. Admins see every customer whatever their
rows say, so assigning customers to an admin is refused rather than silently ignored.
Portal users keep the old rules (their assignments may be emptied).

Every code must name an existing customer: a typo would otherwise scope a user to a
customer that does not exist, which reads as "sees nothing" with no explanation.
"""

from typing import Iterable
from typing import List

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import CUSTOMER_SCOPED_SOC_ROLES
from app.auth.models.users import RoleEnum
from app.auth.models.users import UserCustomerAccess
from app.db.universal_models import Customers

NEEDS_A_CUSTOMER = "Analysts and responders must be assigned at least one customer"
ADMIN_IS_DEPLOYMENT_WIDE = "Admins see every customer: assigning customers to an admin has no effect"


def normalize_codes(customer_codes: Iterable[str]) -> List[str]:
    """Trimmed, de-duplicated, in the order given."""
    seen: List[str] = []
    for code in customer_codes:
        code = (code or "").strip()
        if code and code not in seen:
            seen.append(code)
    return seen


async def validate_assignment(role_id: int, customer_codes: Iterable[str], session: AsyncSession) -> List[str]:
    """The codes to store for a user of ``role_id``, or a 400 saying why they cannot be."""
    codes = normalize_codes(customer_codes)

    if role_id == RoleEnum.admin and codes:
        raise HTTPException(status_code=400, detail=ADMIN_IS_DEPLOYMENT_WIDE)
    if role_id in CUSTOMER_SCOPED_SOC_ROLES and not codes:
        raise HTTPException(status_code=400, detail=NEEDS_A_CUSTOMER)

    if codes:
        found = set((await session.execute(select(Customers.customer_code).where(Customers.customer_code.in_(codes)))).scalars().all())
        unknown = [code for code in codes if code not in found]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown customer code(s): {', '.join(unknown)}")
    return codes


async def assigned_codes(user_id: int, session: AsyncSession) -> List[str]:
    result = await session.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user_id))
    return list(result.scalars().all())


async def replace_assignment(user_id: int, customer_codes: List[str], session: AsyncSession) -> None:
    """Make ``customer_codes`` the user's assignments. The caller commits, then forgets the memo."""
    await session.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user_id))
    for code in customer_codes:
        session.add(UserCustomerAccess(user_id=user_id, customer_code=code))
