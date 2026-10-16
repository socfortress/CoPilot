"""Who may decide a Talon v2 action proposal, what is checked again just before it runs, and the
run itself (plan M5-11a steps 2, 5 and 6; talon-analyst SPEC §5.3 M5-11, §9.5, D46, D47).

**D47, in CoPilot** (``check_d47``), before anything is claimed:
- the role, from the user's ``role_id`` (never the token's scopes, so a demoted admin's old token
  doesn't count): admin or responder for an ``endpoint-action`` (quarantine, release); admin,
  analyst or responder for an ``external-action`` (an alert's status, assignee, comment);
- ``enforce_customer_access`` on the record's customer;
- an alert target: ``_ensure_alert_access`` (customer and tags, as the alert routes check), and the
  alert's customer must be the record's;
- a host target: ``enforce_hostname_access``.

**Re-checks** (``recheck``), after talon-analyst granted the claim and just before running; a
failure runs nothing:
- ``assign_alert``: the assignee is exactly one CoPilot user, of a SOC role (decision h), with
  access to the record's customer (CoPilot's own route only checks that the name exists);
- quarantine and release, under ``SELECT … FOR UPDATE`` on ``agents`` (held while the route runs;
  index lookups only, so other agents stay writable; a lock wait of at most 5 s, then it fails
  closed): exactly one row for the host name (compared with ``lower()`` *and* the column's
  collation, which is what the route's own lookup uses), whose canonical client id (``C.`` + 16
  lowercase hex) is the record's, whose customer is the record's, and no other row claiming that
  client id. CoPilot's
  quarantine route resolves the host's client by name with ``.first()``; this makes that first row
  the proposal's.

**The run** (``run``): CoPilot's existing route handlers, called directly under the approver
(decision e), so their own tenant checks, the SLA lifecycle, the assignment notification,
``agents.quarantined`` and the ``RESPONSE_QUARANTINE`` audit all happen as for a manual action.
Calling a handler skips its ``Security(...)`` scope dependency, which is why D47 checks the role
first. ``tests/test_talon_actions.py`` pins the handlers' signatures.
"""
import re
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import SOC_ROLES
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import TalonActionRequest
from app.connectors.talon.services.talon_action_sync import ACTION_CLASSES
from app.connectors.talon.services.talon_action_sync import ALERT_ACTIONS
from app.connectors.talon.services.talon_action_sync import APPROVER_ROLES
from app.connectors.talon.services.talon_action_sync import HOST_ACTIONS
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes
from app.connectors.velociraptor.schema.artifacts import ActionEnum
from app.connectors.velociraptor.schema.artifacts import QuarantineArtifactsEnum
from app.connectors.velociraptor.schema.artifacts import QuarantineBody
from app.db.universal_models import Agents
from app.incidents.routes import db_operations as incident_routes
from app.incidents.schema.db_operations import AlertStatus
from app.incidents.schema.db_operations import AssignedToAlert
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_access import enforce_hostname_access

#: A root-org Velociraptor client id (talon-analyst ``rules.CLIENT_ID_RE``).
CLIENT_ID = re.compile(r"C\.[0-9a-fA-F]{16}")
#: A stored client id as the "does anyone else claim it" check reads it: any case, any org suffix
#: (talon-analyst ``rules._CLAIM_CLIENT_RE``; anything after ``-`` counts, to fail closed).
_CLAIMED_CLIENT = re.compile(r"[Cc]\.([0-9a-fA-F]{16})(?:-.*)?", re.DOTALL)
#: talon-analyst's limits on the arguments it proposes (``talon.tools.actions``).
ASSIGNEE_MAX = 64
COMMENT_MAX = 4000
#: The longest handler message kept in a result (the result is a summary, at most 16 KB as JSON).
MESSAGE_MAX = 500
QUARANTINE_ACTION = {"quarantine_host": ActionEnum.quarantine.value, "release_host": ActionEnum.remove_quarantine.value}
NOT_ALLOWED = "this role may not decide this action"


def canonical_client_id(value: object) -> Optional[str]:
    """``C.1A2B…`` → ``C.1a2b…``; None for anything else (an org-suffixed id included)."""
    if isinstance(value, str) and CLIENT_ID.fullmatch(value):
        return "C." + value[2:].lower()
    return None


def claimed_client_id(value: object) -> Optional[str]:
    """The canonical id a stored client id claims, whatever its case or org suffix."""
    if isinstance(value, str):
        match = _CLAIMED_CLIENT.fullmatch(value)
        if match:
            return "C." + match.group(1).lower()
    return None


def role_name(user: Any) -> Optional[str]:
    try:
        return RoleEnum(getattr(user, "role_id", None)).name
    except ValueError:
        return None


def role_may_decide(action: str, user: Any) -> bool:
    """D47 by the user's role in the database (``role_id``), not by the token's scopes."""
    side_effect = ACTION_CLASSES.get(action)
    return side_effect is not None and role_name(user) in APPROVER_ROLES[side_effect]


def _int(value: object) -> Optional[int]:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class ProposalShape(ValueError):
    """The record's target or arguments aren't what this action takes: CoPilot can't run it."""


@dataclass(frozen=True)
class Plan:
    """What CoPilot will run for a proposal: its arguments, checked against its target."""

    action: str
    alert_id: Optional[int] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    comment: Optional[str] = None
    hostname: Optional[str] = None
    velociraptor_id: Optional[str] = None
    quarantine_action: Optional[str] = None
    artifact_name: Optional[str] = None


def plan_for(row: TalonActionRequest) -> Plan:
    """The run a record asks for, or ``ProposalShape``. The arguments must name the target the
    record binds (talon-analyst wrote both from the same check); anything else isn't run."""
    target, args = row.target or {}, row.args or {}
    if row.action in ALERT_ACTIONS:
        alert_id = _int(target.get("alert_id"))
        if alert_id is None or _int(args.get("alert_id")) != alert_id:
            raise ProposalShape("the arguments don't name the target alert")
        if row.action == "set_alert_status":
            status = args.get("status")
            if status not in {s.value for s in AlertStatus}:
                raise ProposalShape("not an alert status")
            return Plan(row.action, alert_id=alert_id, status=status)
        if row.action == "assign_alert":
            assignee = args.get("assigned_to")
            if not isinstance(assignee, str) or not 1 <= len(assignee) <= ASSIGNEE_MAX:
                raise ProposalShape("not a user name")
            return Plan(row.action, alert_id=alert_id, assigned_to=assignee)
        comment = args.get("comment")
        if not isinstance(comment, str) or not 1 <= len(comment) <= COMMENT_MAX:
            raise ProposalShape("not a comment")
        return Plan(row.action, alert_id=alert_id, comment=comment)  # as written (decision i)
    if row.action in HOST_ACTIONS:
        hostname = target.get("hostname")
        client = canonical_client_id(target.get("velociraptor_id"))
        if target.get("customer_code") != row.customer_code:
            raise ProposalShape("the target names another customer")
        if not isinstance(hostname, str) or not hostname or client is None or client != target.get("velociraptor_id"):
            raise ProposalShape("the target is not a host bound to a root-org Velociraptor client")
        if args.get("hostname") != hostname or args.get("velociraptor_id") != target.get("velociraptor_id"):
            raise ProposalShape("the arguments don't name the target host")
        if args.get("action") != QUARANTINE_ACTION[row.action]:
            raise ProposalShape("the arguments ask for the other action")
        if args.get("artifact_name") not in {a.value for a in QuarantineArtifactsEnum}:
            raise ProposalShape("not a quarantine artifact")
        return Plan(
            row.action,
            hostname=hostname,
            velociraptor_id=client,
            quarantine_action=args["action"],
            artifact_name=args["artifact_name"],
        )
    raise ProposalShape("an action CoPilot doesn't run")


# ── D47 ───────────────────────────────────────────────────────────────────────


async def check_d47(user: Any, row: TalonActionRequest, session: AsyncSession) -> None:
    """Raise 403/404 unless ``user`` may decide ``row`` (module docstring)."""
    if not role_may_decide(row.action, user):
        raise HTTPException(status_code=403, detail=NOT_ALLOWED)
    await customer_access_handler.enforce_customer_access(user, row.customer_code, session)
    target = row.target or {}
    if row.action in ALERT_ACTIONS:
        alert_id = _int(target.get("alert_id"))
        if alert_id is None:
            raise HTTPException(status_code=409, detail="this proposal names no alert")
        alert = await incident_routes._ensure_alert_access(alert_id, user, session)
        if getattr(alert, "customer_code", None) != row.customer_code:
            raise HTTPException(status_code=403, detail="the alert is not this proposal's customer's")
    elif row.action in HOST_ACTIONS:
        hostname = target.get("hostname")
        if not isinstance(hostname, str) or not hostname:
            raise HTTPException(status_code=409, detail="this proposal names no host")
        await enforce_hostname_access(user, hostname, session)
    else:
        raise HTTPException(status_code=409, detail="an action CoPilot doesn't run")


async def may_decide(user: Any, row: TalonActionRequest, session: AsyncSession) -> bool:
    """Whether D47 lets ``user`` decide ``row`` (whatever its state). Never raises."""
    try:
        await check_d47(user, row, session)
        return True
    except HTTPException:
        return False


# ── re-checks ─────────────────────────────────────────────────────────────────


class RecheckFailed(Exception):
    """A check just before the run failed: nothing runs (CoPilot's fixed words)."""


async def recheck_assignee(plan: Plan, row: TalonActionRequest, session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.username == plan.assigned_to))
    named = [user for user in result.scalars().all() if user.username == plan.assigned_to]
    if len(named) != 1:
        raise RecheckFailed("the assignee is not one CoPilot user")
    assignee = named[0]
    if assignee.role_id not in {role.value for role in SOC_ROLES}:
        raise RecheckFailed("the assignee is not a SOC user")
    if not await customer_access_handler.check_customer_access(assignee, row.customer_code, session):
        raise RecheckFailed("the assignee has no access to this customer")


#: How long the re-check waits for a host's ``agents`` rows another change holds (MySQL's
#: ``innodb_lock_wait_timeout``, set for the re-check's own statements only): a Talon run fails
#: closed quickly rather than queueing behind it.
LOCK_WAIT_SECONDS = 5


def host_lock_queries(hostname: str, client: str) -> List[Any]:
    """The re-check's ``SELECT … FOR UPDATE`` queries, each one an index lookup (migration
    ``d5b11a2b3c4d``), so only the matching rows and their gaps are locked, never the table:

    1. the host name as the column's collation compares it (the quarantine route's own lookup);
    2. ``lower(hostname)``, which doesn't rely on that collation;
    3. ``lower(substr(velociraptor_id, 1, 18))``: every row whose client id claims the record's
       (``C.`` + 16 hex digits, any case, any org suffix; the exact claim is checked in Python).
    """
    return [
        select(Agents).where(Agents.hostname == hostname).with_for_update(),
        select(Agents).where(func.lower(Agents.hostname) == hostname.lower()).with_for_update(),
        select(Agents).where(func.lower(func.substr(Agents.velociraptor_id, 1, 18)) == client.lower()).with_for_update(),
    ]


async def _lock_host_rows(session: AsyncSession, hostname: str, client: str) -> Tuple[List[Agents], List[Agents]]:
    """Lock and read the host's rows (by name) and the client's claimants, waiting at most
    ``LOCK_WAIT_SECONDS`` on MySQL. The locks stay with ``session``'s transaction."""
    connection = await session.connection()
    mysql = connection.dialect.name == "mysql"
    if mysql:
        await session.execute(text(f"SET SESSION innodb_lock_wait_timeout = {LOCK_WAIT_SECONDS}"))
    try:
        by_name, by_client = {}, {}
        queries = host_lock_queries(hostname, client)
        for n, query in enumerate(queries):
            for agent in (await session.execute(query)).scalars().all():
                (by_client if n == len(queries) - 1 else by_name)[agent.id] = agent
        return list(by_name.values()), list(by_client.values())
    except DBAPIError as e:  # a lock wait timeout, mostly: the rows are someone else's right now
        logger.warning(f"Talon v2 action re-check: the host's agent rows could not be locked: {type(e).__name__}")
        raise RecheckFailed("the host's agent rows are being changed; try again") from None
    finally:
        if mysql:
            try:
                # Back to the server's value before anything else runs on this connection (the
                # route's own statements, then whoever the pool hands it to next).
                await session.execute(text("SET SESSION innodb_lock_wait_timeout = DEFAULT"))
            except Exception as e:  # noqa: BLE001 - never return the connection with our setting
                logger.error(f"Talon v2 action re-check: resetting the lock wait failed ({type(e).__name__}); dropping the connection")
                await connection.invalidate()


async def lock_and_recheck_host(plan: Plan, row: TalonActionRequest, session: AsyncSession) -> None:
    """Lock the host's ``agents`` rows (and every row claiming its client) and check them. The
    locks are held by ``session``'s transaction, so the route run in it sees what was checked."""
    hostname, client = plan.hostname or "", plan.velociraptor_id or ""
    host_rows, client_rows = await _lock_host_rows(session, hostname, client)
    claimants = {agent.id for agent in client_rows if claimed_client_id(agent.velociraptor_id) == client}
    if len(host_rows) != 1 or (host_rows[0].hostname or "").lower() != hostname.lower():
        raise RecheckFailed("the host name is not on exactly one agent")
    agent = host_rows[0]
    if canonical_client_id(agent.velociraptor_id) != client:
        raise RecheckFailed("the host's Velociraptor client changed")
    if agent.customer_code != row.customer_code:
        raise RecheckFailed("the host belongs to another customer")
    if claimants != {agent.id}:
        raise RecheckFailed("another agent carries the host's Velociraptor client")


async def recheck(plan: Plan, row: TalonActionRequest, session: AsyncSession) -> None:
    if plan.action == "assign_alert":
        await recheck_assignee(plan, row, session)
    elif plan.action in HOST_ACTIONS:
        await lock_and_recheck_host(plan, row, session)


# ── the run ───────────────────────────────────────────────────────────────────


def _message(value: object) -> str:
    text = value if isinstance(value, str) else ""
    return text[:MESSAGE_MAX]


async def call_handler(plan: Plan, approver: Any, session: AsyncSession, request: Optional[Request]) -> Any:
    """Call CoPilot's own route handler for ``plan`` as ``approver`` (decision e)."""
    if plan.action == "set_alert_status":
        return await incident_routes.update_alert_status_endpoint(
            alert_status=UpdateAlertStatus(alert_id=plan.alert_id, status=AlertStatus(plan.status)),
            current_user=approver,
            db=session,
        )
    if plan.action == "assign_alert":
        return await incident_routes.update_assigned_to_endpoint(
            assigned_to=AssignedToAlert(alert_id=plan.alert_id, assigned_to=plan.assigned_to),
            current_user=approver,
            db=session,
        )
    if plan.action == "comment_on_alert":
        return await incident_routes.create_comment_endpoint(
            # The route signs the comment with the approver's name, whatever ``user_name`` says.
            comment=CommentCreate(alert_id=plan.alert_id, comment=plan.comment, user_name=getattr(approver, "username", "")),
            current_user=approver,
            db=session,
        )
    if plan.action in HOST_ACTIONS:
        return await velociraptor_routes.quarantine(
            quarantine_body=QuarantineBody(
                hostname=plan.hostname,
                action=ActionEnum(plan.quarantine_action),
                artifact_name=QuarantineArtifactsEnum(plan.artifact_name),
            ),
            request=request,
            current_user=approver,
            session=session,
        )
    raise ProposalShape("an action CoPilot doesn't run")


async def run(plan: Plan, approver: Any, session: AsyncSession, request: Optional[Request]) -> Dict[str, Any]:
    """Run ``plan`` and say what happened as ``{success, message, status_code}``: what CoPilot
    posts to talon-analyst as the result. A handler's refusal keeps its status and CoPilot's own
    text; anything else unexpected is a fixed text (never an exception's)."""
    try:
        response = await call_handler(plan, approver, session, request)
    except HTTPException as e:
        return {"success": False, "message": _message(str(e.detail)) or "the action failed in CoPilot", "status_code": e.status_code}
    except Exception as e:  # noqa: BLE001 - a result to report, not a crash
        logger.error(f"Talon v2 action ({plan.action}) failed in CoPilot: {type(e).__name__}")
        return {"success": False, "message": "the action failed in CoPilot", "status_code": 500}
    success = getattr(response, "success", True)
    message = _message(getattr(response, "message", "")) or "done"
    return {"success": bool(success), "message": message, "status_code": 200 if success else 500}
