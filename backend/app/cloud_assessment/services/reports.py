"""Prowler's HTML and CSV reports, kept in MinIO (bucket ``cloud-assessment``).

A report is copied from copilot-prowler to MinIO as it arrives, in parts of ``PART_SIZE``: it
is never held whole in memory nor written to the backend's disk, and its size is capped
(``MAX_REPORT_BYTES``). Its SHA-256 and size are recorded on the scan. Keys are
``scans/<scan id>/prowler-report.<html|csv>``: ids only, nothing a user typed.

A report is served as a download, never as a page of CoPilot's (the download route sets
``Content-Disposition: attachment`` and a sandboxing CSP): Prowler's HTML report holds
resource names and tags from the customer's cloud.
"""

import hashlib
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Tuple

from loguru import logger

from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError
from app.cloud_assessment.services.runner_client import raw_chunks

BUCKET = "cloud-assessment"
PART_SIZE = 16 << 20
MAX_REPORT_BYTES = 512 << 20
READ_CHUNK = 64 << 10
CONTENT_TYPES = {"html": "text/html; charset=utf-8", "csv": "text/csv; charset=utf-8"}


class ReportTooLarge(Exception):
    pass


async def _client():
    """A MinIO client (the unit tests replace this)."""
    from app.data_store.data_store_session import create_session

    return await create_session()


async def _close(client) -> None:
    close = getattr(client, "close_session", None)
    if close is not None:
        try:
            await close()
        except Exception:  # noqa: BLE001 - closing must not mask what happened before
            pass


def object_key(scan_id: int, kind: str) -> str:
    return f"scans/{int(scan_id)}/prowler-report.{kind}"


class _Reader:
    """``put_object``'s ``read(size)`` over a runner response's raw chunks, hashing and counting as it goes."""

    def __init__(self, response, limit: int = MAX_REPORT_BYTES) -> None:
        self._chunks = raw_chunks(response)
        self._buffer = bytearray()
        self._done = False
        self._limit = limit
        self.size = 0
        self._sha256 = hashlib.sha256()

    async def read(self, size: int = -1) -> bytes:
        size = size if size and size > 0 else PART_SIZE
        while not self._done and len(self._buffer) < size:
            try:
                chunk = await self._chunks.__anext__()
            except StopAsyncIteration:
                self._done = True
                break
            self.size += len(chunk)
            if self.size > self._limit:
                raise ReportTooLarge()
            self._sha256.update(chunk)
            self._buffer.extend(chunk)
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def hexdigest(self) -> str:
        return self._sha256.hexdigest()


async def store_artifact(runner: RunnerClient, job_id: str, kind: str, scan_id: int) -> Optional[Dict[str, Any]]:
    """Copy one of the scan's reports from copilot-prowler into MinIO.

    ``{"key", "size", "sha256"}``, or None when the runner has no such report. Raises
    ``RunnerError`` when the runner can't be read, and anything MinIO raises.
    """
    key = object_key(scan_id, kind)
    client = await _client()
    try:
        if not await client.bucket_exists(BUCKET):
            await client.make_bucket(BUCKET)
        try:
            async with runner.artifact(job_id, kind) as response:
                reader = _Reader(response)
                await client.put_object(
                    BUCKET,
                    key,
                    reader,
                    length=-1,
                    part_size=PART_SIZE,
                    content_type=CONTENT_TYPES[kind],
                    num_parallel_uploads=1,
                )
        except RunnerError as error:
            if error.reason == "not_found" and error.code == "no_artifact":
                return None
            raise
        return {"key": key, "size": reader.size, "sha256": reader.hexdigest()}
    finally:
        await _close(client)


async def open_report(bucket: str, key: str) -> AsyncIterator[bytes]:
    """The report's bytes, as an iterator that closes its connection when it ends (or is closed).
    Raises before returning when MinIO doesn't have the object."""
    client = await _client()
    try:
        response = await client.get_object(bucket_name=bucket, object_name=key)
    except Exception:
        await _close(client)
        raise

    async def chunks() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.content.iter_chunked(READ_CHUNK):
                yield chunk
        finally:
            response.release()
            await _close(client)

    return chunks()


async def delete_objects(objects: Iterable[Tuple[str, str]]) -> int:
    """Delete these (bucket, key) objects, best effort: a failure is logged, never raised. How many went."""
    pairs = [(bucket, key) for bucket, key in objects if bucket and key]
    if not pairs:
        return 0
    deleted = 0
    client = await _client()
    try:
        for bucket, key in pairs:
            try:
                await client.remove_object(bucket, key)
                deleted += 1
            except Exception as error:  # noqa: BLE001 - one object must not stop the rest
                logger.warning(f"Cloud assessment: couldn't delete report {key}: {type(error).__name__}")
    finally:
        await _close(client)
    return deleted
