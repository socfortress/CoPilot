"""A disabled account can neither sign in nor use a session it already holds (#1296).

``user.disabled_at`` is set by a SOC admin (``/auth/security/users/{id}/disable``) or, for a
portal user, by a customer admin (``/customer_portal/users/{id}/disable``). It is enforced in two
places, so no path around it exists:

- ``AuthHandler.encode_token``: every token CoPilot issues goes through it (password logins, the
  2FA completion, passkeys, SSO, refresh), so a disabled account is never given one;
- ``AuthHandler.get_current_user`` / ``require_any_scope``: every authenticated request resolves
  its user there, so a session held when the account is disabled ends at its next request.

Both answer 401: the session is over, which is exactly how the frontends read a 401.
"""

from fastapi import HTTPException

from app.auth.models.users import User

ACCOUNT_DISABLED = "This account has been disabled. Contact your administrator."
ACCOUNT_DISABLED_HEADER = "X-Account-Disabled"


def is_disabled(user: User) -> bool:
    return getattr(user, "disabled_at", None) is not None


def disabled_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=ACCOUNT_DISABLED,
        headers={"WWW-Authenticate": "Bearer", ACCOUNT_DISABLED_HEADER: "true"},
    )


def ensure_active(user: User) -> None:
    """Refuse a disabled account."""
    if is_disabled(user):
        raise disabled_error()


async def refuse_disabled_login(user: User, request, where: str) -> None:
    """At sign-in: audit and refuse a disabled account once its password (or second factor)
    checked out, so the failure says why rather than "incorrect password"."""
    if not is_disabled(user):
        return
    from app.audit.models.audit import AuditAction
    from app.audit.models.audit import AuditResult
    from app.audit.services.audit import record_audit_event

    await record_audit_event(
        action=AuditAction.AUTH_LOGIN_FAILED,
        actor_user_id=user.id,
        actor_username=user.username,
        entity_type="user",
        entity_id=user.username,
        result=AuditResult.FAILURE,
        details=f"Disabled account denied: {where}",
        request=request,
    )
    raise disabled_error()
