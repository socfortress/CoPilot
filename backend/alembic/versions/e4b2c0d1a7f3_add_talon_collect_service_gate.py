"""add the Talon service account's collection allowlist to talon_connector_settings

Revision ID: e4b2c0d1a7f3
Revises: f1282a0b1c2d
Create Date: 2026-10-20 12:00:00.000000

Two nullable columns on ``talon_connector_settings`` for ``POST /api/artifacts/collect/start``'s
second gate (talon-analyst EA-4b, D77): the CoPilot user talon-analyst logs in as, and the auto-run
artifacts it may start. Both start unset: the service account starts nothing until an admin sets
the allowlist (``PUT /api/talon/v2/settings/collections``).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b2c0d1a7f3"
down_revision: Union[str, None] = "f1282a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "talon_connector_settings"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("collect_service_username", sa.String(length=256), nullable=True))
    op.add_column(TABLE, sa.Column("collect_allowed_artifacts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, "collect_allowed_artifacts")
    op.drop_column(TABLE, "collect_service_username")
