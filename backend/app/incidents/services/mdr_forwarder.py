"""
Forward newly-created CoPilot alerts to the SOCFortress MDR server.

When MDR forwarding is enabled (MDR_ENABLED) and a customer has the
"SOCFortress MDR" integration deployed, this module POSTs the alert's indexer
pointers + CoPilot alert ID to the MDR server:

    POST {MDR_SERVER_URL}/api/v1/alerts/copilot
    {
        "collector_uuid":   <MDR_COLLECTOR_UUID>,
        "index_name":       <Wazuh Indexer index name>,
        "index_id":         <Wazuh Indexer document id>,
        "copilot_alert_id": <CoPilot alert id>
    }

The MDR server authenticates the request by the collector UUID (no bearer
token) and then tasks the customer's collector to fetch the authoritative
document from the Wazuh Indexer. Forwarding is best-effort: failures are logged
and never propagate to alert creation.
"""

import os
from typing import Optional

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import IntegrationSubscription

# Name of the customer integration that gates MDR forwarding. Must match the
# integration_service_name stored in the customer_integrations table and the
# catalog entry seeded in app/db/db_populate.py.
MDR_INTEGRATION_NAME = "SOCFortress MDR"

_MDR_TIMEOUT_S = 30.0


def _mdr_config() -> dict:
    """Read global MDR forwarding config from the environment (see settings.py)."""
    return {
        "enabled": os.getenv("MDR_ENABLED", "False").lower() in ("true", "1", "yes"),
        "server_url": os.getenv("MDR_SERVER_URL", "").rstrip("/"),
        # Per-customer COLLECTOR_UUID (integration auth key) takes precedence; this
        # env value is only a fallback for single-tenant CoPilot deployments.
        "collector_uuid_fallback": os.getenv("MDR_COLLECTOR_UUID", ""),
    }


async def get_mdr_collector_uuid(
    customer_code: str,
    session: AsyncSession,
) -> Optional[str]:
    """
    Return the MDR collector UUID for a customer, or None if the customer is not
    an MDR customer.

    Gating: the customer must have the "SOCFortress MDR" integration with
    deployed=True. The collector UUID comes from that integration's COLLECTOR_UUID
    auth key (per-customer); if absent, falls back to the MDR_COLLECTOR_UUID env
    var (single-tenant convenience). Returns None if neither is available.
    """
    result = await session.execute(
        select(CustomerIntegrations)
        .options(
            joinedload(CustomerIntegrations.integration_subscriptions).joinedload(
                IntegrationSubscription.integration_auth_keys,
            ),
        )
        .where(CustomerIntegrations.customer_code == customer_code)
        .where(CustomerIntegrations.integration_service_name == MDR_INTEGRATION_NAME)
        .where(CustomerIntegrations.deployed == True),  # noqa: E712 (SQLModel needs ==)
    )
    integration = result.scalars().unique().first()
    if integration is None:
        return None

    for subscription in integration.integration_subscriptions:
        for auth_key in subscription.integration_auth_keys:
            if auth_key.auth_key_name == "COLLECTOR_UUID" and auth_key.auth_value:
                return auth_key.auth_value

    # Deployed but no per-customer COLLECTOR_UUID stored — fall back to env.
    return _mdr_config()["collector_uuid_fallback"] or None


async def forward_alert_to_mdr(
    customer_code: str,
    alert_payload: CreatedAlertPayload,
    session: AsyncSession,
) -> None:
    """
    Forward a freshly-created alert to the MDR server (best-effort, never raises).

    Args:
        customer_code: The customer the alert belongs to.
        alert_payload: The created alert payload (carries alert_id + index pointers).
        session: Async DB session, used to check the customer's integration.
    """
    try:
        config = _mdr_config()

        if not config["enabled"]:
            return

        if not config["server_url"]:
            logger.warning(
                "MDR_ENABLED is set but MDR_SERVER_URL is not configured — "
                "skipping MDR forward",
            )
            return

        # Need indexer pointers to forward; threshold/aggregation alerts that have
        # no individual document cannot be fetched by the collector.
        if not alert_payload.index_name or not alert_payload.index_id:
            logger.info(
                f"Skipping MDR forward for customer {customer_code}: alert has no "
                f"index_name/index_id (likely a threshold/aggregation alert)",
            )
            return

        if alert_payload.alert_id is None:
            logger.warning(
                f"Skipping MDR forward for customer {customer_code}: alert_id is not set",
            )
            return

        # Gate: customer must have the SOCFortress MDR integration deployed. The
        # collector UUID is resolved per-customer (auth key) with env fallback.
        collector_uuid = await get_mdr_collector_uuid(customer_code, session)
        if not collector_uuid:
            # Not an MDR customer (or deployed without a collector UUID) — nothing to do.
            return

        url = f"{config['server_url']}/api/v1/alerts/copilot"
        body = {
            "collector_uuid": collector_uuid,
            "index_name": alert_payload.index_name,
            "index_id": alert_payload.index_id,
            "copilot_alert_id": alert_payload.alert_id,
        }

        logger.info(
            f"Forwarding CoPilot alert {alert_payload.alert_id} (customer {customer_code}) "
            f"to MDR at {url}",
        )

        async with httpx.AsyncClient(timeout=_MDR_TIMEOUT_S) as client:
            response = await client.post(url, json=body)

        if response.status_code >= 400:
            logger.error(
                f"MDR forward failed for alert {alert_payload.alert_id} "
                f"(HTTP {response.status_code}): {response.text[:300]}",
            )
            return

        logger.info(
            f"MDR forward accepted for alert {alert_payload.alert_id}: "
            f"{response.text[:200]}",
        )
    except Exception as e:
        # Best-effort: never let MDR forwarding break alert creation.
        logger.error(f"MDR forward errored (non-fatal): {e!r}")
