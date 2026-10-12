from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.services.customer_assignment import replace_assignment
from app.auth.services.customer_assignment import validate_assignment
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler

customer_users_router = APIRouter()


@customer_users_router.post("/users/{user_id}/customers")
async def assign_customer_access(
    user_id: int,
    customer_codes: List[str],
    current_user: User = Depends(AuthHandler().require_any_scope("admin")),
    session: AsyncSession = Depends(get_db),
):
    """Replace a user's customer assignments (admin only).

    An analyst or responder keeps at least one customer, an admin gets none (they see
    every customer anyway), and every code must exist: see ``customer_assignment``.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    codes = await validate_assignment(user.role_id, customer_codes, session)
    await replace_assignment(user_id, codes, session)
    await session.commit()
    customer_access_handler.forget_accessible_customers(session, user_id)

    return {"success": True, "message": f"Assigned {len(codes)} customers to user {user_id}", "customer_codes": codes}


@customer_users_router.get("/users/{user_id}/customers")
async def get_user_customer_access(
    user_id: int,
    current_user: User = Depends(AuthHandler().require_any_scope("admin")),
    session: AsyncSession = Depends(get_db),
):
    """Get customer codes accessible to user (admin only)"""

    result = await session.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user_id))
    customer_codes = result.scalars().all()

    return {"success": True, "customer_codes": customer_codes}


@customer_users_router.get("/me/customers")
async def get_my_customer_access(current_user: User = Depends(AuthHandler().get_current_user), session: AsyncSession = Depends(get_db)):
    """Get current user's accessible customers, and *why* they are what they are.

    - ``scope="deployment"``: an admin, ``customer_codes == ["*"]``;
    - ``scope="assigned"``: the customers assigned to the caller;
    - ``scope="unassigned"``: an analyst, responder or portal user nobody has assigned a
      customer to — they see nothing (#1219; before it, an unassigned analyst saw every
      customer). Naming it lets the UI say why the caller sees nothing.
    """
    customer_codes = await customer_access_handler.get_user_accessible_customers(current_user, session)

    if "*" in customer_codes:
        scope = "deployment"
    elif customer_codes:
        scope = "assigned"
    else:
        scope = "unassigned"

    return {"success": True, "customer_codes": customer_codes, "scope": scope}
