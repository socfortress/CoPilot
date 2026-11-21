"""Read a CAPE report into its summary without the event loop ever parsing it (#1361).

The backend is one process with one event loop. A CAPE report runs to tens of MB (59 MB in
#1361), and parsing it stalled every request: ``json.loads`` holds the GIL for the whole
parse, so moving it to a thread doesn't help. Measured on a 59 MB report: 708 ms of stall
inline, 744 ms with ``asyncio.to_thread``.

So the report never reaches this process as a whole. Its chunks go, as they arrive from
CAPE, into the stdin of ``report_worker`` (a separate Python process), which parses and
summarises it and answers with the summary, a few hundred KB to a few MB. The pipes are
served by a small thread pool of their own; the loop only hands chunks over. No file is
written: the report, which quotes the sample, never touches the CoPilot host's disk.

Bounds: the report's size (``max_bytes``, from ``CAPE_REPORT_MAX_MB``), the time to read and
summarise it (``timeout``, ``CAPE_REPORT_TIMEOUT``), the summary's size
(``SUMMARY_MAX_BYTES``) and the number of reports read at once (``REPORT_SLOTS``: each
worker holds a parsed report). Every refusal is a ``ReportUnavailable`` whose text is fixed.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import IO
from typing import Any
from typing import AsyncIterator
from typing import Dict
from typing import Tuple

from loguru import logger

from app.file_analysis.services.sandbox.base import ReportUnavailable

WORKER_MODULE = "app.file_analysis.services.sandbox.report_worker"
# The worker's exit codes, besides 0.
EXIT_NOT_JSON = 3
EXIT_NOT_A_REPORT = 4
EXIT_SUMMARY_FAILED = 5
# The directory holding the ``app`` package: the worker runs with it as its working
# directory, so ``python -m`` finds the module however the backend was started.
_BACKEND_DIR = Path(__file__).resolve().parents[4]

# A worker holds a parsed report, several times the report's size, so two at most.
REPORT_SLOTS = 2
# The summary is a few hundred KB to a few MB; this only stops a runaway answer.
SUMMARY_MAX_BYTES = 64 * 1024 * 1024
_STDERR_MAX_BYTES = 16 * 1024
_PIPE_CHUNK = 64 * 1024

_slots = asyncio.Semaphore(REPORT_SLOTS)
# Three pipe jobs per report (stdin writes, stdout and stderr reads). A pool of their own,
# so a report being read for minutes never holds the default executor's threads.
_pipes = ThreadPoolExecutor(max_workers=3 * REPORT_SLOTS + 2, thread_name_prefix="cape-report")


def too_large(max_bytes: int) -> ReportUnavailable:
    return ReportUnavailable(
        f"The CAPE report is larger than CoPilot reads ({max_bytes // (1024 * 1024)} MB, CAPE_REPORT_MAX_MB).",
    )


async def summarize_stream(chunks: AsyncIterator[bytes], *, max_bytes: int, timeout: float) -> Dict[str, Any]:
    """The ``CapeSummary`` dict of the report ``chunks`` make up.

    ``chunks`` is closed whatever happens. An error it raises (a dropped download) is
    re-raised as it is, so the caller can retry; anything wrong with the report itself is a
    ``ReportUnavailable``.
    """
    async with contextlib.aclosing(chunks):
        async with _slots:
            try:
                async with asyncio.timeout(timeout):
                    return await _summarize(chunks, max_bytes)
            except TimeoutError:
                raise ReportUnavailable(
                    f"Reading the CAPE report took longer than CoPilot waits ({timeout:g} s, CAPE_REPORT_TIMEOUT).",
                ) from None


async def _summarize(chunks: AsyncIterator[bytes], max_bytes: int) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    try:
        worker = subprocess.Popen(
            [sys.executable, "-m", WORKER_MODULE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=_BACKEND_DIR,
        )
    except OSError as exc:
        logger.error(f"could not start the CAPE report worker: {exc}")
        raise ReportUnavailable("CoPilot could not start the process that reads the CAPE report.") from None
    stdout = loop.run_in_executor(_pipes, _read_capped, worker.stdout, SUMMARY_MAX_BYTES)
    stderr = loop.run_in_executor(_pipes, _read_capped, worker.stderr, _STDERR_MAX_BYTES)
    try:
        received = 0
        async for chunk in chunks:
            received += len(chunk)
            if received > max_bytes:
                raise too_large(max_bytes)
            try:
                await loop.run_in_executor(_pipes, worker.stdin.write, chunk)
            except (BrokenPipeError, ValueError):
                # The worker stopped reading: it exited. Its exit code says why.
                break
        with contextlib.suppress(BrokenPipeError, ValueError):
            await loop.run_in_executor(_pipes, worker.stdin.close)
        returncode = await loop.run_in_executor(_pipes, worker.wait)
        summary, summary_cut = await stdout
        errors, _ = await stderr
    finally:
        _stop(worker)
        # Left behind when the read ended early; they finish at the worker's exit.
        for reader in (stdout, stderr):
            reader.add_done_callback(_settle)

    if returncode != 0:
        detail = errors.decode("utf-8", "replace").strip()[-2000:]
        logger.warning(f"CAPE report worker exited with {returncode}: {detail or '<no output>'}")
        raise _failure(returncode)
    if summary_cut:
        raise ReportUnavailable(
            f"The summary of the CAPE report is larger than CoPilot stores ({SUMMARY_MAX_BYTES // (1024 * 1024)} MB).",
        )
    try:
        parsed = json.loads(summary)
    except ValueError:
        parsed = None
    if not isinstance(parsed, dict):
        raise ReportUnavailable("CoPilot could not read the summary of the CAPE report.")
    return parsed


def _failure(returncode: int) -> ReportUnavailable:
    if returncode == EXIT_NOT_JSON:
        return ReportUnavailable("The CAPE report is not valid JSON.")
    if returncode == EXIT_NOT_A_REPORT:
        return ReportUnavailable("CAPE's answer is not a report.")
    if returncode < 0:
        # Killed by a signal: on a host short of memory, the kernel's OOM killer.
        return ReportUnavailable(
            f"The process reading the CAPE report was stopped (signal {-returncode}); the host may be short of memory.",
        )
    return ReportUnavailable("CoPilot could not summarise the CAPE report.")


def _read_capped(stream: IO[bytes], cap: int) -> Tuple[bytes, bool]:
    """Read ``stream`` to its end and close it, keeping at most ``cap`` bytes.

    It keeps reading past the cap, discarding, so the worker never blocks on a full pipe.
    Returns the bytes kept and whether any were dropped.
    """
    kept = bytearray()
    cut = False
    try:
        while True:
            chunk = stream.read(_PIPE_CHUNK)
            if not chunk:
                return bytes(kept), cut
            room = cap - len(kept)
            if len(chunk) > room:
                cut = True
                if room > 0:
                    kept += chunk[:room]
            else:
                kept += chunk
    finally:
        stream.close()


def _settle(future: asyncio.Future) -> None:
    """Collect an abandoned reader's outcome, so asyncio never reports it as unretrieved."""
    if not future.cancelled():
        future.exception()


def _stop(worker: subprocess.Popen) -> None:
    """Make sure the worker is gone and reaped, whatever path left ``_summarize``.

    Its stdout and stderr are closed by their readers, which see the end of the stream as
    soon as the worker is gone.
    """
    if worker.poll() is None:
        worker.kill()
        try:
            worker.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover — a killed process exits
            logger.error(f"CAPE report worker {worker.pid} did not exit after being killed")
    if worker.stdin is not None:
        with contextlib.suppress(OSError, ValueError):
            worker.stdin.close()
