"""drop the superseded per-channel columns

Revision ID: b3f5a91c72d4
Revises: 8c41d7e2b90a
Create Date: 2026-08-01 15:45:00.000000

Phase 1b of the notification refactor (#1024), second of two steps.

8c41d7e2b90a added `config` and backfilled it from the six columns dropped here,
leaving them in place and dual-written so that revision stayed revertible. This
one removes the scaffolding.

IRREVERSIBLE IN PRACTICE. `downgrade()` recreates the columns but CANNOT
repopulate them — the application stopped writing them the moment this shipped,
so any route created or edited afterwards has its settings only in `config`.
Before running, verify config matches the legacy columns for every route and
take a snapshot of them; see the checklist on #1024.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f5a91c72d4"
down_revision: Union[str, None] = "8c41d7e2b90a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Superseded by `config`. `shuffle_integration_id` is deliberately NOT here:
    # it is a foreign key, and burying an FK in JSON would give up referential
    # integrity and the cross-tenant check the dispatcher performs at send time.
    # `destination` also stays — NOT NULL and shared across channels.
    op.drop_column("customer_notification_route", "shuffle_app_id")
    op.drop_column("customer_notification_route", "shuffle_app_name")
    op.drop_column("customer_notification_route", "webhook_url")
    op.drop_column("customer_notification_route", "webhook_method")
    op.drop_column("customer_notification_route", "webhook_headers")
    op.drop_column("customer_notification_route", "include_full_report")


def downgrade() -> None:
    """Recreates the columns EMPTY.

    This restores the shape, not the data. Every column comes back NULL, which
    for the pre-8c41d7e2b90a code means every route reads as unconfigured: a
    shuffle route with no app_id and a webhook route with no url both fail at
    dispatch with a data-integrity message rather than sending anything.

    Repopulating means replaying `config` back out — from the #1024 snapshot for
    routes that predate the drop, or by parsing `config` for those that don't.
    Deliberately not automated here: doing it silently would hide that a
    downgrade past this point needs a human decision.
    """
    op.add_column("customer_notification_route", sa.Column("shuffle_app_id", sa.String(64), nullable=True))
    op.add_column("customer_notification_route", sa.Column("shuffle_app_name", sa.String(128), nullable=True))
    op.add_column("customer_notification_route", sa.Column("webhook_url", sa.Text(), nullable=True))
    op.add_column("customer_notification_route", sa.Column("webhook_method", sa.String(8), nullable=True))
    op.add_column("customer_notification_route", sa.Column("webhook_headers", sa.Text(), nullable=True))
    op.add_column("customer_notification_route", sa.Column("include_full_report", sa.Boolean(), nullable=True))
