from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.customer_portal.schema.me import PortalCustomer
from app.customer_portal.schema.me import PortalMeResponse
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler


async def portal_customers(user: User, session: AsyncSession) -> List[PortalCustomer]:
    """The customers ``user`` may see, with their names, sorted by name.

    A code with no ``customers`` row is still listed, under its code: hiding it would
    hide data the user can reach. The wildcard is never expanded: only an admin holds
    it, and an admin does not use the portal.
    """
    codes = [code for code in await customer_access_handler.get_user_accessible_customers(user, session) if code != "*"]
    if not codes:
        return []

    result = await session.execute(select(Customers.customer_code, Customers.customer_name).where(Customers.customer_code.in_(codes)))
    names = {code: name for code, name in result.all()}
    customers = [PortalCustomer(customer_code=code, customer_name=(names.get(code) or "").strip() or code) for code in codes]
    return sorted(customers, key=lambda customer: (customer.customer_name.casefold(), customer.customer_code))


async def get_portal_profile(user: User, session: AsyncSession) -> PortalMeResponse:
    return PortalMeResponse(
        success=True,
        message="Profile retrieved successfully",
        username=user.username,
        role=RoleEnum(user.role_id).name,
        customers=await portal_customers(user, session),
        must_change_password=bool(user.must_change_password),
    )
