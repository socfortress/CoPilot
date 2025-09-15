# Create new file: app/auth/routes/customer_users.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.auth.utils import AuthHandler
from app.auth.models.users import User, UserCustomerAccess, RoleEnum
from app.db.db_session import get_db
from app.middleware.customer_access import customer_access_handler

customer_users_router = APIRouter()

@customer_users_router.post("/users/{user_id}/customers")
async def assign_customer_access(
    user_id: int,
    customer_codes: List[str],
    current_user: User = Depends(AuthHandler().require_any_scope("admin")),
    session: AsyncSession = Depends(get_db)
):
    """Assign customer access to a user (admin only)"""

    # Remove existing access
    await session.execute(
        delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user_id)
    )

    # Add new access
    for customer_code in customer_codes:
        access = UserCustomerAccess(
            user_id=user_id,
            customer_code=customer_code
        )
        session.add(access)

    await session.commit()

    return {
        "success": True,
        "message": f"Assigned {len(customer_codes)} customers to user {user_id}",
        "customer_codes": customer_codes
    }

@customer_users_router.get("/users/{user_id}/customers")
async def get_user_customer_access(
    user_id: int,
    current_user: User = Depends(AuthHandler().require_any_scope("admin")),
    session: AsyncSession = Depends(get_db)
) -> List[str]:
    """Get customer codes accessible to user (admin only)"""

    result = await session.execute(
        select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user_id)
    )
    return result.scalars().all()

@customer_users_router.get("/me/customers")
async def get_my_customer_access(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db)
) -> List[str]:
    """Get current user's accessible customers"""
    return await customer_access_handler.get_user_accessible_customers(current_user, session)
