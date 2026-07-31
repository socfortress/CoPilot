"""Add customer_portal_ai_report_settings table

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-07-29 00:00:00.000000

Per-customer switch for the Customer Portal AI Analyst surfaces (overview
insights card + alert-detail AI Report tab). Opt-in by design: no row means the
customer does not see AI findings, so this migration does not backfill anything.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_ai_report_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_ai_report_settings_customer_code",
        "customer_portal_ai_report_settings",
        ["customer_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_portal_ai_report_settings_customer_code",
        table_name="customer_portal_ai_report_settings",
    )
    op.drop_table("customer_portal_ai_report_settings")
