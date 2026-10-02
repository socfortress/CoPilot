"""
SOCFortress UBA routes: ``/api/uba``.

Every route but ``/availability`` names its tenant in the path and carries
``verify_customer_code_access``. Reads are admin/analyst; suppressions and
verdicts are analyst actions; native rule scores (tuning risk for a whole
customer) and identity source test/sync (a customer's directory credentials) are
admin only. The caller's username goes to UBA as ``X-UBA-Actor``.

Upstream failures come back as ``{"detail", "reason", "success": false}`` with 502
(or 404 / 409 / 422), never 401/403, which the frontend reads as the analyst's own
session ending (see ``utils/universal.py``).

Entity keys (``upn:jane@contoso.com``, ``windows-demo\\jdoe``, identity ids) travel
as the ``entity_key`` query parameter rather than a path segment. Route ordering:
``/availability`` is the only path without ``{customer_code}`` and is declared first.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from fastapi.responses import JSONResponse

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.uba.schema.uba import UbaAvailabilityResponse
from app.connectors.uba.schema.uba import UbaCustomerStatusResponse
from app.connectors.uba.schema.uba import UbaFeedbackRequest
from app.connectors.uba.schema.uba import UbaResponse
from app.connectors.uba.schema.uba import UbaScoreRequest
from app.connectors.uba.schema.uba import UbaSuppressionRequest
from app.connectors.uba.services import uba as svc
from app.connectors.uba.utils.universal import UbaRequestError
from app.middleware.customer_access import verify_customer_code_access

uba_router = APIRouter()

_READ = [Security(AuthHandler().require_any_scope("admin", "analyst")), Depends(verify_customer_code_access)]
_ADMIN = [Security(AuthHandler().require_any_scope("admin")), Depends(verify_customer_code_access)]


def _error(e: UbaRequestError) -> JSONResponse:
    return JSONResponse(status_code=e.status_code, content={"detail": e.detail, "reason": e.reason, "success": False})


async def _call(awaitable):
    try:
        return await awaitable
    except UbaRequestError as e:
        return _error(e)


@uba_router.get(
    "/availability",
    response_model=UbaAvailabilityResponse,
    description="Whether the SOCFortress UBA connector is configured and verified. Reads the connector row only; never calls UBA.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_uba_availability() -> UbaAvailabilityResponse:
    return await svc.get_availability()


@uba_router.get(
    "/{customer_code}/status",
    response_model=UbaCustomerStatusResponse,
    description="UBA for this customer: worker lag, alerts and signals in the last 24 h, open alerts",
    dependencies=_READ,
)
async def get_status(customer_code: str):
    return await _call(svc.get_customer_status(customer_code))


@uba_router.get(
    "/{customer_code}/entities",
    response_model=UbaResponse,
    description="Users, hosts and addresses ranked by current risk (last 14 days, decayed now). native=false ranks by UBA's own findings.",
    dependencies=_READ,
)
async def list_entities(
    customer_code: str,
    entity_type: Optional[str] = Query(None, description="actor | target | host | src_ip"),
    q: Optional[str] = Query(None, max_length=200, description="Substring of the entity name or key"),
    min_risk: float = Query(0.0, ge=0),
    native: bool = Query(True, description="false: leave native alert (Wazuh rule) risk out of the ranking"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    return await _call(
        svc.list_entities(
            customer_code,
            entity_type=entity_type,
            q=q,
            min_risk=min_risk,
            native=str(native).lower(),
            page=page,
            page_size=page_size,
        ),
    )


@uba_router.get(
    "/{customer_code}/entity",
    response_model=UbaResponse,
    description="One entity: current risk by rule, identity and aliases, recent alerts, suppressions",
    dependencies=_READ,
)
async def get_entity(customer_code: str, entity_key: str = Query(..., min_length=1, max_length=512)):
    return await _call(svc.get_entity(customer_code, entity_key))


@uba_router.get(
    "/{customer_code}/entity/risk-history",
    response_model=UbaResponse,
    description="The entity's risk over time, its native part, and the findings and alerts that moved it",
    dependencies=_READ,
)
async def get_entity_risk_history(
    customer_code: str,
    entity_key: str = Query(..., min_length=1, max_length=512),
    since: Optional[str] = Query(None, description="ISO time or duration (default 14d, at most 30d)"),
    step: str = Query("1h", pattern="^(15m|1h|6h|1d)$"),
):
    return await _call(svc.get_entity_risk_history(customer_code, entity_key, since=since, step=step))


@uba_router.get(
    "/{customer_code}/entity/timeline",
    response_model=UbaResponse,
    description="The entity's signals, newest first, including suppressed findings and native alert contributions",
    dependencies=_READ,
)
async def get_entity_timeline(
    customer_code: str,
    entity_key: str = Query(..., min_length=1, max_length=512),
    since: Optional[str] = Query(None, description="ISO time or duration (default 14d)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    return await _call(svc.get_entity_timeline(customer_code, entity_key, since=since, page=page, page_size=page_size))


@uba_router.get("/{customer_code}/signals", response_model=UbaResponse, dependencies=_READ)
async def list_signals(
    customer_code: str,
    rule_id: Optional[str] = None,
    entity_key: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO time or duration (default 24h)"),
    until: Optional[str] = None,
    include_native: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    return await _call(
        svc.list_signals(
            customer_code,
            rule_id=rule_id,
            entity_key=entity_key,
            since=since,
            until=until,
            include_native=str(include_native).lower(),
            page=page,
            page_size=page_size,
        ),
    )


@uba_router.get("/{customer_code}/alerts", response_model=UbaResponse, description="UBA alerts, newest first", dependencies=_READ)
async def list_alerts(
    customer_code: str,
    status: Optional[str] = Query(None, pattern="^(open|closed)$", description="open = no verdict yet"),
    entity_key: Optional[str] = None,
    since: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    return await _call(svc.list_alerts(customer_code, status=status, entity_key=entity_key, since=since, page=page, page_size=page_size))


@uba_router.get(
    "/{customer_code}/alerts/{alert_id}",
    response_model=UbaResponse,
    description="A UBA alert with the signals it was made of and its updates",
    dependencies=_READ,
)
async def get_alert(customer_code: str, alert_id: str):
    return await _call(svc.get_alert(customer_code, alert_id))


@uba_router.post(
    "/{customer_code}/alerts/{alert_id}/feedback",
    response_model=UbaResponse,
    description="An analyst's verdict. FALSE_POSITIVE suppresses the alert's rules for the entity (like closing its incident alert as a false positive).",
    dependencies=_READ,
)
async def submit_feedback(
    customer_code: str,
    alert_id: str,
    body: UbaFeedbackRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.submit_feedback(customer_code, alert_id, body, current_user.username))


@uba_router.get("/{customer_code}/suppressions", response_model=UbaResponse, dependencies=_READ)
async def list_suppressions(customer_code: str, entity_key: Optional[str] = None, include_expired: bool = False):
    return await _call(svc.list_suppressions(customer_code, entity_key=entity_key, include_expired=str(include_expired).lower()))


@uba_router.post(
    "/{customer_code}/suppressions",
    response_model=UbaResponse,
    description="Suppress rules for an entity: their findings are kept but add no risk",
    dependencies=_READ,
)
async def add_suppressions(
    customer_code: str,
    body: UbaSuppressionRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.add_suppressions(customer_code, body, current_user.username))


@uba_router.delete("/{customer_code}/suppressions", response_model=UbaResponse, dependencies=_READ)
async def remove_suppressions(
    customer_code: str,
    entity_key: str = Query(..., min_length=1, max_length=512),
    rule_id: Optional[str] = Query(None, description="Omit to remove all of the entity's suppressions"),
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.remove_suppressions(customer_code, entity_key, rule_id, current_user.username))


@uba_router.get(
    "/{customer_code}/signals/{signal_id}/evidence",
    response_model=UbaResponse,
    description="The source events behind a UBA finding, fetched by UBA from the indexer",
    dependencies=_READ,
)
async def get_signal_evidence(customer_code: str, signal_id: str):
    return await _call(svc.get_signal_evidence(customer_code, signal_id))


@uba_router.get(
    "/{customer_code}/identity-sources",
    response_model=UbaResponse,
    description="Directory syncs (Entra ID) of this customer and how their last run went; never the secret",
    dependencies=_READ,
)
async def list_identity_sources(customer_code: str):
    return await _call(svc.list_identity_sources(customer_code))


@uba_router.post(
    "/{customer_code}/identity-sources/{source_id}/test",
    response_model=UbaResponse,
    description="Sign in to the directory and check each permission; the result names a missing one",
    dependencies=_ADMIN,
)
async def test_identity_source(
    customer_code: str,
    source_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.test_identity_source(customer_code, source_id, current_user.username))


@uba_router.post(
    "/{customer_code}/identity-sources/{source_id}/sync",
    response_model=UbaResponse,
    description="Queue a directory sync; UBA's worker runs it within about a minute",
    dependencies=_ADMIN,
)
async def sync_identity_source(
    customer_code: str,
    source_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.sync_identity_source(customer_code, source_id, current_user.username))


@uba_router.get(
    "/{customer_code}/rules/stats",
    response_model=UbaResponse,
    description="What each UBA rule found for this customer",
    dependencies=_READ,
)
async def get_rule_stats(customer_code: str, since: str = Query("24h", description="ISO time or duration")):
    return await _call(svc.get_rule_stats(customer_code, since))


@uba_router.get(
    "/{customer_code}/native-overrides",
    response_model=UbaResponse,
    description="Per-customer risk score of native alert rules (e.g. Wazuh rule id -> score)",
    dependencies=_READ,
)
async def get_native_overrides(customer_code: str, integration: str = "wazuh"):
    return await _call(svc.get_native_overrides(customer_code, integration))


@uba_router.put("/{customer_code}/native-overrides/{rule_id}", response_model=UbaResponse, dependencies=_ADMIN)
async def set_native_override(
    customer_code: str,
    rule_id: str,
    body: UbaScoreRequest,
    integration: str = "wazuh",
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.set_native_override(customer_code, rule_id, body, integration, current_user.username))


@uba_router.delete("/{customer_code}/native-overrides/{rule_id}", response_model=UbaResponse, dependencies=_ADMIN)
async def delete_native_override(
    customer_code: str,
    rule_id: str,
    integration: str = "wazuh",
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.delete_native_override(customer_code, rule_id, integration, current_user.username))
