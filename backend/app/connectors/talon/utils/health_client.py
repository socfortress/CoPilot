"""The HTTP client behind the Talon health dashboard (``services/talon_health.py``).

Short and bounded on purpose: the dashboard must answer even when Talon doesn't. Every request has
one 5 s deadline (connect, headers and body together), reads at most a capped number of raw bytes
(``capped_body``: an encoded answer is refused, never inflated), follows no redirect and ignores the
host's proxy settings (``trust_env=False``: no proxy nobody chose for Talon carries the API key).
Nothing here raises: every outcome is a ``Probe``, whose ``error`` is a fixed text plus at most an
exception's class name. An exception's own text names hosts and ports, so it is never kept.

TLS isn't verified, as for the rest of the Talon connector: talon-analyst belongs on a private
network.
"""
import time
from dataclasses import dataclass
from typing import Optional

import anyio
import httpx
from loguru import logger

from app.connectors.talon.utils import capped_body

#: Seconds for a whole request, connect to last byte.
TIMEOUT_SECONDS = 5.0
TIMEOUT = httpx.Timeout(TIMEOUT_SECONDS)


@dataclass(frozen=True)
class Probe:
    """One GET's outcome. ``status`` None: no usable answer (``error`` says why)."""

    status: Optional[int]
    body: bytes = b""
    latency_ms: Optional[float] = None
    error: Optional[str] = None


def _new_client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    """One client per request (tests replace this to mock the transport)."""
    return httpx.AsyncClient(verify=False, timeout=timeout, follow_redirects=False, trust_env=False)


def join(base_url: str, path: str) -> str:
    return f"{str(base_url).rstrip('/')}{path}"


async def get(base_url: str, path: str, *, api_key: Optional[str], max_body_bytes: int) -> Probe:
    """GET ``path`` on Talon. ``api_key`` None sends no key (Talon's ``/health`` takes none)."""
    headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
    if api_key:
        headers["x-api-key"] = api_key
    started = time.perf_counter()
    try:
        with anyio.fail_after(TIMEOUT_SECONDS):
            async with _new_client(TIMEOUT) as client:
                async with client.stream("GET", join(base_url, path), headers=headers) as response:
                    latency_ms = round((time.perf_counter() - started) * 1000, 1)
                    if not capped_body.is_identity(response):
                        logger.warning(f"Talon health GET {path}: the answer came with a Content-Encoding; not read")
                        return Probe(response.status_code, b"", latency_ms, "Talon's answer was compressed; not read")
                    body = await capped_body.read_capped(response, max_body_bytes)
                    if body is None:
                        logger.warning(f"Talon health GET {path}: the answer is over {max_body_bytes} bytes")
                        return Probe(response.status_code, b"", latency_ms, "Talon's answer was too large")
                    return Probe(response.status_code, body, latency_ms)
    except TimeoutError:
        logger.warning(f"Talon health GET {path}: no answer within {TIMEOUT_SECONDS:g} s")
        return Probe(None, error=f"Talon did not answer within {TIMEOUT_SECONDS:g} s (TimeoutError)")
    except Exception as e:  # noqa: BLE001 - a transport error or a malformed connector URL
        name = type(e).__name__
        logger.warning(f"Talon health GET {path} failed: {name}")
        if isinstance(e, httpx.TimeoutException):
            return Probe(None, error=f"Talon did not answer within {TIMEOUT_SECONDS:g} s ({name})")
        return Probe(None, error=f"Talon could not be reached ({name})")
