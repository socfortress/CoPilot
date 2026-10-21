"""add talon_investigation_trigger and talon_automation_alert_cap (talon-analyst plan AP-2a)

Revision ID: c2a2a0b1d3e4
Revises: f1289a0b1c2d
Create Date: 2026-10-21 12:00:00.000000

One row per ``POST /investigate`` CoPilot sends to Talon (talon-analyst plan AP-2a): the alert, its
customer, who sent it (``pipeline``, ``analyst``, ``portal``, ``replay``), the user who asked, the
alert's assets at that moment and the time. ``POST /api/artifacts/collect/start`` binds the Talon
service account's automated collections to it. Starts empty: until an alert is sent again, nothing
can be bound to it.

``talon_automation_alert_cap``: one row per alert, the window and the bound starts in it, which the
start takes a slot from (a guarded UPDATE) before the flow starts.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2a2a0b1d3e4"
down_revision: Union[str, None] = "f1289a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "talon_investigation_trigger"
INDEX = "ix_talon_investigation_trigger_alert_id_sent_at"
CAP_TABLE = "talon_automation_alert_cap"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=256), nullable=True),
        sa.Column("assets", sa.JSON(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(INDEX, TABLE, ["alert_id", "sent_at"], unique=False)
    op.create_table(
        CAP_TABLE,
        sa.Column("alert_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("customer_code", sa.String(length=64), nullable=False),
        sa.Column("starts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("alert_id"),
    )


def downgrade() -> None:
    op.drop_table(CAP_TABLE)
    op.drop_index(INDEX, table_name=TABLE)
    op.drop_table(TABLE)
