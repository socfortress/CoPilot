"""The HTTP client for talon-analyst's v2 API (talon-analyst SPEC §8 "v2 API"; plan M5-5a).

Unlike ``universal.py``'s helpers, nothing here raises on an upstream status: v2's 404, 409 and 403
mean something to the UI (an unknown thread, a decision pending, a customer taken away), so every
call returns the status and the body for the route to pass on. ``None`` as the status means there
was no answer to pass on (no connector, a connection error, an answer too big to relay).

Every upstream header is built here from scratch: the connector's API key, the content type and
the five identity headers from ``services/identity.py``. Nothing is copied from the browser's
request, which is how a client-sent ``X-Talon-*`` header is dropped.

The chat stream (``open_v2_stream``) is the one call whose upstream outlives the function: on a 2xx
it returns a ``V2Stream`` that owns the upstream connection until ``aclose``, which
``V2StreamingResponse`` always calls, however the response ends (finished, cut off by the browser,
cancelled). On any other answer the upstream is read (at most 4 KB) and closed before returning.
"""
from dataclasses import dataclass
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Union

import anyio
import httpx
from loguru import logger
from starlette.responses import StreamingResponse
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from app.connectors.talon.services.identity import IDENTITY_HEADERS
from app.connectors.talon.utils.universal import MAX_REFUSAL_BODY_BYTES
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

TALON_CONNECTOR = "Talon"

#: Thread routes answer in milliseconds; a hung talon-analyst must not hold the request.
REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
#: The chat stream sends a keepalive every 15 s while a turn is quiet (TALON_SSE_KEEPALIVE_SECONDS),
#: so two minutes without a byte means the upstream is gone.
STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
#: The largest JSON answer relayed (a page of 200 threads is a few tens of KB).
MAX_JSON_BODY_BYTES = 1024 * 1024
#: The largest page of a thread's messages relayed: talon-analyst ends a page at about 1,000,000
#: characters of stored JSON (``transcript.PAGE_CHARS``), which as UTF-8 can be more bytes.
MAX_MESSAGES_BODY_BYTES = 4 * 1024 * 1024

#: The stream's own headers (talon-analyst ``v2_chat.HEADERS``), set by CoPilot, not copied.
STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


@dataclass(frozen=True)
class V2Answer:
    """A v2 answer that isn't a stream: the status (None: no answer) and at most a capped body."""

    status: Optional[int]
    body: bytes = b""


def build_upstream_headers(api_key: str, identity: Mapping[str, str], *, accept: str, json_body: bool) -> Dict[str, str]:
    """Every header of an upstream v2 request, built from nothing. ``identity`` must hold exactly
    the five identity headers (``talon_identity_headers``)."""
    if set(identity) != set(IDENTITY_HEADERS):
        raise ValueError("the identity must be exactly the five X-Talon-* headers")
    headers = {"x-api-key": api_key, "Accept": accept, "Accept-Encoding": "identity"}
    if json_body:
        headers["Content-Type"] = "application/json"
    for name in IDENTITY_HEADERS:
        headers[name] = identity[name]
    return headers


def _new_client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    """One client per request, as v1's stream does (tests replace this to mock the transport).

    ``trust_env=False``: a host's ``HTTPS_PROXY``/``HTTP_PROXY`` must never carry the API key and
    the identity headers through a proxy nobody chose for Talon. TLS isn't verified, as for v1
    (the connector's own TLS option is a follow-up), so talon-analyst belongs on a private network."""
    return httpx.AsyncClient(verify=False, timeout=timeout, follow_redirects=False, trust_env=False)


async def _connector(connector_name: str) -> Optional[Dict[str, Any]]:
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if not attributes or not attributes.get("connector_url"):
        logger.error(f"Talon v2: no usable '{connector_name}' connector")
        return None
    return attributes


def _url(attributes: Mapping[str, Any], path: str) -> str:
    return f"{str(attributes['connector_url']).rstrip('/')}{path}"


async def _read_capped(response: httpx.Response, limit: int) -> Optional[bytes]:
    """The body, or None when it is longer than ``limit``. Collected in a ``bytearray``: appending
    to ``bytes`` copies the whole body each time, quadratic for a 4 MB transcript page."""
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


async def _shielded_close(*closables: Any) -> None:
    """Close each of ``closables`` even inside a cancelled task (a browser that left)."""
    with anyio.CancelScope(shield=True):
        for closable in closables:
            try:
                await closable.aclose()
            except Exception as e:  # noqa: BLE001 - closing must never mask the real outcome
                logger.debug(f"Talon v2: closing the upstream failed: {type(e).__name__}")


async def v2_request(
    method: str,
    path: str,
    identity: Mapping[str, str],
    *,
    params: Optional[Mapping[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    connector_name: str = TALON_CONNECTOR,
    max_body_bytes: int = MAX_JSON_BODY_BYTES,
) -> V2Answer:
    """One v2 request that answers JSON. Never raises for an upstream status or a transport error."""
    attributes = await _connector(connector_name)
    if attributes is None:
        return V2Answer(None)
    headers = build_upstream_headers(
        attributes.get("connector_api_key") or "",
        identity,
        accept="application/json",
        json_body=json_body is not None,
    )
    try:
        async with _new_client(REQUEST_TIMEOUT) as client:
            async with client.stream(method, _url(attributes, path), headers=headers, params=params, json=json_body) as response:
                body = await _read_capped(response, max_body_bytes)
                if body is None:
                    logger.error(f"Talon v2 {method} {path}: the answer is over {max_body_bytes} bytes")
                    return V2Answer(None)
                return V2Answer(response.status_code, body)
    except Exception as e:  # noqa: BLE001 - a transport error or a malformed connector URL
        # The exception's text names hosts and ports: logged by class, never returned.
        logger.error(f"Talon v2 {method} {path} failed: {type(e).__name__}")
        return V2Answer(None)


class V2Stream:
    """An open upstream chat stream (a 2xx). Owns the client and the response until ``aclose``."""

    def __init__(self, client: httpx.AsyncClient, response: httpx.Response) -> None:
        self._client = client
        self._response = response
        self.closed = False

    async def chunks(self) -> AsyncIterator[bytes]:
        """The upstream's bytes as they arrive, unchanged (keepalive comments included)."""
        try:
            async for chunk in self._response.aiter_bytes():
                yield chunk
        except httpx.HTTPError as e:
            # Cut off mid-stream: the browser sees the stream end without [DONE] (the parser's
            # "stream closed" case). Nothing is added: a chunk of ours could land mid-event.
            logger.error(f"Talon v2 chat stream ended early: {type(e).__name__}")
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        if self.closed:
            return
        self.closed = True
        await _shielded_close(self._response, self._client)


async def open_v2_stream(
    path: str,
    identity: Mapping[str, str],
    json_body: Dict[str, Any],
    *,
    connector_name: str = TALON_CONNECTOR,
) -> Union[V2Answer, V2Stream]:
    """POST ``json_body`` and open the answer as a stream. A 2xx is a ``V2Stream`` the caller must
    close (``V2StreamingResponse`` does); anything else is a ``V2Answer`` whose upstream is already
    closed, with at most ``MAX_REFUSAL_BODY_BYTES`` of its body."""
    attributes = await _connector(connector_name)
    if attributes is None:
        return V2Answer(None)
    headers = build_upstream_headers(
        attributes.get("connector_api_key") or "",
        identity,
        accept="text/event-stream",
        json_body=True,
    )
    client = _new_client(STREAM_TIMEOUT)
    try:
        request = client.build_request("POST", _url(attributes, path), headers=headers, json=json_body)
        response = await client.send(request, stream=True)
    except Exception as e:  # noqa: BLE001 - a transport error or a malformed connector URL
        await _shielded_close(client)
        logger.error(f"Talon v2 POST {path} failed: {type(e).__name__}")
        return V2Answer(None)
    except BaseException:  # cancelled while connecting (the browser left): nothing may stay open
        await _shielded_close(client)
        raise
    if response.is_success:
        return V2Stream(client, response)
    try:
        body = b""
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) >= MAX_REFUSAL_BODY_BYTES:
                body = body[:MAX_REFUSAL_BODY_BYTES]
                break
    except httpx.HTTPError:
        body = b""
    finally:
        await _shielded_close(response, client)
    return V2Answer(response.status_code, body)


class V2StreamingResponse(StreamingResponse):
    """The upstream stream's bytes as they are, with the stream's own headers. The upstream is
    closed when the response ends, whatever ends it: the stream finishing, the browser leaving
    (Starlette cancels the send, or the send fails), or the task being cancelled."""

    def __init__(self, stream: V2Stream) -> None:
        super().__init__(stream.chunks(), media_type="text/event-stream", headers=STREAM_HEADERS)
        self._stream = stream

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await self.body_iterator.aclose()  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001 - the generator may already be closed
                    pass
                await self._stream.aclose()
