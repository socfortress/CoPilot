"""
Channel-specific delivery helpers for the notification dispatcher.

Each helper is async, returns a (status, error_message, latency_ms)
tuple, and never raises — failures are reported via the tuple so the
caller can log them in a single shape regardless of which channel failed.
This keeps the dispatch loop's try/except surface trivial.

Phase 1 ships two channels:
  - slack_webhook : POSTs a JSON body to a Slack incoming webhook URL
  - smtp_email    : sends a plaintext email via SMTP env config

Phase 2 will add a third helper that POSTs to Shuffle's hosted MCP
(`https://shuffler.io/api/v1/apps/{app}/mcp`). Same return shape, same
caller — just a new branch in the dispatcher's channel switch.
"""

from __future__ import annotations

import asyncio
import os
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Tuple

import httpx
from loguru import logger

# Tuple shape used by every dispatcher: (status, error_message, latency_ms)
# status is one of 'sent' | 'failed'; the caller turns 'sent' into a
# DispatchStatus.SENT row. error_message is None on success.
DispatchResult = Tuple[str, str | None, int]


# Hard cap on the upstream POST. 10s is generous for Slack's incoming
# webhook latency (typically <500ms) but tight enough that a hung edge
# doesn't stall the dispatch loop. SMTP gets the same budget.
_PROVIDER_TIMEOUT_S = 10.0


async def dispatch_slack_webhook(url: str, text: str) -> DispatchResult:
    """POST a plaintext message to a Slack incoming-webhook URL.

    Slack's incoming webhook accepts a JSON body of `{"text": "..."}` —
    that's the simplest possible Slack message and it renders as plain
    text. Phase 4 will swap this for blocks for richer formatting; for
    Phase 1 plaintext is enough to validate the dispatch loop.
    """
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT_S) as client:
            response = await client.post(url, json={"text": text})
        latency_ms = int((time.monotonic() - started) * 1000)
        # Slack returns 200 + body "ok" on success; any other status is a
        # webhook config / Slack-side issue and should surface to the user
        # via the dispatch log error_message.
        if response.status_code != 200 or response.text.strip().lower() != "ok":
            return (
                "failed",
                f"Slack returned {response.status_code}: {response.text[:200]}",
                latency_ms,
            )
        return ("sent", None, latency_ms)
    except Exception as e:  # noqa: BLE001 — caller logs everything
        latency_ms = int((time.monotonic() - started) * 1000)
        logger.warning(f"Slack webhook dispatch failed: {e!r}")
        return ("failed", f"{type(e).__name__}: {e}", latency_ms)


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
    with smtplib.SMTP(host, port, timeout=_PROVIDER_TIMEOUT_S) as smtp:
        smtp.ehlo()
        if use_tls:
            ctx = ssl.create_default_context()
            smtp.starttls(context=ctx)
            smtp.ehlo()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
