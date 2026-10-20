"""The collection start route for investigations, and its second gate for talon-analyst's service
account (talon-analyst plan EA-4b; SPEC D77, INV-ACT-1's stated exception).

An investigation collects an **auto-run** artifact (process, network, service, scheduled-task and
startup state) on the alert's own host without an approval, as talon-analyst's CoPilot service user
(analyst role, assigned only to the live customers). ``/collect`` can't serve it: it waits up to
``VELOCIRAPTOR_FLOW_TIMEOUT``, uploads the flow to MinIO and answers rows without the flow id.
``POST /api/artifacts/collect/start`` (``start``) starts the flow and answers its id, never rows.

**In order** (a refusal starts nothing):
1. the shape: a root-org client id (``C.`` and 16 hex digits), parameters as an ``env`` list of
   short plain-text values, each name once (400);
2. ``enforce_hostname_access`` on the host (403/404);
3. the artifact. **The Talon service account** (``talon_service_account.is_service_account``: the
   user id recorded with the setting, the user named by ``collect_service_username``, and
   ``talon-analyst``, whatever its role; every other route that starts endpoint work refuses it)
   must name an artifact on the admin's allowlist (``collect_allowed_artifacts``) with exactly its
   pins and nothing else (``talon_catalogue.auto_run_violation``), else 403; **with the allowlist
   unset it starts nothing** (403); and the artifact's and its dependencies' definitions must have
   the SHA-256s saved with the allowlist (``collect_definition_hashes``), else 403 until an admin
   reviews the change and saves again. Everyone else: no command, script, quarantine or remediation
   artifact (403), then ``/collect``'s own analyst policy as usual;
4. in a fresh transaction, the host's ``agents`` rows locked and checked as for an approved Talon
   action (``talon_action_execution.lock_and_check_host``): exactly one row with the host name,
   carrying the body's client id, in the root org, no other row claiming that client (409);
5. ``/collect``'s shared start function (``routes.artifacts.start_collection_as``), under the locks:
   the caller's access to every row of the host, the host's artifact list (400), the analyst policy
   (for the service account: the auto-run allowlist instead, plus
   ``collection_policy.enforce_auto_run_definitions``: built-in definitions, no tools, imports or
   elevated permissions, for the artifact and its dependencies), the parameter names, the ``ARTIFACT_COLLECT`` audit event once
   with the caller as the actor, and EA-1's parameterized start with the resource limits
   (``collect_start_limits``) as ``collect_client`` arguments. No wait, no MinIO upload, no rows.

The answer is ``{success, message, flow_id, client_id, artifact}``; ``flow_id`` only in
talon-analyst's ``F.[A-Za-z0-9]{1,64}`` form. Every refusal is a fixed text with its status (never
the host, the artifact or a value back), and a server error starting the flow is "CoPilot could not
start the collection". Only validated values are logged; never a parameter value.

**The setting** is an admin's (by ``role_id``), on the Talon connector's ``talon_connector_settings``
row beside the "Talon v2" switch: ``GET``/``PUT /api/talon/v2/settings/collections``, audited
``connector.update``. The route itself is behind "Talon v2" (D54): 404 while it is off.
"""
from typing import Any
from typing import Dict
from typing import FrozenSet
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings
from app.connectors.talon.schema.talon_collections import CollectStartBody
from app.connectors.talon.schema.talon_collections import CollectStartResponse
from app.connectors.talon.schema.talon_collections import (
    TalonCollectionSettingsResponse,
)
from app.connectors.talon.services import talon_action_execution as execution
from app.connectors.talon.services.talon_service_account import DEFAULT_SERVICE_USERNAME
from app.connectors.talon.services.talon_service_account import effective_username
from app.connectors.talon.services.talon_service_account import is_service_account
from app.connectors.talon.services.talon_service_account import settings_row
from app.connectors.talon.services.talon_service_account import user_id_for
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.velociraptor.routes import artifacts as velociraptor_routes
from app.connectors.velociraptor.schema.artifacts import CollectArtifactBody
from app.connectors.velociraptor.schema.artifacts import ParameterKeyValue
from app.connectors.velociraptor.services.artifacts import FlowLimits
from app.connectors.velociraptor.services.collection_policy import auto_run_definitions
from app.connectors.velociraptor.services.collection_policy import built_in_violation
from app.connectors.velociraptor.services.collection_policy import definition_hashes
from app.connectors.velociraptor.services.collection_policy import response_artifacts
from app.connectors.velociraptor.services.collection_policy import structure_violation
from app.connectors.velociraptor.services.talon_catalogue import TALON_AUTO_RUN
from app.connectors.velociraptor.services.talon_catalogue import auto_run_violation
from app.connectors.velociraptor.services.talon_catalogue import is_response_artifact
from app.connectors.velociraptor.utils.universal import _positive_int_from_env
from app.connectors.velociraptor.utils.validation import validate_artifact_name
from app.connectors.velociraptor.utils.validation import validate_hostname
from app.middleware.customer_access import enforce_hostname_access
from app.time_utils import now_utc

#: The resource limits' settings (environment), their defaults and their ceilings. The timeout is
#: at most 300 s: talon-analyst's one-collection-per-host lock assumes a flow ends by then.
LIMIT_SETTINGS = {
    "timeout": ("VELOCIRAPTOR_COLLECT_START_TIMEOUT", 300, 300),
    "cpu_limit": ("VELOCIRAPTOR_COLLECT_START_CPU_LIMIT", 25, 100),
    "max_rows": ("VELOCIRAPTOR_COLLECT_START_MAX_ROWS", 10000, None),
    "max_bytes": ("VELOCIRAPTOR_COLLECT_START_MAX_BYTES", 1048576, None),
}

STARTED = "Velociraptor flow started"
NO_FLOW_ID = "Velociraptor gave no usable flow id"
OTHER_CLIENT = "the flow started on another Velociraptor client than the request's"
START_FAILED = "CoPilot could not start the collection"
NOT_CLIENT = "velociraptor_id must be the host's root-org Velociraptor client id (C. and 16 hex digits)"
UNSET = "the Talon service account has no collection allowlist in CoPilot (Talon v2 settings, collections)"
RESPONSE_ARTIFACT = "command, script, quarantine and remediation artifacts can't be started here"
ADMIN_ONLY = "Only an admin may read or change the Talon collection setting"
#: This route's refusals are fixed texts: never the host, the artifact or a value back.
BAD_REQUEST = "not started: the request is not one CoPilot can start (host, artifact or parameters)"
NOT_APPLICABLE = "not started: the artifact or its parameters don't apply to this host"
NO_ACCESS = "not started: no access to this host"
NOT_FOUND = "not started: the host or its Velociraptor client was not found"
SERVICE_REFUSED = "The Talon service account may not start this collection"
POLICY_REFUSED = "not started: this artifact can't be collected by this user"
DEFINITION_CHANGED = (
    "The Talon service account may not start this collection: its Velociraptor definition changed since the setting was saved; "
    "an admin must review it and save the Talon collection setting again"
)
DEFINITIONS_UNREADABLE = "Velociraptor's artifact definitions could not be read, so the Talon collection setting was not saved"
DEFINITION_REFUSED = "allowed_artifacts names an artifact whose definition in Velociraptor's root org can't be pinned (not found, not built in, or not read-only)"
#: The org the service account collects in: ``lock_and_check_host`` refuses any other.
ROOT_ORG = "root"
FIXED_BY_STATUS = {400: NOT_APPLICABLE, 403: POLICY_REFUSED, 404: NOT_FOUND}


def collect_start_limits() -> FlowLimits:
    """The flow's resource limits, from the environment (``LIMIT_SETTINGS``): a positive integer
    each, else the default; above a ceiling, the ceiling."""
    values = {}
    for field, (name, default, ceiling) in LIMIT_SETTINGS.items():
        value = _positive_int_from_env(name, default)
        if ceiling is not None and value > ceiling:
            logger.warning(f"{name}={value} is above {ceiling}; using {ceiling}")
            value = ceiling
        values[field] = value
    return FlowLimits(**values)


# ── who the gate holds (``talon_service_account``) ────────────────────────────


def allowed_artifacts(row: Optional[TalonConnectorSettings]) -> Optional[FrozenSet[str]]:
    """The service account's allowlist, auto-run names only; None when unset (it starts nothing)."""
    if row is None or row.collect_allowed_artifacts is None:
        return None
    return frozenset(name for name in row.collect_allowed_artifacts if isinstance(name, str) and name in TALON_AUTO_RUN)


# ── the start ─────────────────────────────────────────────────────────────────


def _parameters(value: Optional[Dict[str, Any]]) -> Tuple[Tuple[str, str], ...]:
    """The body's parameters as ``(key, value)`` pairs (an approved collection's rules: an ``env``
    list, each name once, each value a short plain string); a fixed 400 otherwise."""
    if value is None:
        return ()
    try:
        return execution._parameters(value)
    except execution.ProposalShape:
        raise HTTPException(status_code=400, detail=BAD_REQUEST) from None


def _fixed(e: HTTPException, default: str) -> HTTPException:
    """A refusal from CoPilot's own checks, with its status and a fixed text (theirs name the host,
    the artifact or a parameter)."""
    if e.status_code >= 500:
        return HTTPException(status_code=e.status_code, detail=START_FAILED)
    return HTTPException(status_code=e.status_code, detail=FIXED_BY_STATUS.get(e.status_code, default))


async def current_hashes(artifact: str, fresh: bool = False) -> Dict[str, str]:
    """The SHA-256s of the artifact's and its dependencies' definitions in the root org (cached a
    minute, ``collection_policy.auto_run_definitions``)."""
    return definition_hashes(await auto_run_definitions(artifact, ROOT_ORG, fresh=fresh))


async def check_definition_pin(row: Optional[TalonConnectorSettings], artifact: str) -> None:
    """403 unless the artifact's definitions are exactly the ones an admin saved the setting with."""
    stored = ((row.collect_definition_hashes if row is not None else None) or {}).get(artifact)
    try:
        current = await current_hashes(artifact)
    except HTTPException as e:
        logger.error(f"Collection start: the definitions of {artifact} could not be read (HTTP {e.status_code})")
        raise HTTPException(status_code=e.status_code if e.status_code >= 500 else 502, detail=START_FAILED) from None
    if not stored or current != stored:
        logger.warning(f"Refused a collection start of {artifact} by the Talon service account: its definitions differ from the saved pin")
        raise HTTPException(status_code=403, detail=DEFINITION_CHANGED)


async def pin_definitions(artifacts: Optional[List[str]]) -> Optional[Dict[str, Dict[str, str]]]:
    """Read each allowed artifact's definitions afresh and return their hashes; refuse to save one
    the start route would refuse (``enforce_auto_run_definitions``) or that can't be read."""
    if artifacts is None:
        return None
    pins = {}
    for artifact in artifacts:
        try:
            definitions = await auto_run_definitions(artifact, ROOT_ORG, fresh=True)
        except HTTPException as e:
            logger.error(f"Talon collection setting: the definitions of {artifact} could not be read (HTTP {e.status_code})")
            raise HTTPException(status_code=502, detail=DEFINITIONS_UNREADABLE) from None
        reason = built_in_violation(artifact, definitions) or next(filter(None, (structure_violation(d) for d in definitions)), None)
        if reason is not None:
            logger.warning(f"Talon collection setting: {artifact} can't be pinned: {reason}")
            raise HTTPException(status_code=400, detail=DEFINITION_REFUSED)
        pins[artifact] = definition_hashes(definitions)
    return pins


async def start(user: User, body: CollectStartBody, request: Optional[Request], session: AsyncSession) -> CollectStartResponse:
    """Start one collection and answer its flow id (module docstring)."""
    parameters = _parameters(body.parameters)
    client = execution.canonical_client_id(body.velociraptor_id)
    try:
        hostname, artifact = validate_hostname(body.hostname), validate_artifact_name(body.artifact_name)
    except HTTPException:
        raise HTTPException(status_code=400, detail=BAD_REQUEST) from None
    if client is None:
        raise HTTPException(status_code=400, detail=NOT_CLIENT)

    try:
        await enforce_hostname_access(user, hostname, session)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=NO_ACCESS if e.status_code == 403 else NOT_FOUND) from None
    row = await settings_row(session)
    service = is_service_account(user, row)
    if service:
        allowed = allowed_artifacts(row)
        if allowed is None:
            logger.warning(f"Refused a collection start by the Talon service account {user.username}: no allowlist is set")
            raise HTTPException(status_code=403, detail=UNSET)
        refused = auto_run_violation(artifact, parameters, allowed)
        if refused is not None:
            # The artifact name is validated (``validate_artifact_name``); a value never reaches here.
            logger.warning(f"Refused a collection start of {artifact} by the Talon service account {user.username}: {refused}")
            raise HTTPException(status_code=403, detail=SERVICE_REFUSED)
        await check_definition_pin(row, artifact)
    elif is_response_artifact(artifact) or artifact in response_artifacts():
        raise HTTPException(status_code=403, detail=RESPONSE_ARTIFACT)

    # A fresh transaction, so the host's locks are taken before anything else is read in it (the
    # start function's own reads then see the rows as they were locked).
    await session.rollback()
    try:
        try:
            await execution.lock_and_check_host(session, hostname, client)
        except execution.RecheckFailed as e:
            raise HTTPException(status_code=409, detail=f"not started: {e}") from None
        # Every value logged here is validated: the host is the agents row's, the client canonical,
        # the artifact a name. Never the parameters: their names are logged by the parameter check,
        # their values nowhere.
        logger.info(f"Collection start: {artifact} on {hostname} ({client}) for user {getattr(user, 'username', '?')}")
        collect_body = CollectArtifactBody(
            hostname=hostname,
            artifact_name=artifact,
            parameters={"env": [ParameterKeyValue(key=key, value=value) for key, value in parameters]} if parameters else None,
        )
        try:
            started = await velociraptor_routes.start_collection_as(
                user,
                collect_body,
                request,
                session,
                # The service account's values are its pins, sent as written (as for an approved
                # Talon collection); other callers keep /collect's VQL unescaping.
                literal_values=service,
                require_built_in=service,
                analyst_policy=not service,
                limits=collect_start_limits(),
            )
        except HTTPException as e:
            if e.status_code >= 500:
                logger.error(f"Collection start of {artifact} on {client} failed in CoPilot (HTTP {e.status_code})")
            raise _fixed(e, POLICY_REFUSED) from None
    finally:
        await session.rollback()  # releases the host's locks
    return started_response(started, client)


def started_response(started: Any, client: str) -> CollectStartResponse:
    """The answer for a started flow, its id in talon-analyst's form on the request's client; a 502
    otherwise (the flow may have started: the message says so)."""
    flow_id = getattr(started, "flow_id", None)
    if not isinstance(flow_id, str) or not execution.TALON_FLOW_ID.fullmatch(flow_id):
        logger.error("Collection start: Velociraptor started a flow but gave no usable flow id")
        raise HTTPException(status_code=502, detail=NO_FLOW_ID)
    if execution.canonical_client_id(getattr(started, "client_id", None)) != client:
        logger.error("Collection start: the flow started on another client than the request's")
        raise HTTPException(status_code=502, detail=OTHER_CLIENT)
    return CollectStartResponse(success=True, message=STARTED, flow_id=flow_id, client_id=client, artifact=started.artifact)


# ── the setting ───────────────────────────────────────────────────────────────


def require_admin(user: User) -> None:
    """By the user's role in the database, not only the token's scope (as the Talon v2 setting)."""
    if getattr(user, "role_id", None) != RoleEnum.admin:
        raise HTTPException(status_code=403, detail=ADMIN_ONLY)


def _settings_response(
    row: Optional[TalonConnectorSettings],
    message: str,
    exists: bool,
    user_id: Optional[int],
) -> TalonCollectionSettingsResponse:
    configured = row.collect_service_username if row is not None else None
    listed = allowed_artifacts(row)
    return TalonCollectionSettingsResponse(
        success=True,
        message=message,
        connector_name=TALON_CONNECTOR,
        service_username=effective_username(row),
        service_username_configured=configured,
        service_user_exists=exists,
        service_user_id=user_id,
        recorded_service_user_id=row.collect_service_user_id if row is not None else None,
        allowed_artifacts=sorted(listed) if listed is not None else None,
        auto_run_catalogue={name: dict(entry.pinned) for name, entry in TALON_AUTO_RUN.items()},
        updated_by_user_id=row.updated_by_user_id if row is not None else None,
        updated_at=row.updated_at if row is not None else None,
    )


async def _describe(session: AsyncSession, row: Optional[TalonConnectorSettings], message: str) -> TalonCollectionSettingsResponse:
    user_id = await user_id_for(session, effective_username(row))
    response = _settings_response(row, message, user_id is not None, user_id)
    stored = (row.collect_definition_hashes if row is not None else None) or {}
    response.definition_hashes = stored
    matches: Dict[str, Optional[bool]] = {}
    for artifact in response.allowed_artifacts or []:
        try:
            matches[artifact] = bool(stored.get(artifact)) and await current_hashes(artifact) == stored.get(artifact)
        except HTTPException:
            matches[artifact] = None  # Velociraptor couldn't be read
    response.definitions_match = matches
    return response


async def get_settings(user: User, session: AsyncSession) -> TalonCollectionSettingsResponse:
    require_admin(user)
    return await _describe(session, await settings_row(session), "Talon collection setting retrieved")


def _clean_username(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not value or value != value.strip() or any(not ch.isprintable() for ch in value):
        raise HTTPException(status_code=400, detail="service_username must be a user name without spaces at its ends or control characters")
    return value


def _clean_artifacts(value: Optional[List[str]]) -> Optional[List[str]]:
    if value is None:
        return None
    unknown = [name for name in value if name not in TALON_AUTO_RUN]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"allowed_artifacts may only name auto-run artifacts ({', '.join(sorted(TALON_AUTO_RUN))})",
        )
    return sorted(set(value))


async def update_settings(
    user: User,
    session: AsyncSession,
    service_username: Optional[str],
    artifacts: Optional[List[str]],
    request: Optional[Request] = None,
) -> TalonCollectionSettingsResponse:
    """Set the service account's name and allowlist (admin only), audited with the old and new values."""
    require_admin(user)
    username, listed = _clean_username(service_username), _clean_artifacts(artifacts)
    row = await settings_row(session)
    old = {
        "collect_service_username": row.collect_service_username if row is not None else None,
        "collect_service_user_id": row.collect_service_user_id if row is not None else None,
        "collect_allowed_artifacts": row.collect_allowed_artifacts if row is not None else None,
    }
    # The id of the one user with the name, recorded so a rename keeps it in the gate.
    service_user_id = await user_id_for(session, username or DEFAULT_SERVICE_USERNAME)
    # The definitions as Velociraptor has them now: what the admin is approving.
    pins = await pin_definitions(listed)
    old["collect_definition_hashes"] = row.collect_definition_hashes if row is not None else None
    new = {
        "collect_service_username": username,
        "collect_service_user_id": service_user_id,
        "collect_allowed_artifacts": listed,
        "collect_definition_hashes": pins,
    }
    row = await _store(session, username, service_user_id, listed, pins, user.id)
    await record_audit_event(
        action=AuditAction.CONNECTOR_UPDATE,
        actor_user_id=user.id,
        actor_username=user.username,
        entity_type="connector",
        entity_id=TALON_CONNECTOR,
        old_value=old,
        new_value=new,
        request=request,
        details=f"Talon collection setting changed for connector '{TALON_CONNECTOR}'",
    )
    return await _describe(session, row, "Talon collection setting saved")


async def _store(
    session: AsyncSession,
    username: Optional[str],
    service_user_id: Optional[int],
    artifacts: Optional[List[str]],
    pins: Optional[Dict[str, Dict[str, str]]],
    user_id: int,
) -> TalonConnectorSettings:
    """Upsert the row (a new row leaves "Talon v2" off). Two admins creating it at once: the loser
    updates the winner's row."""
    for attempt in range(2):
        row = await settings_row(session)
        if row is None:
            row = TalonConnectorSettings(connector_name=TALON_CONNECTOR)
            session.add(row)
        row.collect_service_username = username
        row.collect_service_user_id = service_user_id
        row.collect_allowed_artifacts = artifacts
        row.collect_definition_hashes = pins
        row.updated_by_user_id = user_id
        row.updated_at = now_utc()
        try:
            await session.commit()
            return row
        except IntegrityError:
            await session.rollback()
            if attempt:
                raise
    raise AssertionError("unreachable")
