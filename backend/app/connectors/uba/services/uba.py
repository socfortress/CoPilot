"""
SOCFortress UBA services: one function per UBA endpoint, keyed by the customer
code (UBA's tenant). Tenancy is the routes' job (``verify_customer_code_access``);
UBA checks its API key's tenants again and answers 404 outside them.
"""

from typing import Any
from typing import Dict
from typing import Optional

from app.connectors.uba.schema.uba import UbaAvailabilityResponse
from app.connectors.uba.schema.uba import UbaBacktestRequest
from app.connectors.uba.schema.uba import UbaCustomerStatusResponse
from app.connectors.uba.schema.uba import UbaFeedbackRequest
from app.connectors.uba.schema.uba import UbaResponse
from app.connectors.uba.schema.uba import UbaScoreRequest
from app.connectors.uba.schema.uba import UbaSuppressionRequest
from app.connectors.uba.schema.uba import UbaTenantStatus
from app.connectors.uba.utils.universal import get_uba_attributes
from app.connectors.uba.utils.universal import path_segment
from app.connectors.uba.utils.universal import uba_request


def _tenant(customer_code: str) -> str:
    return f"/v1/tenants/{path_segment(customer_code)}"


async def get_availability() -> UbaAvailabilityResponse:
    """Whether the UI should offer UBA at all: the connector row only, UBA is not called."""
    attributes = await get_uba_attributes()
    if attributes is None:
        return UbaAvailabilityResponse(success=True, message="SOCFortress UBA connector is not installed", configured=False, verified=False)
    configured = bool((attributes.get("connector_url") or "").strip() and (attributes.get("connector_api_key") or "").strip())
    verified = configured and bool(attributes.get("connector_verified"))
    return UbaAvailabilityResponse(
        success=True,
        message="SOCFortress UBA connector is verified" if verified else "SOCFortress UBA connector is not verified",
        configured=configured,
        verified=verified,
    )


async def get_customer_status(customer_code: str) -> UbaCustomerStatusResponse:
    """UBA's status for one customer: worker lag, alerts and signals in 24 h, open alerts."""
    body = await uba_request("GET", "/v1/status")
    row = next((t for t in body.get("tenants", []) if t.get("tenant") == customer_code), None)
    return UbaCustomerStatusResponse(
        success=True,
        message="UBA status" if row else f"SOCFortress UBA has no data for {customer_code}",
        version=body.get("version", ""),
        status=UbaTenantStatus(**row) if row else None,
    )


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> UbaResponse:
    return UbaResponse(**await uba_request("GET", path, params=params))


async def list_entities(customer_code: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/entities", params)


async def get_entity(customer_code: str, entity_key: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/entities/{path_segment(entity_key)}")


async def get_entity_risk_history(customer_code: str, entity_key: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/entities/{path_segment(entity_key)}/risk-history", params)


async def get_entity_timeline(customer_code: str, entity_key: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/entities/{path_segment(entity_key)}/timeline", params)


async def list_signals(customer_code: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/signals", params)


async def get_signal_evidence(customer_code: str, signal_id: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/signals/{path_segment(signal_id)}/evidence")


async def list_alerts(customer_code: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/alerts", params)


async def get_alert(customer_code: str, alert_id: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/alerts/{path_segment(alert_id)}")


async def submit_feedback(customer_code: str, alert_id: str, body: UbaFeedbackRequest, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/alerts/{path_segment(alert_id)}/feedback"
    return UbaResponse(**await uba_request("POST", path, json=body.model_dump(), actor=actor))


async def list_suppressions(customer_code: str, **params: Any) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/suppressions", params)


async def add_suppressions(customer_code: str, body: UbaSuppressionRequest, actor: str) -> UbaResponse:
    return UbaResponse(**await uba_request("POST", f"{_tenant(customer_code)}/suppressions", json=body.model_dump(), actor=actor))


async def remove_suppressions(customer_code: str, entity_key: str, rule_id: Optional[str], actor: str) -> UbaResponse:
    params = {"entity_key": entity_key, "rule_id": rule_id}
    return UbaResponse(**await uba_request("DELETE", f"{_tenant(customer_code)}/suppressions", params=params, actor=actor))


async def list_identity_sources(customer_code: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/identity-sources")


async def test_identity_source(customer_code: str, source_id: str, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/identity-sources/{path_segment(source_id)}/test"
    return UbaResponse(**await uba_request("POST", path, actor=actor))


async def sync_identity_source(customer_code: str, source_id: str, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/identity-sources/{path_segment(source_id)}/sync"
    return UbaResponse(**await uba_request("POST", path, actor=actor))


async def list_rule_catalog() -> UbaResponse:
    """UBA's rules (id, name, detector, score, MITRE); not per tenant, so the caller's route checks access."""
    rules = await uba_request("GET", "/v1/rules")
    return UbaResponse(rules=rules if isinstance(rules, list) else [])


async def create_backtest(customer_code: str, body: UbaBacktestRequest, actor: str) -> UbaResponse:
    payload = body.model_dump(exclude_none=True)
    return UbaResponse(**await uba_request("POST", f"{_tenant(customer_code)}/backtests", json=payload, actor=actor))


async def list_backtests(customer_code: str, limit: int) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/backtests", {"limit": limit})


async def get_backtest(customer_code: str, job_id: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/backtests/{path_segment(job_id)}")


async def cancel_backtest(customer_code: str, job_id: str, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/backtests/{path_segment(job_id)}/cancel"
    return UbaResponse(**await uba_request("POST", path, actor=actor))


async def get_rule_stats(customer_code: str, since: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/rules/stats", {"since": since})


async def get_native_overrides(customer_code: str, integration: str) -> UbaResponse:
    return await _get(f"{_tenant(customer_code)}/native-overrides", {"integration": integration})


async def set_native_override(customer_code: str, rule_id: str, body: UbaScoreRequest, integration: str, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/native-overrides/{path_segment(rule_id)}"
    return UbaResponse(**await uba_request("PUT", path, params={"integration": integration}, json=body.model_dump(), actor=actor))


async def delete_native_override(customer_code: str, rule_id: str, integration: str, actor: str) -> UbaResponse:
    path = f"{_tenant(customer_code)}/native-overrides/{path_segment(rule_id)}"
    return UbaResponse(**await uba_request("DELETE", path, params={"integration": integration}, actor=actor))
