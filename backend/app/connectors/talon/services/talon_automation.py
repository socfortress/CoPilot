"""The per-customer automation policy, the global automation switch, and the record and caps of the
Talon service account's automated starts (talon-analyst plan AP-2; SPEC D85, D86, INV-ACT-1).

**The policy** (``talon_automation_policy``, one row per customer) says, level by level, what
talon-analyst's automatic investigations may run on the customer's endpoints: ``off``, ``shadow``
("would-have-run": a dry run, nothing runs), ``propose`` (an analyst's approval, AP-5) or ``auto``.
**No row means every level off.** One admin sets it (``GET``/``PUT
/api/talon/v2/automation/{customer_code}``: admin by token scope and database role; the Talon
service account refused, whatever its role, so a compromised talon-analyst can't edit its own
policy). Any mode may be set directly (no shadow gate, Q2/Q6). Raising level 3 or 4 needs
``acknowledge_risk: true``, recorded with the admin (Q7: one admin). No level can be raised for a
customer the Talon service user isn't assigned to. Every change is audited
``talon_automation.policy_update`` with the old and new values.

**The switch** (``talon_connector_settings.automation_enabled``, ``GET``/``PUT
/api/talon/v2/settings/automation``, admin only, audited the same way): off, every automated start
and dry run is refused, whatever the rows say. Off by default.

**What CoPilot checks** on the service account's start (``talon_collections.start``) and dry run
(``talon_collections.dry_run``), after AP-2a's ``ALERT_REQUIRED``: the switch, the customer's row,
the level CoPilot classifies itself (``classify``: an auto-run artifact is level 1, another catalogue
artifact level 2, anything else no level) and its mode (``auto`` to start; ``shadow`` or ``auto``
for a dry run), the level's own checks (level 1: EA-4b's allowlist and definition pins; levels 2-4
aren't startable yet), the host lock, AP-2a's trigger record, then the caps (``reserve_start``):

- **per alert**: AP-2a's ``talon_automation_alert_cap`` slot (2 per 2-hour window, every job
  together), its guarded ``UPDATE``;
- **per host**: 6 automated starts per hour, every level together, counted by client id;
- **per customer**: 10 collections per hour, levels 1-2 together.

All of it in **one transaction** under the customer's policy row locked ``FOR UPDATE`` (so the
customer's starts are serialized and the counts can't race), which re-reads the switch and the row
(CoPilot enforces its *current* policy, D86 e), takes the alert's slot, counts
``talon_automation_start``, writes the start's row (``reserved``) and its
``talon_automation.start`` audit row, and commits **before the flow starts**. No committed record,
no start (500 ``CAP_UNRECORDED``). A refusal there rolls everything back, the alert's slot included.
After the start the row gets its flow id (``finish_start``). Over a cap is a fixed 429.

A dry run counts its own ``shadow`` rows instead (so the would-have-run list shows what ``auto``
would have done, "capped" included) and never counts against the ``auto`` caps.
"""
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditLog
from app.audit.models.audit import AuditResult
from app.audit.services.audit import _client_ip
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.connectors.talon.models.talon_v2 import AUTOMATION_LEVELS
from app.connectors.talon.models.talon_v2 import AUTOMATION_MODES
from app.connectors.talon.models.talon_v2 import TalonAutomationPolicy
from app.connectors.talon.models.talon_v2 import TalonAutomationStart
from app.connectors.talon.models.talon_v2 import TalonConnectorSettings
from app.connectors.talon.schema.talon_automation import TalonAutomationPolicyResponse
from app.connectors.talon.schema.talon_automation import TalonAutomationPolicyUpdate
from app.connectors.talon.schema.talon_automation import TalonAutomationSwitchResponse
from app.connectors.talon.services import talon_triggers
from app.connectors.talon.services.talon_service_account import DEFAULT_SERVICE_USERNAME
from app.connectors.talon.services.talon_service_account import effective_username
from app.connectors.talon.services.talon_service_account import is_service_account
from app.connectors.talon.services.talon_service_account import settings_row
from app.connectors.talon.services.talon_service_account import user_id_for
from app.connectors.talon.utils.v2_client import TALON_CONNECTOR
from app.connectors.velociraptor.services.talon_catalogue import TALON_AUTO_RUN
from app.connectors.velociraptor.services.talon_catalogue import TALON_CATALOGUE
from app.connectors.velociraptor.services.talon_catalogue import is_response_artifact
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc

#: The caps (plan Q9, D85 h), by name, with their defaults. A policy may only lower them. CoPilot
#: enforces ``ENFORCED_CAPS`` on starts today; the others are stored for the levels that use them
#: (AP-6 files, AP-7 commands).
CAP_DEFAULTS: Mapping[str, int] = {
    "per_alert": talon_triggers.PER_ALERT_CAP,  # level 1 per run, enforced per alert per 2 h (AP-2a)
    "per_host_hour": 6,  # automated starts per host per hour, every level together
    "per_customer_hour": 10,  # collections per customer per hour, levels 1-2 together
    "level_2_artifacts_per_alert": 1,
    "files_per_alert": 1,
    "files_per_customer_day": 10,
    "file_bytes_per_customer_day": 500 * 1024 * 1024,
    "commands_per_alert": 3,
    "free_form_per_alert": 1,
    "commands_per_customer_day": 20,
}
ENFORCED_CAPS = ("per_alert", "per_host_hour", "per_customer_hour")
#: The levels whose ``auto`` starts CoPilot can make today: level 2 comes with AP-6, 3-4 with AP-7/8.
STARTABLE_LEVELS = (1,)
HOUR = timedelta(hours=1)
#: What ``auto`` and the dry run count.
COUNTED_AUTO = ("reserved", "started", "failed", "unknown")
WOULD_START = "would_start"
RANK = {mode: rank for rank, mode in enumerate(AUTOMATION_MODES)}

#: The honest risk (D85), acknowledged by the admin who raises level 3 or 4.
RISK_TEXT = (
    "At levels 3 and 4 an automatic investigation runs commands on the alert's host without a person approving each one. "
    "Anyone who can write text into this customer's logs can try to steer such a command onto that host. The filters, the "
    "injection downgrade and the caps reduce this risk; they don't remove it."
)

# ── fixed texts ───────────────────────────────────────────────────────────────
#: The start route's refusals (also the dry run's verdicts): fixed texts, never a part of the request.
AUTOMATION_OFF = "not started: automated endpoint actions are turned off in CoPilot (Talon settings, automation)"
NO_POLICY = "not started: this customer has no automation policy in CoPilot, so every level is off"
LEVEL_OFF = "not started: the customer's automation policy has this level off"
LEVEL_SHADOW = "not started: the customer's automation policy has this level in shadow mode (would-have-run), which runs nothing"
LEVEL_PROPOSE = "not started: the customer's automation policy has this level in propose mode, which runs only what an analyst approves"
NOT_AUTOMATABLE = "The Talon service account may not start this collection"  # the same text as EA-4b's SERVICE_REFUSED
LEVEL_NOT_AVAILABLE = "not started: CoPilot can't start this level's automated actions yet"
HOST_CAP = "not started: this host has reached its hourly cap of automated starts"
CUSTOMER_CAP = "not started: this customer has reached its hourly cap of automated collections"
DRY_RUN_UNRECORDED = "CoPilot could not record the dry run"
#: The routes' own refusals.
ADMIN_ONLY = "Only an admin may read or change the Talon automation policy"
SERVICE_REFUSED = "The Talon service account may not read or change the Talon automation policy"
NO_CUSTOMER = "customer_code is not a customer"
VERSION_CHANGED = "The automation policy changed since it was read; read it again and review the change"
RISK_NOT_ACKNOWLEDGED = "Raising level 3 or 4 needs acknowledge_risk: true (the admin acknowledges the risk text)"
SERVICE_USER_UNASSIGNED = "No level can be raised: the Talon service user isn't assigned to this customer"
BAD_ARTIFACTS = (
    "level_2_artifacts may only name Talon catalogue artifacts that are not command, script, quarantine or remediation artifacts"
)
BAD_GLOBS = "file_allow_globs: at most 32 globs per OS, each 1 to 512 printable characters without spaces at its ends"
BAD_CAPS = "caps: only known cap names, each a whole number between 0 and its default"

MODE_REFUSAL = {"off": LEVEL_OFF, "shadow": LEVEL_SHADOW, "propose": LEVEL_PROPOSE}


def utcnow() -> datetime:
    return talon_triggers.utcnow()


# ── the gate ──────────────────────────────────────────────────────────────────


def classify(artifact: str) -> Optional[int]:
    """CoPilot's own level for a collection (D86 d), by name: an auto-run artifact is level 1 (its
    parameters are then held to the pins, ``auto_run_violation``), another catalogue artifact level
    2, anything else none (never startable by the service account)."""
    if artifact in TALON_AUTO_RUN:
        return 1
    if artifact in TALON_CATALOGUE:
        return 2
    return None


async def policy_row(session: AsyncSession, customer_code: Optional[str], lock: bool = False) -> Optional[TalonAutomationPolicy]:
    if not customer_code:
        return None
    query = select(TalonAutomationPolicy).where(TalonAutomationPolicy.customer_code == customer_code)
    if lock:
        query = query.with_for_update()
    row = (await session.execute(query)).scalars().first()
    # MySQL compares case-insensitively; a policy is the exact customer's.
    return row if isinstance(row, TalonAutomationPolicy) and row.customer_code == customer_code else None


def check_policy(
    settings: Optional[TalonConnectorSettings],
    policy: Optional[TalonAutomationPolicy],
    level: Optional[int],
    *,
    dry_run: bool,
) -> None:
    """The switch, the row, the level and its mode, in that order: a fixed 403 unless the level is
    on ``auto`` (a dry run: ``shadow`` or ``auto``) and startable here. Anything not on ``auto`` is
    never started (D86 i)."""
    if settings is None or not settings.automation_enabled:
        raise HTTPException(status_code=403, detail=AUTOMATION_OFF)
    if policy is None:
        raise HTTPException(status_code=403, detail=NO_POLICY)
    if level is None:
        raise HTTPException(status_code=403, detail=NOT_AUTOMATABLE)
    mode = policy.mode(level)
    if mode != "auto" and not (dry_run and mode == "shadow"):
        raise HTTPException(status_code=403, detail=MODE_REFUSAL.get(mode, LEVEL_OFF))
    if level not in STARTABLE_LEVELS:
        raise HTTPException(status_code=403, detail=LEVEL_NOT_AVAILABLE)


def effective_caps(policy: Optional[TalonAutomationPolicy]) -> Dict[str, int]:
    """The defaults, lowered by the row's overrides (never raised, whatever is stored)."""
    caps = dict(CAP_DEFAULTS)
    for name, value in ((policy.caps if policy is not None else None) or {}).items():
        if name in caps and isinstance(value, int) and not isinstance(value, bool):
            caps[name] = max(0, min(caps[name], value))
    return caps


async def _count(session: AsyncSession, *conditions: Any) -> int:
    return int((await session.execute(select(func.count()).select_from(TalonAutomationStart).where(*conditions))).scalar_one())


async def _cap_refusal(
    session: AsyncSession,
    caps: Mapping[str, int],
    *,
    mode: str,
    verdicts: Sequence[str],
    customer_code: str,
    client: str,
    now: datetime,
) -> Optional[str]:
    """The per-host and per-customer caps, counted from ``talon_automation_start`` rows of ``mode``."""
    counted = (TalonAutomationStart.mode == mode, TalonAutomationStart.verdict.in_(verdicts), TalonAutomationStart.created_at >= now - HOUR)
    if await _count(session, *counted, TalonAutomationStart.velociraptor_id == client) >= caps["per_host_hour"]:
        return HOST_CAP
    if (
        await _count(session, *counted, TalonAutomationStart.customer_code == customer_code, TalonAutomationStart.level.in_((1, 2)))
        >= caps["per_customer_hour"]
    ):
        return CUSTOMER_CAP
    return None


def _start_row(
    *,
    user: Any,
    binding: Optional[talon_triggers.Binding],
    alert_id: int,
    customer_code: str,
    hostname: str,
    client: str,
    level: Optional[int],
    mode: str,
    artifact: str,
    parameters: Iterable[Tuple[str, str]],
    job_id: Optional[str],
    verdict: str,
    code: Optional[str],
    policy: Optional[TalonAutomationPolicy],
    now: datetime,
) -> TalonAutomationStart:
    return TalonAutomationStart(
        customer_code=customer_code,
        alert_id=alert_id,
        hostname=hostname,
        velociraptor_id=client,
        level=level,
        mode=mode,
        artifact=artifact,
        parameters=[[key, value] for key, value in parameters],
        trigger_id=binding.trigger_id if binding else None,
        trigger_source=binding.source if binding else None,
        trigger_user_id=binding.user_id if binding else None,
        trigger_username=binding.username if binding else None,
        job_id=job_id,
        verdict=verdict,
        code=code,
        policy_version=policy.version if policy is not None else None,
        user_id=getattr(user, "id", None),
        username=getattr(user, "username", None),
        created_at=now,
    )


async def reserve_start(
    *,
    user: Any,
    binding: talon_triggers.Binding,
    customer_code: str,
    hostname: str,
    client: str,
    level: int,
    artifact: str,
    parameters: Sequence[Tuple[str, str]],
    job_id: Optional[str],
    request: Optional[Request],
) -> int:
    """The policy re-check, the caps, the start's row and its audit row, in one transaction under the
    customer's policy row lock, committed before the flow starts (module docstring). Returns the
    row's id; a fixed 403 or 429 otherwise (nothing kept), or 500 ``CAP_UNRECORDED`` (no start)."""
    try:
        async with talon_triggers.new_session() as session:
            await talon_triggers.ensure_cap_row(session, binding)
            policy = await policy_row(session, customer_code, lock=True)
            check_policy(await settings_row(session), policy, level, dry_run=False)
            caps, now = effective_caps(policy), utcnow()
            if not await talon_triggers._take_slot(session, binding.alert_id, customer_code, now, caps["per_alert"]):
                logger.warning(
                    f"Refused an automated start for alert {binding.alert_id}: the per-alert cap ({caps['per_alert']}) is reached",
                )
                raise HTTPException(status_code=429, detail=talon_triggers.ALERT_CAP)
            refused = await _cap_refusal(
                session,
                caps,
                mode="auto",
                verdicts=COUNTED_AUTO,
                customer_code=customer_code,
                client=client,
                now=now,
            )
            if refused is not None:
                logger.warning(f"Refused an automated start on {client} for {customer_code}: {refused}")
                raise HTTPException(status_code=429, detail=refused)
            row = _start_row(
                user=user,
                binding=binding,
                alert_id=binding.alert_id,
                customer_code=customer_code,
                hostname=hostname,
                client=client,
                level=level,
                mode="auto",
                artifact=artifact,
                parameters=parameters,
                job_id=job_id,
                verdict="reserved",
                code=None,
                policy=policy,
                now=now,
            )
            session.add(row)
            await session.flush()
            session.add(
                AuditLog(
                    action=AuditAction.TALON_AUTOMATION_START.value,
                    actor_user_id=getattr(user, "id", None),
                    actor_username=getattr(user, "username", None),
                    customer_code=customer_code,
                    entity_type="talon_automation_start",
                    entity_id=str(row.id),
                    result=AuditResult.SUCCESS.value,
                    new_value={
                        "automation_start_id": row.id,
                        "level": level,
                        "mode": "auto",
                        "artifact": artifact,
                        "hostname": hostname,
                        "velociraptor_id": client,
                        "policy_version": row.policy_version,
                        **binding.audit_values(job_id),
                    },
                    source_ip=_client_ip(request),
                    details=f"Automated level {level} start reserved for alert {binding.alert_id} ({binding.source})",
                ),
            )
            await session.commit()
            return row.id
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - no committed record, no start
        logger.error(f"Could not record an automated start for alert {binding.alert_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=talon_triggers.CAP_UNRECORDED) from None


async def finish_start(record_id: int, verdict: str, flow_id: Optional[str] = None, code: Optional[str] = None) -> None:
    """The start's outcome on its row. Best effort: the slot is spent and audited either way."""
    try:
        async with talon_triggers.new_session() as session:
            await session.execute(
                update(TalonAutomationStart)
                .where(TalonAutomationStart.id == record_id)
                .values(verdict=verdict, flow_id=flow_id, code=code, finished_at=utcnow()),
            )
            await session.commit()
    except Exception as e:  # noqa: BLE001 - logged, never the start's answer
        logger.error(f"Could not record the outcome of automated start {record_id}: {type(e).__name__}")


async def dry_run_caps(
    session: AsyncSession,
    policy: Optional[TalonAutomationPolicy],
    *,
    alert_id: int,
    customer_code: str,
    client: str,
) -> None:
    """The caps as ``auto`` would apply them, counted from the dry runs' own ``would_start`` rows: a
    fixed 429 over one."""
    caps, now = effective_caps(policy), utcnow()
    alert_runs = await _count(
        session,
        TalonAutomationStart.mode == "shadow",
        TalonAutomationStart.verdict == WOULD_START,
        TalonAutomationStart.alert_id == alert_id,
        TalonAutomationStart.created_at >= now - talon_triggers.WINDOW,
    )
    if alert_runs >= caps["per_alert"]:
        raise HTTPException(status_code=429, detail=talon_triggers.ALERT_CAP)
    refused = await _cap_refusal(session, caps, mode="shadow", verdicts=(WOULD_START,), customer_code=customer_code, client=client, now=now)
    if refused is not None:
        raise HTTPException(status_code=429, detail=refused)


async def record_dry_run(
    *,
    user: Any,
    binding: Optional[talon_triggers.Binding],
    alert_id: int,
    customer_code: str,
    hostname: str,
    client: str,
    level: Optional[int],
    artifact: str,
    parameters: Sequence[Tuple[str, str]],
    job_id: Optional[str],
    refusal: Optional[Tuple[int, str, str]],
) -> Tuple[int, Optional[Tuple[int, str, str]], Optional[TalonAutomationPolicy]]:
    """Check the caps (when nothing refused it yet) and record the dry run's verdict (``mode =
    shadow``) in a session of its own. Returns the row's id, the refusal (status, code, text) or
    None, and the policy it was checked against. 500 ``DRY_RUN_UNRECORDED`` if it can't be written."""
    try:
        async with talon_triggers.new_session() as session:
            policy = await policy_row(session, customer_code)
            if refusal is None:
                try:
                    check_policy(await settings_row(session), policy, level, dry_run=True)
                    await dry_run_caps(session, policy, alert_id=alert_id, customer_code=customer_code, client=client)
                except HTTPException as e:
                    refusal = (e.status_code, *code_and_text(e))
            row = _start_row(
                user=user,
                binding=binding,
                alert_id=alert_id,
                customer_code=customer_code,
                hostname=hostname,
                client=client,
                level=level,
                mode="shadow",
                artifact=artifact,
                parameters=parameters,
                job_id=job_id,
                verdict="refused" if refusal else WOULD_START,
                code=refusal[1] if refusal else None,
                policy=policy,
                now=utcnow(),
            )
            session.add(row)
            await session.commit()
            return row.id, refusal, policy
    except Exception as e:  # noqa: BLE001 - a dry run CoPilot couldn't record is no answer
        logger.error(f"Could not record a dry run for alert {alert_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=DRY_RUN_UNRECORDED) from None


#: Every fixed text the start route and the dry run answer, by code (the dry run's ``code``).
_CODES: Dict[str, str] = {}


def register_codes(pairs: Iterable[Tuple[str, str]]) -> None:
    for code, text in pairs:
        _CODES.setdefault(text, code)


register_codes(
    [
        ("AUTOMATION_OFF", AUTOMATION_OFF),
        ("NO_POLICY", NO_POLICY),
        ("LEVEL_OFF", LEVEL_OFF),
        ("LEVEL_SHADOW", LEVEL_SHADOW),
        ("LEVEL_PROPOSE", LEVEL_PROPOSE),
        ("SERVICE_REFUSED", NOT_AUTOMATABLE),  # EA-4b's text: no level, or not the allowlist's pins
        ("LEVEL_NOT_AVAILABLE", LEVEL_NOT_AVAILABLE),
        ("HOST_CAP", HOST_CAP),
        ("CUSTOMER_CAP", CUSTOMER_CAP),
        ("ALERT_REQUIRED", talon_triggers.ALERT_REQUIRED),
        ("NO_TRIGGER", talon_triggers.NO_TRIGGER),
        ("PORTAL_TRIGGER", talon_triggers.PORTAL_TRIGGER),
        ("REPLAY_TRIGGER", talon_triggers.REPLAY_TRIGGER),
        ("OTHER_CUSTOMER", talon_triggers.OTHER_CUSTOMER),
        ("SERVICE_TRIGGER", talon_triggers.SERVICE_TRIGGER),
        ("NOT_ALERT_HOST", talon_triggers.NOT_ALERT_HOST),
        ("ALERT_CAP", talon_triggers.ALERT_CAP),
        ("CAP_UNRECORDED", talon_triggers.CAP_UNRECORDED),
    ],
)


def code_and_text(e: HTTPException) -> Tuple[str, str]:
    """A refusal's code and fixed text. A text no code names (the host re-check's 409 names what
    failed in CoPilot's own words) is ``HOST_RECHECK`` for a 409, else ``REFUSED``."""
    text = e.detail if isinstance(e.detail, str) else ""
    code = _CODES.get(text) or ("HOST_RECHECK" if e.status_code == 409 else "REFUSED")
    return code, text


# ── the policy routes ─────────────────────────────────────────────────────────


async def _refuse_non_admin(user: User, session: AsyncSession) -> None:
    """The Talon service account first (whatever its role), then the database role."""
    if is_service_account(user, await settings_row(session)):
        logger.warning(f"Refused the Talon service account {getattr(user, 'username', '?')} on the automation policy")
        raise HTTPException(status_code=403, detail=SERVICE_REFUSED)
    if getattr(user, "role_id", None) != RoleEnum.admin:
        raise HTTPException(status_code=403, detail=ADMIN_ONLY)


async def _require_customer(session: AsyncSession, customer_code: str) -> None:
    """An exact-case ``customers`` row (MySQL compares case-insensitively); a fixed 404 otherwise."""
    if len(customer_code) > 64:
        raise HTTPException(status_code=404, detail=NO_CUSTOMER)
    codes = (await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))).scalars().all()
    if customer_code not in set(codes):
        raise HTTPException(status_code=404, detail=NO_CUSTOMER)


async def service_user_assigned(session: AsyncSession, customer_code: str) -> bool:
    """Whether a Talon service user (the recorded id, the configured name or ``talon-analyst``)
    exists and may see the customer (its assignments; an admin sees every customer)."""
    row = await settings_row(session)
    ids = {row.collect_service_user_id if row is not None else None}
    for name in {effective_username(row), DEFAULT_SERVICE_USERNAME}:
        ids.add(await user_id_for(session, name))
    for user_id in sorted(i for i in ids if i is not None):
        user = await session.get(User, user_id)
        if user is not None and await customer_access_handler.check_customer_access(user, customer_code, session):
            return True
    return False


def _snapshot(row: Optional[TalonAutomationPolicy]) -> Dict[str, Any]:
    """What the audit records as the old or new value."""
    if row is None:
        return {"exists": False, **{f"level_{level}_mode": "off" for level in AUTOMATION_LEVELS}, "version": 0}
    return {
        "exists": True,
        **{f"level_{level}_mode": row.mode(level) for level in AUTOMATION_LEVELS},
        "level_2_artifacts": row.level_2_artifacts,
        "file_allow_globs": row.file_allow_globs,
        "caps": row.caps,
        "risk_acknowledged_by_user_id": row.risk_acknowledged_by_user_id,
        "risk_acknowledged_by_username": row.risk_acknowledged_by_username,
        "risk_acknowledged_at": row.risk_acknowledged_at.isoformat() if row.risk_acknowledged_at else None,
        "version": row.version,
    }


async def _describe(
    session: AsyncSession,
    customer_code: str,
    row: Optional[TalonAutomationPolicy],
    message: str,
) -> TalonAutomationPolicyResponse:
    settings = await settings_row(session)
    return TalonAutomationPolicyResponse(
        success=True,
        message=message,
        customer_code=customer_code,
        exists=row is not None,
        automation_enabled=bool(settings is not None and settings.automation_enabled),
        **{f"level_{level}_mode": row.mode(level) if row is not None else "off" for level in AUTOMATION_LEVELS},
        level_2_artifacts=row.level_2_artifacts if row is not None else None,
        file_allow_globs=row.file_allow_globs if row is not None else None,
        caps=row.caps if row is not None else None,
        effective_caps=effective_caps(row),
        cap_defaults=dict(CAP_DEFAULTS),
        enforced_caps=list(ENFORCED_CAPS),
        startable_levels=list(STARTABLE_LEVELS),
        service_user_assigned=await service_user_assigned(session, customer_code),
        risk_acknowledgement_text=RISK_TEXT,
        risk_acknowledged_by_user_id=row.risk_acknowledged_by_user_id if row is not None else None,
        risk_acknowledged_by_username=row.risk_acknowledged_by_username if row is not None else None,
        risk_acknowledged_at=row.risk_acknowledged_at if row is not None else None,
        shadow_reviewed=row.shadow_reviewed if row is not None else None,
        version=row.version if row is not None else 0,
        updated_by_user_id=row.updated_by_user_id if row is not None else None,
        updated_by_username=row.updated_by_username if row is not None else None,
        updated_at=row.updated_at if row is not None else None,
    )


async def get_policy(user: User, session: AsyncSession, customer_code: str) -> TalonAutomationPolicyResponse:
    await _refuse_non_admin(user, session)
    await _require_customer(session, customer_code)
    return await _describe(session, customer_code, await policy_row(session, customer_code), "Talon automation policy retrieved")


def _clean_artifacts(value: Optional[List[str]]) -> Optional[List[str]]:
    if value is None:
        return None
    if any(name not in TALON_CATALOGUE or is_response_artifact(name) for name in value):
        raise HTTPException(status_code=400, detail=BAD_ARTIFACTS)
    return sorted(set(value))


def _clean_globs(value: Optional[Dict[str, List[str]]]) -> Optional[Dict[str, List[str]]]:
    if value is None:
        return None
    out = {}
    for os_name, globs in value.items():
        if len(globs) > 32 or any(not isinstance(g, str) or not 1 <= len(g) <= 512 or g != g.strip() or not g.isprintable() for g in globs):
            raise HTTPException(status_code=400, detail=BAD_GLOBS)
        out[os_name] = sorted(set(globs))
    return out


def _clean_caps(value: Optional[Dict[str, int]]) -> Optional[Dict[str, int]]:
    if value is None:
        return None
    if any(name not in CAP_DEFAULTS or not 0 <= cap <= CAP_DEFAULTS[name] for name, cap in value.items()):
        raise HTTPException(status_code=400, detail=BAD_CAPS)
    return dict(sorted(value.items()))


async def update_policy(
    user: User,
    session: AsyncSession,
    customer_code: str,
    body: TalonAutomationPolicyUpdate,
    request: Optional[Request] = None,
) -> TalonAutomationPolicyResponse:
    """Replace the customer's policy (module docstring), under its row locked, audited with the old
    and new values."""
    await _refuse_non_admin(user, session)
    await _require_customer(session, customer_code)
    artifacts, globs, caps = _clean_artifacts(body.level_2_artifacts), _clean_globs(body.file_allow_globs), _clean_caps(body.caps)
    modes = {level: getattr(body, f"level_{level}_mode") for level in AUTOMATION_LEVELS}
    for attempt in range(2):
        row = await policy_row(session, customer_code, lock=True)
        old = _snapshot(row)
        current = {level: row.mode(level) if row is not None else "off" for level in AUTOMATION_LEVELS}
        raised = [level for level in AUTOMATION_LEVELS if RANK[modes[level]] > RANK[current[level]]]
        if body.expected_version is not None and body.expected_version != old["version"]:
            await session.rollback()
            raise HTTPException(status_code=409, detail=VERSION_CHANGED)
        risky = [level for level in raised if level in (3, 4)]
        if risky and not body.acknowledge_risk:
            await session.rollback()
            raise HTTPException(status_code=400, detail=RISK_NOT_ACKNOWLEDGED)
        if raised and not await service_user_assigned(session, customer_code):
            await session.rollback()
            raise HTTPException(status_code=409, detail=SERVICE_USER_UNASSIGNED)
        now = now_utc()
        if row is None:
            row = TalonAutomationPolicy(customer_code=customer_code, version=0, created_at=now)
            session.add(row)
        for level in AUTOMATION_LEVELS:
            setattr(row, f"level_{level}_mode", modes[level])
        row.level_2_artifacts, row.file_allow_globs, row.caps = artifacts, globs, caps
        if risky:
            row.risk_acknowledged_by_user_id, row.risk_acknowledged_by_username, row.risk_acknowledged_at = user.id, user.username, now
        elif modes[3] == "off" and modes[4] == "off":
            row.risk_acknowledged_by_user_id = row.risk_acknowledged_by_username = row.risk_acknowledged_at = None
        row.version = (row.version or 0) + 1
        row.updated_by_user_id, row.updated_by_username, row.updated_at = user.id, user.username, now
        new = {**_snapshot(row), "acknowledge_risk": bool(risky)}
        try:
            await session.commit()
        except IntegrityError:  # another admin created the row first: read it again
            await session.rollback()
            if attempt:
                raise
            continue
        await record_audit_event(
            action=AuditAction.TALON_AUTOMATION_POLICY_UPDATE,
            actor_user_id=user.id,
            actor_username=user.username,
            customer_code=customer_code,
            entity_type="talon_automation_policy",
            entity_id=customer_code,
            old_value=old,
            new_value=new,
            request=request,
            details=(
                f"Talon automation policy for {customer_code} set to version {row.version}"
                + (f"; the risk of level(s) {', '.join(map(str, risky))} acknowledged" if risky else "")
            ),
        )
        return await _describe(session, customer_code, row, "Talon automation policy saved")
    raise AssertionError("unreachable")


# ── the global switch ─────────────────────────────────────────────────────────


def _switch_response(row: Optional[TalonConnectorSettings], message: str) -> TalonAutomationSwitchResponse:
    return TalonAutomationSwitchResponse(
        success=True,
        message=message,
        connector_name=TALON_CONNECTOR,
        automation_enabled=bool(row is not None and row.automation_enabled),
        updated_by_user_id=row.updated_by_user_id if row is not None else None,
        updated_at=row.updated_at if row is not None else None,
    )


async def get_switch(user: User, session: AsyncSession) -> TalonAutomationSwitchResponse:
    await _refuse_non_admin(user, session)
    return _switch_response(await settings_row(session), "Talon automation switch retrieved")


async def update_switch(
    user: User,
    session: AsyncSession,
    enabled: bool,
    request: Optional[Request] = None,
) -> TalonAutomationSwitchResponse:
    """Turn every automated start on or off (a new settings row leaves "Talon v2" off), audited."""
    await _refuse_non_admin(user, session)
    for attempt in range(2):
        row = await settings_row(session)
        old = bool(row is not None and row.automation_enabled)
        if row is None:
            row = TalonConnectorSettings(connector_name=TALON_CONNECTOR)
            session.add(row)
        row.automation_enabled = enabled
        row.updated_by_user_id = user.id
        row.updated_at = now_utc()
        try:
            await session.commit()
            break
        except IntegrityError:
            await session.rollback()
            if attempt:
                raise
    await record_audit_event(
        action=AuditAction.TALON_AUTOMATION_POLICY_UPDATE,
        actor_user_id=user.id,
        actor_username=user.username,
        entity_type="connector",
        entity_id=TALON_CONNECTOR,
        old_value={"automation_enabled": old},
        new_value={"automation_enabled": enabled},
        request=request,
        details=f"Talon automation turned {'on' if enabled else 'off'} for connector '{TALON_CONNECTOR}'",
    )
    return _switch_response(row, f"Talon automation turned {'on' if enabled else 'off'}")
