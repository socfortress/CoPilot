"""
Channel-specific delivery helpers for the notification dispatcher.

Each helper is async, returns a (status, error_message, latency_ms,
*provider-specific extras) tuple, and never raises — failures are
reported via the tuple so the caller can log them in a single shape
regardless of which channel failed. This keeps the dispatch loop's
try/except surface trivial.

Channels:
  - smtp_email : direct SMTP via env config (deployment-wide)
  - shuffle    : POST to https://shuffler.io/api/v1/apps/{id}/mcp using
                 the deployment's Bearer (from the Shuffle connector)
                 + customer's Org-Id header. Fire-and-record — we
                 capture Shuffle's execution_id but don't poll for the
                 downstream provider's terminal state.
"""

from __future__ import annotations

import asyncio
import os
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import httpx
from loguru import logger

# Tuple shape used by every dispatcher: (status, error_message, latency_ms)
# status is one of 'sent' | 'failed'; the caller turns 'sent' into a
# DispatchStatus.SENT row. error_message is None on success.
DispatchResult = Tuple[str, Optional[str], int]


# Shuffle's dispatcher returns a 4-tuple — the standard triple plus an
# execution_id. None when the kickoff failed before Shuffle returned one.
ShuffleDispatchResult = Tuple[str, Optional[str], int, Optional[str]]


# Hard cap on the upstream provider call. SMTP usually completes in
# <2s; Shuffle's MCP kickoff is usually <1s but cold-start paths
# (first call against an org, or Shuffle's backend warming) can spike.
# Two budgets so a slow Shuffle response doesn't masquerade as a
# dispatch failure while keeping SMTP failures fast.
_SMTP_TIMEOUT_S = 10.0
_SHUFFLE_TIMEOUT_S = 30.0


async def dispatch_smtp_email(
    recipients: list[str],
    subject: str,
    body: str,
) -> DispatchResult:
    """Send a plaintext email to one or more recipients via SMTP.

    Configuration is read from environment variables on each call so a
    customer can re-point SMTP at runtime without restarting CoPilot:

      SMTP_HOST       hostname (required)
      SMTP_PORT       int, defaults to 587 (STARTTLS)
      SMTP_USER       optional — when set, AUTH LOGIN is performed
      SMTP_PASSWORD   optional — paired with SMTP_USER
      SMTP_FROM       From: header value (required)
      SMTP_USE_TLS    'true' (default) | 'false' — STARTTLS toggle
    """
    started = time.monotonic()
    try:
        host = os.getenv("SMTP_HOST")
        from_addr = os.getenv("SMTP_FROM")
        if not host or not from_addr:
            latency_ms = int((time.monotonic() - started) * 1000)
            return (
                "failed",
                "SMTP not configured (set SMTP_HOST and SMTP_FROM)",
                latency_ms,
            )

        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        # smtplib is sync — push it to a thread so the event loop stays
        # responsive while we wait on the network.
        await asyncio.get_running_loop().run_in_executor(
            None,
            _send_smtp_sync,
            host,
            port,
            user,
            password,
            use_tls,
            msg,
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        return ("sent", None, latency_ms)
    except Exception as e:  # noqa: BLE001
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.warning(f"SMTP email dispatch failed: {e!r}")
        return ("failed", f"{type(e).__name__}: {e}", latency_ms)


def _send_smtp_sync(
    host: str,
    port: int,
    user: str | None,
    password: str | None,
    use_tls: bool,
    msg: EmailMessage,
) -> None:
    """Synchronous SMTP send — invoked in a worker thread by the async
    wrapper. Raises on failure; the caller catches and reports."""
    with smtplib.SMTP(host, port, timeout=_SMTP_TIMEOUT_S) as smtp:
        smtp.ehlo()
        if use_tls:
            ctx = ssl.create_default_context()
            smtp.starttls(context=ctx)
            smtp.ehlo()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)


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
