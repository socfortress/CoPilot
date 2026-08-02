"""Resend connector verification.

Backs the Verify button on the Connectors page, the same mechanism every other
connector uses (`ConnectorServices.verify_connector_by_id` → `service_map` →
`verify_authentication`).

**The important subtlety: a valid key can answer 401.**

Resend supports restricted, send-only API keys — the recommended shape for a
service that only ever sends mail, which is exactly what CoPilot does. Such a
key authenticates fine but is refused on management endpoints:

    valid, send-only  ->  401  {"name": "restricted_api_key"}
    invalid           ->  400  {"name": "validation_error"}

So a naive "200 means healthy" check reports a correctly-configured production
key as broken. Verification treats `restricted_api_key` as success: the key was
recognised, it simply lacks scope for the endpoint we probed.

We probe `GET /domains` rather than sending mail. A send would consume the
deployment's shared monthly quota (1,000 on the free tier, across every
customer) and needs a recipient — verification should be free and side-effect
free. To confirm delivery actually works, use the per-route "Send test" button,
which sends through the real path.
"""

from typing import Any
from typing import Dict

import httpx
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

_VERIFY_TIMEOUT_S = 15.0

#: Resend's error name for a key that is valid but scoped to sending only.
_RESTRICTED_KEY_ERROR = "restricted_api_key"


async def verify_resend_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Probe Resend with the stored API key.

    Returns the ``{"connectionSuccessful": bool, "message": str}`` shape
    ``verify_connector_by_id`` expects.
    """
    base_url = (attributes.get("connector_url") or "https://api.resend.com").rstrip("/")
    api_key = attributes.get("connector_api_key") or ""

    if not api_key:
        return {
            "connectionSuccessful": False,
            "message": "No API key set on the Resend connector.",
        }

    logger.info(f"Verifying the Resend connection to {base_url}")
    try:
        async with httpx.AsyncClient(timeout=_VERIFY_TIMEOUT_S) as client:
            response = await client.get(
                f"{base_url}/domains",
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except Exception as e:  # noqa: BLE001 — verification never raises
        logger.error(f"Connection to {base_url} failed with error: {e}")
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {base_url} failed: {type(e).__name__}: {e}",
        }

    if response.status_code == 200:
        # Full-access key. Report the verified-domain count, because "the key
        # works but you have no verified domain" is the next thing that bites —
        # sends are then limited to the account owner's own address.
        try:
            domains = response.json().get("data", []) or []
        except ValueError:
            domains = []
        verified = [d for d in domains if str(d.get("status", "")).lower() == "verified"]
        if verified:
            names = ", ".join(str(d.get("name")) for d in verified[:3])
            return {
                "connectionSuccessful": True,
                "message": f"Resend connection successful. Verified sending domain(s): {names}.",
            }
        return {
            "connectionSuccessful": True,
            "message": (
                "Resend connection successful, but no verified sending domain was found. "
                "Until a domain is verified, mail can only be sent to the account owner's address."
            ),
        }

    error_name = ""
    error_message = ""
    try:
        body = response.json()
        error_name = str(body.get("name") or "")
        error_message = str(body.get("message") or "")
    except ValueError:
        error_message = response.text[:200]

    if error_name == _RESTRICTED_KEY_ERROR:
        # The key authenticated; it just isn't scoped for this endpoint. That is
        # a correct, and arguably preferable, configuration for CoPilot.
        return {
            "connectionSuccessful": True,
            "message": (
                "Resend connection successful (send-only restricted key). "
                "Sending works; management endpoints are not accessible with this key."
            ),
        }

    logger.error(f"Connection to {base_url} failed with status {response.status_code}: {error_message}")
    return {
        "connectionSuccessful": False,
        "message": f"Resend rejected the API key ({response.status_code}): {error_message or 'no detail returned'}",
    }


async def verify_resend_connection(connector_name: str = "Resend") -> Dict[str, Any]:
    """Verify the Resend connector using its stored credentials."""
    logger.info("Verifying Resend connection")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Resend connector found in the database")
        return {
            "connectionSuccessful": False,
            "message": "No Resend connector found in the database.",
        }
    return await verify_resend_credentials(attributes)
