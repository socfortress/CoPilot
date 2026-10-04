"""add customer portal SLA settings

Revision ID: f1187c3d4e5f
Revises: e1187b2c3d4e
Create Date: 2026-10-02 12:00:00.000000

The per-customer switch for the Customer Portal's SLA page (#1187). Opt-in: a
customer with no row does not see the page, so existing deployments publish nothing
new to their customers on upgrade.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1187c3d4e5f"
down_revision: Union[str, None] = "e1187b2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_sla_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_sla_settings_customer_code",
        "customer_portal_sla_settings",
        ["customer_code"],
        unique=True,
    )


def downgrade() -> None:
    # Dropping the table drops its index; MySQL refuses to drop the index alone while
    # the foreign key on customer_code relies on it.
    op.drop_table("customer_portal_sla_settings")
