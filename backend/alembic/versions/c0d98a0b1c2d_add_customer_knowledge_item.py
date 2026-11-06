"""add customer knowledge items

Revision ID: c0d98a0b1c2d
Revises: c0d97a0b1c2d
Create Date: 2026-11-06 12:00:00.000000

What the SOC records about a customer (talon-analyst SPEC D98, plan K1): one row per fact, its kind's
value in JSON, validated per kind on write. talon-analyst reads it over its read-only MySQL user.
Nothing reads an empty table differently, so existing deployments see no change on upgrade.
"""

from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0d98a0b1c2d"
down_revision: Union[str, None] = "c0d97a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_knowledge_item",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("branch", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        # No defaults: a row written outside the service must not come out approved.
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("natural_key", sa.String(length=320), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_username", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code", "natural_key", name="uq_customer_knowledge_item_natural_key"),
    )
    op.create_index(
        "ix_customer_knowledge_item_customer_kind",
        "customer_knowledge_item",
        ["customer_code", "kind"],
    )


def downgrade() -> None:
    # The table only: MySQL refuses to drop an index a foreign key relies on.
    op.drop_table("customer_knowledge_item")
