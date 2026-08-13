"""record who triggered a dispatch and how

Revision ID: d1a7c4e2f905
Revises: c92e4a1f8b73
Create Date: 2026-08-02 17:10:00.000000

Manual send (#1010) pushes a specific customer's data outward on demand. "Who
sent which customer's data where" is a compliance question, and the dispatch log
had no way to answer it — every row looked the same whether it was fired by an
alert landing or by a person clicking a button.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a7c4e2f905"
down_revision: Union[str, None] = "c92e4a1f8b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL for automatic dispatches — nobody triggered them. Also populated from
    # the acting user on assignment events, where the actor is already known.
    op.add_column(
        "notification_dispatch_log",
        sa.Column("triggered_by", sa.String(length=128), nullable=True),
    )

    # 'automatic' | 'manual' | 'test'. Every existing row predates manual send,
    # so the server_default backfills them correctly in one step; it is then
    # dropped so the column matches the model, which carries a Python-side
    # default only.
    op.add_column(
        "notification_dispatch_log",
        sa.Column("trigger_source", sa.String(length=16), nullable=False, server_default="automatic"),
    )
    op.create_index(
        "ix_notification_dispatch_log_trigger_source",
        "notification_dispatch_log",
        ["trigger_source"],
    )
    op.alter_column(
        "notification_dispatch_log",
        "trigger_source",
        existing_type=sa.String(length=16),
        server_default=None,
    )


def downgrade() -> None:
    """Non-lossy for anything that existed before this revision.

    Only manual and test sends carry values these columns record; automatic
    dispatches were indistinguishable from each other anyway, which is the gap
    this closed.
    """
    op.drop_index("ix_notification_dispatch_log_trigger_source", table_name="notification_dispatch_log")
    op.drop_column("notification_dispatch_log", "trigger_source")
    op.drop_column("notification_dispatch_log", "triggered_by")
