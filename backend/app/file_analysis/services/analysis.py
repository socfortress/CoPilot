"""Job orchestration: submission, analysis, persistence, fan-out.

The lifecycle is ``pending -> running -> completed | failed`` (#974 §A).

Analysis runs **out of band**, on a background task, for two reasons: parsing is
CPU-bound and would block the event loop for the whole process, and a large
sample would otherwise hold the HTTP request open for a minute. The upload
returns as soon as the bytes are safely in MinIO and the row exists.

A failed job is a first-class outcome, not an error to swallow: "this file could
not be parsed" is triage material, and it stays queryable with the reason on the
row.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.data_store.data_store_operations import retrieve_file_from_minio
from app.data_store.data_store_operations import store_file_in_minio
from app.db.db_session import get_db_session
from app.db.universal_models import Customers
from app.file_analysis.models.file_analysis import FileAnalysisFinding
from app.file_analysis.models.file_analysis import FileAnalysisIoC
from app.file_analysis.models.file_analysis import FileAnalysisJob
from app.file_analysis.services import identify as identify_svc
from app.file_analysis.services import scoring
from app.file_analysis.services.inspectors import select_inspector
from app.file_analysis.services.inspectors.base import InspectorContext
from app.file_analysis.services.inspectors.base import InspectorResult
from app.file_analysis.services.iocs import merge_iocs
from app.file_analysis.services.limits import load_limits
from app.file_analysis.services.shipper import ship_job
from app.middleware.customer_access import customer_access_handler

BUCKET_NAME = "copilot-file-analysis"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Upload is read in chunks so an oversized submission is refused without ever
# holding the whole thing in memory.
READ_CHUNK_SIZE = 1024 * 1024


async def create_job(
    customer_code: str,
    file: UploadFile,
    submitted_by: Optional[str],
    session: AsyncSession,
) -> FileAnalysisJob:
    """Persist an uploaded sample and queue it for analysis."""
    limits = load_limits()

    # Checked before a byte reaches MinIO. customer_code is a real FK, so an
    # unknown code fails on INSERT -- and by then the object is already stored,
    # leaving a blob in the bucket that no row will ever point at or clean up.
    # The scope dependency on the route cannot cover this: it answers "may this
    # caller reach this tenant", not "does this tenant exist".
    exists = await session.scalar(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if not exists:
        raise HTTPException(status_code=404, detail=f"Customer {customer_code} not found")

    data = await _read_capped(file, limits.max_file_size)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Return the connection to the pool before the object-storage upload. With
    # no open transaction SQLAlchemy releases it here and re-acquires for the
    # INSERT below, so a slow MinIO PUT -- up to the full max_file_size -- no
    # longer keeps a connection checked out for its duration. Under a burst of
    # uploads that hold is what pushes the shared pool over its limit.
    await session.commit()

    job_uuid = str(uuid.uuid4())
    safe_name = (file.filename or "sample")[:512]
    object_key = f"{customer_code}/{job_uuid}/{safe_name}"

    stored = await store_file_in_minio(
        file_content=data,
        bucket_name=BUCKET_NAME,
        object_key=object_key,
        content_type=file.content_type or "application/octet-stream",
    )
    if not stored.get("success"):
        raise HTTPException(status_code=502, detail=f"Could not store the file: {stored.get('error', 'unknown error')}")

    job = FileAnalysisJob(
        job_uuid=job_uuid,
        customer_code=customer_code,
        file_name=safe_name,
        submitted_by=submitted_by,
        source="upload",
        bucket_name=BUCKET_NAME,
        object_key=object_key,
        file_size=stored["file_size"],
        file_hash=stored["file_hash"],
        content_type=file.content_type or "application/octet-stream",
        status=STATUS_PENDING,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    logger.info(f"file_analysis: queued job {job_uuid} for customer {customer_code} ({job.file_size} bytes)")
    return job


async def _read_capped(file: UploadFile, max_size: int) -> bytes:
    """Read an upload, refusing anything past the ceiling.

    The check is per chunk rather than on the final buffer: a client that lies
    about Content-Length would otherwise still get the whole file into memory
    before being told no.
    """
    chunks: List[bytes] = []
    total = 0

    while True:
        chunk = await file.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {max_size} byte analysis limit",
            )
        chunks.append(chunk)

    return b"".join(chunks)


class _Sample(NamedTuple):
    """Everything the analysis needs, detached from any session.

    The analysis phase must not hold an ORM object, because it must not hold the
    connection that object belongs to -- see :func:`run_analysis`.
    """

    job_uuid: str
    file_name: str
    bucket_name: str
    object_key: str


_analysis_slots: Optional[asyncio.Semaphore] = None


def _slots() -> asyncio.Semaphore:
    """Concurrency gate for analyses, created on the running loop.

    Built lazily rather than at import: a Semaphore binds to the event loop
    alive when it is constructed, and at import time under uvicorn that is not
    the loop the app will run on.
    """
    global _analysis_slots
    if _analysis_slots is None:
        _analysis_slots = asyncio.Semaphore(load_limits().max_concurrent_analyses)
    return _analysis_slots


async def run_analysis(job_uuid: str) -> None:
    """Analyse one queued job. Safe to call as a background task.

    Two protections against this feature destabilising the rest of the app, both
    learned the hard way against a live stack:

    - **Bounded concurrency.** Every upload queues one of these, so an unbounded
      burst puts N analyses in flight at once, all drawing on the SQLAlchemy pool
      the whole application shares. Waiting for a slot is the difference between
      a slow queue and a deployment where login returns 401.
    - **No connection held across the slow work.** The first version wrapped the
      whole function in one session, keeping a connection checked out for the
      MinIO download and the entire inspector run -- up to the 60s timeout. That
      alone exhausted the pool
      (``QueuePool limit of size 5 overflow 10 reached``).

    Each phase below opens its own short-lived session; the request that queued
    the job is long gone by now, and its session with it.
    """
    async with _slots():
        await _run_analysis(job_uuid)


async def _run_analysis(job_uuid: str) -> None:
    """The analysis itself. Always entered holding a concurrency slot."""
    # -- phase 1: claim the job, then let go of the connection ---------------
    async with get_db_session() as session:
        job = (await session.execute(select(FileAnalysisJob).where(FileAnalysisJob.job_uuid == job_uuid))).scalars().first()
        if job is None:
            logger.error(f"file_analysis: job {job_uuid} vanished before analysis")
            return

        job.status = STATUS_RUNNING
        job.started_at = datetime.utcnow()
        await session.commit()

        started = job.started_at
        sample = _Sample(
            job_uuid=job.job_uuid,
            file_name=job.file_name,
            bucket_name=job.bucket_name,
            object_key=job.object_key,
        )

    # -- phase 2: the slow part, holding nothing -----------------------------
    try:
        result, identification, inspector_name = await _analyse(sample)
    except Exception as exc:
        logger.exception(f"file_analysis: job {job_uuid} failed")
        async with get_db_session() as session:
            await _mark_failed(session, job_uuid, started, exc)
        return

    # -- phase 3: publish the result in a single transaction -----------------
    async with get_db_session() as session:
        job = (await session.execute(select(FileAnalysisJob).where(FileAnalysisJob.job_uuid == job_uuid))).scalars().first()
        if job is None:
            logger.error(f"file_analysis: job {job_uuid} disappeared during analysis")
            return

        job.magic_type = identification.magic_type
        job.mime_type = identification.mime_type
        job.md5 = identification.md5
        job.sha1 = identification.sha1
        job.entropy = identification.entropy
        job.inspector = inspector_name
        job.truncated_reason = result.truncated_reason
        job.score = scoring.score_flags(result.flags)
        job.verdict = scoring.verdict_for(job.score, inspected=inspector_name is not None)
        job.completed_at = datetime.utcnow()
        job.duration_ms = _elapsed_ms(started, job.completed_at)

        findings, iocs = _persist_children(session, job, result, inspector_name)

        # Written last and committed together with the children. Marking the job
        # completed in an earlier commit published a job that polling clients
        # could read as finished while its findings and indicators were still
        # uncommitted -- a completed, empty, wrong-looking result.
        job.status = STATUS_COMPLETED
        await session.commit()

    # -- phase 4: fan out to Graylog, again holding no connection ------------
    # The job objects are detached here. Reading their attributes is safe only
    # because the session factory sets expire_on_commit=False; with the default
    # every access would raise MissingGreenlet under AsyncSession.
    shipped = await ship_job(job, result.flags, iocs)

    async with get_db_session() as session:
        await session.execute(
            update(FileAnalysisJob).where(FileAnalysisJob.job_uuid == job_uuid).values(shipped_to_graylog=shipped),
        )
        await session.commit()

    logger.info(
        f"file_analysis: job {job_uuid} {job.verdict} (score {job.score}, "
        f"{len(findings)} finding(s), {len(iocs)} indicator(s), shipped={shipped})",
    )


async def _mark_failed(session: AsyncSession, job_uuid: str, started: Optional[datetime], exc: Exception) -> None:
    """Record a failure without re-reading the row into the identity map."""
    completed_at = datetime.utcnow()
    await session.execute(
        update(FileAnalysisJob)
        .where(FileAnalysisJob.job_uuid == job_uuid)
        .values(
            status=STATUS_FAILED,
            completed_at=completed_at,
            duration_ms=_elapsed_ms(started, completed_at),
            error_message=str(exc)[:4000],
        ),
    )
    await session.commit()


async def _analyse(job: _Sample) -> Tuple[InspectorResult, identify_svc.Identification, Optional[str]]:
    """Download, identify and inspect. Raises on anything unrecoverable."""
    limits = load_limits()

    retrieved = await retrieve_file_from_minio(job.bucket_name, job.object_key)
    if not retrieved.get("success"):
        raise RuntimeError(f"Could not retrieve the stored file: {retrieved.get('error', 'unknown error')}")

    data: bytes = retrieved["file_content"]
    identification = identify_svc.identify(data)

    result = InspectorResult()

    if identify_svc.contains_eicar(data):
        result.add("generic.eicar", "EICAR-STANDARD-ANTIVIRUS-TEST-FILE")

    if identify_svc.high_entropy_for_type(identification.entropy, identification.mime_type):
        result.add("generic.high_entropy", f"entropy {identification.entropy:.2f} for {identification.mime_type}")

    mismatch = identify_svc.detect_extension_mismatch(data, identification.mime_type, job.file_name)
    if mismatch:
        result.add("generic.extension_mismatch", mismatch)

    inspector = select_inspector(data, identification.mime_type, job.file_name)
    if inspector is None:
        logger.info(f"file_analysis: no inspector claims {identification.mime_type} for job {job.job_uuid}")
        result.iocs = merge_iocs([result.iocs])
        return result, identification, None

    ctx = InspectorContext(
        data=data,
        file_name=job.file_name,
        mime_type=identification.mime_type,
        magic_type=identification.magic_type,
        limits=limits,
    )

    try:
        # Off the event loop, because inspectors are synchronous and CPU-bound;
        # running one inline would stall every other request for its duration.
        #
        # The timeout bounds the *job*, not the thread: Python cannot cancel a
        # running thread, so a wedged parser keeps its worker until it returns.
        # What this guarantees is that the job stops waiting, records why, and
        # reports a partial result instead of hanging forever.
        inspected = await asyncio.wait_for(
            asyncio.to_thread(inspector.inspect, ctx),
            timeout=limits.inspector_timeout_seconds,
        )
        result.merge(inspected)
    except asyncio.TimeoutError:
        logger.warning(f"file_analysis: inspector {inspector.name} timed out on job {job.job_uuid}")
        result.add("limit.inspector_timeout", f"{inspector.name} exceeded {limits.inspector_timeout_seconds}s")
        result.truncated_reason = f"{inspector.name} inspector timed out"

    result.iocs = merge_iocs([result.iocs])
    return result, identification, inspector.name


def _persist_children(
    session: AsyncSession,
    job: FileAnalysisJob,
    result: InspectorResult,
    inspector_name: Optional[str],
) -> Tuple[List[FileAnalysisFinding], List[FileAnalysisIoC]]:
    """Turn the inspector output into finding and IOC rows.

    The catalogue's weight and severity are *copied onto the row* rather than
    referenced, so re-tuning ``FLAG_CATALOGUE`` later never rewrites a verdict
    that has already been reported.
    """
    findings: List[FileAnalysisFinding] = []
    for flag in result.flags:
        spec = scoring.flag_spec(flag)
        finding = FileAnalysisFinding(
            job_id=job.id,
            flag=flag,
            category=spec.category,
            title=spec.title,
            description=None,
            severity=spec.severity,
            weight=spec.weight,
            evidence=result.evidence.get(flag),
            inspector=inspector_name,
        )
        session.add(finding)
        findings.append(finding)

    iocs: List[FileAnalysisIoC] = []
    for extracted in result.iocs:
        ioc = FileAnalysisIoC(
            job_id=job.id,
            ioc_type=extracted.ioc_type,
            value=extracted.value,
            context=extracted.context,
            inspector=inspector_name,
        )
        session.add(ioc)
        iocs.append(ioc)

    return findings, iocs


def _elapsed_ms(start: Optional[datetime], end: Optional[datetime]) -> Optional[int]:
    if not start or not end:
        return None
    return int((end - start).total_seconds() * 1000)


# ---------------------------------------------------------------------------
# Read paths -- every one of them is tenant-scoped
# ---------------------------------------------------------------------------


async def list_jobs(
    user: User,
    session: AsyncSession,
    customer_code: Optional[str] = None,
    status: Optional[str] = None,
    verdict: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[FileAnalysisJob], int]:
    """List jobs the caller may see, newest first."""
    base = select(FileAnalysisJob)
    if status:
        base = base.where(FileAnalysisJob.status == status)
    if verdict:
        base = base.where(FileAnalysisJob.verdict == verdict)

    requested = [customer_code] if customer_code else None
    scoped = await customer_access_handler.filter_query_by_customer_access(
        user=user,
        session=session,
        base_query=base,
        customer_code_field=FileAnalysisJob.customer_code,
        requested_customers=requested,
    )

    total = await session.scalar(select(func.count()).select_from(scoped.subquery()))

    rows = (
        (
            await session.execute(
                scoped.order_by(FileAnalysisJob.submitted_at.desc()).limit(limit).offset(offset),
            )
        )
        .scalars()
        .all()
    )

    return list(rows), int(total or 0)


async def get_job(job_uuid: str, user: User, session: AsyncSession) -> FileAnalysisJob:
    """Fetch one job, refusing it outright when it belongs to another tenant.

    Filtering the *list* is not enough. A caller who guesses or is given a UUID
    must be stopped here, which is why this raises rather than returning None
    for an inaccessible job -- and why the API addresses jobs by UUID, so ids
    cannot be walked in the first place.
    """
    job = (await session.execute(select(FileAnalysisJob).where(FileAnalysisJob.job_uuid == job_uuid))).scalars().first()
    if job is None:
        raise HTTPException(status_code=404, detail="File analysis job not found")

    await customer_access_handler.enforce_customer_access(user, job.customer_code, session)
    return job


async def get_findings(job: FileAnalysisJob, session: AsyncSession) -> List[FileAnalysisFinding]:
    rows = (
        (
            await session.execute(
                select(FileAnalysisFinding)
                .where(FileAnalysisFinding.job_id == job.id)
                .order_by(FileAnalysisFinding.weight.desc(), FileAnalysisFinding.flag),
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def get_iocs(job: FileAnalysisJob, session: AsyncSession) -> List[FileAnalysisIoC]:
    rows = (
        (
            await session.execute(
                select(FileAnalysisIoC).where(FileAnalysisIoC.job_id == job.id).order_by(FileAnalysisIoC.ioc_type, FileAnalysisIoC.id),
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
