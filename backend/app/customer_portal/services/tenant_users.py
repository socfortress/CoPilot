"""Self-service management of a customer's portal users by a customer admin (#1296).

A customer admin is a ``customer_user`` whose ``user_customer_access`` row for a customer has
``is_customer_admin`` (set by the SOC only, ``/auth/security/customers/{code}/users/{id}/customer-admin``).
From the Customer Portal they list that customer's portal users, invite new ones, disable and enable
them, reset their 2FA and issue them a temporary password. Nothing else, and only within these rules:

- **Who is listed**: active and disabled ``customer_user`` accounts with access to a customer the
  caller administers. SOC staff assigned to the customer are never listed, nor is any customer the
  caller does not administer ever named.
- **Who can be managed** (``manage_refusal``): never the caller themself (their own account is the
  Profile's), never another customer admin (the SOC appointed them), never an account that also
  belongs to a customer the caller does not administer (disabling it would lock it out of that
  customer too). The SOC manages those.
- **Invitations** create a ``customer_user`` with access to customers the caller administers only,
  never an admin, with a generated password the user must replace at first sign-in (#1277).
- **A temporary password** (invitation or reset) goes by email when SMTP is configured; when it is
  not, or the email cannot be rendered or sent, it is returned once to the caller instead
  (``deliver_temporary_password``). The password is never logged.

An account someone cannot see (another tenant's, a SOC user's, an unknown id) is a 404 like a
missing one, so ids cannot be probed. Every action is audited.
"""

from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.totp import UserTOTP
from app.auth.models.users import Password
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.services import password_change
from app.auth.services import security_admin
from app.auth.services import temp_password_email
from app.customer_portal.schema.me import PortalCustomer
from app.customer_portal.schema.tenant_users import InviteRequest
from app.customer_portal.schema.tenant_users import TemporaryPassword
from app.customer_portal.schema.tenant_users import TenantUser
from app.db.universal_models import Customers
from app.time_utils import now_utc

NOT_A_CUSTOMER_ADMIN = "Only a customer administrator can manage users."
USER_NOT_FOUND = "User not found"
REASON_SELF = "This is your own account: change it from your Profile."
REASON_ADMIN = "Customer administrators are managed by your SOC."
REASON_OTHER_CUSTOMER = "This account also belongs to another customer, so your SOC manages it."


# ── Who the caller administers ────────────────────────────────────────────────


async def administered_customer_codes(user: User, session: AsyncSession) -> List[str]:
    """The customers ``user`` administers: none unless they are a ``customer_user``."""
    if user.role_id != RoleEnum.customer_user.value:
        return []
    result = await session.execute(
        select(UserCustomerAccess.customer_code)
        .where(UserCustomerAccess.user_id == user.id, UserCustomerAccess.is_customer_admin.is_(True))
        .order_by(UserCustomerAccess.customer_code),
    )
    return list(dict.fromkeys(result.scalars().all()))


async def require_customer_admin(user: User, session: AsyncSession) -> List[str]:
    codes = await administered_customer_codes(user, session)
    if not codes:
        raise HTTPException(status_code=403, detail=NOT_A_CUSTOMER_ADMIN)
    return codes


async def customer_names(codes: List[str], session: AsyncSession) -> Dict[str, str]:
    if not codes:
        return {}
    result = await session.execute(select(Customers.customer_code, Customers.customer_name).where(Customers.customer_code.in_(codes)))
    names = {code: (name or "").strip() for code, name in result.all()}
    return {code: names.get(code) or code for code in codes}


# ── The portal users of those customers ───────────────────────────────────────


@dataclass
class Member:
    """A portal user with every customer access row they hold."""

    user: User
    access: Dict[str, bool]  # customer code -> is_customer_admin


async def members_of(codes: List[str], session: AsyncSession, user_id: Optional[int] = None) -> List[Member]:
    """The ``customer_user`` accounts with access to any of ``codes`` (one of them with ``user_id``),
    each with all their access rows, oldest account first."""
    if not codes:
        return []
    ids_query = (
        select(UserCustomerAccess.user_id)
        .join(User, User.id == UserCustomerAccess.user_id)
        .where(UserCustomerAccess.customer_code.in_(codes), User.role_id == RoleEnum.customer_user.value)
    )
    if user_id is not None:
        ids_query = ids_query.where(UserCustomerAccess.user_id == user_id)
    ids = list(dict.fromkeys((await session.execute(ids_query)).scalars().all()))
    if not ids:
        return []
    users = (await session.execute(select(User).where(User.id.in_(ids)).order_by(User.id))).scalars().all()
    rows = (
        await session.execute(
            select(UserCustomerAccess.user_id, UserCustomerAccess.customer_code, UserCustomerAccess.is_customer_admin).where(
                UserCustomerAccess.user_id.in_(ids),
            ),
        )
    ).all()
    access: Dict[int, Dict[str, bool]] = {}
    for uid, code, is_admin in rows:
        held = access.setdefault(uid, {})
        held[code] = held.get(code, False) or bool(is_admin)
    return [Member(user=user, access=access.get(user.id, {})) for user in users]


def manage_refusal(caller: User, member: Member, administered: Set[str]) -> Optional[str]:
    """Why ``caller`` may not manage ``member``, or None. Pure."""
    if member.user.id == caller.id:
        return REASON_SELF
    if any(member.access.get(code) for code in member.access):
        return REASON_ADMIN
    if not set(member.access) <= administered:
        return REASON_OTHER_CUSTOMER
    return None


async def totp_enabled_for(ids: List[int], session: AsyncSession) -> Set[int]:
    if not ids:
        return set()
    rows = (await session.execute(select(UserTOTP.user_id, UserTOTP.enabled).where(UserTOTP.user_id.in_(ids)))).all()
    return {uid for uid, enabled in rows if enabled}


def to_tenant_user(caller: User, member: Member, administered: List[str], names: Dict[str, str], totp: Set[int]) -> TenantUser:
    reason = manage_refusal(caller, member, set(administered))
    user = member.user
    return TenantUser(
        id=user.id,
        username=user.username,
        email=user.email,
        customers=[
            PortalCustomer(customer_code=code, customer_name=names.get(code, code), is_customer_admin=member.access[code])
            for code in administered
            if code in member.access
        ],
        is_customer_admin=any(member.access.get(code) for code in administered),
        disabled=user.disabled_at is not None,
        disabled_at=user.disabled_at,
        must_change_password=bool(user.must_change_password),
        totp_enabled=user.id in totp,
        last_login_at=user.last_login_at,
        is_self=user.id == caller.id,
        can_manage=reason is None,
        managed_by_soc_reason=reason,
    )


async def list_users(caller: User, session: AsyncSession) -> Tuple[List[str], Dict[str, str], List[TenantUser]]:
    administered = await require_customer_admin(caller, session)
    names = await customer_names(administered, session)
    members = await members_of(administered, session)
    totp = await totp_enabled_for([m.user.id for m in members], session)
    users = [to_tenant_user(caller, m, administered, names, totp) for m in members]
    # The caller first, then by name: a list to scan, not an audit trail.
    users.sort(key=lambda u: (not u.is_self, u.username.casefold()))
    return administered, names, users


async def view(caller: User, user_id: int, administered: List[str], session: AsyncSession) -> TenantUser:
    members = await members_of(administered, session, user_id=user_id)
    if not members:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    names = await customer_names(administered, session)
    totp = await totp_enabled_for([user_id], session)
    return to_tenant_user(caller, members[0], administered, names, totp)


async def manageable(caller: User, user_id: int, session: AsyncSession) -> Tuple[List[str], Member]:
    """The target, if ``caller`` may manage them: 404 if they cannot see them, 403 with the reason
    if they can see but not manage them."""
    administered = await require_customer_admin(caller, session)
    members = await members_of(administered, session, user_id=user_id)
    if not members:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    reason = manage_refusal(caller, members[0], set(administered))
    if reason:
        raise HTTPException(status_code=403, detail=reason)
    return administered, members[0]


def audit_customer(member: Member, administered: List[str]) -> Optional[str]:
    """The customer an action is filed under: the target's first administered customer."""
    return next((code for code in administered if code in member.access), None)


async def audit(
    action: AuditAction,
    caller: User,
    target: User,
    customer_code: Optional[str],
    details: str,
    request: Optional[Request],
    new_value: Optional[dict] = None,
) -> None:
    await record_audit_event(
        action=action,
        actor_user_id=caller.id,
        actor_username=caller.username,
        customer_code=customer_code,
        entity_type="user",
        entity_id=target.username,
        details=details,
        new_value=new_value,
        request=request,
    )


# ── Temporary passwords ───────────────────────────────────────────────────────


async def deliver_temporary_password(
    session: AsyncSession,
    user: User,
    customer_code: Optional[str],
    password: Password,
) -> TemporaryPassword:
    """Email ``password`` to ``user``, or say why it could not go and return it to be shown once.

    The email uses the customer's temporary-password template (#999), like the SOC's own send.
    """
    if not security_admin.smtp_configured():
        return TemporaryPassword(delivery="shown", temporary_password=password.plain, email_problem="Email is not configured")
    try:
        template = await temp_password_email.resolve_template(session, customer_code)
        customer_name = await temp_password_email.customer_name_for(session, customer_code)
        subject, text_body, html_body = await temp_password_email.render_email(
            session,
            template=template,
            username=user.username,
            email=user.email,
            temp_password=password.plain,
            customer_code=customer_code,
            customer_name=customer_name,
            user_id=user.id,
        )
        await security_admin.send_email(to_addr=user.email, subject=subject, body=text_body, html_body=html_body)
    except Exception as e:  # noqa: BLE001 - any failure falls back to showing the password once
        logger.error(f"Temporary password email for {user.username} could not be sent: {type(e).__name__}")
        return TemporaryPassword(
            delivery="shown",
            temporary_password=password.plain,
            email_problem="The email could not be sent",
        )
    return TemporaryPassword(delivery="email")


# ── Actions ───────────────────────────────────────────────────────────────────


async def invite(
    caller: User,
    body: InviteRequest,
    session: AsyncSession,
    request: Optional[Request],
) -> Tuple[TenantUser, TemporaryPassword]:
    administered = await require_customer_admin(caller, session)
    outside = [code for code in body.customer_codes if code not in administered]
    if outside:
        raise HTTPException(status_code=403, detail="You can only invite users to customers you administer.")

    taken = await session.execute(
        select(User.username, User.email).where(
            (func.lower(User.username) == body.username.lower()) | (func.lower(User.email) == str(body.email).lower()),
        ),
    )
    for username, email in taken.all():
        if username.lower() == body.username.lower():
            raise HTTPException(status_code=409, detail="That username is taken.")
        if (email or "").lower() == str(body.email).lower():
            raise HTTPException(status_code=409, detail="That email address is already registered.")

    password = security_admin.generate_temporary_password()
    user = User(
        username=body.username,
        password=password.hashed,
        email=str(body.email),
        role_id=RoleEnum.customer_user.value,
        must_change_password=True,
    )
    session.add(user)
    await session.flush()
    for code in body.customer_codes:
        session.add(UserCustomerAccess(user_id=user.id, customer_code=code, is_customer_admin=False))
    await session.commit()
    await session.refresh(user)

    member = Member(user=user, access={code: False for code in body.customer_codes})
    customer_code = audit_customer(member, administered)
    await audit(
        AuditAction.CUSTOMER_USER_INVITE,
        caller,
        user,
        customer_code,
        "Portal user invited by a customer admin",
        request,
        new_value={"username": user.username, "email": user.email, "customer_codes": body.customer_codes},
    )
    await password_change.record_change_required(user, caller, "invitation", request)
    delivered = await deliver_temporary_password(session, user, body.customer_codes[0] if len(body.customer_codes) == 1 else None, password)
    return await view(caller, user.id, administered, session), delivered


async def set_disabled(caller: User, user_id: int, disabled: bool, session: AsyncSession, request: Optional[Request]) -> TenantUser:
    administered, member = await manageable(caller, user_id, session)
    user = member.user
    if (user.disabled_at is not None) != disabled:
        user.disabled_at = now_utc() if disabled else None
        session.add(user)
        await session.commit()
        await audit(
            AuditAction.USER_DISABLE if disabled else AuditAction.USER_ENABLE,
            caller,
            user,
            audit_customer(member, administered),
            f"Portal user {'disabled' if disabled else 'enabled'} by a customer admin",
            request,
        )
    return await view(caller, user_id, administered, session)


async def reset_totp(caller: User, user_id: int, session: AsyncSession, request: Optional[Request]) -> Tuple[TenantUser, bool]:
    administered, member = await manageable(caller, user_id, session)
    removed = await security_admin.force_reset_totp(session, user_id)
    await audit(
        AuditAction.CUSTOMER_USER_TOTP_RESET,
        caller,
        member.user,
        audit_customer(member, administered),
        f"2FA reset by a customer admin ({'removed' if removed else 'no enrolment present'})",
        request,
    )
    return await view(caller, user_id, administered, session), removed


async def issue_temporary_password(
    caller: User,
    user_id: int,
    session: AsyncSession,
    request: Optional[Request],
) -> Tuple[TenantUser, TemporaryPassword]:
    administered, member = await manageable(caller, user_id, session)
    user = member.user
    password = security_admin.generate_temporary_password()
    await security_admin.apply_temporary_password(session, user, password)
    customer_code = audit_customer(member, administered)
    await audit(
        AuditAction.CUSTOMER_USER_PASSWORD_RESET,
        caller,
        user,
        customer_code,
        "Temporary password issued by a customer admin",
        request,
    )
    await password_change.record_change_required(user, caller, "temporary password from a customer admin", request)
    delivered = await deliver_temporary_password(session, user, customer_code, password)
    return await view(caller, user_id, administered, session), delivered
