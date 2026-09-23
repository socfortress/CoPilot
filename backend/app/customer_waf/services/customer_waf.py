"""
Business logic for a customer's SOCFortress WAFs (#1165 / #1166).

Two rules every function here keeps:

- **A WAF id belongs to a tenant.** ``get_instance_for_customer`` is the only way a
  route turns ``{waf_id}`` into a row, and it refuses a row owned by a different
  customer than the one in the path. The path's customer is what
  ``verify_customer_code_access`` authorised, so without this check a scoped analyst
  could reach another tenant's WAF by guessing an id. A mismatch is a 404, not a
  403, so ids can't be enumerated.
- **The token is write-only.** It is encrypted on the way in and only ever decrypted
  inside the transport (``utils/universal.py``). Nothing returned from here carries
  it — ``to_schema`` is the single projection to the API shape.
"""

import ssl
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.customer_waf.schema.customer_waf import WafCapabilities
from app.customer_waf.schema.customer_waf import WafEvent
from app.customer_waf.schema.customer_waf import WafInstance
from app.customer_waf.schema.customer_waf import WafInstanceCreate
from app.customer_waf.schema.customer_waf import WafInstanceUpdate
from app.customer_waf.schema.customer_waf import WafSite
from app.customer_waf.schema.customer_waf import WafStats
from app.customer_waf.schema.customer_waf import WafThreatIntelEntry
from app.customer_waf.schema.customer_waf import WafThreatIntelSummary
from app.customer_waf.schema.customer_waf import WafVerifyResult
from app.customer_waf.services.crypto import display_prefix
from app.customer_waf.services.crypto import encrypt_token
from app.customer_waf.services.crypto import normalize_token
from app.customer_waf.utils.universal import WafRequestError
from app.customer_waf.utils.universal import normalize_api_url
from app.customer_waf.utils.universal import waf_get
from app.db.universal_models import Customers
from app.db.universal_models import CustomerWafInstance

# Mirror of the WAF's built-in role → permission table (waf-platform
# backend/app/core/rbac.py:ROLE_PERMISSIONS). Only used to *describe* what a token can
# do in the UI; the WAF enforces its own table on every request.
WAF_ROLE_PERMISSIONS: Dict[str, set] = {
    "admin": {
        "sites:read",
        "sites:write",
        "sites:delete",
        "rules:read",
        "rules:write",
        "rules:delete",
        "config:read",
        "config:write",
        "logs:read",
        "alerts:read",
        "alerts:write",
        "audit:read",
    },
    "operator": {"rules:read", "rules:write", "logs:read"},
    "viewer": {"sites:read", "rules:read", "config:read", "logs:read", "alerts:read", "audit:read"},
}

# The column is varchar(50); a user with several roles is summarised, not truncated mid-name.
_ROLE_COLUMN_LENGTH = 50


def capabilities_for_roles(roles: List[str]) -> WafCapabilities:
    perms = set().union(*(WAF_ROLE_PERMISSIONS.get(r, set()) for r in roles)) if roles else set()
    return WafCapabilities(
        can_read={"sites:read", "logs:read"} <= perms,
        can_block={"rules:read", "rules:write"} <= perms,
        can_manage_forwarders="config:write" in perms,
    )


def summarize_roles(roles: List[str]) -> Optional[str]:
    if not roles:
        return None
    joined = ",".join(sorted(roles))
    return joined if len(joined) <= _ROLE_COLUMN_LENGTH else joined[: _ROLE_COLUMN_LENGTH - 3] + "..."


def to_schema(row: CustomerWafInstance) -> WafInstance:
    return WafInstance(
        id=row.id,
        customer_code=row.customer_code,
        name=row.name,
        api_url=row.api_url,
        token_prefix=row.token_prefix,
        verify_tls=row.verify_tls,
        has_ca_cert=bool(row.ca_cert_pem),
        enabled=row.enabled,
        last_verified_at=row.last_verified_at,
        last_verified_role=row.last_verified_role,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


# ── validation ─────────────────────────────────────────────────────────────


def _clean_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name must not be blank")
    return name


def _clean_api_url(api_url: str) -> str:
    try:
        return normalize_api_url(api_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _clean_ca_cert(ca_cert_pem: Optional[str]) -> Optional[str]:
    pem = (ca_cert_pem or "").strip()
    if not pem:
        return None
    try:
        ssl.create_default_context(cadata=pem)
    except (ssl.SSLError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"ca_cert_pem is not a valid PEM certificate: {e}")
    return pem


def config_warnings(row: CustomerWafInstance) -> List[str]:
    warnings = []
    if row.api_url.startswith("http://"):
        warnings.append("The API URL uses http:// — the service token is sent in clear text. Prefer the WAF admin UI's https listener.")
    return warnings


# ── persistence ────────────────────────────────────────────────────────────


async def ensure_customer_exists(session: AsyncSession, customer_code: str) -> None:
    result = await session.execute(select(Customers).where(Customers.customer_code == customer_code))
    if result.scalars().first() is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_code} not found")


async def list_all_instances(session: AsyncSession, customer_codes: Optional[List[str]]) -> List[CustomerWafInstance]:
    """WAFs across customers, for the WAF page's pickers. ``None`` = no filter (deployment-wide caller).

    Callers must resolve ``customer_codes`` with ``scoped_customer_codes`` and short-circuit
    on ``[]`` themselves — an empty list here would mean "everything".
    """
    query = select(CustomerWafInstance).order_by(CustomerWafInstance.customer_code, CustomerWafInstance.name)
    if customer_codes is not None:
        query = query.where(CustomerWafInstance.customer_code.in_(customer_codes))
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_instances(session: AsyncSession, customer_code: str) -> List[CustomerWafInstance]:
    result = await session.execute(
        select(CustomerWafInstance).where(CustomerWafInstance.customer_code == customer_code).order_by(CustomerWafInstance.name),
    )
    return list(result.scalars().all())


async def get_instance_for_customer(session: AsyncSession, customer_code: str, waf_id: int) -> CustomerWafInstance:
    row = await session.get(CustomerWafInstance, waf_id)
    if row is None or row.customer_code != customer_code:
        raise HTTPException(status_code=404, detail=f"WAF {waf_id} not found for customer {customer_code}")
    return row


async def _commit_or_conflict(session: AsyncSession, customer_code: str, name: str) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=f"Customer {customer_code} already has a WAF named '{name}'")


async def create_instance(
    session: AsyncSession,
    customer_code: str,
    request: WafInstanceCreate,
    user_id: Optional[int],
) -> CustomerWafInstance:
    await ensure_customer_exists(session, customer_code)
    token = normalize_token(request.service_token)
    row = CustomerWafInstance(
        customer_code=customer_code,
        name=_clean_name(request.name),
        api_url=_clean_api_url(request.api_url),
        service_token_encrypted=encrypt_token(token),
        token_prefix=display_prefix(token),
        verify_tls=request.verify_tls,
        ca_cert_pem=_clean_ca_cert(request.ca_cert_pem),
        enabled=request.enabled,
        created_by=user_id,
        created_at=datetime.utcnow(),
    )
    session.add(row)
    await _commit_or_conflict(session, customer_code, row.name)
    await session.refresh(row)
    logger.info(f"Customer WAF created: id={row.id} customer={customer_code} name={row.name} by user={user_id}")
    return row


async def update_instance(
    session: AsyncSession,
    row: CustomerWafInstance,
    request: WafInstanceUpdate,
    user_id: Optional[int],
) -> Tuple[CustomerWafInstance, bool]:
    """Apply a partial update. Returns ``(row, connection_changed)`` so the caller knows whether to re-verify."""
    connection_changed = False
    if request.name is not None:
        row.name = _clean_name(request.name)
    if request.api_url is not None:
        new_url = _clean_api_url(request.api_url)
        connection_changed |= new_url != row.api_url
        row.api_url = new_url
    # Write-only: blank means "keep the current token".
    if request.service_token is not None and request.service_token.strip():
        token = normalize_token(request.service_token)
        row.service_token_encrypted = encrypt_token(token)
        row.token_prefix = display_prefix(token)
        connection_changed = True
    if request.verify_tls is not None:
        connection_changed |= request.verify_tls != row.verify_tls
        row.verify_tls = request.verify_tls
    if request.ca_cert_pem is not None:
        row.ca_cert_pem = _clean_ca_cert(request.ca_cert_pem)
        connection_changed = True
    if request.enabled is not None:
        row.enabled = request.enabled

    if connection_changed:
        # The cached role described the old connection; don't let the UI keep showing it.
        row.last_verified_at = None
        row.last_verified_role = None
    row.updated_by = user_id
    row.updated_at = datetime.utcnow()
    session.add(row)
    await _commit_or_conflict(session, row.customer_code, row.name)
    await session.refresh(row)
    logger.info(f"Customer WAF updated: id={row.id} customer={row.customer_code} by user={user_id}")
    return row, connection_changed


async def delete_instance(session: AsyncSession, row: CustomerWafInstance, user_id: Optional[int]) -> None:
    await session.delete(row)
    await session.commit()
    logger.info(f"Customer WAF deleted: id={row.id} customer={row.customer_code} name={row.name} by user={user_id}")


# ── WAF-facing ─────────────────────────────────────────────────────────────


async def verify_instance(session: AsyncSession, row: CustomerWafInstance) -> WafVerifyResult:
    """Check the token against the WAF and cache the role on the row.

    ``/users/me`` is the real check (reachability + token + role). ``/health`` is a
    bonus: it sits outside ``/api`` and the admin UI's nginx only proxies ``/api/``, so
    through the recommended https:8080 URL it serves the SPA — a missing health block
    is not a failure.
    """
    try:
        me = await waf_get(row, "/users/me", allow_disabled=True)
    except WafRequestError as e:
        if e.reason in ("not_found", "bad_response"):
            # Something answered, but not a SOCFortress WAF API (wrong host/port, or a WAF too old for service tokens).
            return WafVerifyResult(
                reachable=True,
                authenticated=False,
                reason="not_a_waf",
                detail=f"{row.api_url} answered, but not as a SOCFortress WAF API with service-token support. "
                "Check the URL points at the WAF admin UI (e.g. https://waf-host:8080) and the WAF is up to date.",
            )
        return WafVerifyResult(
            reachable=e.reason not in ("unreachable", "tls_error"),
            authenticated=False,
            reason=e.reason,
            detail=e.detail,
        )

    roles = [r.get("name") for r in (me.get("roles") or []) if isinstance(r, dict) and r.get("name")]
    health = None
    try:
        body = await waf_get(row, "/health", api=False, allow_disabled=True, timeout=5.0)
        health = body if isinstance(body, dict) else None
    except WafRequestError:
        pass

    row.last_verified_at = datetime.utcnow()
    row.last_verified_role = summarize_roles(roles)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    return WafVerifyResult(
        reachable=True,
        authenticated=True,
        waf_user_email=me.get("email"),
        waf_roles=roles,
        capabilities=capabilities_for_roles(roles),
        health=health,
    )


async def fetch_sites(row: CustomerWafInstance) -> List[WafSite]:
    body = await waf_get(row, "/sites/")
    return [
        WafSite(
            id=str(s["id"]),
            name=s.get("name", ""),
            hostname=s.get("hostname", ""),
            upstream_url=s.get("upstream_url", ""),
            is_enabled=bool(s.get("is_enabled")),
            detection_mode=bool(s.get("detection_mode")),
            created_at=s.get("created_at"),
        )
        for s in body or []
    ]


def build_event_params(
    *,
    action: Optional[str],
    severity: Optional[str],
    client_ip: Optional[str],
    rule_id: Optional[str],
    site_id: Optional[str],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    optional = {"action": action, "severity": severity, "client_ip": client_ip, "rule_id": rule_id, "site_id": site_id}
    params.update({k: v for k, v in optional.items() if v})
    if start_time:
        params["start_time"] = _utc_iso(start_time)
    if end_time:
        params["end_time"] = _utc_iso(end_time)
    return params


def _utc_iso(value: datetime) -> str:
    """Always send an explicit offset: the WAF reads a naive timestamp in its own process's
    timezone, so the same query would silently match different windows on different hosts.
    A naive value from our side is taken to be UTC (CoPilot's convention)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


async def fetch_events(row: CustomerWafInstance, params: Dict[str, Any]) -> List[WafEvent]:
    body = await waf_get(row, "/logs/", params=params)
    events = []
    for e in body or []:
        # raw_log (the full Coraza audit record) is deliberately dropped.
        data = {k: v for k, v in e.items() if k in WafEvent.model_fields}
        data["id"] = str(e["id"])
        data["site_id"] = str(e["site_id"]) if e.get("site_id") else None
        data["matched_rules"] = [m for m in (e.get("matched_rules") or []) if isinstance(m, dict)]
        events.append(WafEvent.model_validate(data))
    return events


async def fetch_stats(row: CustomerWafInstance) -> WafStats:
    return WafStats.model_validate(await waf_get(row, "/logs/stats"))


async def fetch_threat_intel(row: CustomerWafInstance) -> Tuple[WafThreatIntelSummary, List[WafThreatIntelEntry]]:
    stats = await waf_get(row, "/threat-intel/stats")
    entries = await waf_get(row, "/threat-intel/")
    summary = WafThreatIntelSummary.model_validate(stats or {"total_ips": 0})
    parsed = []
    for e in entries or []:
        data = dict(e)
        data["top_rules"] = data.get("top_rules") or []
        parsed.append(WafThreatIntelEntry.model_validate(data))
    return summary, parsed


# ── block provenance (#1167) ───────────────────────────────────────────────


async def verify_block_provenance(session: AsyncSession, user, customer_code: str, alert_id: Optional[int], case_id: Optional[int]):
    """Check the caller may cite this alert/case, and that it belongs to the WAF's customer.

    Without the same-customer check an analyst who can see two tenants could block on
    tenant A's WAF "because of" tenant B's alert — and leave a comment on B's alert
    announcing an action taken on A's infrastructure.
    """
    from app.incidents.services.db_operations import get_alert_by_id
    from app.incidents.services.db_operations import get_case_by_id
    from app.middleware.customer_access import enforce_owned_object_access

    if alert_id is not None:
        alert = await get_alert_by_id(alert_id, session, user=user)
        await enforce_owned_object_access(user, alert.customer_code, session, subject=f"alert {alert_id}")
        if alert.customer_code != customer_code:
            raise HTTPException(status_code=400, detail=f"Alert {alert_id} belongs to a different customer than this WAF")
    if case_id is not None:
        case = await get_case_by_id(case_id, session)
        await enforce_owned_object_access(user, case.customer_code, session, subject=f"case {case_id}")
        if case.customer_code != customer_code:
            raise HTTPException(status_code=400, detail=f"Case {case_id} belongs to a different customer than this WAF")


BLOCK_COMMENT_PREFIX = "WAF block: "


async def comment_block_on_alert(session: AsyncSession, alert_id: int, text: str, username: str) -> None:
    """Best-effort reverse link on the alert; the block itself already happened."""
    from app.incidents.schema.db_operations import CommentCreate
    from app.incidents.services.db_operations import create_comment

    try:
        await create_comment(CommentCreate(alert_id=alert_id, comment=f"{BLOCK_COMMENT_PREFIX}{text}", user_name=username), session)
    except Exception as e:
        logger.error(f"WAF block succeeded but the comment on alert {alert_id} failed: {e}")
