# Create new file: app/middleware/customer_access.py
from typing import List, Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.auth.models.users import User, UserCustomerAccess, RoleEnum
from app.auth.utils import AuthHandler
from app.db.db_session import get_db

class CustomerAccessHandler:

    async def get_user_accessible_customers(self, user: User, session: AsyncSession) -> List[str]:
        """Get all customer codes accessible to a user"""
        # Admin and analyst users have access to all customers
        if user.role_id in [RoleEnum.admin, RoleEnum.analyst]:
            return ["*"]  # Wildcard for all customers

        # Customer users only see their assigned customers
        if user.role_id == RoleEnum.customer_user:
            result = await session.execute(
                select(UserCustomerAccess.customer_code)
                .where(UserCustomerAccess.user_id == user.id)
            )
            return result.scalars().all()

        return []  # No access by default

    async def check_customer_access(self, user: User, customer_code: str, session: AsyncSession) -> bool:
        """Check if user has access to specific customer"""
        accessible_customers = await self.get_user_accessible_customers(user, session)

        # Wildcard access (admin/analyst)
        if "*" in accessible_customers:
            return True

        # Specific customer access
        return customer_code in accessible_customers

    async def filter_query_by_customer_access(
        self,
        user: User,
        session: AsyncSession,
        base_query,
        customer_code_field
    ):
        """Filter any query by user's customer access"""
        accessible_customers = await self.get_user_accessible_customers(user, session)

        # Admin/analyst see everything
        if "*" in accessible_customers:
            return base_query

        # Customer users see only their data
        if accessible_customers:
            return base_query.where(customer_code_field.in_(accessible_customers))

        # No access - return empty result
        return base_query.where(False)

    def require_customer_access(self, customer_code: Optional[str] = None):
        """FastAPI dependency to enforce customer access"""
        async def _check_access(
            current_user: User = Depends(AuthHandler().get_current_user),
            session: AsyncSession = Depends(get_db)
        ):
            if customer_code:
                if not await self.check_customer_access(current_user, customer_code, session):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Access denied to customer {customer_code}"
                    )
            return current_user
        return _check_access

# Create a singleton instance
customer_access_handler = CustomerAccessHandler()
