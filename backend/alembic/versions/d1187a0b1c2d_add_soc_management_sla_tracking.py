"""add SOC management SLA policy, SLA tracking and case severity

Revision ID: d1187a0b1c2d
Revises: c1169f0a1b2c
Create Date: 2026-10-01 12:00:00.000000

SOC Management & SLA (#1187).

- ``incident_management_case.severity`` — nullable; NULL means "take the most severe
  linked alert". Nothing backfilled into it: no analyst ever chose a severity for an
  existing case, and inventing one would hide the derivation.
- ``soc_sla_policy`` — configured SLA targets per (scope, entity, severity). Empty on
  upgrade: the built-in defaults in ``soc_management/domain/policy.py`` apply until an
  operator saves a policy.
- ``soc_sla_alert_tracking`` / ``soc_sla_case_tracking`` — one row per alert/case with
  its SLA clocks.

**Backfill, and why it is marked untracked.** Every existing alert and case gets a
tracking row, so "every item has exactly one row" holds from the first request and no
code path has to create rows lazily. Those rows carry ``tracked = 0``:

- their opening time is approximate — for alerts it is ``alert_creation_time``, which
  ingest moves to the *latest* trigger while an alert stays OPEN;
- their response history is unknown — nothing recorded who acted first, or when.

So they count in volumes and in the open backlog, but in no duration and no SLA
compliance figure, and they get no due times. Severity is the effective one (an alert's
stored severity or the deployment default; a case's most severe linked alert), which is
what the backlog-by-severity view needs.

The downgrade drops the tables and the column; it is lossy (the recorded response
history cannot be re-derived from anything else).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op
from app.incidents.services.alert_severity import SEVERITY_LEVELS
from app.incidents.services.alert_severity import default_severity

# revision identifiers, used by Alembic.
revision: str = "d1187a0b1c2d"
down_revision: Union[str, None] = "c1169f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tracking_columns():
    return [
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("ack_due_at", sa.DateTime(), nullable=True),
        sa.Column("resolve_due_at", sa.DateTime(), nullable=True),
        sa.Column("first_ack_at", sa.DateTime(), nullable=True),
        sa.Column("first_ack_by", sa.String(length=100), nullable=True),
        sa.Column("first_ack_action", sa.String(length=32), nullable=True),
        sa.Column("first_assigned_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("first_resolved_at", sa.DateTime(), nullable=True),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tracked", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def _tracking_indexes(table: str) -> None:
    for column in ("severity", "opened_at", "first_ack_by", "resolved_at", "resolved_by", "tracked"):
        op.create_index(f"ix_{table}_{column}", table, [column])


def _severity_rank_sql(column: str) -> str:
    """CASE expression ranking a severity name (Informational=1 … Critical=5)."""
    whens = " ".join(f"WHEN '{name}' THEN {rank}" for rank, name in enumerate(SEVERITY_LEVELS, start=1))
    return f"CASE {column} {whens} ELSE NULL END"


def _severity_name_sql(rank_expr: str) -> str:
    whens = " ".join(f"WHEN {rank} THEN '{name}'" for rank, name in enumerate(SEVERITY_LEVELS, start=1))
    return f"CASE {rank_expr} {whens} ELSE NULL END"


def upgrade() -> None:
    op.add_column("incident_management_case", sa.Column("severity", sa.String(length=20), nullable=True))
    op.create_index("ix_incident_management_case_severity", "incident_management_case", ["severity"])

    op.create_table(
        "soc_sla_policy",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_code",
            sa.String(length=50),
            sa.ForeignKey("customers.customer_code", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("ack_minutes", sa.Integer(), nullable=True),
        sa.Column("resolve_minutes", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.UniqueConstraint("customer_code", "entity_type", "severity", name="uq_soc_sla_policy_cell"),
    )
    op.create_index("ix_soc_sla_policy_customer_code", "soc_sla_policy", ["customer_code"])

    op.create_table(
        "soc_sla_alert_tracking",
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("incident_management_alert.id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        *_tracking_columns(),
    )
    _tracking_indexes("soc_sla_alert_tracking")

    op.create_table(
        "soc_sla_case_tracking",
        sa.Column(
            "case_id",
            sa.Integer(),
            sa.ForeignKey("incident_management_case.id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        *_tracking_columns(),
    )
    _tracking_indexes("soc_sla_case_tracking")

    fallback = default_severity()
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "INSERT INTO soc_sla_alert_tracking "
            "(alert_id, severity, opened_at, resolved_at, first_resolved_at, reopen_count, tracked, updated_at) "
            "SELECT id, COALESCE(severity, :fallback), COALESCE(alert_creation_time, CURRENT_TIMESTAMP), "
            "CASE WHEN status = 'CLOSED' THEN time_closed END, CASE WHEN status = 'CLOSED' THEN time_closed END, "
            "0, :untracked, CURRENT_TIMESTAMP FROM incident_management_alert",
        ),
        {"fallback": fallback, "untracked": False},
    )

    linked_max_rank = (
        "(SELECT MAX(" + _severity_rank_sql("COALESCE(a.severity, :fallback)") + ") "
        "FROM incident_management_casealertlink l JOIN incident_management_alert a ON a.id = l.alert_id "
        "WHERE l.case_id = c.id)"
    )
    bind.execute(
        sa.text(
            "INSERT INTO soc_sla_case_tracking "
            "(case_id, severity, opened_at, resolved_at, first_resolved_at, reopen_count, tracked, updated_at) "
            f"SELECT c.id, COALESCE({_severity_name_sql(linked_max_rank)}, :fallback), "
            "COALESCE(c.case_creation_time, CURRENT_TIMESTAMP), "
            "CASE WHEN c.case_status = 'CLOSED' THEN c.case_closed_time END, "
            "CASE WHEN c.case_status = 'CLOSED' THEN c.case_closed_time END, "
            "0, :untracked, CURRENT_TIMESTAMP FROM incident_management_case c",
        ),
        {"fallback": fallback, "untracked": False},
    )


def downgrade() -> None:
    op.drop_table("soc_sla_case_tracking")
    op.drop_table("soc_sla_alert_tracking")
    op.drop_index("ix_soc_sla_policy_customer_code", table_name="soc_sla_policy")
    op.drop_table("soc_sla_policy")
    op.drop_index("ix_incident_management_case_severity", table_name="incident_management_case")
    op.drop_column("incident_management_case", "severity")
