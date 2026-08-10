"""Add file_analysis_job / _finding / _ioc tables

Revision ID: c3f9a71d4e08
Revises: b4c7e2a91f38
Create Date: 2026-08-10 00:00:00.000000

Tier 1 static file analysis (#1067, epic #974).

Purely additive: three new tables, no column added, dropped or renamed on any
existing table, and nothing backfilled. ``customer_code`` is a real FK to
``customers.customer_code`` because every row is created by an authenticated
submission against an existing customer -- unlike the incident_management
tables, there is no ingest path here that could land an orphan.

Child rows cascade on delete: a job's findings and indicators have no meaning
without the job they belong to.
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f9a71d4e08"
down_revision: Union[str, None] = "b4c7e2a91f38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_analysis_job",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("job_uuid", sa.String(length=36), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        # submission
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("submitted_by", sa.String(length=256), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="upload"),
        # MinIO blob pointer
        sa.Column("bucket_name", sa.String(length=255), nullable=False, server_default="copilot-file-analysis"),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False, server_default="application/octet-stream"),
        # identification
        sa.Column("magic_type", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("md5", sa.String(length=32), nullable=True),
        sa.Column("sha1", sa.String(length=40), nullable=True),
        sa.Column("entropy", sa.Float(), nullable=True),
        # lifecycle
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # result
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("inspector", sa.String(length=64), nullable=True),
        sa.Column("truncated_reason", sa.String(length=255), nullable=True),
        sa.Column("shipped_to_graylog", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_analysis_job_job_uuid", "file_analysis_job", ["job_uuid"], unique=True)
    op.create_index("ix_file_analysis_job_customer_code", "file_analysis_job", ["customer_code"], unique=False)
    op.create_index("ix_file_analysis_job_submitted_at", "file_analysis_job", ["submitted_at"], unique=False)
    op.create_index("ix_file_analysis_job_file_hash", "file_analysis_job", ["file_hash"], unique=False)
    op.create_index("ix_file_analysis_job_mime_type", "file_analysis_job", ["mime_type"], unique=False)
    op.create_index("ix_file_analysis_job_md5", "file_analysis_job", ["md5"], unique=False)
    op.create_index("ix_file_analysis_job_sha1", "file_analysis_job", ["sha1"], unique=False)
    op.create_index("ix_file_analysis_job_status", "file_analysis_job", ["status"], unique=False)
    op.create_index("ix_file_analysis_job_verdict", "file_analysis_job", ["verdict"], unique=False)

    op.create_table(
        "file_analysis_finding",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("flag", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("inspector", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["file_analysis_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_analysis_finding_job_id", "file_analysis_finding", ["job_id"], unique=False)
    op.create_index("ix_file_analysis_finding_flag", "file_analysis_finding", ["flag"], unique=False)
    op.create_index("ix_file_analysis_finding_severity", "file_analysis_finding", ["severity"], unique=False)

    op.create_table(
        "file_analysis_ioc",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("ioc_type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.String(length=2048), nullable=False),
        sa.Column("context", sa.String(length=32), nullable=False, server_default="raw"),
        sa.Column("inspector", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["file_analysis_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_analysis_ioc_job_id", "file_analysis_ioc", ["job_id"], unique=False)
    op.create_index("ix_file_analysis_ioc_ioc_type", "file_analysis_ioc", ["ioc_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_file_analysis_ioc_ioc_type", table_name="file_analysis_ioc")
    op.drop_index("ix_file_analysis_ioc_job_id", table_name="file_analysis_ioc")
    op.drop_table("file_analysis_ioc")

    op.drop_index("ix_file_analysis_finding_severity", table_name="file_analysis_finding")
    op.drop_index("ix_file_analysis_finding_flag", table_name="file_analysis_finding")
    op.drop_index("ix_file_analysis_finding_job_id", table_name="file_analysis_finding")
    op.drop_table("file_analysis_finding")

    op.drop_index("ix_file_analysis_job_verdict", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_status", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_sha1", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_md5", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_mime_type", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_file_hash", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_submitted_at", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_customer_code", table_name="file_analysis_job")
    op.drop_index("ix_file_analysis_job_job_uuid", table_name="file_analysis_job")
    op.drop_table("file_analysis_job")
