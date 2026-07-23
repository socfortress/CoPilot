"""Admin security operations for a customer's user accounts.

Powers the customer-detail "Security" tab: list the users scoped to a customer,
show TOTP/last-login status, force-reset a user's TOTP, and issue a temporary
password (optionally emailed). All of these are admin-only (enforced at the
route layer).

Email uses the Python standard library only (``smtplib`` + ``email.message``) so
it adds no dependency. SMTP is configured via environment variables; when unset,
``smtp_configured()`` returns ``False`` and the UI disables the email action.
"""
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.models.totp import UserTOTP
from app.auth.models.users import Password
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess

TEMP_PASSWORD_LENGTH = 16

_ROLE_NAMES = {
    RoleEnum.admin.value: "admin",
    RoleEnum.analyst.value: "analyst",
    RoleEnum.scheduler.value: "scheduler",
    RoleEnum.customer_user.value: "customer_user",
}


def _role_name(role_id: Optional[int]) -> Optional[str]:
    return _ROLE_NAMES.get(role_id) if role_id is not None else None


async def list_customer_users(session: AsyncSession, customer_code: str) -> List[Dict[str, Any]]:
    """List the users that have access to ``customer_code`` with security info.

    Users are matched through ``user_customer_access`` (the per-tenant scoping
    table), so admins/analysts with wildcard access do not appear — only the
    accounts actually bound to this customer (the "customers").
    """
    result = await session.execute(
        select(User)
        .join(UserCustomerAccess, UserCustomerAccess.user_id == User.id)
        .where(UserCustomerAccess.customer_code == customer_code),
    )
    users = list(result.scalars().unique().all())
    if not users:
        return []

    user_ids = [u.id for u in users]
    totp_result = await session.execute(select(UserTOTP.user_id, UserTOTP.enabled).where(UserTOTP.user_id.in_(user_ids)))
    totp_map = {row[0]: bool(row[1]) for row in totp_result.all()}

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role_id": u.role_id,
            "role_name": _role_name(u.role_id),
            "last_login_at": u.last_login_at,
            "totp_enabled": totp_map.get(u.id, False),
        }
        for u in users
    ]


async def force_reset_totp(session: AsyncSession, user_id: int) -> bool:
    """Force-remove a user's TOTP enrolment WITHOUT requiring their code.

    Used when a user has lost their authenticator. Returns ``True`` if a row was
    deleted, ``False`` if the user had no TOTP configured. Deleting the row means
    ``is_2fa_enabled`` becomes false and the user can log in with just a password
    and re-enrol from scratch.
    """
    result = await session.execute(select(UserTOTP).where(UserTOTP.user_id == user_id))
    entry = result.scalars().first()
    if entry is None:
        return False
    await session.delete(entry)
    await session.commit()
    return True


async def set_temporary_password(session: AsyncSession, user: User) -> str:
    """Generate a strong temporary password, store its hash, return the plaintext.

    The caller is responsible for delivering the plaintext (e.g. by email) and
    should advise the user to change it on next login.
    """
    password = Password.generate(TEMP_PASSWORD_LENGTH)
    user.password = password.hashed
    session.add(user)
    await session.commit()
    return password.plain


# ── Email (stdlib SMTP) ───────────────────────────────────────────────────────


def _smtp_config() -> Optional[Dict[str, Any]]:
    host = os.getenv("SMTP_HOST")
    if not host:
        return None
    username = os.getenv("SMTP_USERNAME")
    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": username,
        "password": os.getenv("SMTP_PASSWORD"),
        "from_addr": os.getenv("SMTP_FROM") or username or "no-reply@copilot.local",
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
    }


def smtp_configured() -> bool:
    """Whether the SMTP env vars are present (drives the UI's email button)."""
    return _smtp_config() is not None


def _send_email_blocking(cfg: Dict[str, Any], to_addr: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = cfg["from_addr"]
    message["To"] = to_addr
    message.set_content(body)

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
        if cfg["use_tls"]:
            server.starttls(context=ssl.create_default_context())
        if cfg["username"] and cfg["password"]:
            server.login(cfg["username"], cfg["password"])
        server.send_message(message)


async def send_email(to_addr: str, subject: str, body: str) -> None:
    """Send a plaintext email via SMTP. Raises RuntimeError if SMTP is unset.

    ``smtplib`` is blocking, so it runs in a worker thread to avoid stalling the
    event loop.
    """
    cfg = _smtp_config()
    if cfg is None:
        raise RuntimeError("SMTP is not configured (set SMTP_HOST and related SMTP_* env vars)")
    await asyncio.to_thread(_send_email_blocking, cfg, to_addr, subject, body)
    logger.info(f"Sent security email to {to_addr}: {subject}")


def build_temp_password_email(username: str, temp_password: str) -> str:
    """Plaintext body for the temporary-password email."""
    return (
        f"Hello {username},\n\n"
        "An administrator has issued a temporary password for your CoPilot account.\n\n"
        f"Temporary password: {temp_password}\n\n"
        "For your security, please sign in with this password and change it immediately.\n"
        "If you did not expect this change, contact your security team.\n"
    )
