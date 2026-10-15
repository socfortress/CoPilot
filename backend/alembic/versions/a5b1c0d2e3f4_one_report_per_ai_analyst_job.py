"""one report per AI analyst job

Revision ID: a5b1c0d2e3f4
Revises: e1258b2c3d4e
Create Date: 2026-10-15 12:00:00.000000

`ai_analyst_report.job_id` becomes unique (`uq_ai_analyst_report_job_id`). Talon files a
job's report once and checks for it before every attempt, so a second report for a job is a
write-back POST retried after its answer was lost. CoPilot now refuses it with a 409.

This runs at startup, so existing duplicates must not stop it. For every job that holds more
than one report, the newest (highest id) stays on the job and each older one moves to a job
of its own: a copy of the original job row, with the id `split-<report id>-<original job id>`
(cut to 64 characters), status `completed`, `completed_at` set to the report's `created_at`,
and an `error_message` naming the original job. Nothing is deleted. A report's IOCs, reviews
and lessons hang off its report id, which doesn't change, and the alert still shows every
report, because `GET /talon/jobs/{alert_id}` lists all of the alert's jobs. Each split is
logged as a warning.

The downgrade drops the index only. Split-off jobs stay as they are.
"""
import logging
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5b1c0d2e3f4"
down_revision: Union[str, None] = "e1258b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REPORTS = "ai_analyst_report"
UNIQUE = "uq_ai_analyst_report_job_id"
JOB_ID_MAX = 64

log = logging.getLogger("alembic.runtime.migration")


def split_job_id(report_id: int, job_id: str) -> str:
    """The id of the job an older duplicate report moves to. Unique because the report id is."""
    return f"split-{report_id}-{job_id}"[:JOB_ID_MAX]


def split_duplicate_reports(bind) -> int:
    """Move every report but the newest of each job onto a job of its own. Returns how many moved."""
    older = bind.execute(
        sa.text(
            f"""
            SELECT r.id, r.job_id, r.created_at
            FROM {REPORTS} r
            JOIN (
                SELECT job_id, MAX(id) AS keep_id
                FROM {REPORTS}
                GROUP BY job_id
                HAVING COUNT(*) > 1
            ) d ON d.job_id = r.job_id
            WHERE r.id <> d.keep_id
            ORDER BY r.id
            """,
        ),
    ).fetchall()
    for report_id, job_id, created_at in older:
        split_id = split_job_id(report_id, job_id)
        exists = bind.execute(sa.text("SELECT 1 FROM ai_analyst_job WHERE id = :id"), {"id": split_id}).first()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO ai_analyst_job
                        (id, alert_id, customer_code, status, alert_type, triggered_by, template_used,
                         created_at, started_at, completed_at, error_message)
                    SELECT :split_id, alert_id, customer_code, 'completed', alert_type, triggered_by, template_used,
                           created_at, started_at, :completed_at, :note
                    FROM ai_analyst_job
                    WHERE id = :job_id
                    """,
                ),
                {
                    "split_id": split_id,
                    "job_id": job_id,
                    "completed_at": created_at,
                    "note": f"Split from job {job_id} by migration {revision}: it held a second report for that job.",
                },
            )
        bind.execute(
            sa.text(f"UPDATE {REPORTS} SET job_id = :split_id WHERE id = :report_id"),
            {"split_id": split_id, "report_id": report_id},
        )
        log.warning(f"ai_analyst_report {report_id}: duplicate report for job {job_id}, moved to job {split_id}")
    return len(older)


def upgrade() -> None:
    moved = split_duplicate_reports(op.get_bind())
    if moved:
        log.warning(f"{moved} duplicate AI analyst report(s) moved to split-off jobs before making job_id unique")
    op.create_unique_constraint(UNIQUE, REPORTS, ["job_id"])


def downgrade() -> None:
    # `ix_ai_analyst_report_job_id` still indexes job_id, so the foreign key keeps an index.
    op.drop_constraint(UNIQUE, REPORTS, type_="unique")
