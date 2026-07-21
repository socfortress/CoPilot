"""Add visible_to_customer to incident management customer reports

Revision ID: e1f2a3b4c5d6
Revises: c9d1e2f3a4b5
Create Date: 2026-07-20 10:00:00.000000

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "c9d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "incident_management_customer_reports"
COLUMN_NAME = "visible_to_customer"


def _has_column(bind) -> bool:
    return any(col["name"] == COLUMN_NAME for col in inspect(bind).get_columns(TABLE_NAME))


def upgrade() -> None:
    # Idempotent: skip if the column already exists (see the c9d1e2f3a4b5 migration
    # note — MySQL DDL auto-commits, so a half-applied run must be safe to re-run).
    bind = op.get_bind()
    if not _has_column(bind):
        op.add_column(
            TABLE_NAME,
            sa.Column("visible_to_customer", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind):
        op.drop_column(TABLE_NAME, COLUMN_NAME)
