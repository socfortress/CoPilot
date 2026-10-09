"""Let Customer Portal users request AI analyses (#1215)

Revision ID: c1215a7b8d9e
Revises: d1195a7b3c4e
Create Date: 2026-10-09 00:00:00.000000

Two per-customer settings next to the AI report switch (requests allowed, daily limit)
and the table of requests, which the per-alert cooldown and the daily limit count.
Opt-in: existing customers keep requests off and no limit set, so nothing changes until
an operator turns it on.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1215a7b8d9e"
down_revision: Union[str, None] = "d1195a7b3c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_portal_ai_report_settings",
        sa.Column("allow_customer_requests", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "customer_portal_ai_report_settings",
        sa.Column("daily_request_limit", sa.Integer(), nullable=True),
    )
    op.create_table(
        "customer_portal_ai_request",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.String(length=256), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_portal_ai_request_customer_code", "customer_portal_ai_request", ["customer_code"])
    op.create_index("ix_customer_portal_ai_request_alert_id", "customer_portal_ai_request", ["alert_id"])
    op.create_index("ix_customer_portal_ai_request_requested_at", "customer_portal_ai_request", ["requested_at"])


def downgrade() -> None:
    # Dropping the table drops its indexes; dropping the customer_code index on its own is
    # refused by MySQL while the foreign key needs it.
    op.drop_table("customer_portal_ai_request")
    op.drop_column("customer_portal_ai_report_settings", "daily_request_limit")
    op.drop_column("customer_portal_ai_report_settings", "allow_customer_requests")
