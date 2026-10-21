"""add customer portal exposure settings

Revision ID: a1289e0b1c2d
Revises: a7d2e9c4b5f1
Create Date: 2026-10-21 09:00:00.000000

The per-customer switch for the Customer Portal's Exposure page (#1289): the tenant-wide
vulnerabilities and compliance views. Opt-in: a customer with no row does not see the
page, so existing deployments publish nothing new to their customers on upgrade.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1289e0b1c2d"
down_revision: Union[str, None] = "a7d2e9c4b5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_exposure_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_exposure_settings_customer_code",
        "customer_portal_exposure_settings",
        ["customer_code"],
        unique=True,
    )


def downgrade() -> None:
    # Dropping the table drops its index; MySQL refuses to drop the index alone while
    # the foreign key on customer_code relies on it.
    op.drop_table("customer_portal_exposure_settings")
