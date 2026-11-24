"""Storing a completed scan's results (#1328).

copilot-prowler holds a finished scan's ``summary.json`` (totals, and per check its metadata and
counts), its FAIL and MANUAL findings (NDJSON) and Prowler's HTML and CSV reports. This copies
them into the scan's rows and MinIO:

- **Idempotent.** A scan is claimed ``running`` → ``ingesting`` by one backend replica, and
  whatever an earlier, interrupted attempt stored is deleted first. A run that dies half-way is
  put back to ``running`` by the job after ``INGESTING_GRACE`` and stored again while the runner
  still holds the results (``PROWLER_JOB_TTL_SECONDS``, a day by default).
- **Streamed.** Findings are read a line at a time and inserted in batches of ``BATCH_SIZE``,
  each committed, so a scan of 100,000 findings never sits in memory or in one transaction.
  At most ``MAX_FINDINGS`` are stored (the counts on the scan are always the summary's).
- **Matched across scans, check by check.** A finding is the same finding as in the account's
  previous completed scan when ``finding_uid_hash`` (the SHA-256 of Prowler's whole id) matches.
  Only a check *observed* in a scan counts: it ran there (a check that errored, or had nothing to
  check, writes no finding at all, not even a PASS) and every one of its unmuted FAIL and MANUAL
  findings was stored (``MAX_FINDINGS`` can cut a scan short). A finding is new (``is_new``) only
  when its check was observed in the previous scan and it didn't have this status there; a failure
  is resolved only when its check was observed in this scan and it doesn't fail any more. So a
  check that errored neither looks like a fix, nor makes its failures look new the next time it
  runs. ``first_seen_at`` carries forward while the status stays the same, across scans in which
  the check didn't run too (from the last kept scan in which it did). The first scan of an account
  marks nothing new, and neither does a check with no earlier run (one Prowler added, or one with
  nothing to check until now). New and resolved are counted by distinct id: Prowler repeats an id
  within one scan for some checks (seen live: API Gateway's per-stage checks, 237 findings with
  229 ids).
- **Checked again.** Every value is cleaned and cut to its column here too (``utils.clean_text``):
  the runner is CoPilot's, but the text is the customer's cloud's.
"""

import os
import re
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Set
from typing import Tuple

from loguru import logger
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud_assessment.models.cloud_assessment import CloudAssessmentCheckResult
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentFinding
from app.cloud_assessment.models.cloud_assessment import CloudAssessmentScan
from app.cloud_assessment.schema.cloud_assessment import CHECK_ID_PATTERN
from app.cloud_assessment.schema.cloud_assessment import FINDING_STATUSES
from app.cloud_assessment.schema.cloud_assessment import REPORT_KINDS
from app.cloud_assessment.schema.cloud_assessment import SEVERITIES
from app.cloud_assessment.services import reports
from app.cloud_assessment.services.accounts import delete_findings
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerJob
from app.cloud_assessment.utils import clean_list
from app.cloud_assessment.utils import clean_text
from app.cloud_assessment.utils import parse_time
from app.cloud_assessment.utils import url_list
from app.cloud_assessment.utils import utc_now

BATCH_SIZE = 500
MAX_CHECKS = 5000
MAX_FRAMEWORKS = 200
MAX_REQUIREMENTS = 500
MAX_COUNT = 2**31 - 1
IN_CHUNK = 500
_CHECK_ID = re.compile(CHECK_ID_PATTERN)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def max_findings() -> int:
    raw = (os.environ.get("CLOUD_ASSESSMENT_MAX_FINDINGS") or "").strip()
    try:
        value = int(raw) if raw else 500_000
    except ValueError:
        value = 500_000
    return min(max(value, 1000), 5_000_000)


def count(value: Any) -> int:
    return min(value, MAX_COUNT) if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def severity(value: Any) -> str:
    text = value.lower() if isinstance(value, str) else ""
    return text if text in SEVERITIES else "unknown"


def compliance_map(value: Any) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    if not isinstance(value, dict):
        return result
    for framework, requirements in value.items():
        key = clean_text(framework, 128)
        ids = clean_list(requirements, 128, MAX_REQUIREMENTS)
        if key and ids and key not in result:
            result[key] = ids
            if len(result) >= MAX_FRAMEWORKS:
                break
    return result


def check_row(entry: Any, scan_id: int) -> Optional[Dict[str, Any]]:
    """A ``cloud_assessment_check_result`` row from one of the summary's checks, or None."""
    if not isinstance(entry, dict):
        return None
    check_id = entry.get("check_id")
    if not isinstance(check_id, str) or not _CHECK_ID.match(check_id):
        return None
    return {
        "scan_id": scan_id,
        "check_id": check_id,
        "title": clean_text(entry.get("title"), 512),
        "service": clean_text(entry.get("service"), 64),
        "severity": severity(entry.get("severity")),
        "description": clean_text(entry.get("description"), 4000) or None,
        "risk": clean_text(entry.get("risk"), 4000) or None,
        "remediation": clean_text(entry.get("remediation"), 4000) or None,
        "remediation_urls": url_list(entry.get("references")) or None,
        "additional_urls": url_list(entry.get("additional_urls")) or None,
        "categories": clean_list(entry.get("categories"), 64, 20) or None,
        "compliance": compliance_map(entry.get("compliance")) or None,
        "pass_count": count(entry.get("pass")),
        "fail_count": count(entry.get("fail")),
        "manual_count": count(entry.get("manual")),
        "muted_count": count(entry.get("muted")),
    }


def finding_row(item: Any, scan: CloudAssessmentScan) -> Optional[Dict[str, Any]]:
    """A ``cloud_assessment_finding`` row from one line of the runner's findings, without the
    cross-scan fields, or None when the line isn't a finding CoPilot stores."""
    if not isinstance(item, dict):
        return None
    check_id = item.get("check_id")
    status = item.get("status")
    finding_uid = clean_text(item.get("finding_uid"), 512)
    uid_hash = item.get("finding_uid_sha256")
    if not isinstance(check_id, str) or not _CHECK_ID.match(check_id) or status not in FINDING_STATUSES:
        return None
    if not finding_uid or not isinstance(uid_hash, str) or not _SHA256.match(uid_hash):
        return None
    return {
        "scan_id": scan.id,
        "account_id": scan.account_id,
        "customer_code": scan.customer_code,
        "finding_uid": finding_uid,
        "finding_uid_hash": uid_hash,
        "check_id": check_id,
        "status": status,
        "severity": severity(item.get("severity")),
        "muted": item.get("muted") is True,
        "status_extended": clean_text(item.get("status_extended"), 4000) or None,
        "service": clean_text(item.get("service"), 64),
        "region": clean_text(item.get("region"), 64),
        "cloud_account_uid": clean_text(item.get("cloud_account_uid"), 256),
        "cloud_account_name": clean_text(item.get("cloud_account_name"), 256),
        "resource_uid": clean_text(item.get("resource_uid"), 1024),
        "resource_name": clean_text(item.get("resource_name"), 512),
        "resource_type": clean_text(item.get("resource_type"), 128),
        "resource_tags": clean_list(item.get("resource_tags"), 256, 50) or None,
        "detected_at": parse_time(item.get("time")),
    }


class Seen(NamedTuple):
    """A finding as an earlier scan of the account stored it."""

    status: str
    muted: bool
    first_seen_at: Any
    check_id: str


def complete_checks(ran: Iterable[str], expected: Dict[str, Tuple[int, int]], stored: Dict[Tuple[str, str], int]) -> Set[str]:
    """The checks in ``ran`` that were observed: every unmuted FAIL and MANUAL finding the summary
    counted (``expected``: per check, its fail and manual counts) was stored (``stored``: rows per
    check and status). A finding cut by ``MAX_FINDINGS`` or unreadable leaves its check unobserved."""
    observed = set()
    for check_id in ran:
        fail, manual = expected.get(check_id, (0, 0))
        if stored.get((check_id, "FAIL"), 0) >= fail and stored.get((check_id, "MANUAL"), 0) >= manual:
            observed.add(check_id)
    return observed


def _add(stored: Dict[Tuple[str, str], int], check_id: str, status: str) -> None:
    stored[(check_id, status)] = stored.get((check_id, status), 0) + 1


class Baseline:
    """What the account's earlier scans saw, to match a new scan's findings with.

    ``findings`` are the previous completed scan's, by ``finding_uid_hash``, and ``observed`` the
    checks observed in it (``complete_checks``), the only ones whose findings can be new. ``earlier``
    has, for each check that ran in this scan and not in the previous one, its findings in the last
    kept scan in which it ran: only ``first_seen_at`` is carried from them.
    """

    def __init__(self) -> None:
        self.findings: Dict[str, Seen] = {}
        self.observed: Set[str] = set()
        self.earlier: Dict[str, Seen] = {}


def _seen_columns():
    return select(
        CloudAssessmentFinding.finding_uid_hash,
        CloudAssessmentFinding.status,
        CloudAssessmentFinding.muted,
        CloudAssessmentFinding.first_seen_at,
        CloudAssessmentFinding.check_id,
    )


async def load_baseline(session: AsyncSession, scan: CloudAssessmentScan, ran_now: Set[str]) -> Baseline:
    """``scan``'s baseline, given the checks that ran in it: the account's newest completed scan
    before it, whose findings are kept (retention keeps the newest), and for checks that didn't run
    there, their last kept run before it. An account's first scan gets an empty one."""
    baseline = Baseline()
    previous_id = (
        await session.execute(
            select(CloudAssessmentScan.id)
            .where(
                CloudAssessmentScan.account_id == scan.account_id,
                CloudAssessmentScan.status == "completed",
                CloudAssessmentScan.findings_pruned_at.is_(None),
                CloudAssessmentScan.id < scan.id,
            )
            .order_by(CloudAssessmentScan.id.desc())
            .limit(1),
        )
    ).scalar()
    if previous_id is None:
        return baseline
    expected = {
        check_id: (fail, manual)
        for check_id, fail, manual in await session.execute(
            select(
                CloudAssessmentCheckResult.check_id,
                CloudAssessmentCheckResult.fail_count,
                CloudAssessmentCheckResult.manual_count,
            ).where(CloudAssessmentCheckResult.scan_id == previous_id),
        )
    }
    ran_before = set(expected)
    stored: Dict[Tuple[str, str], int] = {}
    names: Dict[str, str] = {}  # one string per check id and status, however many findings share it
    for uid_hash, status, muted, first_seen, check_id in await session.execute(
        _seen_columns().where(CloudAssessmentFinding.scan_id == previous_id),
    ):
        status = names.setdefault(status, status)
        check_id = names.setdefault(check_id, check_id)
        baseline.findings[uid_hash] = Seen(status, bool(muted), first_seen, check_id)
        ran_before.add(check_id)
        if not muted:
            _add(stored, check_id, status)
    baseline.observed = complete_checks(ran_before, expected, stored)
    missing = sorted(ran_now - ran_before)
    if missing:
        baseline.earlier = await earlier_findings(session, scan.account_id, previous_id, missing)
    return baseline


async def earlier_findings(session: AsyncSession, account_id: int, before_id: int, check_ids: List[str]) -> Dict[str, Seen]:
    """For checks that didn't run in the scan ``before_id``: their findings in the account's last
    kept scan before it in which they ran, by ``finding_uid_hash``. A check ran in a scan when it
    has a check result there (one per check with a finding of any status)."""
    last_run: Dict[int, List[str]] = {}
    for start in range(0, len(check_ids), IN_CHUNK):
        rows = await session.execute(
            select(CloudAssessmentCheckResult.check_id, func.max(CloudAssessmentCheckResult.scan_id))
            .join(CloudAssessmentScan, CloudAssessmentScan.id == CloudAssessmentCheckResult.scan_id)
            .where(
                CloudAssessmentScan.account_id == account_id,
                CloudAssessmentScan.status == "completed",
                CloudAssessmentScan.findings_pruned_at.is_(None),
                CloudAssessmentScan.id < before_id,
                CloudAssessmentCheckResult.check_id.in_(check_ids[start : start + IN_CHUNK]),
            )
            .group_by(CloudAssessmentCheckResult.check_id),
        )
        for check_id, scan_id in rows:
            last_run.setdefault(scan_id, []).append(check_id)
    found: Dict[str, Seen] = {}
    for scan_id, ids in last_run.items():
        for start in range(0, len(ids), IN_CHUNK):
            rows = await session.execute(
                _seen_columns().where(
                    CloudAssessmentFinding.scan_id == scan_id,
                    CloudAssessmentFinding.check_id.in_(ids[start : start + IN_CHUNK]),
                ),
            )
            for uid_hash, status, muted, first_seen, check_id in rows:
                found[uid_hash] = Seen(status, bool(muted), first_seen, check_id)
    return found


class FindingsUnreadable(Exception):
    """copilot-prowler sent findings and CoPilot could read none of them."""


class Ingestion:
    """One attempt at storing a scan's results. ``run`` returns False when the scan went away meanwhile."""

    def __init__(self, session: AsyncSession, runner: RunnerClient, scan: CloudAssessmentScan, job: RunnerJob) -> None:
        self.session = session
        self.runner = runner
        self.scan = scan
        self.job = job
        self.limit = max_findings()
        self.stored = 0
        self.skipped = 0
        self.dropped = 0
        self.fail_hashes: Set[str] = set()
        self.new_fail_hashes: Set[str] = set()
        self.ran: Set[str] = set()
        self.stored_counts: Dict[Tuple[str, str], int] = {}
        self.baseline = Baseline()

    async def _insert(self, model, rows: List[Dict[str, Any]]) -> None:
        if rows:
            await self.session.execute(insert(model.__table__), rows)
            await self.session.commit()

    async def run(self) -> bool:
        scan = self.scan
        await self.session.execute(delete(CloudAssessmentCheckResult).where(CloudAssessmentCheckResult.scan_id == scan.id))
        await self.session.commit()
        await delete_findings(self.session, [scan.id])

        summary = await self.runner.summary(self.job.job_id)
        checks: Dict[str, Dict[str, Any]] = {}
        for entry in summary.get("checks") if isinstance(summary.get("checks"), list) else []:
            row = check_row(entry, scan.id)
            if row and row["check_id"] not in checks and len(checks) < MAX_CHECKS:
                checks[row["check_id"]] = row
        rows = list(checks.values())
        for start in range(0, len(rows), BATCH_SIZE):
            await self._insert(CloudAssessmentCheckResult, rows[start : start + BATCH_SIZE])
        self.ran.update(checks)
        self.baseline = await load_baseline(self.session, scan, set(checks))

        now = utc_now()
        first_seen_default = scan.started_at or now
        batch: List[Dict[str, Any]] = []
        async with self.runner.findings(self.job.job_id) as lines:
            async for item in lines:
                row = finding_row(item, scan)
                if row is None:
                    self.skipped += 1
                    continue
                if self.stored >= self.limit:
                    self.dropped += 1
                    continue
                self._match(row, row["detected_at"] or first_seen_default)
                batch.append(row)
                self.stored += 1
                if len(batch) >= BATCH_SIZE:
                    await self._insert(CloudAssessmentFinding, batch)
                    batch = []
        await self._insert(CloudAssessmentFinding, batch)
        if self.dropped:
            logger.warning(
                f"Cloud assessment: scan {scan.id} stored {self.stored} findings and left {self.dropped} out (CLOUD_ASSESSMENT_MAX_FINDINGS)",
            )
        if self.skipped:
            logger.warning(f"Cloud assessment: scan {scan.id} skipped {self.skipped} lines that weren't findings")
            if not self.stored:
                # Not one line read: a copilot-prowler of another version than CoPilot, most likely.
                # A scan that completed with its failures counted and none of them listed would mislead.
                raise FindingsUnreadable()

        expected = {check_id: (entry["fail_count"], entry["manual_count"]) for check_id, entry in checks.items()}
        observed = complete_checks(self.ran, expected, self.stored_counts)
        resolved = sum(
            1
            for uid_hash, seen in self.baseline.findings.items()
            if seen.status == "FAIL" and not seen.muted and seen.check_id in observed and uid_hash not in self.fail_hashes
        )
        stored_reports = await self._store_reports()
        return await self._finish(summary, resolved, stored_reports)

    def _match(self, row: Dict[str, Any], first_seen: Any) -> None:
        """Set a stored row's ``first_seen_at`` and ``is_new`` from the baseline, and count it for this
        scan's own observed checks and new and resolved failures."""
        uid_hash = row["finding_uid_hash"]
        before = self.baseline.findings.get(uid_hash) or self.baseline.earlier.get(uid_hash)
        same = before is not None and before.status == row["status"]
        row["first_seen_at"] = before.first_seen_at if same and before.first_seen_at is not None else first_seen
        row["is_new"] = row["check_id"] in self.baseline.observed and not same
        self.ran.add(row["check_id"])
        if not row["muted"]:
            _add(self.stored_counts, row["check_id"], row["status"])
        if row["status"] == "FAIL":
            self.fail_hashes.add(uid_hash)
            if row["is_new"] and not row["muted"]:
                self.new_fail_hashes.add(uid_hash)

    async def _store_reports(self) -> Dict[str, Dict[str, Any]]:
        stored: Dict[str, Dict[str, Any]] = {}
        for kind in REPORT_KINDS:
            try:
                result = await reports.store_artifact(self.runner, self.job.job_id, kind, self.scan.id)
            except Exception as error:  # noqa: BLE001 - a report that can't be kept doesn't fail the scan
                logger.warning(f"Cloud assessment: scan {self.scan.id}'s {kind} report wasn't kept: {type(error).__name__}")
                continue
            if result:
                stored[kind] = result
        return stored

    async def _finish(self, summary: Dict[str, Any], resolved: int, stored_reports: Dict[str, Dict[str, Any]]) -> bool:
        totals = summary.get("totals") if isinstance(summary.get("totals"), dict) else {}
        by_severity = summary.get("fail_by_severity") if isinstance(summary.get("fail_by_severity"), dict) else {}
        version = clean_text(summary.get("prowler_version"), 32) or self.job.prowler_version
        html = stored_reports.get("html") or {}
        csv = stored_reports.get("csv") or {}
        values = {
            "status": "completed",
            "completed_at": utc_now(),
            "prowler_version": version,
            "total_count": count(totals.get("total")),
            "pass_count": count(totals.get("pass")),
            "fail_count": count(totals.get("fail")),
            "manual_count": count(totals.get("manual")),
            "muted_count": count(totals.get("muted")),
            "new_fail_count": len(self.new_fail_hashes),
            "resolved_fail_count": resolved,
            "log_error_lines": self.job.error_lines,
            "error_code": None,
            "prowler_errors": None,
            "report_bucket": reports.BUCKET if stored_reports else None,
            "html_object_key": html.get("key"),
            "html_file_size": html.get("size"),
            "html_file_hash": html.get("sha256"),
            "csv_object_key": csv.get("key"),
            "csv_file_size": csv.get("size"),
            "csv_file_hash": csv.get("sha256"),
        }
        for level in SEVERITIES:
            values[f"fail_{level}"] = count(by_severity.get(level))
        result = await self.session.execute(
            update(CloudAssessmentScan)
            .where(CloudAssessmentScan.id == self.scan.id, CloudAssessmentScan.status == "ingesting")
            .values(**values),
        )
        await self.session.commit()
        if result.rowcount != 1:
            # Deleted or cancelled while its results were stored: what was kept goes with it.
            await reports.delete_objects([(reports.BUCKET, item["key"]) for item in stored_reports.values()])
            return False
        return True
