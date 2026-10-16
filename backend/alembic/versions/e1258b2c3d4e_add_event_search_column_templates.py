"""add event search column templates

Revision ID: e1258b2c3d4e
Revises: d1258a1b2c3d
Create Date: 2026-10-15 16:00:00.000000

Named column sets for event search (#1258): `event_search_column_template`, one row per
template, unique on (user_id, customer_code, source_name, name). A user switches between
them; applying one copies its columns into `event_search_columns`, so editing the columns
afterwards never changes the template.

`user_id` and `customer_code` are hard FKs with ON DELETE CASCADE, like the other event
search tables. A new table only; the downgrade drops it, losing the templates.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1258b2c3d4e"
down_revision: Union[str, None] = "d1258a1b2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATES = "event_search_column_template"


def upgrade() -> None:
    op.create_table(
        TEMPLATES,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=f"fk_{TEMPLATES}_user_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
            name=f"fk_{TEMPLATES}_customer_code",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "customer_code", "source_name", "name", name="uq_event_search_column_template"),
    )


def downgrade() -> None:
    op.drop_table(TEMPLATES)
