"""add customer portal ioc enrichment: its per-customer switch, the cache and the lookups

Revision ID: a1318a0b1c2d
Revises: f1312a0b1c2d
Create Date: 2026-10-28 09:00:00.000000

Threat Intel enrichment of a customer's own IOCs in the Customer Portal (#1318):
``customer_portal_ioc_enrichment_settings`` is the per-customer switch with an optional daily
limit, ``customer_portal_ioc_enrichment`` what VirusTotal and OpenCTI said about an IOC value
for a customer, and ``customer_portal_ioc_lookup`` the lookups the limit counts. Opt-in: a
customer with no settings row gets nothing, so existing deployments offer nothing new on upgrade.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1318a0b1c2d"
down_revision: Union[str, None] = "f1312a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_ioc_enrichment_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("daily_lookup_limit", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_ioc_enrichment_settings_customer_code",
        "customer_portal_ioc_enrichment_settings",
        ["customer_code"],
        unique=True,
    )

    op.create_table(
        "customer_portal_ioc_enrichment",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("value_sha256", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Leads with customer_code, so it also serves the foreign key and every read by customer.
        sa.UniqueConstraint("customer_code", "value_sha256", "source", name="uq_customer_portal_ioc_enrichment_customer_value_source"),
    )

    op.create_table(
        "customer_portal_ioc_lookup",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("value_sha256", sa.String(length=64), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_portal_ioc_lookup_customer_code", "customer_portal_ioc_lookup", ["customer_code"])
    op.create_index("ix_customer_portal_ioc_lookup_value_sha256", "customer_portal_ioc_lookup", ["value_sha256"])
    op.create_index("ix_customer_portal_ioc_lookup_requested_at", "customer_portal_ioc_lookup", ["requested_at"])


def downgrade() -> None:
    # Dropping a table drops its indexes; MySQL refuses to drop an index alone while a
    # foreign key relies on it.
    op.drop_table("customer_portal_ioc_lookup")
    op.drop_table("customer_portal_ioc_enrichment")
    op.drop_table("customer_portal_ioc_enrichment_settings")
