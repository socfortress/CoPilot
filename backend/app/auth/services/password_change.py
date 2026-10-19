"""A password an admin chose must be replaced by the user (#1277).

An admin chooses a user's password in three places: a temporary password emailed from the
customer's Security tab (``/auth/security/users/{id}/send-temp-password``), a reset
(``/auth/reset-password``) and a new account (``/auth/register``). Each sets
``user.must_change_password``; the user's own change (``/auth/reset-password/me``) clears it.

While it is set, a ``customer_user`` reaches only what the forced change needs
(``ALLOWED_PATHS``); every other authenticated route answers 403 with
``PASSWORD_CHANGE_HEADER``, never 401, which the portal would read as the end of the
session. The check runs where the user is resolved for every authenticated request
(``AuthHandler``), on the stored flag, so it takes effect and lifts at the next request:
no token has to be re-issued either way.

Analysts and admins carry the flag too, but nothing enforces it for them yet: the analyst
frontend has no forced-change flow.
"""

from typing import Optional

from fastapi import HTTPException
from fastapi import Request

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User

PASSWORD_CHANGE_HEADER = "X-Password-Change-Required"
PASSWORD_CHANGE_REQUIRED = "Your password was set by your security team. Choose a new password to continue."

# What a held user may still reach: the change itself, who they are, a token refresh (a
# refused one would end the session) and the portal's branding (the change page wears it).
# Route templates without the app's "/api" prefix, so the check holds however the routers
# are mounted.
API_PREFIX = "/api"
ALLOWED_PATHS = frozenset(
    {
        "/auth/reset-password/me",
        "/auth/refresh",
        "/customer_portal/me",
        "/customer_portal/settings/effective",
        "/customer_portal/settings/effective/logo",
    },
)


def is_held(user: User) -> bool:
    """Whether ``user`` must change their password before using the portal."""
    return bool(getattr(user, "must_change_password", False)) and user.role_id == RoleEnum.customer_user.value


def route_path(request: Request) -> str:
    """The matched route's path template, else the request's path, without the "/api" prefix."""
    route = request.scope.get("route")
    path = getattr(route, "path", None) or request.url.path
    return path[len(API_PREFIX) :] if path.startswith(API_PREFIX + "/") else path


def enforce_password_change(request: Request, user: User) -> None:
    """Refuse every route but ``ALLOWED_PATHS`` to a held user."""
    if is_held(user) and route_path(request) not in ALLOWED_PATHS:
        raise HTTPException(status_code=403, detail=PASSWORD_CHANGE_REQUIRED, headers={PASSWORD_CHANGE_HEADER: "true"})


def require_change(user: User, chosen_by: User) -> bool:
    """Mark ``user`` as having to replace a password ``chosen_by`` set; a no-op for one's own.

    Returns whether it applied, i.e. whether the change is to be audited.
    """
    if chosen_by.id == user.id:
        return False
    user.must_change_password = True
    return True


async def record_change_required(user: User, actor: User, how: str, request: Optional[Request] = None) -> None:
    """Audit that ``actor`` chose ``user``'s password, so ``user`` must replace it."""
    await record_audit_event(
        action=AuditAction.USER_PASSWORD_CHANGE_REQUIRED,
        actor_user_id=actor.id,
        actor_username=actor.username,
        entity_type="user",
        entity_id=user.username,
        details=f"Password set by an admin ({how}); the user must choose a new one",
        request=request,
    )


async def record_changed(user: User, request: Optional[Request] = None) -> None:
    """Audit that ``user`` replaced a password an admin had chosen."""
    await record_audit_event(
        action=AuditAction.USER_PASSWORD_CHANGE,
        actor_user_id=user.id,
        actor_username=user.username,
        entity_type="user",
        entity_id=user.username,
        details="Replaced the password an admin had set",
        request=request,
    )
