"""add event search memory tables

Revision ID: d1258a1b2c3d
Revises: c1241a1b2c3d
Create Date: 2026-10-15 12:00:00.000000

What event search remembers for a user, per customer (#1258), kept on the server so the
user finds it on any device:

- `event_search_saved_query`: searches saved under a name, unique on
  (user_id, customer_code, name);
- `event_search_recent_query`: the last searches run (the service keeps ten);
- `event_search_columns`: the columns picked for one event source, unique on
  (user_id, customer_code, source_name).

`user_id` and `customer_code` are hard FKs with ON DELETE CASCADE, so deleting a user
or a customer takes their rows with it (`delete_user` deletes the user row only).

New tables only: nothing is backfilled and no existing table is touched. The downgrade
drops the three tables, losing what users saved.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1258a1b2c3d"
down_revision: Union[str, None] = "c1241a1b2c3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SAVED = "event_search_saved_query"
RECENT = "event_search_recent_query"
COLUMNS = "event_search_columns"


def _owner(table: str) -> list:
    return [
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name=f"fk_{table}_user_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
            name=f"fk_{table}_customer_code",
            ondelete="CASCADE",
        ),
    ]


def _state() -> list:
    return [
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("time_mode", sa.String(length=16), nullable=False),
        sa.Column("time_amount", sa.Integer(), nullable=False),
        sa.Column("time_unit", sa.String(length=1), nullable=False),
        sa.Column("time_from", sa.DateTime(), nullable=True),
        sa.Column("time_to", sa.DateTime(), nullable=True),
        sa.Column("page_size", sa.Integer(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        SAVED,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        *_owner(SAVED),
        sa.Column("name", sa.String(length=80), nullable=False),
        *_state(),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "customer_code", "name", name="uq_event_search_saved_query"),
    )
    op.create_table(
        RECENT,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        *_owner(RECENT),
        *_state(),
        sa.Column("ran_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_search_recent_query_owner", RECENT, ["user_id", "customer_code"], unique=False)
    op.create_table(
        COLUMNS,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        *_owner(COLUMNS),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "customer_code", "source_name", name="uq_event_search_columns"),
    )


def downgrade() -> None:
    op.drop_table(COLUMNS)
    op.drop_table(RECENT)
    op.drop_table(SAVED)
