# Create new file: app/middleware/customer_access.py
from typing import List
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.utils import AuthHandler
from app.db.db_session import get_db


class CustomerAccessHandler:
    async def get_user_accessible_customers(self, user: User, session: AsyncSession) -> List[str]:
        """Get all customer codes accessible to a user.

        Returns ``["*"]`` for deployment-wide access, or a concrete list of codes.

        Roles differ in how an *empty* ``user_customer_access`` set is read, and the
        difference is deliberate:

        - **admin** — always deployment-wide. Assignments are never consulted, so an
          admin cannot lock themselves out of the tenant they administer.
        - **analyst** — scoped to their assignments *when they have any*, otherwise
          deployment-wide. Assigning customers to an analyst is what opts that analyst
          into scoping (#1050); without this, an upgrade would silently strip every
          existing analyst of all access, since no deployment has assigned them rows.
        - **customer_user** — always scoped to their assignments, and no assignments
          means no access. A portal user must never fall back to seeing everything.
        """
        # Admins are unconditionally deployment-wide.
        if user.role_id == RoleEnum.admin:
            return ["*"]  # Wildcard for all customers

        if user.role_id in [RoleEnum.analyst, RoleEnum.customer_user]:
            result = await session.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == user.id))
            assigned_customers = list(result.scalars().all())

            # An unassigned analyst keeps the deployment-wide access they had before
            # scoping existed; an unassigned portal user gets nothing.
            if not assigned_customers and user.role_id == RoleEnum.analyst:
                return ["*"]

            return assigned_customers

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

    async def enforce_customer_access(self, user: User, customer_code: str, session: AsyncSession) -> None:
        """Raise 403 unless ``user`` may see ``customer_code``.

        The counterpart to ``filter_query_by_customer_access`` for single-tenant
        routes, where there is no query to narrow — the tenant is named in the path.
        """
        if not await self.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

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


async def verify_customer_code_access(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str:
    """Route dependency enforcing access to the ``{customer_code}`` path parameter.

    Add to ``dependencies=[...]`` alongside the scope check on any route keyed by a
    customer code: the scope check answers "may this role reach the route at all",
    this answers "is this caller entitled to *this* tenant".
    """
    await customer_access_handler.enforce_customer_access(current_user, customer_code, session)
    return customer_code


async def verify_optional_customer_code_access(
    customer_code: Optional[str] = Query(None),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Optional[str]:
    """Route dependency for a ``?customer_code=`` filter that is optional.

    Enforces access to the code when one is supplied, so a scoped caller cannot
    read another tenant by naming it. It deliberately does **not** constrain the
    no-code case: that means "everything the caller may see", and narrowing an
    aggregate is the calling service's job, not a dependency's.
    """
    if customer_code:
        await customer_access_handler.enforce_customer_access(current_user, customer_code, session)
    return customer_code


# ── object-keyed enforcement ──────────────────────────────────────────────────
#
# #1050 closed every route keyed by a literal ``{customer_code}``. That left the
# larger family of routes keyed by something a tenant *owns* — an agent id, a
# hostname, a report id — reachable by any analyst who can guess the key. The
# helpers below resolve such a key back to its owning tenant so the same
# ``enforce_customer_access`` decision applies there too.
#
# They are **fail-closed**: a key that resolves to no tenant is denied for a scoped
# caller. Being unable to prove ownership is not permission to read.


async def customer_code_for_agent(session: AsyncSession, agent_id: str) -> Optional[str]:
    """Resolve an ``agents.agent_id`` to the customer code that owns it."""
    from app.db.universal_models import Agents

    result = await session.execute(select(Agents.customer_code).where(Agents.agent_id == agent_id))
    return result.scalars().first()


async def customer_code_for_hostname(session: AsyncSession, hostname: str) -> Optional[str]:
    """Resolve an ``agents.hostname`` to the customer code that owns it."""
    from app.db.universal_models import Agents

    result = await session.execute(select(Agents.customer_code).where(Agents.hostname == hostname))
    return result.scalars().first()


async def enforce_owned_object_access(
    user: User,
    owner_customer_code: Optional[str],
    session: AsyncSession,
    *,
    subject: str,
) -> None:
    """Enforce access to an object whose owning tenant has already been resolved.

    ``owner_customer_code`` of ``None`` means the object could not be tied to a
    tenant (unknown agent, orphaned row). A wildcard caller is let through — the
    object is deployment-wide as far as they are concerned — while a scoped caller
    is denied, because an unattributable object may belong to anyone.
    """
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    if "*" in accessible:
        return
    if owner_customer_code and owner_customer_code in accessible:
        return
    raise HTTPException(status_code=403, detail=f"Access denied to {subject}")


async def enforce_agent_access(user: User, agent_id: str, session: AsyncSession) -> None:
    """Enforce access to the tenant that owns ``agent_id``."""
    await enforce_owned_object_access(
        user,
        await customer_code_for_agent(session, agent_id),
        session,
        subject=f"agent {agent_id}",
    )


async def enforce_hostname_access(user: User, hostname: str, session: AsyncSession) -> None:
    """Enforce access to the tenant that owns ``hostname``."""
    await enforce_owned_object_access(
        user,
        await customer_code_for_hostname(session, hostname),
        session,
        subject=f"host {hostname}",
    )


async def verify_agent_id_access(
    agent_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str:
    """Route dependency enforcing access to the tenant owning the ``{agent_id}`` path param."""
    await enforce_agent_access(current_user, agent_id, session)
    return agent_id


async def verify_hostname_access(
    hostname: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str:
    """Route dependency enforcing access to the tenant owning the ``{hostname}`` path param."""
    await enforce_hostname_access(current_user, hostname, session)
    return hostname


async def verify_customer_name_access(
    customer_name: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str:
    """Route dependency for a ``{customer_name}`` path param.

    ``custom_alert_creation_settings`` is keyed by the customer *name*, not the code,
    so the name is resolved to its code before the normal decision is applied. A name
    that matches no settings row is denied for a scoped caller.
    """
    from app.integrations.alert_creation_settings.models.alert_creation_settings import (
        AlertCreationSettings,
    )

    result = await session.execute(select(AlertCreationSettings.customer_code).where(AlertCreationSettings.customer_name == customer_name))
    await enforce_owned_object_access(
        current_user,
        result.scalars().first(),
        session,
        subject=f"customer {customer_name}",
    )
    return customer_name


async def scoped_customer_codes(
    user: User,
    requested_customers: Optional[List[str]],
    session: AsyncSession,
) -> Optional[List[str]]:
    """The customer codes an aggregate listing must be narrowed to.

    A thin, honest wrapper over ``resolve_effective_customers`` for services whose
    ``customer_codes`` parameter already means "filter to these":

      - ``None``  — caller is deployment-wide and asked for no subset: no filtering.
      - ``[]``    — the caller may see nothing here; the route must return an empty
                    result rather than calling the service, since most services read
                    an empty list as "no filter" and would leak everything.
      - a list    — filter to exactly these.
    """
    resolved = await customer_access_handler.resolve_effective_customers(user, requested_customers, session)
    if "*" in resolved:
        return None
    return resolved
