"""
SOCFortress UBA transport.

CoPilot is the analyst UI for SOCFortress UBA (user behavior analytics,
https://github.com/socfortress/socfortress-uba): entities ranked by risk, their
signals and alerts, suppressions and verdicts. Everything goes through
`uba_request`, which calls the UBA API (`/v1/...`) with the connector's API key.

Rules this module exists to enforce:

- **The key is a UBA API key** (`uba_…`, created with `uba-admin api-keys create
  --name copilot --scope write`), sent as `x-api-key`. The analyst behind a call
  is sent as `X-UBA-Actor` so UBA records who suppressed or judged what.
- **A UBA 401/403 is never a CoPilot 401/403.** The frontend treats a 401 from
  our own API as the analyst's session ending (`frontend/src/api/session-expiry.ts`),
  so upstream auth failures come back as **502** with a `reason` (`key_rejected`,
  `insufficient_scope`), like the Customer WAF routes. A missing connector is 409.
- **TLS is verified.** UBA runs over plain HTTP on the private network next to CoPilot
  (e.g. the Docker bridge) or behind HTTPS with a certificate CoPilot trusts.
- **UBA answers 404 for another tenant's data** (the key may be scoped to a subset
  of customers); that stays a 404.
"""

from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import quote

import httpx
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

UBA_CONNECTOR_NAME = "SOCFortress UBA"
DEFAULT_TIMEOUT = 20.0


class UbaRequestError(Exception):
    """A UBA call that failed; routes turn it into ``{"detail", "reason", "success": false}``."""

    def __init__(self, reason: str, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.status_code = status_code


def normalize_base_url(connector_url: str) -> str:
    """The UBA API root: operators may paste it with or without a trailing ``/v1``."""
    base = (connector_url or "").strip().rstrip("/")
    return base[: -len("/v1")] if base.endswith("/v1") else base


def path_segment(value: str) -> str:
    """Encode one path segment (entity keys hold ``\\``, ``:`` and ``@``)."""
    return quote(value, safe="")


async def get_uba_attributes() -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        return await get_connector_info_from_db(UBA_CONNECTOR_NAME, session)


def _upstream_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:  # FastAPI validation errors
        first = detail[0]
        return f"{'.'.join(str(p) for p in first.get('loc', []))}: {first.get('msg', '')}"
    return ""


async def uba_request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
    actor: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """Call the UBA API and return its decoded JSON body, or raise ``UbaRequestError``.

    ``path`` starts with ``/v1/``. ``None`` values in ``params`` are dropped.
    """
    attributes = attributes if attributes is not None else await get_uba_attributes()
    if attributes is None:
        raise UbaRequestError("not_configured", f"No {UBA_CONNECTOR_NAME} connector found in the database", 409)
    base = normalize_base_url(attributes.get("connector_url") or "")
    key = (attributes.get("connector_api_key") or "").strip()
    if not base or not key:
        raise UbaRequestError("not_configured", f"The {UBA_CONNECTOR_NAME} connector needs a URL and an API key", 409)

    headers = {"x-api-key": key, "Accept": "application/json"}
    if actor:
        headers["X-UBA-Actor"] = actor[:128]
    query = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{base}{path}"
    try:
        # TLS is verified (httpx default). UBA normally runs over plain HTTP on a private
        # network next to CoPilot; behind HTTPS it needs a certificate CoPilot trusts.
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=query, json=json, headers=headers)
    except httpx.TimeoutException:
        raise UbaRequestError("unreachable", f"SOCFortress UBA did not respond within {timeout:.0f}s")
    except httpx.HTTPError as e:
        logger.warning(f"UBA {method} {path} failed: {type(e).__name__}")
        raise UbaRequestError("unreachable", f"Could not reach SOCFortress UBA at {base}: {type(e).__name__}")

    if response.status_code == 401:
        raise UbaRequestError(
            "key_rejected",
            "SOCFortress UBA rejected the API key (revoked or wrong). Create one with "
            "`uba-admin api-keys create --name copilot --scope write` and update the connector.",
        )
    if response.status_code == 403:
        raise UbaRequestError(
            "insufficient_scope",
            f"The UBA API key's scope does not allow this ({_upstream_detail(response) or 'forbidden'}). "
            "CoPilot needs a key with scope write; setting UBA up for a customer needs scope admin "
            "for that customer (or all: `--scope admin --tenants '*'`).",
        )
    if response.status_code == 404:
        raise UbaRequestError("not_found", _upstream_detail(response) or "Not found in SOCFortress UBA", 404)
    if response.status_code == 422:
        raise UbaRequestError("invalid_request", _upstream_detail(response) or "SOCFortress UBA rejected the request", 422)
    if response.status_code >= 400:
        logger.warning(f"UBA {method} {path} returned HTTP {response.status_code}")
        raise UbaRequestError("upstream_error", f"SOCFortress UBA returned HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise UbaRequestError("bad_response", f"SOCFortress UBA returned a non-JSON response for {path}: check the connector URL")


async def verify_uba_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Connector check: ``GET /v1/status`` with the stored key."""
    try:
        body = await uba_request("GET", "/v1/status", attributes=attributes, timeout=10.0)
    except UbaRequestError as e:
        return {"connectionSuccessful": False, "message": e.detail}
    tenants = [t.get("tenant") for t in body.get("tenants", [])]
    return {
        "connectionSuccessful": True,
        "message": f"Connected to SOCFortress UBA {body.get('version', '')}; tenants: {', '.join(tenants) or 'none'}",
    }


async def verify_uba_connection(connector_name: str = UBA_CONNECTOR_NAME) -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error(f"No {connector_name} connector found in the database")
        return None
    return await verify_uba_credentials(attributes)
