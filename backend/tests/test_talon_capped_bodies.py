"""Byte caps on every Talon connector read (review of #1271, ``utils/capped_body.py``).

httpx inflates each listed ``Content-Encoding`` with ``zlib.decompress`` and no output limit, so a
few hundred bytes of stacked ``gzip, gzip`` became hundreds of megabytes in one chunk, before any
cap that counted decoded bytes. Every capped read in the Talon connector (v1's SSE proxy, the v2
client and its chat stream, the Phoenix client) now reads raw bytes and refuses any encoding but
identity. Pinned here with hostile ``MockTransport`` answers whose bodies are raw streams, as a
network transport's are. No network, no database.

Run with: cd backend && python -m pytest tests/test_talon_capped_bodies.py
"""

import asyncio
import json
import os
import tracemalloc
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.connectors.talon.services.identity import IDENTITY_HEADERS  # noqa: E402
from app.connectors.talon.utils import capped_body  # noqa: E402
from app.connectors.talon.utils import universal  # noqa: E402
from app.connectors.talon.utils import v2_client  # noqa: E402
from tests.talon_v2_support import RawStream  # noqa: E402
from tests.talon_v2_support import bomb_response  # noqa: E402
from tests.talon_v2_support import stacked_gzip  # noqa: E402

IDENTITY = {name: "x" for name in IDENTITY_HEADERS}
CONNECTOR = {"connector_url": "http://talon.invalid", "connector_api_key": "k"}
_RealAsyncClient = httpx.AsyncClient


def response(headers=None, body=b"{}"):
    return httpx.Response(200, headers=headers or {}, stream=RawStream(body))


@pytest.mark.parametrize(
    "headers, identity",
    [
        ({}, True),
        ({"content-encoding": "identity"}, True),
        ({"content-encoding": " IDENTITY "}, True),
        ({"content-encoding": "gzip"}, False),
        ({"content-encoding": "gzip, gzip"}, False),
        ({"content-encoding": "identity, br"}, False),
        ({"content-encoding": ""}, True),
    ],
)
def test_only_identity_passes(headers, identity):
    assert capped_body.is_identity(response(headers)) is identity


def test_two_encoding_header_lines_are_both_read():
    answer = httpx.Response(200, headers=[("content-encoding", "identity"), ("content-encoding", "gzip")], stream=RawStream(b"{}"))
    assert capped_body.is_identity(answer) is False


def test_the_raw_bytes_are_counted_and_an_encoded_body_raises():
    async def run():
        ok = await capped_body.read_capped(response(body=b"x" * 10), 10)
        over = await capped_body.read_capped(response(body=b"x" * 11), 10)
        prefix = await capped_body.read_prefix(response(body=b"x" * 11), 4)
        encoded_prefix = await capped_body.read_prefix(bomb_response(), 4096)
        with pytest.raises(capped_body.EncodedBody):
            await capped_body.read_capped(bomb_response(), 10**9)
        with pytest.raises(capped_body.EncodedBody):
            async for _ in capped_body.raw_chunks(bomb_response()):
                pass
        return ok, over, prefix, encoded_prefix

    assert asyncio.run(run()) == (b"x" * 10, None, b"xxxx", b"")


def test_httpx_would_have_inflated_the_bomb_and_the_capped_read_does_not():
    stacked_gzip()

    async def run():
        tracemalloc.start()
        try:
            with pytest.raises(capped_body.EncodedBody):
                await capped_body.read_capped(bomb_response(), 1024)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        first = None
        async for chunk in bomb_response().aiter_bytes():  # what httpx itself does
            first = len(chunk)
            break
        return peak, first

    peak, first = asyncio.run(run())
    assert peak < 1024 * 1024
    assert first > 16 * 1024 * 1024  # one decoded "chunk" larger than any cap


# ── v2 ────────────────────────────────────────────────────────────────────────


def v2(handler, coroutine):
    def new_client(timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)

    async def run():
        with patch.object(v2_client, "_new_client", new_client), patch.object(v2_client, "_connector", AsyncMock(return_value=CONNECTOR)):
            return await coroutine()

    return asyncio.run(run())


@pytest.mark.parametrize("status, expected", [(200, v2_client.V2Answer(None)), (404, v2_client.V2Answer(404, b""))])
def test_a_v2_answer_with_stacked_gzip_is_never_read(status, expected):
    answer = v2(lambda request: bomb_response(status), lambda: v2_client.v2_request("GET", "/v2/threads", IDENTITY))
    assert answer == expected


def test_v2_asks_for_identity():
    seen = []

    def handler(request):
        seen.append(request.headers["accept-encoding"])
        return httpx.Response(200, json={})

    v2(handler, lambda: v2_client.v2_request("GET", "/v2/threads", IDENTITY))
    assert seen == ["identity"]


def test_an_encoded_v2_chat_stream_is_refused_and_closed():
    stream = RawStream(b"data: {}\n\n")
    answer = v2(
        lambda request: httpx.Response(200, headers={"content-encoding": "gzip"}, stream=stream),
        lambda: v2_client.open_v2_stream("/v2/chat/x", IDENTITY, {"m": 1}),
    )
    assert answer == v2_client.V2Answer(None) and stream.sent == 0


def test_an_encoded_v2_refusal_reads_as_no_reason():
    answer = v2(lambda request: bomb_response(409), lambda: v2_client.open_v2_stream("/v2/chat/x", IDENTITY, {"m": 1}))
    assert answer == v2_client.V2Answer(409, b"")


def test_an_identity_v2_chat_stream_passes_byte_for_byte():
    raw = b': keepalive\n\ndata: {"type": "start"}\n\n'

    async def collect():
        opened = await v2_client.open_v2_stream("/v2/chat/x", IDENTITY, {"m": 1})
        return b"".join([chunk async for chunk in opened.chunks()])

    assert v2(lambda request: httpx.Response(200, stream=RawStream(raw, chunk=7)), collect) == raw


# ── v1 ────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def _no_db():
    yield None


def v1_stream(handler) -> bytes:
    seen = []

    def client(**kwargs):
        def recording(request):
            seen.append(request)
            return handler(request)

        return _RealAsyncClient(transport=httpx.MockTransport(recording), timeout=kwargs.get("timeout"))

    async def run():
        with patch.object(universal, "get_db_session", _no_db), patch.object(
            universal,
            "get_connector_info_from_db",
            AsyncMock(return_value=CONNECTOR),
        ), patch.object(universal.httpx, "AsyncClient", client):
            return b"".join([chunk async for chunk in universal.send_post_request_sse("/message", data={"message": "hi"})])

    return asyncio.run(run()), seen


def error_text(body: bytes) -> str:
    return json.loads(body[len(b"data: ") : -2])["error"]


def test_an_encoded_v1_stream_is_the_fixed_error_event():
    body, seen = v1_stream(lambda request: bomb_response(200))
    assert error_text(body) == "Failed to stream from /message"
    assert seen[0].headers["accept-encoding"] == "identity"


def test_an_encoded_v1_refusal_is_the_fixed_text():
    body, _ = v1_stream(lambda request: bomb_response(400))
    assert error_text(body) == "Failed to stream from /message"


def test_an_identity_v1_stream_passes_unchanged():
    raw = b'data: {"text": "a"}\n\ndata: [DONE]\n\n'
    body, _ = v1_stream(lambda request: httpx.Response(200, stream=RawStream(raw, chunk=5)))
    assert body == raw


def test_a_deeply_nested_v1_refusal_is_no_reason():
    assert universal.refusal_reason(400, b"[" * 4000) is None
