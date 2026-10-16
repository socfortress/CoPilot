"""add talon_connector_settings (the "Talon v2" setting)

Revision ID: d54a0c1b2e3f
Revises: a5b1c0d2e3f5
Create Date: 2026-10-16 12:00:00.000000

One row per Talon connector, keyed by its name, holding the "Talon v2" switch (talon-analyst
SPEC §5.3, D54; plan M5-5a). Off by default and opt-in: no row is written here, and a missing
row reads as off, so nothing changes until an admin turns it on.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d54a0c1b2e3f"
down_revision: Union[str, None] = "a5b1c0d2e3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "talon_connector_settings"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("connector_name", sa.String(length=256), nullable=False),
        sa.Column("v2_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(f"ix_{TABLE}_connector_name", TABLE, ["connector_name"], unique=True)


def downgrade() -> None:
    op.drop_index(f"ix_{TABLE}_connector_name", table_name=TABLE)
    op.drop_table(TABLE)
