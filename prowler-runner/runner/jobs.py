"""Scan jobs: one ``prowler`` process each, then one normalizer process.

Jobs live in memory. The runner is a single process (uvicorn's default of one
worker), and a restart forgets its jobs and empties its work directory, credential
files included: the backend then gets a 404 for the job and marks the scan failed.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import signal
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path

from runner.commands import ScanCommand
from runner.commands import build_scan_command
from runner.errors import MESSAGES
from runner.errors import RunnerError
from runner.errors import classify_failure
from runner.layout import COMPLIANCE_DIR
from runner.layout import CSV_FILE
from runner.layout import FINDINGS_FILE
from runner.layout import HTML_FILE
from runner.layout import JOB_ID
from runner.layout import OCSF_FILE
from runner.layout import OUT_DIR
from runner.layout import SECRETS_DIR
from runner.layout import SUMMARY_FILE
from runner.logs import LogCollector
from runner.models import ScanRequest
from runner.settings import Settings

logger = logging.getLogger("prowler_runner")

APP_ROOT = Path(__file__).resolve().parent.parent
# What the runner itself creates in its work directory. Anything else there is left alone,
# so a work directory set to the wrong path is never emptied.
OWN_ENTRY = re.compile(r"^(conn-)?[0-9a-f]{32}$")
TERMINATE_GRACE_SECONDS = 10
READER_GRACE_SECONDS = 10
REAP_INTERVAL_SECONDS = 60
READ_CHUNK = 64 * 1024
MAX_LOG_LINE = 64 * 1024
ARTIFACTS = {"html": (HTML_FILE, "text/html; charset=utf-8"), "csv": (CSV_FILE, "text/csv; charset=utf-8")}


class JobStatus(str, Enum):
    RUNNING = "running"
    NORMALIZING = "normalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE = (JobStatus.RUNNING, JobStatus.NORMALIZING)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


@dataclass
class Job:
    id: str
    provider: str
    dir: Path
    timeout: int
    prowler_version: str | None = None
    created_at: datetime = field(default_factory=_now)
    status: JobStatus = JobStatus.RUNNING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    finished_monotonic: float | None = None
    exit_code: int | None = None
    error_code: str | None = None
    prowler_errors: list[str] = field(default_factory=list)
    logs: dict = field(default_factory=dict)
    totals: dict | None = None
    process: asyncio.subprocess.Process | None = None
    task: asyncio.Task | None = None
    cancel_requested: bool = False

    @property
    def out_dir(self) -> Path:
        return self.dir / OUT_DIR

    @property
    def secrets_dir(self) -> Path:
        return self.dir / SECRETS_DIR

    def public(self) -> dict:
        error = None
        if self.error_code:
            error = {"code": self.error_code, "message": MESSAGES[self.error_code], "prowler_errors": self.prowler_errors}
        return {
            "job_id": self.id,
            "provider": self.provider,
            "status": self.status.value,
            "prowler_version": self.prowler_version,
            "created_at": _iso(self.created_at),
            "started_at": _iso(self.started_at),
            "finished_at": _iso(self.finished_at),
            "timeout_seconds": self.timeout,
            "exit_code": self.exit_code,
            "error": error,
            # How many checks logged an error in a scan that still finished (a missing permission, usually).
            "logs": self.logs or None,
            "totals": self.totals,
        }


def _signal_group(pid: int, signal_number: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, signal_number)


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def drop_raw_output(out_dir: Path) -> None:
    """Delete what is never served: the OCSF file (raw resource configuration) and the compliance CSVs."""
    with contextlib.suppress(FileNotFoundError):
        (out_dir / OCSF_FILE).unlink()
    remove_tree(out_dir / COMPLIANCE_DIR)


def prepare_work_dir(work_dir: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(work_dir, 0o700)
    for entry in work_dir.iterdir():
        if not OWN_ENTRY.match(entry.name):
            continue
        if entry.is_dir() and not entry.is_symlink():
            remove_tree(entry)
        else:
            entry.unlink(missing_ok=True)


def _create_job_dir(job: Job, secret_files: dict[str, bytes]) -> None:
    os.mkdir(job.dir, 0o700)
    os.mkdir(job.out_dir, 0o700)
    os.mkdir(job.secrets_dir, 0o700)
    for name, content in secret_files.items():
        descriptor = os.open(job.secrets_dir / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)


def _read_totals(summary_path: Path) -> dict:
    with open(summary_path, encoding="utf-8") as handle:
        summary = json.load(handle)
    return {**summary.get("totals", {}), "fail_by_severity": summary.get("fail_by_severity", {})}


async def read_lines(stream: asyncio.StreamReader, feed: Callable[[str], None]) -> None:
    """Pass each line of `stream` to `feed`; a line longer than MAX_LOG_LINE is dropped."""
    pending = b""
    while True:
        chunk = await stream.read(READ_CHUNK)
        if not chunk:
            break
        pending += chunk
        *lines, pending = pending.split(b"\n")
        for line in lines:
            feed(line.decode("utf-8", "replace"))
        if len(pending) > MAX_LOG_LINE:
            pending = b""
    if pending:
        feed(pending.decode("utf-8", "replace"))


class JobManager:
    def __init__(self, settings: Settings, prowler_version: str | None = None) -> None:
        self.settings = settings
        self.prowler_version = prowler_version
        self.jobs: dict[str, Job] = {}
        self._admission = asyncio.Lock()
        self._reaper: asyncio.Task | None = None

    async def startup(self) -> None:
        await asyncio.to_thread(prepare_work_dir, self.settings.work_dir)
        self._reaper = asyncio.create_task(self._reap_forever(), name="reaper")

    async def shutdown(self) -> None:
        if self._reaper:
            self._reaper.cancel()
        for job in list(self.jobs.values()):
            if job.status in ACTIVE:
                job.cancel_requested = True
                await self.terminate(job)
        tasks = [job.task for job in self.jobs.values() if job.task and not job.task.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self._reaper:
            await asyncio.gather(self._reaper, return_exceptions=True)

    def active_count(self) -> int:
        return sum(1 for job in self.jobs.values() if job.status in ACTIVE)

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id) if JOB_ID.match(job_id) else None
        if job is None:
            raise RunnerError(404, "not_found")
        return job

    def completed(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status is not JobStatus.COMPLETED:
            raise RunnerError(409, "not_ready")
        return job

    def job_file(self, job: Job, *parts: str) -> Path:
        """A file of `job`'s, built from the runner's own work directory and the job's id (never a
        request's text), and resolved to make sure it lies inside the work directory."""
        base = os.path.realpath(self.settings.work_dir)
        target = os.path.realpath(os.path.join(base, os.path.basename(job.id), *(os.path.basename(part) for part in parts)))
        if os.path.commonpath([base, target]) != base:
            raise RunnerError(404, "not_found")
        return Path(target)

    def summary_path(self, job: Job) -> Path:
        return self.job_file(job, SUMMARY_FILE)

    def findings_path(self, job: Job) -> Path:
        return self.job_file(job, FINDINGS_FILE)

    def artifact(self, job: Job, kind: str) -> tuple[Path, str, str]:
        """The report's path, media type and download name (built from the job's own id, never the request's)."""
        if kind not in ARTIFACTS:
            raise RunnerError(404, "no_artifact")
        name, media_type = ARTIFACTS[kind]
        path = self.job_file(job, OUT_DIR, name)
        if not path.is_file():
            raise RunnerError(404, "no_artifact")
        return path, media_type, f"prowler-{job.id}{Path(name).suffix}"

    async def start(self, request: ScanRequest) -> Job:
        async with self._admission:
            if self.active_count() >= self.settings.max_concurrent:
                raise RunnerError(429, "busy")
            if len(self.jobs) >= self.settings.max_jobs:
                raise RunnerError(429, "too_many_jobs")
            job_id = uuid.uuid4().hex
            job = Job(
                id=job_id,
                provider=request.provider,
                dir=self.settings.work_dir / job_id,
                timeout=request.options.timeout_seconds or self.settings.scan_timeout,
                prowler_version=self.prowler_version,
            )
            command = build_scan_command(request, self.settings, job.out_dir, job.secrets_dir)
            try:
                _create_job_dir(job, command.secret_files)
            except OSError as error:
                remove_tree(job.dir)
                logger.error("scan %s: its directory could not be created (%s)", job.id, type(error).__name__)
                raise RunnerError(500, "internal") from None
            self.jobs[job.id] = job
            job.task = asyncio.create_task(self._run(job, command), name=f"scan-{job.id}")
        return job

    async def delete(self, job_id: str) -> None:
        """Cancel the scan if it is still running, then forget it and delete its files."""
        job = self.get(job_id)
        if job.status in ACTIVE:
            job.cancel_requested = True
            await self.terminate(job)
        if job.task and not job.task.done():
            try:
                await asyncio.wait_for(asyncio.shield(job.task), TERMINATE_GRACE_SECONDS * 3)
            except TimeoutError:
                job.task.cancel()
                await asyncio.gather(job.task, return_exceptions=True)
        self.jobs.pop(job.id, None)
        await asyncio.to_thread(remove_tree, job.dir)

    async def terminate(self, job: Job) -> None:
        process = job.process
        if process is None or process.returncode is not None:
            return
        _signal_group(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), TERMINATE_GRACE_SECONDS)
        except TimeoutError:
            _signal_group(process.pid, signal.SIGKILL)
            await process.wait()

    async def reap(self, now: float | None = None) -> int:
        """Forget finished jobs older than PROWLER_JOB_TTL_SECONDS and delete their files."""
        now = time.monotonic() if now is None else now
        expired = [
            job
            for job in self.jobs.values()
            if job.status not in ACTIVE and job.finished_monotonic is not None and now - job.finished_monotonic >= self.settings.job_ttl
        ]
        for job in expired:
            self.jobs.pop(job.id, None)
            await asyncio.to_thread(remove_tree, job.dir)
        return len(expired)

    async def _reap_forever(self) -> None:
        while True:
            await asyncio.sleep(REAP_INTERVAL_SECONDS)
            try:
                await self.reap()
            except Exception as error:  # noqa: BLE001 - the reaper must outlive one bad pass
                logger.error("reaper: %s", type(error).__name__)

    def _finish(self, job: Job, status: JobStatus, code: str | None) -> None:
        if job.status not in ACTIVE:
            return
        job.status = status
        job.error_code = code if status is not JobStatus.COMPLETED else None
        job.finished_at = _now()
        job.finished_monotonic = time.monotonic()
        logger.info("scan %s: %s%s", job.id, status.value, f" ({code})" if code else "")

    async def _run(self, job: Job, command: ScanCommand) -> None:
        try:
            await self._scan(job, command)
            if job.status is JobStatus.NORMALIZING:
                await self._normalize(job)
        except asyncio.CancelledError:
            await self.terminate(job)
            self._finish(job, JobStatus.CANCELLED, "cancelled")
            raise
        except Exception as error:  # noqa: BLE001 - a job must always end in a final state
            logger.error("scan %s: runner error (%s)", job.id, type(error).__name__)
            await self.terminate(job)
            self._finish(job, JobStatus.FAILED, "internal")
        finally:
            remove_tree(job.secrets_dir)
            drop_raw_output(job.out_dir)

    async def _scan(self, job: Job, command: ScanCommand) -> None:
        job.started_at = _now()
        collector = LogCollector()
        try:
            job.process = await asyncio.create_subprocess_exec(
                *command.argv,
                env=command.env,
                cwd=str(job.dir),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as error:
            logger.error("scan %s: Prowler could not be started (%s)", job.id, type(error).__name__)
            self._finish(job, JobStatus.FAILED, "internal")
            return
        logger.info("scan %s: %s scan started", job.id, job.provider)
        reader = asyncio.create_task(read_lines(job.process.stdout, collector.feed))
        timed_out = False
        try:
            await asyncio.wait_for(job.process.wait(), timeout=job.timeout)
        except TimeoutError:
            timed_out = True
            await self.terminate(job)
        # Whatever Prowler started (PowerShell, Trivy) goes with it.
        _signal_group(job.process.pid, signal.SIGKILL)
        try:
            await asyncio.wait_for(reader, READER_GRACE_SECONDS)
        except TimeoutError:
            reader.cancel()
        remove_tree(job.secrets_dir)
        job.exit_code = job.process.returncode
        job.logs = collector.summary()
        if job.cancel_requested:
            self._finish(job, JobStatus.CANCELLED, "cancelled")
        elif timed_out:
            self._finish(job, JobStatus.FAILED, "timeout")
        elif job.exit_code not in (0, 3):
            job.prowler_errors = collector.failure_names()
            # 2 is argparse refusing the command line.
            code = (
                "invalid_request"
                if job.exit_code == 2
                else classify_failure(collector.critical_names, collector.error_names, collector.reasons)
            )
            self._finish(job, JobStatus.FAILED, code)
        else:
            job.status = JobStatus.NORMALIZING

    async def _normalize(self, job: Job) -> None:
        argv = [sys.executable, "-m", "runner.normalize_cli", str(job.dir), job.provider]
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
        job.process = await asyncio.create_subprocess_exec(
            *argv,
            env=env,
            cwd=str(APP_ROOT),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            exit_code = await asyncio.wait_for(job.process.wait(), timeout=self.settings.normalize_timeout)
        except TimeoutError:
            await self.terminate(job)
            exit_code = None
        if job.cancel_requested:
            self._finish(job, JobStatus.CANCELLED, "cancelled")
            return
        if exit_code != 0:
            self._finish(job, JobStatus.FAILED, "output_invalid")
            return
        drop_raw_output(job.out_dir)
        job.totals = await asyncio.to_thread(_read_totals, job.dir / SUMMARY_FILE)
        self._finish(job, JobStatus.COMPLETED, None)
