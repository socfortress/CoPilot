"""add SLA business hours, customer-wait pause and SLA notification stamps

Revision ID: e1187b2c3d4e
Revises: d1187a0b1c2d
Create Date: 2026-10-02 09:00:00.000000

Follow-ups to SOC Management & SLA (#1187):

- ``soc_sla_calendar`` — business hours (weekly windows in a timezone, holidays) for
  the deployment (customer_code NULL) or one customer. Empty on upgrade: business-hours
  targets fall back to Monday–Friday 09:00–17:00 UTC until an operator sets one.
- ``soc_sla_policy.business_hours`` — a cell's targets count business hours. Existing
  cells stay 24/7, so nothing an operator saved changes meaning.
- tracking ``business_hours`` (snapshot of the cell at opening), ``paused_at`` /
  ``paused_seconds`` / ``pause_credit_seconds`` (PENDING_CUSTOMER stops the clocks),
  and the four ``*_notified_at`` stamps that make SLA notifications fire once per clock.
  Existing rows: 24/7, never paused, nothing notified.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1187b2c3d4e"
down_revision: Union[str, None] = "d1187a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRACKING_TABLES = ("soc_sla_alert_tracking", "soc_sla_case_tracking")
NOTIFIED = ("ack_at_risk_notified_at", "ack_breached_notified_at", "resolve_at_risk_notified_at", "resolve_breached_notified_at")


def upgrade() -> None:
    op.create_table(
        "soc_sla_calendar",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), sa.ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("week", sa.JSON(), nullable=False),
        sa.Column("holidays", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.UniqueConstraint("customer_code", name="uq_soc_sla_calendar_scope"),
    )
    op.create_index("ix_soc_sla_calendar_customer_code", "soc_sla_calendar", ["customer_code"])

    op.add_column("soc_sla_policy", sa.Column("business_hours", sa.Boolean(), nullable=False, server_default=sa.false()))

    for table in TRACKING_TABLES:
        op.add_column(table, sa.Column("business_hours", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.add_column(table, sa.Column("paused_at", sa.DateTime(), nullable=True))
        op.add_column(table, sa.Column("paused_seconds", sa.Integer(), nullable=False, server_default="0"))
        op.add_column(table, sa.Column("pause_credit_seconds", sa.Integer(), nullable=False, server_default="0"))
        for column in NOTIFIED:
            op.add_column(table, sa.Column(column, sa.DateTime(), nullable=True))


def downgrade() -> None:
    for table in TRACKING_TABLES:
        for column in (*NOTIFIED, "pause_credit_seconds", "paused_seconds", "paused_at", "business_hours"):
            op.drop_column(table, column)
    op.drop_column("soc_sla_policy", "business_hours")
    # Dropping the table drops its indexes; MySQL refuses to drop an index alone while
    # the foreign key on customer_code relies on it.
    op.drop_table("soc_sla_calendar")
