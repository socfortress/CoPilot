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
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.uba.schema.provision import UbaProvisionRequest
from app.connectors.uba.schema.provision import UbaProvisionResponse
from app.connectors.uba.schema.provision import UbaProvisionStatusResponse
from app.connectors.uba.schema.uba import UbaAlertThresholdRequest
from app.connectors.uba.schema.uba import UbaAvailabilityResponse
from app.connectors.uba.schema.uba import UbaBacktestRequest
from app.connectors.uba.schema.uba import UbaCustomerStatusResponse
from app.connectors.uba.schema.uba import UbaFeedbackRequest
from app.connectors.uba.schema.uba import UbaIdentityMergeRequest
from app.connectors.uba.schema.uba import UbaResponse
from app.connectors.uba.schema.uba import UbaRuleSettingRequest
from app.connectors.uba.schema.uba import UbaScoreRequest
from app.connectors.uba.schema.uba import UbaSuppressionRequest
from app.connectors.uba.services import provision as provisioning
from app.connectors.uba.services import uba as svc
from app.connectors.uba.utils.universal import UbaRequestError
from app.db.db_session import get_db
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
    "/{customer_code}/identities/review",
    response_model=UbaResponse,
    description="Identity review: merge candidates from directory syncs, unmatched accounts with recent findings, recent merges",
    dependencies=_READ,
)
async def get_identity_review(customer_code: str, include_reviewed: bool = False):
    return await _call(svc.get_identity_review(customer_code, include_reviewed))


@uba_router.get(
    "/{customer_code}/identities",
    response_model=UbaResponse,
    description="Identities by name or alias (merge targets), directory users first",
    dependencies=_READ,
)
async def search_identities(customer_code: str, q: str = Query(..., min_length=2, max_length=200)):
    return await _call(svc.search_identities(customer_code, q))


@uba_router.post(
    "/{customer_code}/identities/merge",
    response_model=UbaResponse,
    description="Merge one identity into another (admin; cannot be undone). Body: identity_id, into",
    dependencies=_ADMIN,
)
async def merge_identity(
    customer_code: str,
    body: UbaIdentityMergeRequest,
    identity_id: str = Query(..., min_length=1, max_length=64),
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.merge_identity(customer_code, identity_id, body, current_user.username))


@uba_router.post(
    "/{customer_code}/identities/reviewed",
    response_model=UbaResponse,
    description="Mark an unmatched account reviewed (kept as it is), or put it back with reviewed=false (admin)",
    dependencies=_ADMIN,
)
async def mark_identity_reviewed(
    customer_code: str,
    identity_id: str = Query(..., min_length=1, max_length=64),
    reviewed: bool = True,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.mark_identity_reviewed(customer_code, identity_id, reviewed, current_user.username))


@uba_router.post(
    "/{customer_code}/identity-candidates/{candidate_id}/dismiss",
    response_model=UbaResponse,
    description="Not the same person: the pair is not suggested again (admin)",
    dependencies=_ADMIN,
)
async def dismiss_merge_candidate(
    customer_code: str,
    candidate_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.dismiss_merge_candidate(customer_code, candidate_id, current_user.username))


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
    "/{customer_code}/about",
    response_model=UbaResponse,
    description="What UBA is, how its risk adds up and what each rule means, for people new to it",
    dependencies=_READ,
)
async def get_about(customer_code: str):
    return await _call(svc.get_about())


@uba_router.get(
    "/{customer_code}/rules/catalog",
    response_model=UbaResponse,
    description="UBA's rules (id, name, detector, score, MITRE); the customer code only checks access",
    dependencies=_READ,
)
async def list_rule_catalog(customer_code: str):
    return await _call(svc.list_rule_catalog())


@uba_router.post(
    "/{customer_code}/backtests",
    response_model=UbaResponse,
    description="Queue a backtest: what UBA's rules would have found over recent history (nothing is alerted)",
    dependencies=_READ,
)
async def create_backtest(
    customer_code: str,
    body: UbaBacktestRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.create_backtest(customer_code, body, current_user.username))


@uba_router.get("/{customer_code}/backtests", response_model=UbaResponse, dependencies=_READ)
async def list_backtests(customer_code: str, limit: int = Query(20, ge=1, le=100)):
    return await _call(svc.list_backtests(customer_code, limit))


@uba_router.get("/{customer_code}/backtests/{job_id}", response_model=UbaResponse, dependencies=_READ)
async def get_backtest(customer_code: str, job_id: str):
    return await _call(svc.get_backtest(customer_code, job_id))


@uba_router.post("/{customer_code}/backtests/{job_id}/cancel", response_model=UbaResponse, dependencies=_READ)
async def cancel_backtest(
    customer_code: str,
    job_id: str,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.cancel_backtest(customer_code, job_id, current_user.username))


@uba_router.get(
    "/{customer_code}/rules/stats",
    response_model=UbaResponse,
    description="What each UBA rule found for this customer",
    dependencies=_READ,
)
async def get_rule_stats(customer_code: str, since: str = Query("24h", description="ISO time or duration")):
    return await _call(svc.get_rule_stats(customer_code, since))


@uba_router.get(
    "/{customer_code}/rule-settings",
    response_model=UbaResponse,
    description="Every UBA rule as it applies to this customer (on or off, points) and its alert threshold, with who changed them",
    dependencies=_READ,
)
async def get_rule_settings(customer_code: str):
    return await _call(svc.get_rule_settings(customer_code))


@uba_router.put(
    "/{customer_code}/rule-settings/{rule_id}",
    response_model=UbaResponse,
    description="Turn a UBA rule off or on, or give it other points, for this customer (admin)",
    dependencies=_ADMIN,
)
async def set_rule_setting(
    customer_code: str,
    rule_id: str,
    body: UbaRuleSettingRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.set_rule_setting(customer_code, rule_id, body, current_user.username))


@uba_router.delete(
    "/{customer_code}/rule-settings/{rule_id}",
    response_model=UbaResponse,
    description="Back to the built-in setting of a UBA rule for this customer (admin)",
    dependencies=_ADMIN,
)
async def reset_rule_setting(customer_code: str, rule_id: str, current_user: User = Depends(AuthHandler().get_current_user)):
    return await _call(svc.reset_rule_setting(customer_code, rule_id, current_user.username))


@uba_router.put(
    "/{customer_code}/risk-policy",
    response_model=UbaResponse,
    description="This customer's UBA alert threshold (admin)",
    dependencies=_ADMIN,
)
async def set_alert_threshold(
    customer_code: str,
    body: UbaAlertThresholdRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
):
    return await _call(svc.set_alert_threshold(customer_code, body, current_user.username))


@uba_router.delete(
    "/{customer_code}/risk-policy",
    response_model=UbaResponse,
    description="Back to UBA's built-in alert threshold for this customer (admin)",
    dependencies=_ADMIN,
)
async def reset_alert_threshold(customer_code: str, current_user: User = Depends(AuthHandler().get_current_user)):
    return await _call(svc.reset_alert_threshold(customer_code, current_user.username))


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


@uba_router.get(
    "/{customer_code}/provisioning",
    response_model=UbaProvisionStatusResponse,
    description="Whether UBA is set up for this customer, its onboarding progress, and the streams provisioning would use",
    dependencies=_ADMIN,
)
async def get_provisioning(customer_code: str, session: AsyncSession = Depends(get_db)):
    return await _call(provisioning.get_provisioning_status(customer_code, session))


@uba_router.post(
    "/{customer_code}/provision",
    response_model=UbaProvisionResponse,
    description=(
        "Set UBA up for this customer: register it with UBA (history replay, then live), create the Graylog "
        "UBA FEED streams, routing pipelines and output next to its Wazuh and Office365 streams, and the UBA "
        "ALERTS input and stream. Optionally deploys UBA's Wazuh rules and restarts the manager. Safe to run again."
    ),
    dependencies=_ADMIN,
)
async def provision(customer_code: str, request: UbaProvisionRequest, session: AsyncSession = Depends(get_db)):
    return await _call(provisioning.provision_uba(customer_code, request, session))
