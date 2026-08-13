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
from app.auth.services import temp_password_email
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


# ── Temporary-password email templates (#999) ────────────────────────────────
#
# The templates themselves live in `notification_template` and are authored in
# the existing Message Templates editor — these routes only cover what the
# Security tab needs: which template would be used for *this* user, what it
# looks like rendered for them, and sending with a per-send override.


class TempPasswordTemplateOption(BaseModel):
    """One selectable template, as the send dialog's picker needs it."""

    id: int
    name: str
    description: Optional[str] = None
    format: str
    # None means shared with every customer. Shown in the picker so an operator
    # can tell their customer-specific template from the shared fallback.
    customer_code: Optional[str] = None
    is_default: bool = False


class TempPasswordOptionsResponse(BaseModel):
    templates: List[TempPasswordTemplateOption]
    # The template that a send with no override would use. None means the email
    # falls back to the built-in plaintext body.
    resolved_template_id: Optional[int] = None
    # Echoed back so the dialog can show which customer's branding applies, and
    # so the caller can see when a multi-customer user resolved to none.
    customer_code: Optional[str] = None
    smtp_configured: bool = True
    success: bool = True
    message: str = "Template options retrieved"


class TempPasswordPreviewRequest(BaseModel):
    template_id: Optional[int] = None
    customer_code: Optional[str] = None


class TempPasswordPreviewResponse(BaseModel):
    subject: Optional[str] = None
    body: str
    # "html" or "text" — tells the dialog whether to sandbox-iframe the body.
    format: str = "text"
    # Non-null when rendering failed. Returned rather than raised so the admin
    # sees the error beside the template that caused it.
    error: Optional[str] = None
    success: bool
    message: str


class SendTempPasswordRequest(BaseModel):
    """Optional body for the send action.

    Both fields are optional so the pre-#999 call — a bare POST with no body —
    keeps working and keeps meaning "resolve the template yourself".
    """

    template_id: Optional[int] = None
    customer_code: Optional[str] = None


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


@security_admin_router.get(
    "/security/users/{user_id}/temp-password-email/options",
    response_model=TempPasswordOptionsResponse,
    description=(
        "Which temporary-password email templates can serve this user, and which one a send with no "
        "override would pick. Best match first — customer-scoped, then shared, then the built-in."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def get_temp_password_email_options(
    user_id: int,
    customer_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> TempPasswordOptionsResponse:
    user = await _get_user_or_404(db, user_id)
    resolved_code = await temp_password_email.resolve_customer_code(db, user, customer_code)

    templates = await temp_password_email.list_available_templates(db, resolved_code)
    # Only formats this sender can actually put in an email are offered; a
    # `json` template scoped to this trigger would be a nonsense selection.
    options = [t for t in templates if t.format in temp_password_email.SUPPORTED_FORMATS]

    return TempPasswordOptionsResponse(
        templates=[
            TempPasswordTemplateOption(
                id=t.id,
                name=t.name,
                description=t.description,
                format=t.format,
                customer_code=t.customer_code,
                is_default=t.is_default,
            )
            for t in options
        ],
        resolved_template_id=options[0].id if options else None,
        customer_code=resolved_code,
        smtp_configured=security_admin.smtp_configured(),
        message=f"{len(options)} template(s) available",
    )


@security_admin_router.post(
    "/security/users/{user_id}/temp-password-email/preview",
    response_model=TempPasswordPreviewResponse,
    description=(
        "Render the temporary-password email as this user would receive it, using a placeholder password. "
        "Nothing is sent and no password is rotated."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def preview_temp_password_email(
    user_id: int,
    payload: TempPasswordPreviewRequest,
    db: AsyncSession = Depends(get_db),
) -> TempPasswordPreviewResponse:
    user = await _get_user_or_404(db, user_id)
    resolved_code = await temp_password_email.resolve_customer_code(db, user, payload.customer_code)
    template = await temp_password_email.resolve_template(db, resolved_code, payload.template_id)

    result = await temp_password_email.preview_for_user(db, template=template, user=user, customer_code=resolved_code)
    return TempPasswordPreviewResponse(
        success=result["error"] is None,
        message="Rendered" if result["error"] is None else "Template failed to render",
        **result,
    )


@security_admin_router.post(
    "/security/users/{user_id}/send-temp-password",
    response_model=ActionResponse,
    description=(
        "Generate a temporary password for the user, set it, and email it to them. Uses the customer's "
        "temporary-password template when one exists, or `template_id` to override for this send."
    ),
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def send_temp_password(
    user_id: int,
    http_request: Request,
    payload: Optional[SendTempPasswordRequest] = None,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActionResponse:
    if not security_admin.smtp_configured():
        raise HTTPException(status_code=400, detail="SMTP is not configured; cannot send the temporary-password email.")

    user = await _get_user_or_404(db, user_id)
    if not user.email:
        raise HTTPException(status_code=400, detail="User has no email address on file.")

    payload = payload or SendTempPasswordRequest()
    resolved_code = await temp_password_email.resolve_customer_code(db, user, payload.customer_code)
    template = await temp_password_email.resolve_template(db, resolved_code, payload.template_id)
    customer_name = await temp_password_email.customer_name_for(db, resolved_code)

    # Generate, then RENDER, then rotate. A template that fails to render must
    # not leave the user holding a password nobody told them about — and unlike
    # the dispatch path there is no safe silent fallback here, because falling
    # back to the built-in English body is the exact outcome a customised
    # template exists to prevent.
    password = security_admin.generate_temporary_password()
    try:
        subject, text_body, html_body = await temp_password_email.render_email(
            db,
            template=template,
            username=user.username,
            email=user.email,
            temp_password=password.plain,
            customer_code=resolved_code,
            customer_name=customer_name,
            user_id=user.id,
        )
    except Exception as e:
        logger.error(f"Temp-password template {getattr(template, 'id', None)} failed to render for {user.username}: {e}")
        raise HTTPException(
            status_code=400,
            detail=(
                f"The email template could not be rendered, so nothing was sent and the password was left "
                f"unchanged: {type(e).__name__}: {e}"
            ),
        )

    await security_admin.apply_temporary_password(db, user, password)
    try:
        await security_admin.send_email(
            to_addr=user.email,
            subject=subject,
            body=text_body,
            html_body=html_body,
        )
    except Exception as e:
        logger.error(f"Failed to send temp-password email to {user.email}: {e}")
        # The password was already rotated; surface the delivery failure clearly.
        raise HTTPException(
            status_code=502,
            detail=f"The password was reset but the email could not be sent: {e}",
        )

    template_note = f"template {template.name!r}" if template else "the built-in default body"
    await record_audit_event(
        action=AuditAction.USER_UPDATE,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        entity_type="user",
        entity_id=user.username,
        details=f"Temporary password issued and emailed by admin using {template_note}",
        request=http_request,
    )
    logger.info(f"Admin {current_user.username} issued a temporary password for {user.username} using {template_note}")
    return ActionResponse(success=True, message=f"A temporary password has been emailed to {user.email}.")
