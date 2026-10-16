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
(cut to 64 characters; `split-<report id>-<n>-<original job id>` if a job not made by this
migration already has that id), status `completed`, `completed_at` set to the report's `created_at`,
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


#: How many ids `split_target` tries for one report before giving up.
MAX_SPLIT_ATTEMPTS = 100


def split_job_id(report_id: int, job_id: str, attempt: int = 1) -> str:
    """The id of the job an older duplicate report moves to: `split-<report>-<job>`, then `split-<report>-<n>-<job>`."""
    infix = f"{report_id}" if attempt == 1 else f"{report_id}-{attempt}"
    return f"split-{infix}-{job_id}"[:JOB_ID_MAX]


def split_note(job_id: str) -> str:
    return f"Split from job {job_id} by migration {revision}: it held a second report for that job."


def split_target(bind, report_id: int, job_id: str, alert_id: int, customer_code: str) -> tuple[str, bool]:
    """The job id to move ``report_id`` to, and whether that job must be created.

    An existing job with the split id is reused only if it is this migration's own split of
    the same job (same alert, customer and note) and holds no report yet. Anything else with
    that id (on code before this change an analyst could create a job under any id for their
    customers) is not ours, so the next suffix is tried rather than moving a report onto it.
    """
    for attempt in range(1, MAX_SPLIT_ATTEMPTS + 1):
        candidate = split_job_id(report_id, job_id, attempt)
        row = bind.execute(
            sa.text("SELECT alert_id, customer_code, error_message FROM ai_analyst_job WHERE id = :id"),
            {"id": candidate},
        ).first()
        if row is None:
            return candidate, True
        ours = row.alert_id == alert_id and row.customer_code == customer_code and row.error_message == split_note(job_id)
        if ours and not bind.execute(sa.text(f"SELECT 1 FROM {REPORTS} WHERE job_id = :id"), {"id": candidate}).first():
            return candidate, False
        log.warning(f"ai_analyst_job {candidate} already exists and is not this migration's split of {job_id}; trying another id")
    raise RuntimeError(
        f"Cannot split duplicate report {report_id} off job {job_id}: {MAX_SPLIT_ATTEMPTS} candidate split-job ids are all taken",
    )


def split_duplicate_reports(bind) -> int:
    """Move every report but the newest of each job onto a job of its own. Returns how many moved."""
    older = bind.execute(
        sa.text(
            f"""
            SELECT r.id, r.job_id, r.created_at, j.alert_id, j.customer_code
            FROM {REPORTS} r
            JOIN (
                SELECT job_id, MAX(id) AS keep_id
                FROM {REPORTS}
                GROUP BY job_id
                HAVING COUNT(*) > 1
            ) d ON d.job_id = r.job_id
            JOIN ai_analyst_job j ON j.id = r.job_id
            WHERE r.id <> d.keep_id
            ORDER BY r.id
            """,
        ),
    ).fetchall()
    for report_id, job_id, created_at, alert_id, customer_code in older:
        split_id, create = split_target(bind, report_id, job_id, alert_id, customer_code)
        if create:
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
                {"split_id": split_id, "job_id": job_id, "completed_at": created_at, "note": split_note(job_id)},
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
