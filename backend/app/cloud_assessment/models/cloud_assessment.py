"""Cloud security assessment tables (#1328): accounts, scans, per-check results, findings.

One customer has any number of cloud accounts (an AWS account, a set of Azure
subscriptions or GCP projects, a Microsoft 365 tenant). Each scan of an account keeps:

- its counts, on the scan row itself, so a trend reads one row per scan;
- one row per check Prowler ran (``cloud_assessment_check_result``), with a snapshot of
  the check's metadata at scan time (title, risk, remediation, compliance mapping) and its
  counts. A check's metadata is stored once per scan, not on every finding;
- one row per FAIL or MANUAL finding (``cloud_assessment_finding``). PASS findings are
  only counted, in the check results.

Tenancy: ``cloud_assessment_account.customer_code`` is a hard FK to
``customers.customer_code`` with ON DELETE CASCADE, and scans, check results and findings
cascade from their account and scan. ``customer_code`` and ``account_id`` are repeated on
scans and findings so tenant-scoped queries need no join; they are copies of the account's
and never change.

Nothing here ever holds a resource's raw configuration: the runner drops it (it can carry
secrets). Datetimes are naive UTC, like every other table.
"""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlmodel import Field
from sqlmodel import SQLModel

from app.time_utils import now_utc


def _count() -> Any:
    return Field(default=0, sa_column=Column(Integer, nullable=False, server_default="0"))


class CloudAssessmentAccount(SQLModel, table=True):
    """A cloud account of a customer's that CoPilot scans.

    ``provider`` is ``aws``, ``azure``, ``gcp`` or ``m365``; ``auth_method`` is ``role``
    (AWS, with an External ID), ``access_keys`` (AWS), ``client_secret`` (Azure, Microsoft
    365) or ``service_account_key`` (GCP). ``config`` holds the non-secret settings,
    validated per provider by the service (role ARN, External ID, regions, tenant and
    client ids, subscriptions, projects, a tenant domain, excluded checks and services),
    so a new provider needs no migration.

    ``secret_ciphertext`` is the credential, Fernet-encrypted with
    ``CLOUD_ASSESSMENT_ENCRYPTION_KEY`` (no fallback to another key): a client secret, a
    GCP key file, AWS keys, or for an AWS role the keys of the identity that assumes it.
    NULL for an AWS role assumed with the host's own identity. It is write-only: nothing
    returns it; ``secret_hint`` (its last characters) and ``secret_expires_at`` (a client
    secret's expiry, as entered) are what the UI shows.

    ``schedule`` is ``off``, ``daily`` or ``weekly``, at ``schedule_hour`` (UTC) and, for
    weekly, ``schedule_weekday`` (0 is Monday).
    """

    __tablename__ = "cloud_assessment_account"
    __table_args__ = (UniqueConstraint("customer_code", "name", name="uq_cloud_assessment_account_customer_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    # CASCADE: deleting a customer deletes its accounts, and with them their scans and findings.
    customer_code: str = Field(
        sa_column=Column(String(50), ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=False),
    )
    name: str = Field(max_length=100, nullable=False)
    provider: str = Field(max_length=16, nullable=False)
    auth_method: str = Field(max_length=32, nullable=False)
    config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    secret_ciphertext: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    secret_hint: Optional[str] = Field(default=None, max_length=16, nullable=True)
    secret_expires_at: Optional[datetime] = Field(default=None, nullable=True)
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default="1"))
    schedule: str = Field(default="off", sa_column=Column(String(16), nullable=False, server_default="off"))
    schedule_hour: Optional[int] = Field(default=None, sa_column=Column(SmallInteger, nullable=True))
    schedule_weekday: Optional[int] = Field(default=None, sa_column=Column(SmallInteger, nullable=True))
    last_connection_test_at: Optional[datetime] = Field(default=None, nullable=True)
    last_connection_ok: Optional[bool] = Field(default=None, nullable=True)
    # The runner's error code for the last failed test (auth_failed, permission_denied, ...).
    last_connection_error: Optional[str] = Field(default=None, max_length=32, nullable=True)
    created_by: Optional[str] = Field(default=None, max_length=256, nullable=True)
    updated_by: Optional[str] = Field(default=None, max_length=256, nullable=True)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)


class CloudAssessmentScan(SQLModel, table=True):
    """One scan of an account.

    ``status`` is ``queued``, ``running``, ``completed``, ``failed`` or ``cancelled``;
    ``trigger_type`` is ``manual`` or ``schedule`` (``trigger`` is a reserved word in
    MySQL). ``runner_job_id`` is the job in copilot-prowler while it holds the results.

    The counts come from the runner's summary: ``pass_count``, ``fail_count`` and
    ``manual_count`` exclude muted findings, counted apart in ``muted_count``; the
    ``fail_<severity>`` columns split ``fail_count``. ``new_fail_count`` and
    ``resolved_fail_count`` compare the account's previous completed scan.
    ``log_error_lines`` is how many check errors Prowler logged in a scan that still
    completed (a missing permission, usually). ``error_code`` is the runner's code for a
    failed scan and ``prowler_errors`` the exception classes it named, never a message.

    Prowler's HTML and CSV reports are kept in MinIO (``report_bucket``, then a key, size
    and SHA-256 per report). ``findings_pruned_at`` is set when retention has removed the
    scan's findings and reports; its counts and check results stay, for trends.
    """

    __tablename__ = "cloud_assessment_scan"
    __table_args__ = (
        Index("ix_cloud_assessment_scan_account_queued", "account_id", "queued_at"),
        Index("ix_cloud_assessment_scan_customer_queued", "customer_code", "queued_at"),
        Index("ix_cloud_assessment_scan_status", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(
        sa_column=Column(Integer, ForeignKey("cloud_assessment_account.id", ondelete="CASCADE"), nullable=False),
    )
    customer_code: str = Field(max_length=50, nullable=False)
    status: str = Field(max_length=16, nullable=False)
    trigger_type: str = Field(max_length=16, nullable=False)
    requested_by: Optional[str] = Field(default=None, max_length=256, nullable=True)
    runner_job_id: Optional[str] = Field(default=None, max_length=32, nullable=True)
    prowler_version: Optional[str] = Field(default=None, max_length=32, nullable=True)
    queued_at: datetime = Field(default_factory=now_utc, nullable=False)
    started_at: Optional[datetime] = Field(default=None, nullable=True)
    completed_at: Optional[datetime] = Field(default=None, nullable=True)
    total_count: int = _count()
    pass_count: int = _count()
    fail_count: int = _count()
    manual_count: int = _count()
    muted_count: int = _count()
    fail_critical: int = _count()
    fail_high: int = _count()
    fail_medium: int = _count()
    fail_low: int = _count()
    fail_informational: int = _count()
    fail_unknown: int = _count()
    new_fail_count: int = _count()
    resolved_fail_count: int = _count()
    log_error_lines: int = _count()
    error_code: Optional[str] = Field(default=None, max_length=32, nullable=True)
    prowler_errors: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    report_bucket: Optional[str] = Field(default=None, max_length=63, nullable=True)
    html_object_key: Optional[str] = Field(default=None, max_length=512, nullable=True)
    html_file_size: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    html_file_hash: Optional[str] = Field(default=None, max_length=64, nullable=True)
    csv_object_key: Optional[str] = Field(default=None, max_length=512, nullable=True)
    csv_file_size: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    csv_file_hash: Optional[str] = Field(default=None, max_length=64, nullable=True)
    findings_pruned_at: Optional[datetime] = Field(default=None, nullable=True)


class CloudAssessmentCheckResult(SQLModel, table=True):
    """One check of one scan: its metadata as it was at scan time, and its counts.

    ``compliance`` maps a framework key (``CIS-5.0``, ``MITRE-ATTACK``: ``<Framework>-<Version>``
    as Prowler writes it) to the requirement ids the check covers; the compliance views
    are computed from these rows. ``remediation_urls`` and ``additional_urls`` hold http(s)
    URLs only.
    """

    __tablename__ = "cloud_assessment_check_result"
    __table_args__ = (
        UniqueConstraint("scan_id", "check_id", name="uq_cloud_assessment_check_result_scan_check"),
        Index("ix_cloud_assessment_check_result_scan_fail", "scan_id", "fail_count"),
    )

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    scan_id: int = Field(
        sa_column=Column(Integer, ForeignKey("cloud_assessment_scan.id", ondelete="CASCADE"), nullable=False),
    )
    check_id: str = Field(max_length=128, nullable=False)
    title: str = Field(default="", max_length=512, nullable=False)
    service: str = Field(default="", max_length=64, nullable=False)
    severity: str = Field(max_length=16, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    risk: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    remediation: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    remediation_urls: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    additional_urls: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    categories: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    compliance: Optional[Dict[str, List[str]]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    pass_count: int = _count()
    fail_count: int = _count()
    manual_count: int = _count()
    muted_count: int = _count()


class CloudAssessmentFinding(SQLModel, table=True):
    """A FAIL or MANUAL finding of one scan (a muted one is flagged ``muted``).

    ``finding_uid`` is Prowler's id for the finding, cut to 512 characters for display;
    ``finding_uid_hash`` is the SHA-256 of the whole id, which is what matches a finding
    across scans: ``first_seen_at`` carries forward while the same finding keeps failing,
    and ``is_new`` marks one the account's previous completed scan didn't have.
    Every text here comes from the customer's cloud and is shown as text only.
    """

    __tablename__ = "cloud_assessment_finding"
    __table_args__ = (
        Index("ix_cloud_assessment_finding_scan_severity", "scan_id", "severity"),
        Index("ix_cloud_assessment_finding_scan_check", "scan_id", "check_id"),
        Index("ix_cloud_assessment_finding_account_uid", "account_id", "finding_uid_hash"),
        Index("ix_cloud_assessment_finding_customer", "customer_code"),
    )

    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    scan_id: int = Field(
        sa_column=Column(Integer, ForeignKey("cloud_assessment_scan.id", ondelete="CASCADE"), nullable=False),
    )
    account_id: int = Field(nullable=False)
    customer_code: str = Field(max_length=50, nullable=False)
    finding_uid: str = Field(max_length=512, nullable=False)
    finding_uid_hash: str = Field(max_length=64, nullable=False)
    check_id: str = Field(max_length=128, nullable=False)
    status: str = Field(max_length=8, nullable=False)
    severity: str = Field(max_length=16, nullable=False)
    muted: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
    status_extended: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    service: str = Field(default="", max_length=64, nullable=False)
    region: str = Field(default="", max_length=64, nullable=False)
    cloud_account_uid: str = Field(default="", max_length=256, nullable=False)
    cloud_account_name: str = Field(default="", max_length=256, nullable=False)
    resource_uid: str = Field(default="", max_length=1024, nullable=False)
    resource_name: str = Field(default="", max_length=512, nullable=False)
    resource_type: str = Field(default="", max_length=128, nullable=False)
    resource_tags: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    detected_at: Optional[datetime] = Field(default=None, nullable=True)
    first_seen_at: datetime = Field(default_factory=now_utc, nullable=False)
    is_new: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="0"))
