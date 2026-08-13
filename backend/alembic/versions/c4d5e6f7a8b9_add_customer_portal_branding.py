"""Add customer_portal_branding table (per-customer branding override)

Revision ID: c4d5e6f7a8b9
Revises: b3d4e5f6a7b8
Create Date: 2026-07-24 00:00:00.000000

The global ``customer_portal_settings`` row keeps its meaning (the default
branding for every customer); this table holds optional per-customer overrides,
so no data migration is needed.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_branding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("logo_base64", mysql.LONGTEXT(), nullable=True),
        sa.Column("logo_mime_type", sa.String(length=50), nullable=True),
        sa.Column("brand_color", sa.String(length=9), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_portal_branding_customer_code"), "customer_portal_branding", ["customer_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_portal_branding_customer_code"), table_name="customer_portal_branding")
    op.drop_table("customer_portal_branding")
