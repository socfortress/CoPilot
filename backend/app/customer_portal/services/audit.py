"""The Customer Portal's Audit Log page (#1298): who did what in a customer's tenant.

A customer admin (#1296) reads it, for the customers they administer whose switch the SOC
turned on (``customer_portal_audit_settings``, a missing row = off). It is a narrow
projection of the SOC's ``audit_log``, never a copy of it:

* **Only actions a customer can recognise** (``ACTIONS``): status changes and comments on
  their alerts and cases, a case opened, a report generated, downloaded or deleted, an AI
  analysis asked for, and what happened to their own portal users' accounts (sign-ins,
  failed sign-ins, password and two-factor changes, invitations, disabling). Never the SOC's
  internal events: connectors, Talon, UBA, verdicts, settings.
* **Which rows** (``visibility_clause``): a data action filed under one of the customers in
  scope; an account action about one of their portal users (``entity_type='user'`` and the
  username), or filed under one of their customers. A report the SOC generated, downloaded or
  deleted only while that report exists and is shown to the customer: a hidden SOC report's
  name is never revealed.
* **Who** (``actor_of``): one of the customer's portal users by name, the SOC as "SOC" (never a
  name), another portal user as such, else unknown. The source address is shown only for the
  customer's own users.
* **What**: the action's label, its target (a report's or a case's name, a username), a status
  before and after. ``details``, the comment text and every other stored value stay in CoPilot.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import String
from sqlalchemy import and_
from sqlalchemy import cast
from sqlalchemy import exists
from sqlalchemy import false
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditLog
from app.audit.services.retention import get_retention_days
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.customer_portal.schema.audit import EXPORT_LIMIT
from app.customer_portal.schema.audit import AuditCategory
from app.customer_portal.schema.audit import PortalAuditActor
from app.customer_portal.schema.audit import PortalAuditCustomer
from app.customer_portal.schema.audit import PortalAuditEntry
from app.customer_portal.schema.audit import PortalAuditMember
from app.customer_portal.schema.audit import PortalAuditResponse
from app.customer_portal.schema.audit import PortalAuditTarget
from app.customer_portal.services.exposure_vulnerabilities import csv_cell
from app.customer_portal.services.tenant_users import administered_customer_codes
from app.customer_portal.services.tenant_users import customer_names
from app.db.universal_models import CustomerPortalAuditSettings
from app.db.universal_models import IncidentManagementCustomerReport
from app.time_utils import now_utc

NOT_AVAILABLE = "The audit log is available to your organization's administrators once your SOC turns it on."

#: Roles whose people the portal calls "the SOC".
SOC_ROLE_IDS = frozenset({RoleEnum.admin.value, RoleEnum.analyst.value, RoleEnum.responder.value, RoleEnum.scheduler.value})


@dataclass(frozen=True)
class ActionSpec:
    category: AuditCategory
    label: str
    # Filed under a customer (an alert, a case, a report) or about a user's account.
    about_user: bool = False


ACTIONS: Dict[str, ActionSpec] = {
    AuditAction.ALERT_STATUS_CHANGE.value: ActionSpec("alerts", "Alert status changed"),
    AuditAction.ALERT_COMMENT_CREATE.value: ActionSpec("alerts", "Comment added to an alert"),
    AuditAction.ALERT_COMMENT_EDIT.value: ActionSpec("alerts", "Comment edited on an alert"),
    AuditAction.ALERT_COMMENT_DELETE.value: ActionSpec("alerts", "Comment deleted from an alert"),
    AuditAction.AI_ANALYSIS_REQUEST.value: ActionSpec("alerts", "AI analysis requested"),
    AuditAction.CASE_CREATE.value: ActionSpec("cases", "Case opened"),
    AuditAction.CASE_STATUS_CHANGE.value: ActionSpec("cases", "Case status changed"),
    AuditAction.CASE_COMMENT_CREATE.value: ActionSpec("cases", "Comment added to a case"),
    AuditAction.CASE_COMMENT_EDIT.value: ActionSpec("cases", "Comment edited on a case"),
    AuditAction.CASE_COMMENT_DELETE.value: ActionSpec("cases", "Comment deleted from a case"),
    AuditAction.REPORT_GENERATE.value: ActionSpec("reports", "Report generated"),
    AuditAction.REPORT_DOWNLOAD.value: ActionSpec("reports", "Report downloaded"),
    AuditAction.REPORT_DELETE.value: ActionSpec("reports", "Report deleted"),
    AuditAction.AUTH_LOGIN.value: ActionSpec("account", "Signed in", about_user=True),
    AuditAction.AUTH_LOGIN_FAILED.value: ActionSpec("account", "Sign-in failed", about_user=True),
    AuditAction.USER_UPDATE.value: ActionSpec("account", "Account updated", about_user=True),
    AuditAction.USER_PASSWORD_CHANGE.value: ActionSpec("account", "Replaced a password set by an administrator", about_user=True),
    AuditAction.USER_TOTP_ENABLE.value: ActionSpec("account", "Two-factor authentication turned on", about_user=True),
    AuditAction.USER_TOTP_DISABLE.value: ActionSpec("account", "Two-factor authentication turned off", about_user=True),
    AuditAction.USER_CREATE.value: ActionSpec("users", "Account created", about_user=True),
    AuditAction.USER_PASSWORD_CHANGE_REQUIRED.value: ActionSpec("users", "Password set by an administrator", about_user=True),
    AuditAction.USER_DISABLE.value: ActionSpec("users", "Account disabled", about_user=True),
    AuditAction.USER_ENABLE.value: ActionSpec("users", "Account enabled", about_user=True),
    AuditAction.CUSTOMER_ADMIN_UPDATE.value: ActionSpec("users", "Administrator role changed", about_user=True),
    AuditAction.CUSTOMER_USER_INVITE.value: ActionSpec("users", "User invited", about_user=True),
    AuditAction.CUSTOMER_USER_TOTP_RESET.value: ActionSpec("users", "Two-factor authentication reset", about_user=True),
    AuditAction.CUSTOMER_USER_PASSWORD_RESET.value: ActionSpec("users", "Temporary password issued", about_user=True),
}

DATA_ACTIONS = tuple(action for action, spec in ACTIONS.items() if not spec.about_user)
USER_ACTIONS = tuple(action for action, spec in ACTIONS.items() if spec.about_user)
REPORT_ACTIONS = (AuditAction.REPORT_GENERATE.value, AuditAction.REPORT_DOWNLOAD.value, AuditAction.REPORT_DELETE.value)

# ``user.update`` covers several changes; its fixed ``details`` (written by CoPilot, never by a
# user) say which. Read here, never sent.
USER_UPDATE_LABELS: Tuple[Tuple[str, str], ...] = (
    ("Self-service password change", "Password changed"),
    ("Password reset by admin", "Password reset by the SOC"),
    ("Forced TOTP (2FA) reset by admin", "Two-factor authentication reset by the SOC"),
    ("Temporary password issued", "Temporary password issued by the SOC"),
)

STATUS_ACTIONS = (AuditAction.ALERT_STATUS_CHANGE.value, AuditAction.CASE_STATUS_CHANGE.value)

TARGET_TYPES = {"alert", "case", "report", "user"}


# ── the switch ────────────────────────────────────────────────────────────────


async def get_audit_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalAuditSettings]:
    result = await session.execute(select(CustomerPortalAuditSettings).where(CustomerPortalAuditSettings.customer_code == customer_code))
    return result.scalars().first()


async def upsert_audit_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalAuditSettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_audit_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalAuditSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def scope_codes(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> List[str]:
    """The customers whose log ``user`` reads: those they administer with the switch on, narrowed to ``requested``."""
    administered = await administered_customer_codes(user, session)
    if not administered:
        return []
    query = select(CustomerPortalAuditSettings.customer_code).where(
        CustomerPortalAuditSettings.enabled.is_(True),
        CustomerPortalAuditSettings.customer_code.in_(administered),
    )
    if requested:
        query = query.where(CustomerPortalAuditSettings.customer_code.in_(requested))
    return sorted((await session.execute(query)).scalars().all())


async def require_scope(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> List[str]:
    codes = await scope_codes(user, session, requested)
    if not codes:
        raise HTTPException(status_code=403, detail=NOT_AVAILABLE)
    return codes


async def availability(user: User, session: AsyncSession) -> List[PortalAuditCustomer]:
    codes = await scope_codes(user, session)
    names = await customer_names(codes, session)
    return [PortalAuditCustomer(customer_code=code, customer_name=names.get(code, code)) for code in codes]


# ── who belongs ───────────────────────────────────────────────────────────────


async def members_of(codes: List[str], session: AsyncSession) -> List[PortalAuditMember]:
    """The portal users of these customers, disabled ones included: whose account events are shown."""
    if not codes:
        return []
    result = await session.execute(
        select(User.id, User.username)
        .join(UserCustomerAccess, UserCustomerAccess.user_id == User.id)
        .where(UserCustomerAccess.customer_code.in_(codes), User.role_id == RoleEnum.customer_user.value)
        .distinct()
        .order_by(User.username),
    )
    return [PortalAuditMember(id=user_id, username=username) for user_id, username in result.all()]


# ── which rows ────────────────────────────────────────────────────────────────


def visible_report_clause():
    """The row's report exists and the customer sees it (shown to them, or generated by a portal user)."""
    report = IncidentManagementCustomerReport
    return exists(
        select(report.id).where(
            cast(report.id, String) == AuditLog.entity_id,
            report.customer_code == AuditLog.customer_code,
            or_(report.visible_to_customer.is_(True), report.generated_by_role == RoleEnum.customer_user.name),
        ),
    )


def visibility_clause(codes: List[str], members: List[PortalAuditMember]):
    """The one definition of which ``audit_log`` rows a customer's log shows."""
    member_ids = [member.id for member in members]
    usernames = [member.username for member in members]
    by_member = AuditLog.actor_user_id.in_(member_ids) if member_ids else false()
    data_rows = and_(
        AuditLog.action.in_(DATA_ACTIONS),
        AuditLog.customer_code.in_(codes),
        # A report row the SOC wrote names the report: only while the customer can see it.
        or_(AuditLog.action.notin_(REPORT_ACTIONS), by_member, visible_report_clause()),
    )
    about_member = and_(AuditLog.entity_type == "user", AuditLog.entity_id.in_(usernames)) if usernames else false()
    user_rows = and_(AuditLog.action.in_(USER_ACTIONS), or_(about_member, AuditLog.customer_code.in_(codes)))
    return or_(data_rows, user_rows)


def filter_clauses(
    *,
    category: Optional[AuditCategory],
    member: Optional[PortalAuditMember],
    since: Optional[datetime],
    until: Optional[datetime],
) -> list:
    clauses: list = []
    if category:
        clauses.append(AuditLog.action.in_([action for action, spec in ACTIONS.items() if spec.category == category]))
    if member is not None:
        clauses.append(
            or_(
                AuditLog.actor_user_id == member.id,
                and_(AuditLog.entity_type == "user", AuditLog.entity_id == member.username),
            ),
        )
    if since is not None:
        clauses.append(AuditLog.timestamp >= since)
    if until is not None:
        clauses.append(AuditLog.timestamp < until)
    return clauses


# ── projection (pure) ─────────────────────────────────────────────────────────


def label_for(row: AuditLog) -> str:
    spec = ACTIONS[row.action]
    if row.action == AuditAction.USER_UPDATE.value:
        details = row.details or ""
        return next((label for prefix, label in USER_UPDATE_LABELS if details.startswith(prefix)), spec.label)
    if row.action == AuditAction.CUSTOMER_ADMIN_UPDATE.value:
        now_admin = (row.new_value or {}).get("is_customer_admin")
        if now_admin is True:
            return "Made a customer administrator"
        if now_admin is False:
            return "No longer a customer administrator"
    return spec.label


def actor_of(row: AuditLog, member_ids: Dict[int, str], roles: Dict[int, int]) -> PortalAuditActor:
    if row.actor_user_id is not None and row.actor_user_id in member_ids:
        return PortalAuditActor(kind="member", username=member_ids[row.actor_user_id])
    role = roles.get(row.actor_user_id) if row.actor_user_id is not None else None
    if role in SOC_ROLE_IDS:
        return PortalAuditActor(kind="soc")
    if role == RoleEnum.customer_user.value:
        return PortalAuditActor(kind="other")
    return PortalAuditActor(kind="unknown")


def _text(value) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def target_of(row: AuditLog) -> Optional[PortalAuditTarget]:
    if row.entity_type not in TARGET_TYPES or row.entity_id in (None, ""):
        return None
    new = row.new_value if isinstance(row.new_value, dict) else {}
    label = None
    if row.entity_type == "report":
        label = _text(new.get("report_name"))
    elif row.entity_type == "case" and row.action == AuditAction.CASE_CREATE.value:
        label = _text(new.get("case_name"))
    elif row.entity_type == "user":
        label = row.entity_id
    return PortalAuditTarget(type=row.entity_type, id=str(row.entity_id), label=label)


def _status(value) -> Optional[str]:
    return _text(value.get("status")) if isinstance(value, dict) else None


def project(row: AuditLog, member_ids: Dict[int, str], roles: Dict[int, int], codes: Iterable[str]) -> PortalAuditEntry:
    """One row as the portal shows it; ``codes`` are the customers in scope, the only ones ever named."""
    actor = actor_of(row, member_ids, roles)
    changes = row.action in STATUS_ACTIONS
    result = row.result if row.result in ("success", "failure") else "unknown"
    return PortalAuditEntry(
        id=row.id,
        timestamp=row.timestamp.replace(microsecond=0).isoformat() + "Z",
        action=row.action,
        label=label_for(row),
        category=ACTIONS[row.action].category,
        actor=actor,
        # A member's sign-in may be filed under another of their customers: never named here.
        customer_code=row.customer_code if row.customer_code in codes else None,
        target=target_of(row),
        from_value=_status(row.old_value) if changes else None,
        to_value=_status(row.new_value) if changes else None,
        result=result,
        source_ip=row.source_ip if actor.kind == "member" else None,
    )


# ── reads ─────────────────────────────────────────────────────────────────────


@dataclass
class Scope:
    codes: List[str]
    members: List[PortalAuditMember]

    @property
    def member_ids(self) -> Dict[int, str]:
        return {member.id: member.username for member in self.members}

    def member(self, user_id: Optional[int]) -> Optional[PortalAuditMember]:
        if user_id is None:
            return None
        found = next((member for member in self.members if member.id == user_id), None)
        if found is None:
            # Not one of theirs: as if it did not exist, so ids cannot be probed.
            raise HTTPException(status_code=404, detail="User not found")
        return found


async def resolve(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> Scope:
    codes = await require_scope(user, session, requested)
    return Scope(codes=codes, members=await members_of(codes, session))


async def _roles(rows: Iterable[AuditLog], session: AsyncSession) -> Dict[int, int]:
    ids = {row.actor_user_id for row in rows if row.actor_user_id is not None}
    if not ids:
        return {}
    result = await session.execute(select(User.id, User.role_id).where(User.id.in_(ids)))
    return {user_id: role_id for user_id, role_id in result.all()}


def _where(scope: Scope, **filters) -> list:
    return [visibility_clause(scope.codes, scope.members), *filter_clauses(**filters)]


async def list_entries(
    scope: Scope,
    session: AsyncSession,
    *,
    category: Optional[AuditCategory] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 25,
) -> PortalAuditResponse:
    where = _where(scope, category=category, member=scope.member(user_id), since=since, until=until)
    total = (await session.execute(select(func.count()).select_from(AuditLog).where(*where))).scalar_one()
    rows = (
        (
            await session.execute(
                select(AuditLog)
                .where(*where)
                .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            )
        )
        .scalars()
        .all()
    )
    roles = await _roles(rows, session)
    member_ids = scope.member_ids
    return PortalAuditResponse(
        entries=[project(row, member_ids, roles, scope.codes) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        retention_days=get_retention_days(),
        members=scope.members,
        success=True,
        message="Audit log retrieved successfully",
    )


CSV_HEADER = ["Time (UTC)", "Customer", "Category", "Action", "By", "Target", "From", "To", "Result", "Source IP"]


def actor_text(actor: PortalAuditActor) -> str:
    if actor.kind == "member":
        return actor.username or ""
    return {"soc": "SOC", "other": "Another portal user"}.get(actor.kind, "Unknown")


def target_text(target: Optional[PortalAuditTarget]) -> str:
    if target is None:
        return ""
    name = target.type.capitalize()
    if target.type == "user":
        return f"User {target.label or target.id}"
    return f"{name} #{target.id}" + (f" ({target.label})" if target.label else "")


def csv_row(entry: PortalAuditEntry) -> List[str]:
    return [
        csv_cell(value)
        for value in (
            entry.timestamp,
            entry.customer_code,
            entry.category,
            entry.label,
            actor_text(entry.actor),
            target_text(entry.target),
            entry.from_value,
            entry.to_value,
            entry.result,
            entry.source_ip,
        )
    ]


async def export_csv(
    scope: Scope,
    session: AsyncSession,
    *,
    category: Optional[AuditCategory] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = EXPORT_LIMIT,
) -> Tuple[str, bool]:
    """The filtered log, newest first, as CSV, and whether it was cut at ``limit``."""
    where = _where(scope, category=category, member=scope.member(user_id), since=since, until=until)
    rows = (
        (await session.execute(select(AuditLog).where(*where).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit + 1)))
        .scalars()
        .all()
    )
    truncated = len(rows) > limit
    rows = rows[:limit]
    roles = await _roles(rows, session)
    member_ids = scope.member_ids
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for row in rows:
        writer.writerow(csv_row(project(row, member_ids, roles, scope.codes)))
    return buffer.getvalue(), truncated
