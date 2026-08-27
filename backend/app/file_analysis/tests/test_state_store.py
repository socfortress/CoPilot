"""state_store retry behaviour — a transient MinIO blip must not abort an analysis.

Pure: no MinIO contacted. We drive ``_retry`` with fake ops so the policy (retry
transient, give up after N, never retry a logical S3 error) is asserted directly.

These are plain sync tests that drive the coroutine via ``asyncio.run`` — this repo
has no pytest-asyncio plugin configured, so ``@pytest.mark.asyncio`` tests are
silently skipped, which would let a regression pass unnoticed.
"""
from __future__ import annotations

import asyncio

import pytest

from app.file_analysis.services import state_store


class _FakeS3Error(Exception):
    """Stands in for miniopy_async S3Error (NoSuchKey etc.) — NOT a transient error."""


def test_retry_recovers_from_transient_blip(monkeypatch):
    monkeypatch.setattr(state_store, "_MINIO_BACKOFF", 0.0)  # no real sleeping in tests
    monkeypatch.setattr(state_store, "_MINIO_RETRIES", 4)
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("semaphore timeout period has expired")
        return "saved"

    assert asyncio.run(state_store._retry("put", op)) == "saved"
    assert calls["n"] == 3  # failed twice, succeeded on the third attempt


def test_retry_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(state_store, "_MINIO_BACKOFF", 0.0)
    monkeypatch.setattr(state_store, "_MINIO_RETRIES", 3)
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        raise TimeoutError("still down")  # asyncio.TimeoutError is this on 3.11

    with pytest.raises(TimeoutError):
        asyncio.run(state_store._retry("put", op))
    assert calls["n"] == 3  # exactly _MINIO_RETRIES attempts, then re-raise


def test_retry_does_not_retry_logical_s3_error(monkeypatch):
    monkeypatch.setattr(state_store, "_MINIO_BACKOFF", 0.0)
    monkeypatch.setattr(state_store, "_MINIO_RETRIES", 4)
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        raise _FakeS3Error("NoSuchKey")

    with pytest.raises(_FakeS3Error):
        asyncio.run(state_store._retry("stat", op))
    assert calls["n"] == 1  # non-transient -> surfaced immediately, no wasted retries
