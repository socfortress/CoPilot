"""
Channel-specific delivery helpers for the notification dispatcher.

Each helper is async, returns a tuple shape that includes status,
error_message, latency_ms, and optional provider-specific extras. None
raise — failures are reported via the tuple so the caller can log them
in a single shape. This keeps the dispatch loop's try/except surface
trivial.

Channels:
  - shuffle : POST to https://shuffler.io/api/v1/apps/{id}/mcp using
              the deployment's Bearer (from the Shuffle connector)
              + customer's Org-Id header. Fire-and-record — we
              capture Shuffle's execution_id but don't poll for the
              downstream provider's terminal state. Email, Slack,
              Teams, etc. all flow through this single channel via
              Shuffle's catalog of authenticated apps.
"""

from __future__ import annotations

import time
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger

# Shuffle's dispatcher returns a 4-tuple — status, error_message,
# latency_ms, and the kickoff execution_id (None if Shuffle didn't
# return one before the call failed).
ShuffleDispatchResult = Tuple[str, Optional[str], int, Optional[str]]


# Hard cap on Shuffle's MCP kickoff. Usually <1s but cold-start paths
# (first call against an org, or Shuffle's backend warming) can spike.
# 30s leaves enough headroom for those without letting a stuck request
# stall the dispatch loop indefinitely.
_SHUFFLE_TIMEOUT_S = 30.0


# ---------------------------------------------------------------------------
# Shuffle dispatcher (Phase 2)
# ---------------------------------------------------------------------------


def _shuffle_headers(api_key: str, org_id: str) -> Dict[str, str]:
    """Bearer auth + Org-Id scope.

    The deployment's Shuffle API key (admin-scoped, lives in CoPilot's
    Shuffle connector row) plus the customer's per-integration Org-Id
    is what scopes a dispatch to the right org. The MCP server in
    shuffle-mcp-server uses the same pair.
    """
    return {
        "Authorization": f"Bearer {api_key}",
        "Org-Id": org_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def dispatch_shuffle(
    *,
    base_url: str,
    api_key: str,
    org_id: str,
    app_id: str,
    input_text: str,
    environment: str = "Shuffle",
) -> ShuffleDispatchResult:
    """Kick off a Shuffle AI Agent run for one app.

    Wraps `POST {base_url}/api/v1/apps/{app_id}/mcp`. Shuffle's response
    contains an `execution_id` + `authorization` — the actual downstream
    delivery (Slack message, email send, etc.) happens asynchronously
    inside Shuffle. Phase 2 is fire-and-record: we treat HTTP 200 from
    Shuffle as `sent` and stash the execution_id for forensic lookups,
    but we do NOT poll for terminal state. Phase 4 may add an optional
    poll-with-timeout mode for high-criticality routes.

    Returns (status, error_message, latency_ms, execution_id_or_None).
    """
    url = f"{base_url.rstrip('/')}/api/v1/apps/{app_id}/mcp"
    body: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {
            "tool_id": app_id,
            "tool_name": app_id,
            "input": {"text": input_text},
            "environment": environment,
        },
    }
    logger.info(f"Dispatching payload to Shuffle body: {body}")
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_SHUFFLE_TIMEOUT_S, http2=True) as client:
            response = await client.post(url, headers=_shuffle_headers(api_key, org_id), json=body)
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code in (401, 403):
            return (
                "failed",
                f"Shuffle authentication failed ({response.status_code}): {response.text[:200]}",
                latency_ms,
                None,
            )
        if response.status_code >= 400:
            return (
                "failed",
                f"Shuffle returned {response.status_code}: {response.text[:200]}",
                latency_ms,
                None,
            )

        try:
            data = response.json()
        except ValueError:
            return ("failed", "Shuffle returned non-JSON response", latency_ms, None)

        # Shuffle's success body shape: {success, execution_id, authorization, mode}.
        # `execution_id` is what we stash for forensic correlation in
        # the dispatch log; no polling.
        execution_id = data.get("execution_id") if isinstance(data, dict) else None
        if isinstance(data, dict) and data.get("success") is False:
            return (
                "failed",
                f"Shuffle reported failure: {data.get('reason') or data.get('error') or data}",
                latency_ms,
                execution_id,
            )
        return ("sent", None, latency_ms, execution_id)
    except Exception as e:  # noqa: BLE001
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.warning(f"Shuffle dispatch failed: {e!r}")
        return ("failed", f"{type(e).__name__}: {e}", latency_ms, None)


async def list_shuffle_apps(
    *,
    base_url: str,
    api_key: str,
    org_id: str,
) -> Tuple[bool, list, Optional[str]]:
    """Fetch the apps catalog the customer's Shuffle org has access to.

    Used by the route form's app picker so admins can pick from a list
    instead of hand-typing UUIDs. Returns (ok, apps, error_message).
    """
    url = f"{base_url.rstrip('/')}/api/v1/apps"
    try:
        async with httpx.AsyncClient(timeout=_SHUFFLE_TIMEOUT_S, http2=True) as client:
            response = await client.get(url, headers=_shuffle_headers(api_key, org_id))
        if response.status_code in (401, 403):
            return (False, [], f"Shuffle authentication failed ({response.status_code})")
        if response.status_code >= 400:
            return (False, [], f"Shuffle returned {response.status_code}: {response.text[:200]}")
        try:
            data = response.json()
        except ValueError:
            return (False, [], "Shuffle returned non-JSON response")

        # Shuffle returns the catalog as a list of app objects with at
        # minimum {id, name, description}. We forward the minimal shape
        # the UI needs and let the route form record (id, name) on submit.
        if not isinstance(data, list):
            return (False, [], f"Unexpected Shuffle response shape: {type(data).__name__}")
        return (True, data, None)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Shuffle apps list failed: {e!r}")
        return (False, [], f"{type(e).__name__}: {e}")


async def verify_shuffle_org(
    *,
    base_url: str,
    api_key: str,
    org_id: str,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Quick auth probe for an integration. Used by the 'Test connection'
    button in the integration form. Returns (ok, app_count, error)."""
    ok, apps, error = await list_shuffle_apps(base_url=base_url, api_key=api_key, org_id=org_id)
    if not ok:
        return (False, None, error)
    return (True, len(apps), None)


async def list_shuffle_orgs(
    *,
    base_url: str,
    api_key: str,
) -> Tuple[bool, list, Optional[str]]:
    """Fetch the orgs the deployment's admin Bearer can see.

    Used by the integration form so admins pick from a dropdown of real
    orgs instead of pasting Org-Ids. Hits `GET /api/v1/orgs` — Shuffle
    treats the admin key as having visibility into the parent org plus
    any sub-orgs. We deliberately do NOT send an `Org-Id` header: the
    request is unscoped so we get the full list back rather than a
    single-org view.

    Returns (ok, orgs, error_message). Each org element is a dict with
    at least `id` and `name`; the service layer trims it to the shape
    the frontend dropdown needs.
    """
    url = f"{base_url.rstrip('/')}/api/v1/orgs"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_SHUFFLE_TIMEOUT_S, http2=True) as client:
            response = await client.get(url, headers=headers)
        if response.status_code in (401, 403):
            return (False, [], f"Shuffle authentication failed ({response.status_code})")
        if response.status_code >= 400:
            return (False, [], f"Shuffle returned {response.status_code}: {response.text[:200]}")
        try:
            data = response.json()
        except ValueError:
            return (False, [], "Shuffle returned non-JSON response")

        # Shuffle's `/api/v1/orgs` historically returns a flat list of
        # org objects; some installs wrap it in `{"orgs": [...]}`. Tolerate
        # both shapes so we don't break on an upstream change.
        if isinstance(data, dict) and "orgs" in data:
            data = data.get("orgs") or []
        if not isinstance(data, list):
            return (False, [], f"Unexpected Shuffle response shape: {type(data).__name__}")
        return (True, data, None)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Shuffle orgs list failed: {e!r}")
        return (False, [], f"{type(e).__name__}: {e}")
