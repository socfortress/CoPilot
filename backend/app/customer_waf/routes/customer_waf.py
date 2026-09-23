"""
Customer WAF routes — ``/api/customer_waf`` (#1166).

Configuration of a customer's SOCFortress WAFs (admin to write, admin/analyst to
read) plus read-only views proxied from each WAF.

Every route names its tenant in the path and carries ``verify_customer_code_access``;
routes that also take ``{waf_id}`` resolve it through
``services.get_instance_for_customer``, which refuses a WAF owned by another customer.

Upstream failures come back as 502 (or 404 / 409) with ``{"detail", "reason"}`` —
never 401/403, which the frontend would read as the analyst's own session ending.

Route ordering: every path here has ``{customer_code}`` as its first segment and the
static tails (``/verify``, ``/sites``, …) differ in segment count from the bare
``/{customer_code}/{waf_id}``, so nothing wildcard-shaped can swallow them. Keep it
that way when appending (see CLAUDE.md route ordering).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.customer_waf.schema.customer_waf import WafAction
from app.customer_waf.schema.customer_waf import WafDeleteResponse
from app.customer_waf.schema.customer_waf import WafEventsResponse
from app.customer_waf.schema.customer_waf import WafInstanceCreate
from app.customer_waf.schema.customer_waf import WafInstanceResponse
from app.customer_waf.schema.customer_waf import WafInstancesResponse
from app.customer_waf.schema.customer_waf import WafInstanceUpdate
from app.customer_waf.schema.customer_waf import WafSitesResponse
from app.customer_waf.schema.customer_waf import WafStatsResponse
from app.customer_waf.schema.customer_waf import WafThreatIntelResponse
from app.customer_waf.schema.customer_waf import WafVerifyResponse
from app.customer_waf.services import customer_waf as svc
from app.customer_waf.services.crypto import WafTokenCryptoError
from app.customer_waf.services.crypto import key_configured
from app.customer_waf.utils.universal import WafRequestError
from app.db.db_session import get_db
from app.middleware.customer_access import verify_customer_code_access

customer_waf_router = APIRouter()

_READ = [Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(verify_customer_code_access)]
_WRITE = [Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)]


def _error(e: Exception) -> JSONResponse:
    if isinstance(e, WafRequestError):
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail, "reason": e.reason, "success": False})
    if isinstance(e, WafTokenCryptoError):
        return JSONResponse(status_code=e.status_code, content={"detail": str(e), "reason": "token_crypto", "success": False})
    raise e


async def _verify_quietly(session: AsyncSession, row):
    """Best-effort verify after a save — the save stands even if the WAF is unreachable."""
    try:
        return await svc.verify_instance(session, row)
    except (WafRequestError, WafTokenCryptoError):
        return None


# ── configuration ──────────────────────────────────────────────────────────


@customer_waf_router.get(
    "/{customer_code}",
    response_model=WafInstancesResponse,
    description="List a customer's WAFs (the service token is never returned)",
    dependencies=_READ,
)
async def list_customer_wafs(customer_code: str, session: AsyncSession = Depends(get_db)):
    rows = await svc.list_instances(session, customer_code)
    return WafInstancesResponse(
        instances=[svc.to_schema(r) for r in rows],
        encryption_key_configured=key_configured(),
        success=True,
        message=f"{len(rows)} WAF(s) configured",
    )


@customer_waf_router.post(
    "/{customer_code}",
    response_model=WafInstanceResponse,
    status_code=201,
    description="Add a WAF for a customer and test the connection",
    dependencies=_WRITE,
)
async def create_customer_waf(
    customer_code: str,
    request: WafInstanceCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
):
    try:
        row = await svc.create_instance(session, customer_code, request, getattr(current_user, "id", None))
    except WafTokenCryptoError as e:
        return _error(e)
    verification = await _verify_quietly(session, row)
    return WafInstanceResponse(
        instance=svc.to_schema(row),
        verification=verification,
        warnings=svc.config_warnings(row),
        success=True,
        message="WAF saved" if verification and verification.authenticated else "WAF saved, but the connection test did not pass",
    )


@customer_waf_router.put(
    "/{customer_code}/{waf_id}",
    response_model=WafInstanceResponse,
    description="Update a customer's WAF. A blank service_token keeps the stored one.",
    dependencies=_WRITE,
)
async def update_customer_waf(
    customer_code: str,
    waf_id: int,
    request: WafInstanceUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    try:
        row, connection_changed = await svc.update_instance(session, row, request, getattr(current_user, "id", None))
    except WafTokenCryptoError as e:
        return _error(e)
    verification = await _verify_quietly(session, row) if connection_changed else None
    return WafInstanceResponse(
        instance=svc.to_schema(row),
        verification=verification,
        warnings=svc.config_warnings(row),
        success=True,
        message="WAF updated",
    )


@customer_waf_router.delete(
    "/{customer_code}/{waf_id}",
    response_model=WafDeleteResponse,
    description="Remove a WAF from CoPilot. Revoke its token in the WAF separately.",
    dependencies=_WRITE,
)
async def delete_customer_waf(
    customer_code: str,
    waf_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(AuthHandler().get_current_user),
):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    name, prefix = row.name, row.token_prefix
    await svc.delete_instance(session, row, getattr(current_user, "id", None))
    return WafDeleteResponse(
        success=True,
        message=(
            f"WAF '{name}' removed from CoPilot. Its token ({prefix}) is still valid on the WAF — "
            "revoke it under Service Tokens in the WAF UI."
        ),
    )


# ── WAF-facing ─────────────────────────────────────────────────────────────


@customer_waf_router.post(
    "/{customer_code}/{waf_id}/verify",
    response_model=WafVerifyResponse,
    description="Test the connection and report what the token is allowed to do",
    dependencies=_READ,
)
async def verify_customer_waf(customer_code: str, waf_id: int, session: AsyncSession = Depends(get_db)):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    try:
        verification = await svc.verify_instance(session, row)
    except WafTokenCryptoError as e:
        return _error(e)
    return WafVerifyResponse(
        instance=svc.to_schema(row),
        verification=verification,
        success=verification.authenticated,
        message="Connection OK" if verification.authenticated else (verification.detail or "Connection test failed"),
    )


@customer_waf_router.get(
    "/{customer_code}/{waf_id}/sites",
    response_model=WafSitesResponse,
    description="Sites protected by this WAF",
    dependencies=_READ,
)
async def get_customer_waf_sites(customer_code: str, waf_id: int, session: AsyncSession = Depends(get_db)):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    try:
        sites = await svc.fetch_sites(row)
    except (WafRequestError, WafTokenCryptoError) as e:
        return _error(e)
    return WafSitesResponse(sites=sites, success=True, message=f"{len(sites)} site(s)")


@customer_waf_router.get(
    "/{customer_code}/{waf_id}/events",
    response_model=WafEventsResponse,
    description="WAF events, newest first",
    dependencies=_READ,
)
async def get_customer_waf_events(
    customer_code: str,
    waf_id: int,
    action: Optional[WafAction] = Query(None),
    severity: Optional[str] = Query(None, max_length=20),
    client_ip: Optional[str] = Query(None, max_length=45),
    rule_id: Optional[str] = Query(None, max_length=20),
    site_id: Optional[str] = Query(None, max_length=64),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    params = svc.build_event_params(
        action=action,
        severity=severity,
        client_ip=client_ip,
        rule_id=rule_id,
        site_id=site_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    try:
        events = await svc.fetch_events(row, params)
    except (WafRequestError, WafTokenCryptoError) as e:
        return _error(e)
    return WafEventsResponse(events=events, limit=limit, offset=offset, success=True, message=f"{len(events)} event(s)")


@customer_waf_router.get(
    "/{customer_code}/{waf_id}/stats",
    response_model=WafStatsResponse,
    description="Last-hour totals, block rate, top rules / IPs and the 24h trend",
    dependencies=_READ,
)
async def get_customer_waf_stats(customer_code: str, waf_id: int, session: AsyncSession = Depends(get_db)):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    try:
        stats = await svc.fetch_stats(row)
    except (WafRequestError, WafTokenCryptoError) as e:
        return _error(e)
    return WafStatsResponse(stats=stats, success=True, message="WAF stats retrieved")


@customer_waf_router.get(
    "/{customer_code}/{waf_id}/threat-intel",
    response_model=WafThreatIntelResponse,
    description="Top offending IPs by threat score",
    dependencies=_READ,
)
async def get_customer_waf_threat_intel(customer_code: str, waf_id: int, session: AsyncSession = Depends(get_db)):
    row = await svc.get_instance_for_customer(session, customer_code, waf_id)
    try:
        summary, entries = await svc.fetch_threat_intel(row)
    except (WafRequestError, WafTokenCryptoError) as e:
        return _error(e)
    return WafThreatIntelResponse(summary=summary, entries=entries, success=True, message=f"{len(entries)} offender(s)")
