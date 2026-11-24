"""A customer's cloud accounts: what CoPilot scans, and with which credential (#1328).

Load-bearing:

- **An account belongs to one customer.** Every route names the customer in its path, and
  ``get_account`` is the only way an id becomes a row: an account of another customer is the
  same 404 as one that doesn't exist, so ids can't be probed across tenants.
- **Settings are checked per provider** (``checked_config``): a field that doesn't apply is
  refused, not ignored, and what the provider needs is required.
- **The credential is write-only.** It is encrypted with ``CLOUD_ASSESSMENT_ENCRYPTION_KEY``
  (``services/crypto.py``) and never returned or logged; a response says whether one is stored
  and shows a hint (the first characters of a client secret, as Azure shows them; the last of
  an AWS key id; the start of a GCP key id). An update without one keeps the stored one.
- **An AWS role's External ID is CoPilot's.** It is generated when the account is created,
  unique per account, and no request can set or change it: the External ID is what stops
  another CoPilot user, or another of the SOC's customers, from pointing an account at a role
  they don't own (AWS's "confused deputy").
- **The runner's request is built here** (``runner_payload``), from the stored settings and the
  decrypted credential, in the shape copilot-prowler validates (``prowler-runner/runner/models.py``).
- **Every write is audited**, with the settings before and after and never a credential.
"""

import secrets
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import RoleEnum
from app.auth.models.users import User
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentAccount
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentFinding
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.schema.cloud_assessment import ACTIVE_STATUSES
from app.cloud_assessment.schema.cloud_assessment import AUTH_METHODS
from app.cloud_assessment.schema.cloud_assessment import AccountConfigIn
from app.cloud_assessment.schema.cloud_assessment import AccountCreate
from app.cloud_assessment.schema.cloud_assessment import AccountOut
from app.cloud_assessment.schema.cloud_assessment import AccountScanBrief
from app.cloud_assessment.schema.cloud_assessment import AccountUpdate
from app.cloud_assessment.schema.cloud_assessment import ConnectionTestResponse
from app.cloud_assessment.schema.cloud_assessment import ScanCounts
from app.cloud_assessment.schema.cloud_assessment import SecretIn
from app.cloud_assessment.services import crypto
from app.cloud_assessment.services import reports
from app.cloud_assessment.services.errors import error_message
from app.cloud_assessment.services.errors import runner_http_error
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError
from app.cloud_assessment.utils import as_utc
from app.cloud_assessment.utils import check_name
from app.cloud_assessment.utils import next_slot
from app.cloud_assessment.utils import utc_now
from app.db.universal_models import Customers
from app.time_utils import to_naive_utc

MAX_ACCOUNTS_PER_CUSTOMER = 100
EXTERNAL_ID_PREFIX = "copilot-"
# The role's credentials last an hour and Prowler renews them as they expire, so this suits any
# scan. Prowler's CloudFormation template gives the role a MaxSessionDuration of 3600.
SESSION_DURATION_SECONDS = 3600
FINDINGS_DELETE_BATCH = 5000

PROVIDER_LABELS = {"aws": "AWS", "azure": "Azure", "gcp": "GCP", "m365": "Microsoft 365"}
OPTION_KEYS = ("excluded_checks", "excluded_services", "timeout_seconds")
#: The settings an admin may give, per provider and sign-in. The External ID and the key's
#: email and project are CoPilot's to fill.
EDITABLE_KEYS: Dict[Tuple[str, str], Tuple[str, ...]] = {
    ("aws", "role"): ("role_arn", "regions"),
    ("aws", "access_keys"): ("regions",),
    ("azure", "client_secret"): ("tenant_id", "client_id", "subscription_ids"),
    ("m365", "client_secret"): ("tenant_id", "client_id", "tenant_domain"),
    ("gcp", "service_account_key"): ("project_ids", "excluded_project_ids", "organization_id"),
}
REQUIRED_KEYS: Dict[Tuple[str, str], Tuple[str, ...]] = {
    ("aws", "role"): ("role_arn",),
    ("azure", "client_secret"): ("tenant_id", "client_id"),
    ("m365", "client_secret"): ("tenant_id", "client_id", "tenant_domain"),
}
DERIVED_KEYS = ("external_id", "client_email", "key_project_id")
#: Which credential fields each sign-in takes; a role's are optional (None: the host's identity).
SECRET_FIELDS = {
    "role": ("access_key_id", "secret_access_key"),
    "access_keys": ("access_key_id", "secret_access_key"),
    "client_secret": ("client_secret",),
    "service_account_key": ("service_account_key",),
}
SECRET_REQUIRED = {"role": False, "access_keys": True, "client_secret": True, "service_account_key": True}


class AccountProblem(HTTPException):
    """A refusal of the request's content: 422 with a fixed text that never echoes a value."""

    def __init__(self, detail: str, status_code: int = 422) -> None:
        super().__init__(status_code=status_code, detail=detail)


def require_admin(user: User) -> None:
    """Cloud accounts and their credentials are an admin's: by the user's role in the database, not
    only the token's scope (a token issued before a demotion still carries ``admin``)."""
    if user.role_id != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Only an admin may add, change or delete cloud accounts")


# --- pure rules ---------------------------------------------------------------------------------


def _unique(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    return list(dict.fromkeys(values))


def checked_config(provider: str, auth_method: str, config: AccountConfigIn, keep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The settings to store for this provider and sign-in. Raises ``AccountProblem``.

    ``keep`` holds what CoPilot filled in (the External ID, a GCP key's email and project); an
    update passes the stored config so they survive it.
    """
    if auth_method not in AUTH_METHODS.get(provider, ()):
        raise AccountProblem(f"{PROVIDER_LABELS.get(provider, provider)} accounts don't sign in with {auth_method}")
    pair = (provider, auth_method)
    editable = EDITABLE_KEYS[pair]
    given = config.model_dump()
    for key, value in given.items():
        if key in OPTION_KEYS or key in editable:
            continue
        if value not in (None, []):
            raise AccountProblem(f"{key} doesn't apply to {PROVIDER_LABELS[provider]} accounts")
    for key in REQUIRED_KEYS.get(pair, ()):
        if not given.get(key):
            raise AccountProblem(f"{key} is required for {PROVIDER_LABELS[provider]} accounts")
    stored: Dict[str, Any] = {}
    for key in editable:
        value = given.get(key)
        value = _unique(value) if isinstance(value, list) else value
        if value not in (None, ""):
            stored[key] = value
    for key in ("excluded_checks", "excluded_services"):
        values = _unique(given.get(key))
        if values:
            stored[key] = values
    if given.get("timeout_seconds") is not None:
        stored["timeout_seconds"] = given["timeout_seconds"]
    for key in DERIVED_KEYS:
        if keep and keep.get(key):
            stored[key] = keep[key]
    return stored


def checked_secret(auth_method: str, secret: Optional[SecretIn]) -> Optional[Dict[str, Any]]:
    """The credential to encrypt, or None when none was sent. Raises ``AccountProblem``."""
    if secret is None:
        return None
    fields = {name for name, value in secret if value is not None}
    allowed = set(SECRET_FIELDS[auth_method])
    extra = fields - allowed
    if extra:
        raise AccountProblem(f"{sorted(extra)[0]} isn't the credential for this account")
    if auth_method in ("role", "access_keys"):
        if fields != allowed:
            raise AccountProblem("enter both the access key id and the secret access key")
        return {"access_key_id": secret.access_key_id, "secret_access_key": secret.secret_access_key.get_secret_value()}
    if auth_method == "client_secret":
        if not fields:
            raise AccountProblem("enter the client secret")
        return {"client_secret": secret.client_secret.get_secret_value()}
    if not fields:
        raise AccountProblem("upload the service account's key file")
    return {"service_account_key": secret.service_account_key.key_file()}


def secret_hint(auth_method: str, secret: Dict[str, Any]) -> Optional[str]:
    """Enough to tell credentials apart, never enough to use one."""
    if auth_method in ("role", "access_keys"):
        return "…" + str(secret.get("access_key_id", ""))[-4:]
    if auth_method == "client_secret":
        # Azure's own hint for a client secret is its first three characters.
        return str(secret.get("client_secret", ""))[:3] + "…"
    if auth_method == "service_account_key":
        return str((secret.get("service_account_key") or {}).get("private_key_id", ""))[:8] + "…"
    return None


def gcp_key_details(secret: Dict[str, Any]) -> Dict[str, Any]:
    key = secret.get("service_account_key") or {}
    return {"client_email": key.get("client_email"), "key_project_id": key.get("project_id")}


def new_external_id() -> str:
    return EXTERNAL_ID_PREFIX + secrets.token_hex(16)


def checked_schedule(schedule: str, hour: Optional[int], weekday: Optional[int]) -> Tuple[str, Optional[int], Optional[int]]:
    if schedule == "off":
        return "off", None, None
    if hour is None:
        raise AccountProblem("a schedule needs an hour (UTC)")
    if schedule == "weekly":
        if weekday is None:
            raise AccountProblem("a weekly schedule needs a weekday")
        return "weekly", hour, weekday
    return "daily", hour, None


def cloud_account(account: CloudAssessmentAccount) -> Optional[str]:
    config = account.config or {}
    if account.provider == "aws" and config.get("role_arn"):
        return str(config["role_arn"]).split(":")[4]
    if account.provider in ("azure", "m365"):
        return config.get("tenant_id")
    if account.provider == "gcp":
        return config.get("key_project_id")
    return None


def runner_payload(account: CloudAssessmentAccount, secret: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The body of copilot-prowler's ``POST /v1/scans`` and ``POST /v1/connection-test``."""
    config = account.config or {}
    options: Dict[str, Any] = {
        "excluded_checks": list(config.get("excluded_checks") or []),
        "excluded_services": list(config.get("excluded_services") or []),
    }
    if config.get("timeout_seconds"):
        options["timeout_seconds"] = config["timeout_seconds"]
    provider = account.provider
    if provider == "aws":
        if account.auth_method == "role":
            auth: Dict[str, Any] = {
                "method": "role",
                "role_arn": config["role_arn"],
                "external_id": config["external_id"],
                "session_duration_seconds": SESSION_DURATION_SECONDS,
            }
            if secret:
                auth["base_credentials"] = {"access_key_id": secret["access_key_id"], "secret_access_key": secret["secret_access_key"]}
        else:
            if not secret:
                raise crypto.CredentialCryptoError("credential_missing")
            auth = {"method": "access_keys", "access_key_id": secret["access_key_id"], "secret_access_key": secret["secret_access_key"]}
        scope: Dict[str, Any] = {"regions": config.get("regions") or None}
    elif provider in ("azure", "m365"):
        if not secret:
            raise crypto.CredentialCryptoError("credential_missing")
        auth = {
            "method": "client_secret",
            "tenant_id": config["tenant_id"],
            "client_id": config["client_id"],
            "client_secret": secret["client_secret"],
        }
        scope = (
            {"subscription_ids": config.get("subscription_ids") or None}
            if provider == "azure"
            else {"tenant_domain": config.get("tenant_domain")}
        )
    else:
        if not secret:
            raise crypto.CredentialCryptoError("credential_missing")
        auth = {"method": "service_account_key", "service_account_key": secret["service_account_key"]}
        scope = {
            "project_ids": config.get("project_ids") or None,
            "excluded_project_ids": config.get("excluded_project_ids") or None,
            "organization_id": config.get("organization_id"),
        }
    return {"provider": provider, "auth": auth, "scope": scope, "options": options}


def account_secret(account: CloudAssessmentAccount) -> Optional[Dict[str, Any]]:
    """The decrypted credential, or None when the account has none. Raises ``CredentialCryptoError``."""
    if not account.secret_ciphertext:
        return None
    return crypto.decrypt_secret(account.secret_ciphertext)


# --- responses ----------------------------------------------------------------------------------


def counts_of(scan: CloudAssessmentScan) -> ScanCounts:
    return ScanCounts(
        total=scan.total_count or 0,
        passed=scan.pass_count or 0,
        failed=scan.fail_count or 0,
        manual=scan.manual_count or 0,
        muted=scan.muted_count or 0,
        failed_critical=scan.fail_critical or 0,
        failed_high=scan.fail_high or 0,
        failed_medium=scan.fail_medium or 0,
        failed_low=scan.fail_low or 0,
        failed_informational=scan.fail_informational or 0,
        failed_unknown=scan.fail_unknown or 0,
        new_failed=scan.new_fail_count or 0,
        resolved_failed=scan.resolved_fail_count or 0,
    )


def scan_brief(scan: Optional[CloudAssessmentScan], previous: Optional[Dict[int, Optional[int]]] = None) -> Optional[AccountScanBrief]:
    if scan is None:
        return None
    return AccountScanBrief(
        id=scan.id,
        status=scan.status,
        trigger_type=scan.trigger_type,
        queued_at=as_utc(scan.queued_at),
        completed_at=as_utc(scan.completed_at),
        counts=counts_of(scan) if scan.status == "completed" else None,
        error_code=scan.error_code,
        previous_scan_id=(previous or {}).get(scan.id),
    )


async def previous_completed(session: AsyncSession, scans: Iterable[Optional[CloudAssessmentScan]]) -> Dict[int, Optional[int]]:
    """Per scan id: its account's newest completed scan before it, the one ingestion compared its new
    and resolved failures with (``ingest.previous_findings``), or None for the account's first."""
    wanted = [scan for scan in scans if scan is not None]
    if not wanted:
        return {}
    rows = await session.execute(
        select(CloudAssessmentScan.account_id, CloudAssessmentScan.id).where(
            CloudAssessmentScan.account_id.in_({scan.account_id for scan in wanted}),
            CloudAssessmentScan.status == "completed",
        ),
    )
    completed: Dict[int, List[int]] = {}
    for account_id, scan_id in rows:
        completed.setdefault(account_id, []).append(scan_id)
    previous: Dict[int, Optional[int]] = {}
    for scan in wanted:
        earlier = [scan_id for scan_id in completed.get(scan.account_id, []) if scan_id < scan.id]
        previous[scan.id] = max(earlier) if earlier else None
    return previous


def to_out(
    account: CloudAssessmentAccount,
    last_scan: Optional[CloudAssessmentScan] = None,
    last_completed: Optional[CloudAssessmentScan] = None,
    now: Optional[datetime] = None,
    previous: Optional[Dict[int, Optional[int]]] = None,
) -> AccountOut:
    now = now or utc_now()
    expires = to_naive_utc(account.secret_expires_at)
    return AccountOut(
        id=account.id,
        customer_code=account.customer_code,
        name=account.name,
        provider=account.provider,
        auth_method=account.auth_method,
        config=dict(account.config or {}),
        cloud_account=cloud_account(account),
        external_id=(account.config or {}).get("external_id"),
        secret_configured=bool(account.secret_ciphertext),
        secret_hint=account.secret_hint,
        secret_expires_at=as_utc(expires),
        secret_expires_in_days=(expires - now).days if expires else None,
        enabled=bool(account.enabled),
        schedule=account.schedule,
        schedule_hour=account.schedule_hour,
        schedule_weekday=account.schedule_weekday,
        next_scheduled_at=as_utc(next_slot(account.schedule, account.schedule_hour, account.schedule_weekday, now))
        if account.enabled
        else None,
        last_connection_test_at=as_utc(account.last_connection_test_at),
        last_connection_ok=account.last_connection_ok,
        last_connection_error=account.last_connection_error,
        last_connection_message=error_message(account.last_connection_error),
        created_by=account.created_by,
        created_at=as_utc(account.created_at),
        updated_by=account.updated_by,
        updated_at=as_utc(account.updated_at),
        last_scan=scan_brief(last_scan, previous),
        last_completed_scan=scan_brief(last_completed, previous),
    )


def audited(account: CloudAssessmentAccount) -> Dict[str, Any]:
    """What an audit row records of an account: its settings, never its credential."""
    return {
        "name": account.name,
        "provider": account.provider,
        "auth_method": account.auth_method,
        "config": dict(account.config or {}),
        "secret_configured": bool(account.secret_ciphertext),
        "secret_hint": account.secret_hint,
        "secret_expires_at": as_utc(account.secret_expires_at).isoformat() if account.secret_expires_at else None,
        "enabled": bool(account.enabled),
        "schedule": account.schedule,
        "schedule_hour": account.schedule_hour,
        "schedule_weekday": account.schedule_weekday,
    }


async def audit(
    action: AuditAction,
    user: User,
    customer_code: str,
    entity_type: str,
    entity_id: Any,
    request: Optional[Request],
    old: Optional[Dict[str, Any]] = None,
    new: Optional[Dict[str, Any]] = None,
    result: AuditResult = AuditResult.SUCCESS,
) -> None:
    await record_audit_event(
        action=action,
        actor_user_id=user.id,
        actor_username=user.username,
        customer_code=customer_code,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        old_value=old,
        new_value=new,
        request=request,
    )


# --- reads --------------------------------------------------------------------------------------


async def stored_customer_code(session: AsyncSession, customer_code: str) -> str:
    """The customer's code as stored (MySQL compares codes case-insensitively), or a 404."""
    found = (await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))).scalars().first()
    if found is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return found


async def get_account(session: AsyncSession, customer_code: str, account_id: int, for_update: bool = False) -> CloudAssessmentAccount:
    statement = select(CloudAssessmentAccount).where(
        CloudAssessmentAccount.id == account_id,
        CloudAssessmentAccount.customer_code == customer_code,
    )
    if for_update:
        statement = statement.with_for_update()
    account = (await session.execute(statement)).scalars().first()
    if account is None:
        raise HTTPException(status_code=404, detail="Cloud account not found")
    return account


async def latest_scans(
    session: AsyncSession,
    account_ids: List[int],
) -> Tuple[Dict[int, CloudAssessmentScan], Dict[int, CloudAssessmentScan], Dict[int, Optional[int]]]:
    """Each account's newest scan, its newest completed one, and each of those scans' previous
    completed scan (``previous_completed``)."""
    if not account_ids:
        return {}, {}, {}
    newest = (
        select(func.max(CloudAssessmentScan.id))
        .where(CloudAssessmentScan.account_id.in_(account_ids))
        .group_by(CloudAssessmentScan.account_id)
    )
    completed = (
        select(func.max(CloudAssessmentScan.id))
        .where(CloudAssessmentScan.account_id.in_(account_ids), CloudAssessmentScan.status == "completed")
        .group_by(CloudAssessmentScan.account_id)
    )
    rows = (await session.execute(select(CloudAssessmentScan).where(CloudAssessmentScan.id.in_(newest.union(completed))))).scalars().all()
    last: Dict[int, CloudAssessmentScan] = {}
    last_completed: Dict[int, CloudAssessmentScan] = {}
    for scan in rows:
        if scan.id > getattr(last.get(scan.account_id), "id", 0):
            last[scan.account_id] = scan
        if scan.status == "completed" and scan.id > getattr(last_completed.get(scan.account_id), "id", 0):
            last_completed[scan.account_id] = scan
    return last, last_completed, await previous_completed(session, [*last.values(), *last_completed.values()])


async def account_out(session: AsyncSession, account: CloudAssessmentAccount) -> AccountOut:
    last, last_completed, previous = await latest_scans(session, [account.id])
    return to_out(account, last.get(account.id), last_completed.get(account.id), previous=previous)


async def list_accounts(session: AsyncSession, customer_code: str) -> List[AccountOut]:
    code = await stored_customer_code(session, customer_code)
    accounts = (
        (
            await session.execute(
                select(CloudAssessmentAccount).where(CloudAssessmentAccount.customer_code == code).order_by(CloudAssessmentAccount.name),
            )
        )
        .scalars()
        .all()
    )
    last, last_completed, previous = await latest_scans(session, [account.id for account in accounts])
    now = utc_now()
    return [to_out(account, last.get(account.id), last_completed.get(account.id), now, previous) for account in accounts]


async def list_all_accounts(session: AsyncSession, customer_codes: Optional[List[str]]) -> List[AccountOut]:
    """Every account of these customers (None: every customer), each with its newest scans. The
    caller has narrowed the codes to the user's own (``scoped_customer_codes``); ``[]`` sees nothing."""
    if customer_codes == []:
        return []
    statement = select(CloudAssessmentAccount).order_by(CloudAssessmentAccount.customer_code, CloudAssessmentAccount.name)
    if customer_codes is not None:
        statement = statement.where(CloudAssessmentAccount.customer_code.in_(customer_codes))
    accounts = (await session.execute(statement)).scalars().all()
    last, last_completed, previous = await latest_scans(session, [account.id for account in accounts])
    now = utc_now()
    return [to_out(account, last.get(account.id), last_completed.get(account.id), now, previous) for account in accounts]


# --- writes -------------------------------------------------------------------------------------


def _encrypt(secret: Dict[str, Any]) -> str:
    try:
        return crypto.encrypt_secret(secret)
    except crypto.CredentialCryptoError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


def _checked_name(name: str) -> str:
    try:
        return check_name(name)
    except ValueError as error:
        raise AccountProblem(str(error)) from error


async def create_account(
    session: AsyncSession,
    customer_code: str,
    body: AccountCreate,
    user: User,
    request: Optional[Request],
) -> AccountOut:
    require_admin(user)
    code = await stored_customer_code(session, customer_code)
    name = _checked_name(body.name)
    config = checked_config(body.provider, body.auth_method, body.config)
    secret = checked_secret(body.auth_method, body.secret)
    if secret is None and SECRET_REQUIRED[body.auth_method]:
        raise AccountProblem("enter the account's credential")
    schedule, hour, weekday = checked_schedule(body.schedule, body.schedule_hour, body.schedule_weekday)
    count = (
        await session.execute(select(func.count()).select_from(CloudAssessmentAccount).where(CloudAssessmentAccount.customer_code == code))
    ).scalar()
    if count >= MAX_ACCOUNTS_PER_CUSTOMER:
        raise AccountProblem(f"a customer has at most {MAX_ACCOUNTS_PER_CUSTOMER} cloud accounts", status_code=409)
    if body.auth_method == "role":
        config["external_id"] = new_external_id()
    if secret and body.auth_method == "service_account_key":
        config.update(gcp_key_details(secret))
    now = utc_now()
    account = CloudAssessmentAccount(
        customer_code=code,
        name=name,
        provider=body.provider,
        auth_method=body.auth_method,
        config=config,
        secret_ciphertext=_encrypt(secret) if secret else None,
        secret_hint=secret_hint(body.auth_method, secret) if secret else None,
        secret_expires_at=to_naive_utc(body.secret_expires_at),
        enabled=body.enabled,
        schedule=schedule,
        schedule_hour=hour,
        schedule_weekday=weekday,
        created_by=user.username,
        updated_by=user.username,
        created_at=now,
        updated_at=now,
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AccountProblem("this customer already has a cloud account with that name", status_code=409) from error
    await session.refresh(account)
    await audit(
        AuditAction.CLOUD_ASSESSMENT_ACCOUNT_CREATE,
        user,
        code,
        "cloud_assessment_account",
        account.id,
        request,
        new=audited(account),
    )
    return to_out(account)


async def update_account(
    session: AsyncSession,
    customer_code: str,
    account_id: int,
    body: AccountUpdate,
    user: User,
    request: Optional[Request],
) -> AccountOut:
    require_admin(user)
    code = await stored_customer_code(session, customer_code)
    account = await get_account(session, code, account_id)
    before = audited(account)
    sent = body.model_fields_set
    secret_changed = False
    if "name" in sent and body.name is not None:
        account.name = _checked_name(body.name)
    if body.config is not None:
        account.config = checked_config(account.provider, account.auth_method, body.config, keep=account.config)
    if body.secret is not None:
        if body.remove_secret:
            raise AccountProblem("send a new credential or remove it, not both")
        secret = checked_secret(account.auth_method, body.secret)
        account.secret_ciphertext = _encrypt(secret)
        account.secret_hint = secret_hint(account.auth_method, secret)
        if account.auth_method == "service_account_key":
            account.config = {**(account.config or {}), **gcp_key_details(secret)}
        secret_changed = True
    elif body.remove_secret:
        if SECRET_REQUIRED[account.auth_method]:
            raise AccountProblem("this account can't do without a credential: send a new one instead")
        account.secret_ciphertext = None
        account.secret_hint = None
        secret_changed = True
    if "secret_expires_at" in sent:
        account.secret_expires_at = to_naive_utc(body.secret_expires_at)
    if "enabled" in sent and body.enabled is not None:
        account.enabled = body.enabled
    if sent & {"schedule", "schedule_hour", "schedule_weekday"}:
        schedule = body.schedule if "schedule" in sent and body.schedule is not None else account.schedule
        hour = body.schedule_hour if "schedule_hour" in sent else account.schedule_hour
        weekday = body.schedule_weekday if "schedule_weekday" in sent else account.schedule_weekday
        account.schedule, account.schedule_hour, account.schedule_weekday = checked_schedule(schedule, hour, weekday)
    after = audited(account)
    if after == before and not secret_changed:
        await session.rollback()
        return await account_out(session, await get_account(session, code, account_id))
    account.updated_by = user.username
    account.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AccountProblem("this customer already has a cloud account with that name", status_code=409) from error
    new_value = {**after, "secret_changed": secret_changed}
    await audit(
        AuditAction.CLOUD_ASSESSMENT_ACCOUNT_UPDATE,
        user,
        code,
        "cloud_assessment_account",
        account_id,
        request,
        old=before,
        new=new_value,
    )
    return await account_out(session, account)


async def delete_findings(session: AsyncSession, scan_ids: List[int]) -> None:
    """Delete these scans' findings in batches, committing each, so no one transaction holds them all."""
    for scan_id in scan_ids:
        while True:
            ids = (
                (
                    await session.execute(
                        select(CloudAssessmentFinding.id).where(CloudAssessmentFinding.scan_id == scan_id).limit(FINDINGS_DELETE_BATCH),
                    )
                )
                .scalars()
                .all()
            )
            if not ids:
                break
            await session.execute(delete(CloudAssessmentFinding).where(CloudAssessmentFinding.id.in_(ids)))
            await session.commit()


async def delete_account(session: AsyncSession, customer_code: str, account_id: int, user: User, request: Optional[Request]) -> int:
    """Delete an account with its scans, findings and reports. A scan still running is stopped first
    (best effort: copilot-prowler forgets a job it isn't asked about after a day anyway)."""
    require_admin(user)
    code = await stored_customer_code(session, customer_code)
    account = await get_account(session, code, account_id)
    before = audited(account)
    scans = (await session.execute(select(CloudAssessmentScan).where(CloudAssessmentScan.account_id == account.id))).scalars().all()
    running_jobs = [scan.runner_job_id for scan in scans if scan.status in ACTIVE_STATUSES and scan.runner_job_id]
    report_keys = [
        (scan.report_bucket, key) for scan in scans for key in (scan.html_object_key, scan.csv_object_key) if scan.report_bucket and key
    ]
    scan_ids = [scan.id for scan in scans]
    await session.commit()
    if running_jobs:
        try:
            async with RunnerClient.from_env() as runner:
                for job_id in running_jobs:
                    await runner.delete_scan(job_id)
        except RunnerError as error:
            logger.warning(f"Cloud assessment: couldn't stop the scans of account {account_id} before deleting it: {error.reason}")
    await delete_findings(session, scan_ids)
    await session.execute(delete(CloudAssessmentScan).where(CloudAssessmentScan.account_id == account_id))
    await session.execute(
        delete(CloudAssessmentAccount).where(CloudAssessmentAccount.id == account_id, CloudAssessmentAccount.customer_code == code),
    )
    await session.commit()
    await reports.delete_objects(report_keys)
    await audit(
        AuditAction.CLOUD_ASSESSMENT_ACCOUNT_DELETE,
        user,
        code,
        "cloud_assessment_account",
        account_id,
        request,
        old={**before, "scans": len(scan_ids)},
    )
    return len(scan_ids)


async def test_connection(
    session: AsyncSession,
    customer_code: str,
    account_id: int,
    user: User,
    request: Optional[Request],
) -> ConnectionTestResponse:
    """Ask copilot-prowler whether the account's credential works, and remember the answer on the
    account. A runner that can't be asked is a 502 or 503 and changes nothing: that says nothing
    about the credential."""
    code = await stored_customer_code(session, customer_code)
    account = await get_account(session, code, account_id)
    try:
        payload = runner_payload(account, account_secret(account))
    except crypto.CredentialCryptoError as error:
        if str(error) == "credential_missing":
            raise AccountProblem(error_message("credential_missing"), status_code=409) from error
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    # Release the database connection: the test can take two minutes.
    await session.close()
    try:
        async with RunnerClient.from_env() as runner:
            verdict = await runner.connection_test(payload)
    except RunnerError as error:
        if error.reason != "refused":
            await audit(
                AuditAction.CLOUD_ASSESSMENT_CONNECTION_TEST,
                user,
                code,
                "cloud_assessment_account",
                account_id,
                request,
                new={"ok": None, "runner": error.reason},
                result=AuditResult.FAILURE,
            )
            raise runner_http_error(error) from error
        verdict = {"ok": False, "code": error.code if error.code else "invalid_request", "prowler_error": None}
    account = await get_account(session, code, account_id)
    account.last_connection_test_at = utc_now()
    account.last_connection_ok = verdict["ok"]
    account.last_connection_error = None if verdict["ok"] else (verdict["code"] or "connection_failed")
    await session.commit()
    await audit(
        AuditAction.CLOUD_ASSESSMENT_CONNECTION_TEST,
        user,
        code,
        "cloud_assessment_account",
        account_id,
        request,
        new={"ok": verdict["ok"], "code": account.last_connection_error, "prowler_error": verdict["prowler_error"]},
        result=AuditResult.SUCCESS if verdict["ok"] else AuditResult.FAILURE,
    )
    return ConnectionTestResponse(
        success=True,
        message="The credentials work" if verdict["ok"] else "The connection test failed",
        ok=verdict["ok"],
        code=account.last_connection_error,
        error_message=error_message(account.last_connection_error),
        prowler_error=verdict["prowler_error"],
        account=await account_out(session, account),
    )


def expiring_soon(account: CloudAssessmentAccount, now: datetime, days: int = 30) -> bool:
    expires = to_naive_utc(account.secret_expires_at)
    return bool(expires and expires - now <= timedelta(days=days))
