"""Scans of a customer's cloud accounts: starting them, following them, cancelling and deleting them (#1328).

A scan goes ``queued`` → ``starting`` → ``running`` → ``ingesting`` → ``completed``, or ends
``failed`` or ``cancelled``. Each step is claimed with a guarded ``UPDATE … WHERE status = <the
step before>``, so with several backend replicas (or a request and the job at once) exactly one
takes it. The job (``invoke_cloud_assessment``, every minute) does the rest:

- **Schedules** (``queue_due_schedules``): an enabled account whose daily or weekly slot has passed
  gets one scan, unless a scan was queued since the slot or one is under way. The check and the
  insert run under ``SELECT … FOR UPDATE`` on the account row, after a commit: under MySQL's
  REPEATABLE READ a transaction reads the snapshot of its first plain read, so the lock comes
  first and the reads after it.
- **Starting** (``dispatch``): the credential is decrypted in memory and sent to copilot-prowler;
  a busy or unreachable runner puts the scan back in the queue.
- **Following** (``poll``): the runner's job status. Completed: the results are stored
  (``ingest.Ingestion``) and the runner's copy deleted. A job the runner no longer holds fails
  the scan (``results_lost``); a runner that can't be asked for ``RUNNER_SILENCE_LIMIT`` too.
- **Recovery** (``recover_stale``): a scan left ``starting`` (a backend that died between the
  claim and the runner's answer) fails after ``STARTING_GRACE``; one left ``ingesting`` goes back
  to ``running`` after ``INGESTING_GRACE`` and is stored again.
- **Retention** (``apply_retention``, hourly): an account's findings and reports are kept for its
  newest ``CLOUD_ASSESSMENT_KEEP_FINDINGS_SCANS`` completed scans (30); older scans keep their
  counts and check results, for trends, until ``CLOUD_ASSESSMENT_RETENTION_DAYS`` (400).
"""

import os
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.auth.models.users import User
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentAccount
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentCheckResult
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.schema.cloud_assessment import ACTIVE_STATUSES
from app.cloud_assessment.schema.cloud_assessment import FINAL_STATUSES
from app.cloud_assessment.schema.cloud_assessment import ScanOut
from app.cloud_assessment.services import crypto
from app.cloud_assessment.services import reports
from app.cloud_assessment.services.accounts import account_secret
from app.cloud_assessment.services.accounts import audit
from app.cloud_assessment.services.accounts import counts_of
from app.cloud_assessment.services.accounts import delete_findings
from app.cloud_assessment.services.accounts import get_account
from app.cloud_assessment.services.accounts import require_admin
from app.cloud_assessment.services.accounts import runner_payload
from app.cloud_assessment.services.accounts import stored_customer_code
from app.cloud_assessment.services.errors import error_message
from app.cloud_assessment.services.errors import runner_http_error
from app.cloud_assessment.services.errors import scan_code_for
from app.cloud_assessment.services.ingest import FindingsUnreadable
from app.cloud_assessment.services.ingest import Ingestion
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError
from app.cloud_assessment.utils import as_utc
from app.cloud_assessment.utils import last_slot
from app.cloud_assessment.utils import schedule_due
from app.cloud_assessment.utils import utc_now

STARTING_GRACE = timedelta(minutes=10)
INGESTING_GRACE = timedelta(minutes=60)
#: A running scan copilot-prowler can't be asked about for this long has failed (the runner keeps
#: a job a day after it ends, and a scan runs at most 12 hours).
RUNNER_SILENCE_LIMIT = timedelta(hours=36)
RETENTION_INTERVAL = timedelta(hours=1)
RETENTION_BATCH = 50
MAX_PAGE_SIZE = 100

SessionFactory = Callable[[], AsyncSession]
_last_retention: Optional[datetime] = None


def _env_int(name: str, default: int, low: int, high: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        return default
    return min(max(value, low), high)


def keep_findings_scans() -> int:
    return _env_int("CLOUD_ASSESSMENT_KEEP_FINDINGS_SCANS", 30, 1, 1000)


def retention_days() -> int:
    return _env_int("CLOUD_ASSESSMENT_RETENTION_DAYS", 400, 30, 3650)


# --- responses ----------------------------------------------------------------------------------


def scan_out(scan: CloudAssessmentScan, account: Optional[CloudAssessmentAccount] = None) -> ScanOut:
    duration = None
    if scan.started_at and scan.completed_at and scan.status == "completed":
        duration = max(int((scan.completed_at - scan.started_at).total_seconds()), 0)
    reports_kept = [
        kind for kind, key in (("html", scan.html_object_key), ("csv", scan.csv_object_key)) if key and not scan.findings_pruned_at
    ]
    return ScanOut(
        id=scan.id,
        account_id=scan.account_id,
        account_name=account.name if account else None,
        provider=account.provider if account else None,
        customer_code=scan.customer_code,
        status=scan.status,
        trigger_type=scan.trigger_type,
        requested_by=scan.requested_by,
        queued_at=as_utc(scan.queued_at),
        started_at=as_utc(scan.started_at),
        completed_at=as_utc(scan.completed_at) if scan.status in FINAL_STATUSES else None,
        duration_seconds=duration,
        prowler_version=scan.prowler_version,
        counts=counts_of(scan),
        check_errors=scan.log_error_lines or 0,
        error_code=scan.error_code,
        error_message=error_message(scan.error_code),
        prowler_errors=list(scan.prowler_errors or []),
        reports=reports_kept,
        findings_pruned=scan.findings_pruned_at is not None,
    )


# --- reads --------------------------------------------------------------------------------------


async def get_scan(session: AsyncSession, customer_code: str, scan_id: int) -> CloudAssessmentScan:
    """A scan of this customer's, or a 404 (another customer's scan is the same 404)."""
    scan = (
        (
            await session.execute(
                select(CloudAssessmentScan).where(CloudAssessmentScan.id == scan_id, CloudAssessmentScan.customer_code == customer_code),
            )
        )
        .scalars()
        .first()
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


async def scan_with_account(
    session: AsyncSession,
    customer_code: str,
    scan_id: int,
) -> Tuple[str, CloudAssessmentScan, Optional[CloudAssessmentAccount]]:
    code = await stored_customer_code(session, customer_code)
    scan = await get_scan(session, code, scan_id)
    account = await session.get(CloudAssessmentAccount, scan.account_id)
    return code, scan, account


async def list_scans(
    session: AsyncSession,
    customer_code: str,
    account_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[ScanOut], int]:
    code = await stored_customer_code(session, customer_code)
    conditions = [CloudAssessmentScan.customer_code == code]
    if account_id is not None:
        conditions.append(CloudAssessmentScan.account_id == account_id)
    if status is not None:
        conditions.append(CloudAssessmentScan.status == status)
    total = (await session.execute(select(func.count()).select_from(CloudAssessmentScan).where(*conditions))).scalar() or 0
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)
    rows = (
        (
            await session.execute(
                select(CloudAssessmentScan)
                .where(*conditions)
                .order_by(CloudAssessmentScan.queued_at.desc(), CloudAssessmentScan.id.desc())
                .offset((max(page, 1) - 1) * page_size)
                .limit(page_size),
            )
        )
        .scalars()
        .all()
    )
    account_ids = {scan.account_id for scan in rows}
    accounts = {}
    if account_ids:
        accounts = {
            account.id: account
            for account in (await session.execute(select(CloudAssessmentAccount).where(CloudAssessmentAccount.id.in_(account_ids))))
            .scalars()
            .all()
        }
    return [scan_out(scan, accounts.get(scan.account_id)) for scan in rows], total


# --- state changes ------------------------------------------------------------------------------


async def _set(session: AsyncSession, scan_id: int, expected: Tuple[str, ...], **values: Any) -> bool:
    """Move a scan on, only from one of the ``expected`` statuses. Whether this call moved it."""
    result = await session.execute(
        update(CloudAssessmentScan).where(CloudAssessmentScan.id == scan_id, CloudAssessmentScan.status.in_(expected)).values(**values),
    )
    await session.commit()
    return result.rowcount == 1


async def _fail(
    session: AsyncSession,
    scan_id: int,
    expected: Tuple[str, ...],
    code: str,
    prowler_errors: Optional[List[str]] = None,
    **values: Any,
) -> bool:
    return await _set(
        session,
        scan_id,
        expected,
        status="failed",
        error_code=code,
        prowler_errors=prowler_errors or None,
        completed_at=utc_now(),
        **values,
    )


async def _active_scan(session: AsyncSession, account_id: int) -> Optional[CloudAssessmentScan]:
    return (
        (
            await session.execute(
                select(CloudAssessmentScan).where(
                    CloudAssessmentScan.account_id == account_id,
                    CloudAssessmentScan.status.in_(ACTIVE_STATUSES),
                ),
            )
        )
        .scalars()
        .first()
    )


async def _queue(
    session: AsyncSession,
    account_id: int,
    trigger: str,
    requested_by: Optional[str],
    since: Optional[datetime] = None,
) -> Optional[CloudAssessmentScan]:
    """Queue a scan of the account under its row lock, unless one is under way (or, for a schedule,
    one was queued at or after ``since``). The caller has just committed."""
    account = (
        (await session.execute(select(CloudAssessmentAccount).where(CloudAssessmentAccount.id == account_id).with_for_update()))
        .scalars()
        .first()
    )
    if account is None or await _active_scan(session, account_id) is not None:
        await session.rollback()
        return None
    if since is not None:
        latest = (
            await session.execute(select(func.max(CloudAssessmentScan.queued_at)).where(CloudAssessmentScan.account_id == account_id))
        ).scalar()
        if latest is not None and latest >= since:
            await session.rollback()
            return None
    scan = CloudAssessmentScan(
        account_id=account.id,
        customer_code=account.customer_code,
        status="queued",
        trigger_type=trigger,
        requested_by=requested_by,
        queued_at=utc_now(),
    )
    session.add(scan)
    await session.commit()
    return scan


async def start_scan(session: AsyncSession, customer_code: str, account_id: int, user: User, request: Optional[Request]) -> ScanOut:
    """Queue a scan of the account and hand it to copilot-prowler at once if it has room (else the
    job starts it within a minute)."""
    code = await stored_customer_code(session, customer_code)
    account = await get_account(session, code, account_id)
    if not account.enabled:
        raise HTTPException(status_code=409, detail="The account is disabled: enable it to scan it")
    try:
        runner_payload(account, account_secret(account))
    except crypto.CredentialCryptoError as error:
        if str(error) == "credential_missing":
            raise HTTPException(status_code=409, detail=error_message("credential_missing")) from error
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
    async with RunnerClient.from_env() as runner:
        problem = runner.problem()
        if problem:
            raise runner_http_error(RunnerError(problem))
        await session.commit()
        scan = await _queue(session, account.id, "manual", user.username)
        if scan is None:
            raise HTTPException(status_code=409, detail="A scan of this account is already queued or running")
        await audit(
            AuditAction.CLOUD_ASSESSMENT_SCAN_START,
            user,
            code,
            "cloud_assessment_scan",
            scan.id,
            request,
            new={"scan_id": scan.id, "account_id": account.id, "account": account.name, "trigger": "manual"},
        )
        await dispatch(session, runner, scan.id)
    scan = await get_scan(session, code, scan.id)
    return scan_out(scan, await session.get(CloudAssessmentAccount, scan.account_id))


async def dispatch(session: AsyncSession, runner: RunnerClient, scan_id: int) -> str:
    """Hand a queued scan to copilot-prowler. ``started``, ``busy`` (back in the queue), ``failed``,
    or ``skipped`` (another replica took it, or it went away)."""
    if not await _set(session, scan_id, ("queued",), status="starting", started_at=utc_now()):
        return "skipped"
    scan = await session.get(CloudAssessmentScan, scan_id)
    account = await session.get(CloudAssessmentAccount, scan.account_id) if scan else None
    if scan is None or account is None:
        return "skipped"
    try:
        payload = runner_payload(account, account_secret(account))
    except crypto.CredentialCryptoError as error:
        code = "credential_missing" if str(error) == "credential_missing" else "credential_unreadable"
        await _fail(session, scan_id, ("starting",), code)
        return "failed"
    # Nothing is held open while copilot-prowler is asked.
    await session.commit()
    try:
        job = await runner.start_scan(payload)
    except RunnerError as error:
        if error.reason in ("busy", "unreachable", "timeout"):
            await _set(session, scan_id, ("starting",), status="queued", started_at=None)
            return "busy"
        await _fail(session, scan_id, ("starting",), scan_code_for(error))
        logger.warning(f"Cloud assessment: copilot-prowler refused scan {scan_id}: {error.reason} {error.code or ''}")
        return "failed"
    if not await _set(session, scan_id, ("starting",), status="running", runner_job_id=job.job_id, prowler_version=job.prowler_version):
        # Cancelled or deleted while it was being handed over: stop what the runner started.
        await _stop_runner_job(runner, job.job_id)
        return "skipped"
    return "started"


async def _stop_runner_job(runner: RunnerClient, job_id: Optional[str]) -> None:
    if not job_id:
        return
    try:
        await runner.delete_scan(job_id)
    except RunnerError as error:
        logger.warning(f"Cloud assessment: couldn't delete copilot-prowler job {job_id}: {error.reason}")


async def poll(session: AsyncSession, runner: RunnerClient, scan_id: int, now: Optional[datetime] = None) -> str:
    """Follow a running scan. ``running``, ``completed``, ``failed``, ``cancelled``, or ``skipped``."""
    now = now or utc_now()
    scan = await session.get(CloudAssessmentScan, scan_id)
    await session.commit()
    if scan is None or scan.status != "running" or not scan.runner_job_id:
        return "skipped"
    try:
        job = await runner.scan_status(scan.runner_job_id)
    except RunnerError as error:
        if error.reason == "not_found":
            await _fail(session, scan_id, ("running",), "results_lost")
            return "failed"
        if scan.started_at and now - scan.started_at > RUNNER_SILENCE_LIMIT:
            await _fail(session, scan_id, ("running",), "runner_unreachable")
            return "failed"
        return "running"
    if job.status in ("running", "normalizing"):
        return "running"
    if job.status == "cancelled":
        await _set(session, scan_id, ("running",), status="cancelled", completed_at=now)
        await _stop_runner_job(runner, job.job_id)
        return "cancelled"
    if job.status == "failed":
        await _fail(session, scan_id, ("running",), job.error_code or "scan_failed", job.prowler_errors, log_error_lines=job.error_lines)
        await _stop_runner_job(runner, job.job_id)
        return "failed"
    if not await _set(session, scan_id, ("running",), status="ingesting", completed_at=now):
        return "skipped"
    scan = await session.get(CloudAssessmentScan, scan_id)
    await session.refresh(scan)
    try:
        kept = await Ingestion(session, runner, scan, job).run()
    except RunnerError as error:
        await session.rollback()
        if error.reason == "not_found":
            await _fail(session, scan_id, ("ingesting",), "results_lost")
            await delete_findings(session, [scan_id])
            return "failed"
        # The runner still holds the results: the next tick tries again.
        await _set(session, scan_id, ("ingesting",), status="running", completed_at=None)
        logger.warning(f"Cloud assessment: scan {scan_id}'s results couldn't be read yet: {error.reason}")
        return "running"
    except IntegrityError:
        await session.rollback()
        return "skipped"  # the scan, or its account, was deleted meanwhile
    except FindingsUnreadable:
        await session.rollback()
        await delete_findings(session, [scan_id])
        await _delete_check_results(session, scan_id)
        await _fail(session, scan_id, ("ingesting",), "findings_unreadable")
        await _stop_runner_job(runner, job.job_id)
        return "failed"
    except Exception as error:  # noqa: BLE001 - a scan that can't be stored fails, it doesn't loop
        await session.rollback()
        # The class only: a database error's text carries the statement's values (findings from a customer's cloud).
        logger.error(f"Cloud assessment: storing scan {scan_id}'s results failed: {type(error).__name__}")
        await delete_findings(session, [scan_id])
        await _fail(session, scan_id, ("ingesting",), "ingest_failed")
        return "failed"
    if kept:
        await _stop_runner_job(runner, job.job_id)
    return "completed" if kept else "skipped"


async def cancel_scan(session: AsyncSession, customer_code: str, scan_id: int, user: User, request: Optional[Request]) -> ScanOut:
    code = await stored_customer_code(session, customer_code)
    scan = await get_scan(session, code, scan_id)
    status = scan.status
    if status in FINAL_STATUSES:
        raise HTTPException(status_code=409, detail="The scan has already ended")
    if status == "ingesting":
        raise HTTPException(status_code=409, detail="The scan has finished: its results are being stored")
    if status == "running":
        await session.commit()
        try:
            async with RunnerClient.from_env() as runner:
                await runner.delete_scan(scan.runner_job_id)
        except RunnerError as error:
            raise runner_http_error(error) from error
    if not await _set(session, scan_id, (status,), status="cancelled", completed_at=utc_now()):
        raise HTTPException(status_code=409, detail="The scan moved on meanwhile: reload it")
    await audit(
        AuditAction.CLOUD_ASSESSMENT_SCAN_CANCEL,
        user,
        code,
        "cloud_assessment_scan",
        scan_id,
        request,
        old={"status": status},
        new={"status": "cancelled", "account_id": scan.account_id},
    )
    scan = await get_scan(session, code, scan_id)
    return scan_out(scan, await session.get(CloudAssessmentAccount, scan.account_id))


async def delete_scan(session: AsyncSession, customer_code: str, scan_id: int, user: User, request: Optional[Request]) -> None:
    require_admin(user)
    code = await stored_customer_code(session, customer_code)
    scan = await get_scan(session, code, scan_id)
    if scan.status in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="The scan is still under way: cancel it first")
    objects = [(scan.report_bucket, key) for key in (scan.html_object_key, scan.csv_object_key) if scan.report_bucket and key]
    old = {
        "status": scan.status,
        "account_id": scan.account_id,
        "queued_at": as_utc(scan.queued_at).isoformat() if scan.queued_at else None,
    }
    await session.commit()
    await delete_findings(session, [scan_id])
    await _delete_scan_rows(session, [scan_id])
    await reports.delete_objects(objects)
    await audit(AuditAction.CLOUD_ASSESSMENT_SCAN_DELETE, user, code, "cloud_assessment_scan", scan_id, request, old=old)


async def _delete_check_results(session: AsyncSession, scan_id: int) -> None:
    await session.execute(delete(CloudAssessmentCheckResult).where(CloudAssessmentCheckResult.scan_id == scan_id))
    await session.commit()


async def _delete_scan_rows(session: AsyncSession, scan_ids: List[int]) -> None:
    if not scan_ids:
        return
    await session.execute(delete(CloudAssessmentCheckResult).where(CloudAssessmentCheckResult.scan_id.in_(scan_ids)))
    await session.execute(delete(CloudAssessmentScan).where(CloudAssessmentScan.id.in_(scan_ids)))
    await session.commit()


# --- the job ------------------------------------------------------------------------------------


async def recover_stale(session: AsyncSession, now: datetime) -> int:
    lost = await session.execute(
        update(CloudAssessmentScan)
        .where(CloudAssessmentScan.status == "starting", CloudAssessmentScan.started_at < now - STARTING_GRACE)
        .values(status="failed", error_code="dispatch_lost", completed_at=now),
    )
    stuck = await session.execute(
        update(CloudAssessmentScan)
        .where(CloudAssessmentScan.status == "ingesting", CloudAssessmentScan.completed_at < now - INGESTING_GRACE)
        .values(status="running", completed_at=None),
    )
    await session.commit()
    return (lost.rowcount or 0) + (stuck.rowcount or 0)


async def queue_due_schedules(session: AsyncSession, now: datetime) -> int:
    accounts = (
        (
            await session.execute(
                select(CloudAssessmentAccount).where(CloudAssessmentAccount.enabled.is_(True), CloudAssessmentAccount.schedule != "off"),
            )
        )
        .scalars()
        .all()
    )
    if not accounts:
        return 0
    latest = dict(
        (
            await session.execute(
                select(CloudAssessmentScan.account_id, func.max(CloudAssessmentScan.queued_at))
                .where(CloudAssessmentScan.account_id.in_([account.id for account in accounts]))
                .group_by(CloudAssessmentScan.account_id),
            )
        ).all(),
    )
    due = [
        account
        for account in accounts
        if schedule_due(
            account.schedule,
            account.schedule_hour,
            account.schedule_weekday,
            now,
            account.updated_at or account.created_at,
            latest.get(account.id),
        )
    ]
    await session.commit()
    queued = 0
    for account in due:
        if await _queue(
            session,
            account.id,
            "schedule",
            None,
            since=last_slot(account.schedule, account.schedule_hour, account.schedule_weekday, now),
        ):
            queued += 1
    return queued


async def dispatch_queued(session: AsyncSession, runner: RunnerClient) -> int:
    ids = (
        (
            await session.execute(
                select(CloudAssessmentScan.id)
                .where(CloudAssessmentScan.status == "queued")
                .order_by(CloudAssessmentScan.queued_at, CloudAssessmentScan.id),
            )
        )
        .scalars()
        .all()
    )
    await session.commit()
    started = 0
    for scan_id in ids:
        outcome = await dispatch(session, runner, scan_id)
        if outcome == "started":
            started += 1
        elif outcome == "busy":
            break
    return started


async def poll_running(session: AsyncSession, runner: RunnerClient, now: datetime) -> Dict[str, int]:
    ids = (await session.execute(select(CloudAssessmentScan.id).where(CloudAssessmentScan.status == "running"))).scalars().all()
    await session.commit()
    outcomes: Dict[str, int] = {}
    for scan_id in ids:
        outcome = await poll(session, runner, scan_id, now)
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return outcomes


async def apply_retention(session: AsyncSession, now: datetime) -> int:
    """Prune findings and reports past each account's newest kept scans, and delete scans past the
    retention period. At most ``RETENTION_BATCH`` scans a pass."""
    pruned = 0
    keep = keep_findings_scans()
    ranked = (
        await session.execute(
            select(CloudAssessmentScan.id, CloudAssessmentScan.account_id, CloudAssessmentScan.findings_pruned_at)
            .where(CloudAssessmentScan.status == "completed")
            .order_by(CloudAssessmentScan.account_id, CloudAssessmentScan.id.desc()),
        )
    ).all()
    seen: Dict[int, int] = {}
    to_prune: List[int] = []
    for scan_id, account_id, pruned_at in ranked:
        seen[account_id] = seen.get(account_id, 0) + 1
        if seen[account_id] > keep and pruned_at is None:
            to_prune.append(scan_id)
    for scan_id in to_prune[:RETENTION_BATCH]:
        scan = await session.get(CloudAssessmentScan, scan_id)
        objects = [(scan.report_bucket, key) for key in (scan.html_object_key, scan.csv_object_key) if scan.report_bucket and key]
        await session.commit()
        await delete_findings(session, [scan_id])
        await reports.delete_objects(objects)
        await session.execute(
            update(CloudAssessmentScan)
            .where(CloudAssessmentScan.id == scan_id)
            .values(findings_pruned_at=now, report_bucket=None, html_object_key=None, csv_object_key=None),
        )
        await session.commit()
        pruned += 1
    cutoff = now - timedelta(days=retention_days())
    old = (
        (
            await session.execute(
                select(CloudAssessmentScan)
                .where(CloudAssessmentScan.status.in_(FINAL_STATUSES), CloudAssessmentScan.queued_at < cutoff)
                .limit(RETENTION_BATCH),
            )
        )
        .scalars()
        .all()
    )
    objects = [
        (scan.report_bucket, key) for scan in old for key in (scan.html_object_key, scan.csv_object_key) if scan.report_bucket and key
    ]
    ids = [scan.id for scan in old]
    await session.commit()
    if ids:
        await delete_findings(session, ids)
        await _delete_scan_rows(session, ids)
        await reports.delete_objects(objects)
    return pruned + len(ids)


def default_session_factory() -> SessionFactory:
    from app.db.db_session import AsyncSessionLocal

    return AsyncSessionLocal


async def run_tick(session_factory: Optional[SessionFactory] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """One pass of the job. Raises only what the caller logs; each scan's failure is its own."""
    global _last_retention
    factory = session_factory or default_session_factory()
    now = now or utc_now()
    counts: Dict[str, Any] = {}
    async with factory() as session, RunnerClient.from_env() as runner:
        counts["recovered"] = await recover_stale(session, now)
        if runner.configured:
            counts["scheduled"] = await queue_due_schedules(session, now)
            counts["dispatched"] = await dispatch_queued(session, runner)
            counts["polled"] = await poll_running(session, runner, now)
        if _last_retention is None or now - _last_retention >= RETENTION_INTERVAL:
            counts["retention"] = await apply_retention(session, now)
            _last_retention = now
    return counts
