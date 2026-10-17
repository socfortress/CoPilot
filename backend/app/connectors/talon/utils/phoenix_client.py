"""CoPilot's read-only client for talon-analyst's Phoenix (talon-analyst SPEC §5.4 FR-PHX-1, D51; plan
M5-9a, decisions A and E).

Phoenix holds talon-analyst's traces, one project per customer (``talon-<customer_code>``). CoPilot
reads them with a **viewer** user's API key stored in the "Talon Phoenix" connector row
(``TALON_PHOENIX_URL`` / ``TALON_PHOENIX_API_KEY``). A Phoenix viewer key reads *every* project
(``restrict_access_by_viewers`` refuses only non-GET requests, with no per-project check), so the
customer check before every read is CoPilot's (``services/talon_runs.py``), never Phoenix's.

What this module guarantees:
- **GET only, in code.** ``get`` is the one way to send a request, and every client carries a
  request hook that refuses any other method before it leaves the process (``OnlyGet``). Phoenix
  20.20's viewer restriction is the second wall, not the first.
- **No proxy, no redirect, short timeouts.** ``trust_env=False`` (a host's ``HTTPS_PROXY`` never
  carries the key), ``follow_redirects=False`` (a redirect is an answer, never followed with the
  key), connect 5 s and read 20 s. TLS is not verified, as for v1 and the v2 client: Phoenix
  belongs on CoPilot's private Docker network (talon-analyst M5-9t, alias
  ``talon-analyst-phoenix``).
- **Byte caps.** Every body is streamed and dropped past its cap (16 MB for a page of spans,
  ``MAX_PAGE_BYTES``), so a huge answer can't fill memory.
- **The viewer role, checked.** No run view unless ``GET /v1/user`` answers 200 with
  ``data.role == "VIEWER"`` exactly (Phoenix 20.20 ``routers/v1/users.py:get_viewer``; anything
  else, an anonymous user included, fails closed). A definite answer is cached for 10 minutes,
  keyed on the connector's ``connector_last_updated`` and a digest of its URL and key, so editing
  the connector re-checks at once.
- **At most two reads per process** (``reading``): a third caller waits at most 5 s, then gets 503.
- **The key is never logged**, nor the URL; failures are logged by class and status only, and
  Phoenix's own text never leaves this module.
"""
import asyncio
import hashlib
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

import httpx
from fastapi import HTTPException
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

PHOENIX_CONNECTOR = "Talon Phoenix"

TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
#: The largest page of spans read (decision E: REST ``getSpans`` with byte caps).
MAX_PAGE_BYTES = 16 * 1024 * 1024
#: ``GET /v1/user`` is one small object.
MAX_USER_BYTES = 64 * 1024

#: Phoenix reads in flight per process, and how long a caller waits for one.
CONCURRENT = 2
QUEUE_WAIT = 5.0
BUSY = "Phoenix reads are busy; try again shortly"

#: How long a definite answer about the key's role is believed.
ROLE_TTL_SECONDS = 600.0
VIEWER = "VIEWER"


class NotGet(RuntimeError):
    """A request other than GET was about to be sent to Phoenix."""


async def _only_get(request: httpx.Request) -> None:
    """The client's request hook: nothing but GET ever leaves for Phoenix."""
    if request.method != "GET":
        raise NotGet("the Phoenix client sends GET requests only")


def _transport() -> Optional[httpx.AsyncBaseTransport]:
    """httpx's own transport (tests replace this with a ``MockTransport``)."""
    return None


def _new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=_transport(),
        verify=False,
        timeout=TIMEOUT,
        follow_redirects=False,
        trust_env=False,
        event_hooks={"request": [_only_get]},
    )


@dataclass(frozen=True)
class PhoenixAnswer:
    """One answer: the status (None: no usable answer) and its body (None: over the cap)."""

    status: Optional[int]
    body: Optional[bytes] = None

    @property
    def over_cap(self) -> bool:
        return self.status is not None and self.body is None


@dataclass(frozen=True)
class PhoenixConnector:
    url: str
    api_key: str
    last_updated: str

    def fingerprint(self) -> Tuple[str, str]:
        """What the role cache is keyed on: the row's last update, and a digest of the URL and the
        key (never the key itself)."""
        digest = hashlib.sha256(f"{self.url}\0{self.api_key}".encode()).hexdigest()
        return (self.last_updated, digest)


def connector_from(attributes: Optional[Mapping[str, Any]]) -> Optional[PhoenixConnector]:
    """A usable connector from its row's attributes, or None: a URL and a key are both required."""
    if not attributes:
        return None
    url = str(attributes.get("connector_url") or "").strip().rstrip("/")
    api_key = str(attributes.get("connector_api_key") or "").strip()
    if not url or not api_key:
        return None
    return PhoenixConnector(url=url, api_key=api_key, last_updated=str(attributes.get("connector_last_updated") or ""))


async def _connector_attributes() -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        return await get_connector_info_from_db(PHOENIX_CONNECTOR, session)


async def connector() -> Optional[PhoenixConnector]:
    """The "Talon Phoenix" connector, read in a session of its own, or None when it isn't usable."""
    try:
        return connector_from(await _connector_attributes())
    except Exception as e:  # noqa: BLE001 - no connector table, no database: not configured
        logger.error(f"Talon Phoenix: the connector could not be read: {type(e).__name__}")
        return None


async def is_configured() -> bool:
    """Whether the run view can be offered: the connector has a URL and a key. No Phoenix call."""
    return await connector() is not None


async def _read_capped(response: httpx.Response, limit: int) -> Optional[bytes]:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


async def get(
    conn: PhoenixConnector,
    path: str,
    params: Optional[Sequence[Tuple[str, str]]] = None,
    *,
    max_bytes: int,
) -> PhoenixAnswer:
    """``GET {url}{path}`` with the viewer key. Never raises for a status or a transport error."""
    if not path.startswith("/v1/"):
        raise ValueError("a Phoenix path starts with /v1/")
    headers = {"Authorization": f"Bearer {conn.api_key}", "Accept": "application/json", "Accept-Encoding": "identity"}
    try:
        async with _new_client() as client:
            async with client.stream("GET", f"{conn.url}{path}", params=list(params or []), headers=headers) as response:
                body = await _read_capped(response, max_bytes)
                if body is None:
                    logger.error(f"Talon Phoenix GET {path.split('?')[0]}: the answer is over {max_bytes} bytes")
                return PhoenixAnswer(response.status_code, body)
    except NotGet:
        raise
    except Exception as e:  # noqa: BLE001 - a transport error or a malformed connector URL
        # The exception's text can name the host: logged by class only, never returned.
        logger.error(f"Talon Phoenix GET failed: {type(e).__name__}")
        return PhoenixAnswer(None)


# ── the viewer role ───────────────────────────────────────────────────────────


def role_of(answer: PhoenixAnswer) -> Optional[str]:
    """The role ``GET /v1/user`` names (``{"data": {"role": …}}``), or None for anything else.

    Phoenix 20.20 answers ``GetViewerResponseBody``: ``data`` is the user (``role`` one of its
    ``UserRoleName``s), or ``{"auth_method": "ANONYMOUS"}`` with no role when authentication is off.
    **[verify on the lab]** The field is read exactly there and nowhere else; any other shape is no
    role, which never passes.
    """
    if answer.status != 200 or answer.body is None:
        return None
    try:
        payload = json.loads(answer.body)
    except ValueError:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    role = data.get("role") if isinstance(data, dict) else None
    return role if isinstance(role, str) else None


def is_viewer_answer(answer: PhoenixAnswer) -> bool:
    return role_of(answer) == VIEWER


#: fingerprint -> (believed until, by ``time.monotonic()``; whether the key is a viewer key)
_ROLE_CACHE: Dict[Tuple[str, str], Tuple[float, bool]] = {}


def clear_role_cache() -> None:
    _ROLE_CACHE.clear()


async def is_viewer(conn: PhoenixConnector) -> bool:
    """Whether the connector's key is a Phoenix VIEWER's. Only a definite answer is cached (a 200
    naming a role, or Phoenix refusing the key); no answer, or a 5xx, is asked again next time."""
    key = conn.fingerprint()
    now = time.monotonic()
    cached = _ROLE_CACHE.get(key)
    if cached is not None and cached[0] > now:
        return cached[1]
    answer = await get(conn, "/v1/user", max_bytes=MAX_USER_BYTES)
    viewer = is_viewer_answer(answer)
    if answer.status in (200, 401, 403):
        for stale in [k for k in _ROLE_CACHE if k != key]:  # the connector changed: forget the old key
            del _ROLE_CACHE[stale]
        _ROLE_CACHE[key] = (now + ROLE_TTL_SECONDS, viewer)
    if not viewer:
        logger.error(f"Talon Phoenix: the connector's key is not a VIEWER key (GET /v1/user answered {answer.status}); no run view")
    return viewer


# ── at most two reads at once ─────────────────────────────────────────────────

_GATES: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}


def _gate() -> asyncio.Semaphore:
    """This process's (this event loop's) semaphore, ``CONCURRENT`` slots."""
    loop = asyncio.get_running_loop()
    gate = _GATES.get(loop)
    if gate is None:
        for old in [k for k in _GATES if k is not loop]:  # an old loop's (tests) is never used again
            del _GATES[old]
        gate = _GATES[loop] = asyncio.Semaphore(CONCURRENT)
    return gate


@asynccontextmanager
async def reading() -> AsyncIterator[None]:
    """One of the ``CONCURRENT`` Phoenix read slots, or 503 after ``QUEUE_WAIT`` seconds."""
    gate = _gate()
    try:
        await asyncio.wait_for(gate.acquire(), timeout=QUEUE_WAIT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail=BUSY) from None
    try:
        yield
    finally:
        gate.release()


# ── the connector check ───────────────────────────────────────────────────────


async def verify_talon_phoenix_credentials(attributes: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """The Connectors page's check: ``GET /v1/user`` with the key passes only for a VIEWER.

    The messages are fixed: they never name the URL, the key, or Phoenix's own text.
    """
    conn = connector_from(attributes)
    if conn is None:
        return {"connectionSuccessful": False, "message": "Set the Phoenix URL and a viewer user's API key"}
    answer = await get(conn, "/v1/user", max_bytes=MAX_USER_BYTES)
    if answer.status is None:
        return {"connectionSuccessful": False, "message": "Phoenix could not be reached"}
    if answer.status in (401, 403):
        return {"connectionSuccessful": False, "message": "Phoenix refused the API key"}
    if answer.status != 200:
        return {"connectionSuccessful": False, "message": f"Phoenix answered HTTP {answer.status}"}
    role = role_of(answer)
    if role is None:
        return {"connectionSuccessful": False, "message": "Phoenix did not name the key's role, so it is not accepted"}
    if role != VIEWER:
        return {"connectionSuccessful": False, "message": "The key is not a Phoenix VIEWER's: CoPilot needs a viewer key"}
    clear_role_cache()  # the next run view re-checks against the saved row
    return {"connectionSuccessful": True, "message": "Talon Phoenix connection successful (viewer key)"}


async def verify_talon_phoenix_connection(connector_name: str = PHOENIX_CONNECTOR) -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error(f"No {connector_name} connector found in the database")
        return None
    return await verify_talon_phoenix_credentials(attributes)
