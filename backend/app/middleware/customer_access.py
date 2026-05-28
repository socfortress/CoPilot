# Create new file: app/middleware/customer_access.py
from typing import List
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
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
            result = await session.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user.id))
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

    async def resolve_effective_customers(
        self,
        user: User,
        requested_customers: Optional[List[str]],
        session: AsyncSession,
    ) -> List[str]:
        """Resolve the customer codes a query should be filtered to.

        Combines the user's *accessible* customers with an optional *requested*
        subset (e.g. a portal customer filter), so a caller can narrow the view
        without ever escaping their own access scope.

        Returns either:
          - ``["*"]`` — no filtering needed (wildcard access and no requested subset), or
          - a concrete list of customer codes to filter on. An empty list means the
            requested subset resolved to nothing the user may see, and callers should
            treat it as "match no rows" (``column.in_([])``).
        """
        accessible_customers = await self.get_user_accessible_customers(user, session)

        # No subset requested -> preserve existing behaviour (may be ["*"]).
        if not requested_customers:
            return accessible_customers

        # Wildcard access (admin/analyst): any requested subset is allowed as-is.
        if "*" in accessible_customers:
            return list(requested_customers)

        # Scoped user: only honor requested codes they actually have access to.
        return [code for code in requested_customers if code in accessible_customers]

    async def filter_query_by_customer_access(
        self,
        user: User,
        session: AsyncSession,
        base_query,
        customer_code_field,
        requested_customers: Optional[List[str]] = None,
    ):
        """Filter any query by user's customer access.

        When ``requested_customers`` is provided, the query is further narrowed to
        that subset (intersected with the user's access — see
        ``resolve_effective_customers``).
        """
        accessible_customers = await self.resolve_effective_customers(user, requested_customers, session)

        # Admin/analyst see everything (no subset requested)
        if "*" in accessible_customers:
            return base_query

        # Customer users (or anyone with a requested subset) see only matching data
        if accessible_customers:
            return base_query.where(customer_code_field.in_(accessible_customers))

        # No access / requested subset resolved to nothing - return empty result
        return base_query.where(False)

    def require_customer_access(self, customer_code: Optional[str] = None):
        """FastAPI dependency to enforce customer access"""

        async def _check_access(current_user: User = Depends(AuthHandler().get_current_user), session: AsyncSession = Depends(get_db)):
            if customer_code:
                if not await self.check_customer_access(current_user, customer_code, session):
                    raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
            return current_user

        return _check_access


# Create a singleton instance
customer_access_handler = CustomerAccessHandler()
