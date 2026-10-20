"""Who may decide a Talon v2 action proposal, what is checked again just before it runs, and the
run itself (plan M5-11a steps 2, 5 and 6; talon-analyst SPEC §5.3 M5-11, §9.5, D46, D47).

**D47, in CoPilot** (``check_d47``), before anything is claimed:
- the role, from the user's ``role_id`` (never the token's scopes, so a demoted admin's old token
  doesn't count): admin or responder for an ``endpoint-action`` (quarantine, release, a
  collection, a command); admin, analyst or responder for an ``external-action`` (an alert's
  status, assignee, comment);
- ``enforce_customer_access`` on the record's customer;
- an alert target: ``_ensure_alert_access`` (customer and tags, as the alert routes check), and the
  alert's customer must be the record's;
- a host target: ``enforce_hostname_access``.

**Re-checks** (``recheck``), after talon-analyst granted the claim and just before running; a
failure runs nothing:
- ``assign_alert``: the assignee is exactly one CoPilot user, of a SOC role (decision h), with
  access to the record's customer (CoPilot's own route only checks that the name exists);
- every host action (quarantine, release, a collection, a command), under ``SELECT … FOR UPDATE``
  on ``agents`` (held while the route runs; index lookups only, locking the host's rows plus the
  neighbouring index gaps for the run, so other agents stay writable but for inserts or moves right
  beside the host's keys; a lock wait of at most 5 s, then it fails closed): exactly one row for the
  host name (compared with ``lower()`` *and* the column's collation, which is what the route's own
  lookup uses), whose canonical client id (``C.`` + 16 lowercase hex) is the record's, whose
  customer is the record's, in Velociraptor's root org, and no other row claiming that client id. CoPilot's Velociraptor
  routes resolve the host's client by name; this makes the row they find the proposal's.

**The run** (``run``): CoPilot's existing route handlers, called directly under the approver
(decision e), so their own tenant checks, the SLA lifecycle, the assignment notification,
``agents.quarantined`` and the ``RESPONSE_QUARANTINE`` audit all happen as for a manual action.
Calling a handler skips its ``Security(...)`` scope dependency, which is why D47 checks the role
first. ``tests/test_talon_actions.py`` pins the handlers' signatures.

**Collections and commands** (``collect_artifact``, ``endpoint_command``; talon-analyst EA-3, D74-D79,
D84; plan EA-4). The shape (``plan_for``): the arguments name the record's host and client;
``endpoint_command``'s artifact is a ``CommandArtifactsEnum`` shell and its command at most
``COMMAND_MAX`` characters of plain text; ``collect_artifact``'s is in Talon's collection catalogue
(``talon_catalogue``: only its settable parameters, every pin at its value, never a command, script,
quarantine or remediation artifact), with ``{"env": [{key, value}]}`` parameters. The run is ``/collect``'s or ``/command``'s shared start function
(``start_collection_as`` / ``start_command_as``: the routes' checks, among them the host's artifact
list, the analyst artifact policy, Velociraptor's built-in definitions in the host's org for a
collection, and the parameter names, and their audit event, once), which
starts the flow and doesn't wait (D84 a), and uploads nothing to MinIO (D84 b). The command and the
parameter values reach Velociraptor as written (``literal_values``): the manual routes' VQL
unescaping would run ``C:\\Users`` as ``C:Users``, which is not what the approver read. The result
adds the flow id, the client id and the artifact; only the flow id is read by talon-analyst's
resume, and only in its ``F.`` form. ``TALON_ACTION_EXECUTE``'s audit keeps a command's SHA-256 and length,
never its text (D84 f, ``audited_args``); the mirror keeps it verbatim for the card.
"""
import hashlib
import re
import unicodedata
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
from app.connectors.talon.services.talon_action_sync import FLOW_ACTIONS
from app.connectors.talon.services.talon_action_sync import HOST_ACTIONS
from app.connectors.talon.services.talon_action_sync import QUARANTINE_ACTIONS
from app.connectors.talon.services.talon_service_account import (
    refuse_talon_service_account,
)
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes
from app.connectors.velociraptor.schema.artifacts import ActionEnum
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import CommandArtifactsEnum
from app.connectors.velociraptor.schema.artifacts import ParameterKeyValue
from app.connectors.velociraptor.schema.artifacts import QuarantineArtifactsEnum
from app.connectors.velociraptor.schema.artifacts import QuarantineBody
from app.connectors.velociraptor.schema.artifacts import RunCommandBody
from app.connectors.velociraptor.services.talon_catalogue import catalogue_violation
from app.connectors.velociraptor.utils.validation import validate_artifact_name
from app.connectors.velociraptor.utils.validation import (
    validate_artifact_parameter_name,
)
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

#: talon-analyst's limits on a collection's and a command's arguments (``talon.endpoint_catalogue``,
#: ``TALON_ENDPOINT_COMMAND_MAX_CHARS``; D79): a command of at most 2,000 characters, a parameter
#: value of at most 512, and at most 10 parameters plus the switches its catalogue pins off.
COMMAND_MAX = 2000
PARAMETER_VALUE_MAX = 512
PARAMETERS_MAX = 16
#: The shells talon-analyst offers (D75): PowerShell and bash; never cmd.
COMMAND_ARTIFACTS = frozenset({CommandArtifactsEnum.windows_powershell.value, CommandArtifactsEnum.linux_bash.value})
#: Characters a command or a parameter value may not hold (talon-analyst's ``plain_text_ok``): format
#: (bidi controls, zero-width), control but newline and tab, surrogate, line and paragraph separators.
_NOT_PLAIN = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
_PLAIN_CONTROLS = frozenset("\n\t")
#: The argument keys each flow action takes, exactly (talon-analyst ``talon.tools.artifacts``).
FLOW_ARGS = {
    "collect_artifact": frozenset({"hostname", "velociraptor_id", "artifact_name", "parameters"}),
    "endpoint_command": frozenset({"hostname", "velociraptor_id", "artifact_name", "command"}),
}
#: A collection's flow id as talon-analyst's resume accepts it (``talon.actions.FLOW_ID``): never a
#: hunt's ``.H``, at most 64 characters after ``F.``.
TALON_FLOW_ID = re.compile(r"F\.[A-Za-z0-9]{1,64}")
STARTED = "Velociraptor flow started"
NO_FLOW_ID = "Velociraptor gave no usable flow id"
START_FAILED = "CoPilot could not start the collection"
OTHER_CLIENT = "the flow started on another Velociraptor client than the proposal's"


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
    #: ``collect_artifact``: the artifact's parameters as ``(key, value)`` pairs, in order.
    parameters: Tuple[Tuple[str, str], ...] = ()
    #: ``endpoint_command``: the command, verbatim.
    command: Optional[str] = None


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
        if row.action in FLOW_ACTIONS:
            return _flow_plan(row.action, args, hostname, client)
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


def _flow_plan(action: str, args: Dict[str, Any], hostname: str, client: str) -> Plan:
    """A collection's or a command's plan; the host is already checked against the target."""
    if set(args) != FLOW_ARGS[action]:
        raise ProposalShape("the arguments are not this action's")
    artifact = args.get("artifact_name")
    if action == "endpoint_command":
        if artifact not in COMMAND_ARTIFACTS:
            raise ProposalShape("not a command artifact")
        command = args.get("command")
        if not isinstance(command, str) or not 1 <= len(command) <= COMMAND_MAX:
            raise ProposalShape(f"not a command of at most {COMMAND_MAX} characters")
        if not plain_text_ok(command):
            raise ProposalShape("the command holds control or invisible characters")
        return Plan(action, hostname=hostname, velociraptor_id=client, artifact_name=artifact, command=command)
    if not _artifact_name_ok(artifact):
        raise ProposalShape("not an artifact CoPilot collects for Talon")
    parameters = _parameters(args.get("parameters"))
    refused = catalogue_violation(artifact, parameters)
    if refused is not None:
        raise ProposalShape(refused)
    return Plan(action, hostname=hostname, velociraptor_id=client, artifact_name=artifact, parameters=parameters)


def plain_text_ok(text: str) -> bool:
    """Whether ``text`` reads as it runs (talon-analyst's ``plain_text_ok``)."""
    return not any(c not in _PLAIN_CONTROLS and unicodedata.category(c) in _NOT_PLAIN for c in text)


def _artifact_name_ok(value: object) -> bool:
    try:
        validate_artifact_name(value)
    except HTTPException:
        return False
    return True


def _parameters(value: object) -> Tuple[Tuple[str, str], ...]:
    """``{"env": [{"key", "value"}, ...]}`` (talon-analyst always sends ``env``) as pairs: each key a
    parameter name CoPilot can pass (``validate_artifact_parameter_name``) and given once, each
    value a string. The names are checked against the artifact's by the route's own check."""
    if not isinstance(value, dict) or set(value) != {"env"} or not isinstance(value["env"], list):
        raise ProposalShape("the parameters are not an env list")
    pairs, seen = [], set()
    if len(value["env"]) > PARAMETERS_MAX:
        raise ProposalShape("too many parameters")
    for item in value["env"]:
        if not isinstance(item, dict) or set(item) != {"key", "value"}:
            raise ProposalShape("a parameter is not a key and a value")
        key, text = item["key"], item["value"]
        if not isinstance(key, str) or not isinstance(text, str) or len(text) > PARAMETER_VALUE_MAX:
            raise ProposalShape("a parameter is not a short string")
        if not plain_text_ok(text):
            raise ProposalShape("a parameter holds control or invisible characters")
        try:
            validate_artifact_parameter_name(key)
        except HTTPException:
            raise ProposalShape("not a parameter name") from None
        if key in seen:
            raise ProposalShape("a parameter is given twice")
        seen.add(key)
        pairs.append((key, text))
    return tuple(pairs)


def audited_args(action: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """A record's arguments as ``TALON_ACTION_EXECUTE``'s audit keeps them: a command replaced by
    its SHA-256 (of its UTF-8) and its length in characters, as ``/command``'s own audit keeps no
    command (talon-analyst D84 f). The mirror keeps it verbatim."""
    if action != "endpoint_command" or "command" not in args:
        return dict(args)
    command = args["command"]
    text = command if isinstance(command, str) else repr(command)
    out = {key: value for key, value in args.items() if key != "command"}
    out["command_sha256"] = hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()
    out["command_length"] = len(text)
    return out


# ── D47 ───────────────────────────────────────────────────────────────────────


async def check_d47(user: Any, row: TalonActionRequest, session: AsyncSession) -> None:
    """Raise 403/404 unless ``user`` may decide ``row`` (module docstring). The Talon service account
    never decides one, whatever its role (``talon_service_account``)."""
    if not role_may_decide(row.action, user):
        raise HTTPException(status_code=403, detail=NOT_ALLOWED)
    await refuse_talon_service_account(user, session)
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
    ``d5b11a2b3c4d``), so what is locked is the matching rows plus the neighbouring index gaps
    (REPEATABLE READ's next-key locks: an insert of another agent with the host's name, which would
    change the route's ``.first()``, waits), never the whole table:

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


def _is_mysql(connection: Any) -> bool:
    return connection.dialect.name == "mysql"


async def _set_lock_wait(session: AsyncSession, value: str) -> None:
    await session.execute(text(f"SET SESSION innodb_lock_wait_timeout = {value}"))


async def _drop_connection(connection: Any) -> None:
    await connection.invalidate()


async def _lock_host_rows(session: AsyncSession, hostname: str, client: str) -> Tuple[List[Agents], List[Agents]]:
    """Lock and read the host's rows (by name) and the client's claimants, waiting at most
    ``LOCK_WAIT_SECONDS`` on MySQL. The locks stay with ``session``'s transaction.

    If the lock wait can't be put back, the connection is dropped (it must never reach the pool
    with our setting), which also drops the locks: then the checks count as not made, and nothing
    runs."""
    connection = await session.connection()
    mysql = _is_mysql(connection)
    if mysql:
        await _set_lock_wait(session, str(LOCK_WAIT_SECONDS))
    done = False
    try:
        by_name, by_client = {}, {}
        queries = host_lock_queries(hostname, client)
        for n, query in enumerate(queries):
            for agent in (await session.execute(query)).scalars().all():
                (by_client if n == len(queries) - 1 else by_name)[agent.id] = agent
        done = True
        return list(by_name.values()), list(by_client.values())
    except DBAPIError as e:  # a lock wait timeout, mostly: the rows are someone else's right now
        logger.warning(f"Talon v2 action re-check: the host's agent rows could not be locked: {type(e).__name__}")
        raise RecheckFailed("the host's agent rows are being changed; try again") from None
    finally:
        if mysql:
            try:
                # Back to the server's value before anything else runs on this connection (the
                # route's own statements, then whoever the pool hands it to next).
                await _set_lock_wait(session, "DEFAULT")
            except Exception as e:  # noqa: BLE001 - never return the connection with our setting
                logger.error(f"Talon v2 action re-check: resetting the lock wait failed ({type(e).__name__}); dropping the connection")
                await _drop_connection(connection)
                if done:  # the locks went with the connection: the checks no longer hold
                    raise RecheckFailed("the checks before the run could not be made") from None


async def lock_and_recheck_host(plan: Plan, row: TalonActionRequest, session: AsyncSession) -> None:
    """Lock the host's ``agents`` rows (and every row claiming its client) and check them. The
    locks are held by ``session``'s transaction, so the route run in it sees what was checked."""
    await lock_and_check_host(session, plan.hostname or "", plan.velociraptor_id or "", row.customer_code)


async def lock_and_check_host(session: AsyncSession, hostname: str, client: str, customer_code: Optional[str] = None) -> Agents:
    """``lock_and_recheck_host``'s check, for a host and a canonical root-org client id: exactly one
    ``agents`` row for the host name, carrying that client, in the root org, no other row claiming
    the client, and (when given) of ``customer_code``. The row, locked by ``session``'s transaction;
    ``RecheckFailed`` otherwise. Also the collection start route's check (talon-analyst EA-4b), where
    the caller's access to the row's customer is checked by the route itself."""
    host_rows, client_rows = await _lock_host_rows(session, hostname, client)
    claimants = {agent.id for agent in client_rows if claimed_client_id(agent.velociraptor_id) == client}
    if len(host_rows) != 1 or (host_rows[0].hostname or "").lower() != hostname.lower():
        raise RecheckFailed("the host name is not on exactly one agent")
    agent = host_rows[0]
    if canonical_client_id(agent.velociraptor_id) != client:
        raise RecheckFailed("the host's Velociraptor client changed")
    if customer_code is not None and agent.customer_code != customer_code:
        raise RecheckFailed("the host belongs to another customer")
    if agent.velociraptor_org != "root":
        raise RecheckFailed("the host is not in Velociraptor's root org")
    if claimants != {agent.id}:
        raise RecheckFailed("another agent carries the host's Velociraptor client")
    return agent


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
    if plan.action == "collect_artifact":
        body = CollectArtifactBody(
            hostname=plan.hostname,
            artifact_name=plan.artifact_name,
            parameters={"env": [ParameterKeyValue(key=key, value=value) for key, value in plan.parameters]} if plan.parameters else None,
        )
        return await velociraptor_routes.start_collection_as(approver, body, request, session, literal_values=True, require_built_in=True)
    if plan.action == "endpoint_command":
        body = RunCommandBody(hostname=plan.hostname, command=plan.command, artifact_name=CommandArtifactsEnum(plan.artifact_name))
        return await velociraptor_routes.start_command_as(approver, body, request, session, literal_values=True)
    if plan.action in QUARANTINE_ACTIONS:
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
    text; anything else unexpected is a fixed text (never an exception's). A started collection or
    command adds ``flow_id``, ``client_id`` and ``artifact``; a server error starting one is a fixed
    text too, since the start's own text names the whole request (a command included)."""
    try:
        response = await call_handler(plan, approver, session, request)
    except HTTPException as e:
        message = _message(str(e.detail)) or "the action failed in CoPilot"
        if plan.action in FLOW_ACTIONS and e.status_code >= 500:
            message = START_FAILED
        return {"success": False, "message": message, "status_code": e.status_code}
    except Exception as e:  # noqa: BLE001 - a result to report, not a crash
        logger.error(f"Talon v2 action ({plan.action}) failed in CoPilot: {type(e).__name__}")
        return {"success": False, "message": "the action failed in CoPilot", "status_code": 500}
    if plan.action in FLOW_ACTIONS:
        return started_result(response, plan)
    success = getattr(response, "success", True)
    message = _message(getattr(response, "message", "")) or "done"
    return {"success": bool(success), "message": message, "status_code": 200 if success else 500}


def started_result(started: Any, plan: Plan) -> Dict[str, Any]:
    """A started flow as the result talon-analyst records: its flow id only in the form its resume
    reads (``TALON_FLOW_ID``), on the plan's client, else ``failed`` (it may have started; the
    message says so)."""
    flow_id = getattr(started, "flow_id", None)
    if not isinstance(flow_id, str) or not TALON_FLOW_ID.fullmatch(flow_id):
        logger.error("Talon v2 action: Velociraptor started a flow but gave no usable flow id")
        return {"success": False, "message": NO_FLOW_ID, "status_code": 500}
    if canonical_client_id(getattr(started, "client_id", None)) != plan.velociraptor_id:
        logger.error("Talon v2 action: the flow started on another client than the proposal's")
        return {"success": False, "message": OTHER_CLIENT, "status_code": 500}
    return {
        "success": True,
        "message": STARTED,
        "status_code": 200,
        "flow_id": flow_id,
        "client_id": plan.velociraptor_id,
        "artifact": getattr(started, "artifact", None),
    }
