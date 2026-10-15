"""The Talon chat proxy's error text (``send_post_request_sse``).

Every upstream failure used to read "Failed to stream from /message", so a user whose
message Talon refused (empty, a bad user id, a wrong API key) could not tell that apart
from Talon being down. Now:
- a 4xx whose reason is one short printable line (``{"detail": "…"}`` or
  ``{"error": "…"}``) is passed through as the SSE error text;
- anything else (a 5xx, a 422's structured detail, a long, multi-line or non-JSON body, a
  connection error) gets the fixed text, so no upstream error body and no exception text
  reaches the user.

Upstream is an ``httpx.MockTransport``; no network, no DB.

Run with: cd backend && python -m pytest tests/test_talon_sse_refusal.py
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402

from app.connectors.talon.utils import universal  # noqa: E402
from app.connectors.talon.utils.universal import refusal_reason  # noqa: E402

FIXED = "Failed to stream from /message"
_RealAsyncClient = httpx.AsyncClient


@asynccontextmanager
async def _no_db():
    yield None


def _stream(handler) -> bytes:
    """Everything ``send_post_request_sse`` yields when Talon answers with ``handler``."""

    def client(**kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout"))

    async def run():
        connector = {"connector_url": "http://talon.invalid", "connector_api_key": "k"}
        with patch.object(universal, "get_db_session", _no_db), patch.object(
            universal,
            "get_connector_info_from_db",
            AsyncMock(return_value=connector),
        ), patch.object(universal.httpx, "AsyncClient", client):
            return b"".join([chunk async for chunk in universal.send_post_request_sse("/message", data={"message": ""})])

    return asyncio.run(run())


def _error_text(body: bytes) -> str:
    assert body.startswith(b"data: ") and body.endswith(b"\n\n"), body
    return json.loads(body[len(b"data: ") : -2])["error"]


def _answer(status, payload=None, content=None):
    def handler(request):
        if content is not None:
            return httpx.Response(status, content=content)
        return httpx.Response(status, json=payload)

    return handler


# ── what reaches the user ─────────────────────────────────────────────────────


def test_a_4xx_reason_is_passed_through():
    body = _stream(_answer(400, {"detail": "message is required"}))
    assert _error_text(body) == "Talon refused the request: message is required"


def test_talon_s_unauthorized_body_is_passed_through():
    assert _error_text(_stream(_answer(401, {"error": "Unauthorized"}))) == "Talon refused the request: Unauthorized"


def test_a_5xx_gives_the_fixed_text_never_its_body():
    body = _stream(_answer(500, {"detail": "Traceback: secret at /srv/talon"}))
    assert _error_text(body) == FIXED
    assert b"secret" not in body


def test_a_502_from_a_proxy_gives_the_fixed_text():
    assert _error_text(_stream(_answer(502, content=b"<html>Bad Gateway</html>"))) == FIXED


def test_an_unusable_4xx_reason_gives_the_fixed_text():
    for status, payload, content in [
        (422, {"detail": [{"loc": ["body", "message"], "msg": "field required"}]}, None),
        (400, {"detail": "x" * 201}, None),
        (400, {"detail": "line one\nline two"}, None),
        (400, {"detail": "café"}, None),
        (400, {"detail": ""}, None),
        (400, None, b"not json"),
        (400, None, b"\xff\xfe"),
        (404, ["a", "list"], None),
    ]:
        assert _error_text(_stream(_answer(status, payload, content))) == FIXED, (status, payload, content)


def test_a_connection_error_gives_the_fixed_text_never_the_exception():
    def handler(request):
        raise httpx.ConnectError("connect to 10.0.0.7:3100 refused")

    body = _stream(handler)
    assert _error_text(body) == FIXED
    assert b"10.0.0.7" not in body


def test_a_successful_stream_passes_through_byte_for_byte():
    sse = b'data: {"type":"text","content":"hi"}\n\n: keepalive\n\ndata: {"type":"done"}\n\n'
    assert _stream(_answer(200, content=sse)) == sse


# ── refusal_reason itself ─────────────────────────────────────────────────────


def test_refusal_reason_prefers_detail_and_reads_only_4xx():
    assert refusal_reason(400, b'{"detail": "a", "error": "b"}') == "a"
    assert refusal_reason(429, b'{"error": "busy"}') == "busy"
    assert refusal_reason(500, b'{"detail": "a"}') is None
    assert refusal_reason(302, b'{"detail": "a"}') is None


def test_refusal_reason_accepts_the_longest_allowed_line():
    assert refusal_reason(400, json.dumps({"detail": "y" * 200}).encode()) == "y" * 200
