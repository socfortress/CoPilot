"""The HTTP client behind the Talon Memory tab (``services/talon_memory.py``): talon-analyst's
``/v2/memory/...`` routes.

Shaped like ``health_client``: one 8 s deadline per request (connect, headers and body together), at
most a capped number of raw bytes read (``capped_body``: an encoded answer is refused, never
inflated), no redirect followed and the host's proxy settings ignored (``trust_env=False``: no proxy
nobody chose for Talon carries the API key). Only the connector's API key is sent: the memory API
trusts CoPilot to have checked the caller's customer (the service does, before asking).

**The path is built here from segments, never from a string a caller formatted.** ``memory_path``
takes the segments after ``/v2/memory/``, refuses any that is empty, ``.`` or ``..``, or holds a
``/``, ``\\``, ``%``, ``?``, ``#`` or a control character, and percent-encodes each one with no safe
characters, so no value from a request can climb out of ``/v2/memory/`` into another talon-analyst
route (``../../threads``). Free text (a search) goes in the query string through httpx's own
encoding, never into the path.

Nothing here raises: every outcome is a ``MemoryAnswer``, whose ``error`` is a fixed text plus at
most an exception's class name. An exception's own text names hosts and ports, so it is never kept.

TLS isn't verified, as for the rest of the Talon connector: talon-analyst belongs on a private
network.
"""
import re
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from urllib.parse import quote

import anyio
import httpx
from loguru import logger

from app.connectors.talon.utils import capped_body

#: Seconds for a whole request, connect to last byte. A semantic search is the slowest call.
TIMEOUT_SECONDS = 8.0
TIMEOUT = httpx.Timeout(TIMEOUT_SECONDS)
PREFIX = "/v2/memory"
#: The largest answer read: a page of 100 drawers with their previews, or one drawer's content.
MAX_BODY_BYTES = 2 * 1024 * 1024

#: Characters no path segment may hold, even percent-encoded afterwards: a separator, an escape,
#: a query or fragment start, a control character.
_UNSAFE_SEGMENT = re.compile(r"[/\\%?#\x00-\x1f\x7f-\x9f]")


class UnsafePath(ValueError):
    """A path segment that could change which talon-analyst route is asked."""


@dataclass(frozen=True)
class MemoryAnswer:
    """One request's outcome. ``status`` None: no usable answer (``error`` says why)."""

    status: Optional[int]
    body: bytes = b""
    error: Optional[str] = None
    timed_out: bool = False


def memory_path(segments: Sequence[str]) -> str:
    """``/v2/memory/<seg>/<seg>…``, each segment checked and percent-encoded (``UnsafePath``)."""
    if not segments:
        raise UnsafePath("no path")
    encoded = []
    for segment in segments:
        if not isinstance(segment, str) or not segment or segment in (".", "..") or _UNSAFE_SEGMENT.search(segment):
            raise UnsafePath("unsafe path segment")
        encoded.append(quote(segment, safe=""))
    return f"{PREFIX}/{'/'.join(encoded)}"


def _new_client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    """One client per request (tests replace this to mock the transport)."""
    return httpx.AsyncClient(verify=False, timeout=timeout, follow_redirects=False, trust_env=False)


def _url(base_url: str, path: str) -> str:
    return f"{str(base_url).rstrip('/')}{path}"


async def request(
    method: str,
    base_url: str,
    segments: Sequence[str],
    *,
    api_key: str,
    params: Optional[Mapping[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    max_body_bytes: Optional[int] = None,
) -> MemoryAnswer:
    """One request to talon-analyst's memory API. ``UnsafePath`` is raised before anything is sent."""
    path = memory_path(segments)
    max_body_bytes = MAX_BODY_BYTES if max_body_bytes is None else max_body_bytes
    headers = {"Accept": "application/json", "Accept-Encoding": "identity", "x-api-key": api_key}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    query = {k: v for k, v in (params or {}).items() if v is not None}
    # The log line names the route's shape, never a drawer, an asset or a search.
    shape = f"{method} {PREFIX}/{segments[0] if segments[0] == 'chat' else '<customer>'}/…"
    try:
        with anyio.fail_after(TIMEOUT_SECONDS):
            async with _new_client(TIMEOUT) as client:
                async with client.stream(method, _url(base_url, path), headers=headers, params=query, json=json_body) as response:
                    if not capped_body.is_identity(response):
                        logger.warning(f"Talon memory {shape}: the answer came with a Content-Encoding; not read")
                        return MemoryAnswer(response.status_code, b"", "Talon's answer was compressed; not read")
                    body = await capped_body.read_capped(response, max_body_bytes)
                    if body is None:
                        logger.warning(f"Talon memory {shape}: the answer is over {max_body_bytes} bytes")
                        return MemoryAnswer(response.status_code, b"", "Talon's answer was too large")
                    return MemoryAnswer(response.status_code, body)
    except TimeoutError:
        logger.warning(f"Talon memory {shape}: no answer within {TIMEOUT_SECONDS:g} s")
        return MemoryAnswer(None, error=f"Talon did not answer within {TIMEOUT_SECONDS:g} s", timed_out=True)
    except Exception as e:  # noqa: BLE001 - a transport error or a malformed connector URL
        name = type(e).__name__
        logger.warning(f"Talon memory {shape} failed: {name}")
        if isinstance(e, httpx.TimeoutException):
            return MemoryAnswer(None, error=f"Talon did not answer within {TIMEOUT_SECONDS:g} s", timed_out=True)
        return MemoryAnswer(None, error=f"Talon could not be reached ({name})")
