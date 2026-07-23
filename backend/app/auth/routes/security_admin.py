"""Admin-only "Security" panel routes for a customer's user accounts.

Backs the customer-detail Security tab: list scoped users with TOTP/last-login
status, force-reset a user's TOTP, and issue+email a temporary password. Every
route requires the ``admin`` scope and records an audit event.

Mounted under ``/auth`` (see app/routers/auth.py), so the effective paths are
``/api/auth/security/...``.
"""
import datetime
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Security
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.services import security_admin
from app.auth.utils import AuthHandler
from app.db.db_session import get_db

security_admin_router = APIRouter()


class CustomerSecurityUser(BaseModel):
    id: int
    username: str
    email: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    last_login_at: Optional[datetime.datetime] = None
    totp_enabled: bool = False


class CustomerSecurityUsersResponse(BaseModel):
    users: List[CustomerSecurityUser]
    success: bool = True
    message: str = "Users retrieved successfully"


class SmtpStatusResponse(BaseModel):
    configured: bool
    success: bool = True
    message: str = "SMTP status retrieved"


class ActionResponse(BaseModel):
    success: bool
    message: str


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


@security_admin_router.get(
    "/security/customers/{customer_code}/users",
    response_model=CustomerSecurityUsersResponse,
    description="List the user accounts scoped to a customer with TOTP and last-login status.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def list_customer_security_users(
    customer_code: str,
    db: AsyncSession = Depends(get_db),
) -> CustomerSecurityUsersResponse:
    users = await security_admin.list_customer_users(db, customer_code)
    return CustomerSecurityUsersResponse(users=[CustomerSecurityUser(**u) for u in users])


@security_admin_router.get(
    "/security/smtp-status",
    response_model=SmtpStatusResponse,
    description="Whether SMTP is configured (drives the temporary-password email action).",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_smtp_status() -> SmtpStatusResponse:
    return SmtpStatusResponse(configured=security_admin.smtp_configured())


@security_admin_router.delete(
    "/security/users/{user_id}/totp",
    response_model=ActionResponse,
    description="Force-reset a user's TOTP (2FA) without requiring their code.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def force_reset_user_totp(
    user_id: int,
    http_request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    user = await _get_user_or_404(db, user_id)
    removed = await security_admin.force_reset_totp(db, user_id)

    audit_details = f"Forced TOTP (2FA) reset by admin ({'removed' if removed else 'no enrolment present'})"
    await record_audit_event(
        action=AuditAction.USER_UPDATE,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        entity_type="user",
        entity_id=user.username,
        details=audit_details,
        request=http_request,
    )
    logger.info(f"Admin {current_user.username} force-reset TOTP for user {user.username} (removed={removed})")
    message = "Two-factor authentication has been reset." if removed else "The user had no two-factor authentication configured."
    return ActionResponse(success=True, message=message)


@security_admin_router.post(
    "/security/users/{user_id}/send-temp-password",
    response_model=ActionResponse,
    description="Generate a temporary password for the user, set it, and email it to them.",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def send_temp_password(
    user_id: int,
    http_request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    if not security_admin.smtp_configured():
        raise HTTPException(status_code=400, detail="SMTP is not configured; cannot send the temporary-password email.")

    user = await _get_user_or_404(db, user_id)
    if not user.email:
        raise HTTPException(status_code=400, detail="User has no email address on file.")

    temp_password = await security_admin.set_temporary_password(db, user)
    try:
        await security_admin.send_email(
            to_addr=user.email,
            subject="CoPilot — temporary password",
            body=security_admin.build_temp_password_email(user.username, temp_password),
        )
    except Exception as e:
        logger.error(f"Failed to send temp-password email to {user.email}: {e}")
        # The password was already rotated; surface the delivery failure clearly.
        raise HTTPException(
            status_code=502,
            detail=f"The password was reset but the email could not be sent: {e}",
        )

    await record_audit_event(
        action=AuditAction.USER_UPDATE,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        entity_type="user",
        entity_id=user.username,
        details="Temporary password issued and emailed by admin",
        request=http_request,
    )
    logger.info(f"Admin {current_user.username} issued a temporary password for {user.username}")
    return ActionResponse(success=True, message=f"A temporary password has been emailed to {user.email}.")
