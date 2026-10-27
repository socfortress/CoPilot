"""A customer admin manages their customers' portal users from the Customer Portal (#1296).

Every route is ``customer_user`` by token and then customer admin by the database
(``services/tenant_users.py``: 403 for anyone else). A response that carries a temporary password
is ``no-store``.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import Response
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.services import security_admin
from app.auth.utils import AuthHandler
from app.customer_portal.routes.errors import internal_errors
from app.customer_portal.schema.me import PortalCustomer
from app.customer_portal.schema.tenant_users import InviteRequest
from app.customer_portal.schema.tenant_users import InviteResponse
from app.customer_portal.schema.tenant_users import ReadOnlyRequest
from app.customer_portal.schema.tenant_users import TemporaryPasswordResponse
from app.customer_portal.schema.tenant_users import TenantUserActionResponse
from app.customer_portal.schema.tenant_users import TenantUsersResponse
from app.customer_portal.services import tenant_users
from app.db.db_session import get_db

customer_portal_tenant_users_router = APIRouter()

PORTAL_USER = [Security(AuthHandler().require_any_scope("customer_user"))]


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@customer_portal_tenant_users_router.get(
    "/users",
    response_model=TenantUsersResponse,
    description="The portal users of the customers the caller administers (customer admins only).",
    dependencies=PORTAL_USER,
)
async def list_tenant_users(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantUsersResponse:
    async with internal_errors("load the users", session):
        administered, names, users = await tenant_users.list_users(current_user, session)
        return TenantUsersResponse(
            customers=[PortalCustomer(customer_code=code, customer_name=names[code], is_customer_admin=True) for code in administered],
            users=users,
            smtp_configured=security_admin.smtp_configured(),
        )


@customer_portal_tenant_users_router.post(
    "/users",
    response_model=InviteResponse,
    status_code=201,
    description="Invite a portal user to customers the caller administers; a temporary password goes by email or is returned once.",
    dependencies=PORTAL_USER,
)
async def invite_tenant_user(
    body: InviteRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InviteResponse:
    no_store(response)
    async with internal_errors("invite the user", session):
        user, delivered = await tenant_users.invite(current_user, body, session, request)
        sent = delivered.delivery == "email"
        return InviteResponse(
            message=f"{user.username} was invited" + (f"; their temporary password was emailed to {user.email}." if sent else "."),
            user=user,
            **delivered.model_dump(),
        )


@customer_portal_tenant_users_router.post(
    "/users/{user_id}/disable",
    response_model=TenantUserActionResponse,
    description="Disable a portal user: they can no longer sign in, and a session they hold ends.",
    dependencies=PORTAL_USER,
)
async def disable_tenant_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantUserActionResponse:
    async with internal_errors("disable the user", session):
        user = await tenant_users.set_disabled(current_user, user_id, True, session, request)
        return TenantUserActionResponse(message=f"{user.username} was disabled.", user=user)


@customer_portal_tenant_users_router.post(
    "/users/{user_id}/enable",
    response_model=TenantUserActionResponse,
    description="Enable a disabled portal user again.",
    dependencies=PORTAL_USER,
)
async def enable_tenant_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantUserActionResponse:
    async with internal_errors("enable the user", session):
        user = await tenant_users.set_disabled(current_user, user_id, False, session, request)
        return TenantUserActionResponse(message=f"{user.username} was enabled.", user=user)


@customer_portal_tenant_users_router.put(
    "/users/{user_id}/read-only",
    response_model=TenantUserActionResponse,
    description="Let a portal user only read their customers' data, or change it again (#1312).",
    dependencies=PORTAL_USER,
)
async def set_tenant_user_read_only(
    user_id: int,
    body: ReadOnlyRequest,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantUserActionResponse:
    async with internal_errors("change the user's access", session):
        user = await tenant_users.set_read_only(current_user, user_id, body.read_only, session, request)
        message = f"{user.username} can now only read your data." if body.read_only else f"{user.username} can change your data again."
        return TenantUserActionResponse(message=message, user=user)


@customer_portal_tenant_users_router.delete(
    "/users/{user_id}/totp",
    response_model=TenantUserActionResponse,
    description="Reset a portal user's two-factor authentication (a lost authenticator).",
    dependencies=PORTAL_USER,
)
async def reset_tenant_user_totp(
    user_id: int,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantUserActionResponse:
    async with internal_errors("reset two-factor authentication", session):
        user, removed = await tenant_users.reset_totp(current_user, user_id, session, request)
        message = "Two-factor authentication was reset." if removed else "The user had no two-factor authentication configured."
        return TenantUserActionResponse(message=message, user=user)


@customer_portal_tenant_users_router.post(
    "/users/{user_id}/temporary-password",
    response_model=TemporaryPasswordResponse,
    description="Issue a portal user a temporary password, emailed or returned once; they replace it at their next sign-in.",
    dependencies=PORTAL_USER,
)
async def issue_tenant_user_password(
    user_id: int,
    request: Request,
    response: Response,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TemporaryPasswordResponse:
    no_store(response)
    async with internal_errors("issue a temporary password", session):
        user, delivered = await tenant_users.issue_temporary_password(current_user, user_id, session, request)
        sent = delivered.delivery == "email"
        return TemporaryPasswordResponse(
            message=f"A temporary password was emailed to {user.email}." if sent else "A temporary password was issued.",
            user=user,
            **delivered.model_dump(),
        )
