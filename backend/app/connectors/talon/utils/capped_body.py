"""Byte-capped reads of upstream bodies for the Talon connector (talon-analyst, Phoenix; review of #1271).

httpx decodes a ``Content-Encoding`` with ``zlib.decompress`` and no output limit, once per listed
encoding, so a few hundred wire bytes of stacked ``gzip, gzip`` inflate into hundreds of megabytes
inside a single chunk, before any cap counting decoded bytes sees it. So every capped read here:

- asks for ``Accept-Encoding: identity`` (the callers' headers), and
- refuses any answer whose ``Content-Encoding`` is anything but absent or ``identity``
  (``EncodedBody``), and
- reads the **raw** bytes (``aiter_raw``), counting them against the cap.

talon-analyst and Phoenix answer uncompressed when asked to, so a compressed answer is either a
misbehaving or a hostile upstream: it gets the caller's fixed failure, never a decoder.
"""
from typing import AsyncIterator
from typing import Optional

import httpx

IDENTITY = frozenset({"", "identity"})


class EncodedBody(Exception):
    """The answer carries a ``Content-Encoding`` other than identity: it is not decoded."""


async def _raw(response: httpx.Response) -> AsyncIterator[bytes]:
    """The raw bytes. A response already read into memory (an in-process transport's, never a
    network one's) is its content, which for an identity body is the raw bytes."""
    if response.is_stream_consumed:
        yield response.content
        return
    async for chunk in response.aiter_raw():
        yield chunk


def is_identity(response: httpx.Response) -> bool:
    """Whether every ``Content-Encoding`` the answer lists (in any header line) is identity."""
    values = response.headers.get_list("content-encoding")
    return all(token.strip().lower() in IDENTITY for value in values for token in value.split(","))


async def read_capped(response: httpx.Response, limit: int) -> Optional[bytes]:
    """The raw body, or None when it is longer than ``limit``. Raises ``EncodedBody``."""
    if not is_identity(response):
        raise EncodedBody()
    body = bytearray()
    async for chunk in _raw(response):
        body.extend(chunk)
        if len(body) > limit:
            return None
    return bytes(body)


async def read_prefix(response: httpx.Response, limit: int) -> bytes:
    """At most the first ``limit`` raw bytes (a refusal's reason is looked for in them); an encoded
    body reads as nothing, so the caller falls back to its fixed text."""
    if not is_identity(response):
        return b""
    body = bytearray()
    async for chunk in _raw(response):
        body.extend(chunk)
        if len(body) >= limit:
            return bytes(body[:limit])
    return bytes(body)


async def raw_chunks(response: httpx.Response) -> AsyncIterator[bytes]:
    """The raw body as it arrives, unchanged. Raises ``EncodedBody`` before the first chunk."""
    if not is_identity(response):
        raise EncodedBody()
    async for chunk in _raw(response):
        yield chunk
