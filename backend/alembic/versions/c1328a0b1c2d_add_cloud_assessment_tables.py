"""add cloud assessment tables

Revision ID: c1328a0b1c2d
Revises: 38c2e85a670a
Create Date: 2026-11-23 12:00:00.000000

Cloud security assessment with Prowler (#1328): four new tables.

- ``cloud_assessment_account``: a customer's cloud account (AWS, Azure, GCP or Microsoft 365),
  its non-secret settings in JSON, its credential as a Fernet ciphertext (TEXT, since the
  length follows the credential; a GCP key file is a few KB), its schedule and last connection
  test. ``customer_code`` is a hard FK to ``customers.customer_code`` with ON DELETE CASCADE:
  customer deletion only deletes the customer row, so a plain FK would make a customer with a
  cloud account undeletable. Unique on (customer_code, name).
- ``cloud_assessment_scan``: one scan of an account, its counts and the MinIO keys of
  Prowler's HTML and CSV reports. Cascades from its account.
- ``cloud_assessment_check_result``: one row per check of a scan (unique on scan and check),
  the check's metadata at scan time and its counts. Cascades from its scan.
- ``cloud_assessment_finding``: one row per FAIL or MANUAL finding of a scan, matched across
  scans by ``finding_uid_hash``. Cascades from its scan.

Every foreign key points at a unique key (``customers.customer_code`` is unique since
38c2e85a670a; the others are primary keys), so MySQL 8.4 needs no setting for them. The ids of
the two high-volume tables are BIGINT. TEXT and JSON columns are nullable: MySQL gives them no
literal default.

New tables only: nothing is backfilled and no existing table changes, so existing deployments
see no difference. The downgrade drops the four tables, and with them every cloud account
(credentials included), scan and finding stored since.
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1328a0b1c2d"
down_revision: Union[str, None] = "38c2e85a670a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _count(name: str) -> sa.Column:
    return sa.Column(name, sa.Integer(), nullable=False, server_default="0")


def upgrade() -> None:
    op.create_table(
        "cloud_assessment_account",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("auth_method", sa.String(length=32), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=True),
        sa.Column("secret_hint", sa.String(length=16), nullable=True),
        sa.Column("secret_expires_at", sa.DateTime(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("schedule", sa.String(length=16), nullable=False, server_default="off"),
        sa.Column("schedule_hour", sa.SmallInteger(), nullable=True),
        sa.Column("schedule_weekday", sa.SmallInteger(), nullable=True),
        sa.Column("last_connection_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_connection_ok", sa.Boolean(), nullable=True),
        sa.Column("last_connection_error", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=256), nullable=True),
        sa.Column("updated_by", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Also the index the customer_code foreign key uses.
        sa.UniqueConstraint("customer_code", "name", name="uq_cloud_assessment_account_customer_name"),
    )

    op.create_table(
        "cloud_assessment_scan",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("trigger_type", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=256), nullable=True),
        sa.Column("runner_job_id", sa.String(length=32), nullable=True),
        sa.Column("prowler_version", sa.String(length=32), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        _count("total_count"),
        _count("pass_count"),
        _count("fail_count"),
        _count("manual_count"),
        _count("muted_count"),
        _count("fail_critical"),
        _count("fail_high"),
        _count("fail_medium"),
        _count("fail_low"),
        _count("fail_informational"),
        _count("fail_unknown"),
        _count("new_fail_count"),
        _count("resolved_fail_count"),
        _count("log_error_lines"),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("prowler_errors", sa.JSON(), nullable=True),
        sa.Column("report_bucket", sa.String(length=63), nullable=True),
        sa.Column("html_object_key", sa.String(length=512), nullable=True),
        sa.Column("html_file_size", sa.BigInteger(), nullable=True),
        sa.Column("html_file_hash", sa.String(length=64), nullable=True),
        sa.Column("csv_object_key", sa.String(length=512), nullable=True),
        sa.Column("csv_file_size", sa.BigInteger(), nullable=True),
        sa.Column("csv_file_hash", sa.String(length=64), nullable=True),
        sa.Column("findings_pruned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["cloud_assessment_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The first is also the index the account_id foreign key uses.
    op.create_index("ix_cloud_assessment_scan_account_queued", "cloud_assessment_scan", ["account_id", "queued_at"])
    op.create_index("ix_cloud_assessment_scan_customer_queued", "cloud_assessment_scan", ["customer_code", "queued_at"])
    op.create_index("ix_cloud_assessment_scan_status", "cloud_assessment_scan", ["status"])

    op.create_table(
        "cloud_assessment_check_result",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("check_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("remediation_urls", sa.JSON(), nullable=True),
        sa.Column("additional_urls", sa.JSON(), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("compliance", sa.JSON(), nullable=True),
        _count("pass_count"),
        _count("fail_count"),
        _count("manual_count"),
        _count("muted_count"),
        sa.ForeignKeyConstraint(["scan_id"], ["cloud_assessment_scan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Also the index the scan_id foreign key uses.
        sa.UniqueConstraint("scan_id", "check_id", name="uq_cloud_assessment_check_result_scan_check"),
    )
    op.create_index("ix_cloud_assessment_check_result_scan_fail", "cloud_assessment_check_result", ["scan_id", "fail_count"])

    op.create_table(
        "cloud_assessment_finding",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("finding_uid", sa.String(length=512), nullable=False),
        sa.Column("finding_uid_hash", sa.String(length=64), nullable=False),
        sa.Column("check_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status_extended", sa.Text(), nullable=True),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("cloud_account_uid", sa.String(length=256), nullable=False),
        sa.Column("cloud_account_name", sa.String(length=256), nullable=False),
        sa.Column("resource_uid", sa.String(length=1024), nullable=False),
        sa.Column("resource_name", sa.String(length=512), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_tags", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["scan_id"], ["cloud_assessment_scan.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # The first is also the index the scan_id foreign key uses.
    op.create_index("ix_cloud_assessment_finding_scan_severity", "cloud_assessment_finding", ["scan_id", "severity"])
    op.create_index("ix_cloud_assessment_finding_scan_check", "cloud_assessment_finding", ["scan_id", "check_id"])
    op.create_index("ix_cloud_assessment_finding_account_uid", "cloud_assessment_finding", ["account_id", "finding_uid_hash"])
    op.create_index("ix_cloud_assessment_finding_customer", "cloud_assessment_finding", ["customer_code"])


def downgrade() -> None:
    # Children first. drop_table takes each table's indexes with it; dropping an index a
    # foreign key relies on first would fail on MySQL.
    op.drop_table("cloud_assessment_finding")
    op.drop_table("cloud_assessment_check_result")
    op.drop_table("cloud_assessment_scan")
    op.drop_table("cloud_assessment_account")
