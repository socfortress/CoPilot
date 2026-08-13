"""add route config, scope and recipient_mode

Revision ID: 8c41d7e2b90a
Revises: 459ad67895be
Create Date: 2026-08-01 15:40:00.000000

Phase 1b of the notification refactor (#1018), first of two steps.

This revision only ADDS and BACKFILLS. The six per-channel columns it supersedes
(shuffle_app_id, shuffle_app_name, webhook_url, webhook_method, webhook_headers,
include_full_report) are deliberately left in place and dual-written by the
application for one release, so this change is losslessly revertible. #1018b
drops them once config has been verified against them on real data.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c41d7e2b90a"
down_revision: Union[str, None] = "459ad67895be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default on the three NOT NULL columns is scaffolding for adding
    # them to a populated table; it comes off at the end so the columns match
    # the model, which declares Python-side defaults only.
    op.add_column("customer_notification_route", sa.Column("config", sa.Text(), nullable=True))
    op.add_column(
        "customer_notification_route",
        sa.Column("scope", sa.String(16), nullable=False, server_default="customer"),
    )
    op.add_column(
        "customer_notification_route",
        sa.Column("recipient_mode", sa.String(16), nullable=False, server_default="static"),
    )
    op.add_column(
        "customer_notification_route",
        sa.Column("notify_on_self_assign", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # customer_code becomes nullable: an internal-scope route belongs to no
    # tenant. Every existing row backfills to scope='customer' and keeps its
    # code, so nothing changes for them.
    op.alter_column(
        "customer_notification_route",
        "customer_code",
        existing_type=sa.String(64),
        nullable=True,
    )

    # Backfill config from the per-channel columns.
    #
    # webhook_headers already holds a JSON *string*, so it is CAST to JSON
    # rather than nested directly — nesting would double-encode it and the
    # provider would read a string where it expects an object. The CASE guards
    # NULL/empty, which CAST would reject.
    #
    # A row whose webhook_headers is present but not valid JSON would fail this
    # statement; the pre-flight check (JSON_VALID) exists to catch that before
    # the migration runs.
    op.execute(
        """
        UPDATE customer_notification_route SET config = JSON_OBJECT(
            'url', webhook_url,
            'method', COALESCE(webhook_method, 'POST'),
            'headers', CASE
                WHEN webhook_headers IS NULL OR webhook_headers = '' THEN NULL
                ELSE CAST(webhook_headers AS JSON)
            END,
            'include_full_report', COALESCE(include_full_report, 0) = 1
        ) WHERE channel = 'webhook'
        """,
    )
    op.execute(
        """
        UPDATE customer_notification_route SET config = JSON_OBJECT(
            'app_id', shuffle_app_id,
            'app_name', shuffle_app_name
        ) WHERE channel = 'shuffle'
        """,
    )
    # Any other channel value is unexpected (the registry ships two), but leave
    # such a row with config = NULL rather than guessing: the provider lookup
    # already records an unsupported channel as a per-route failure, and the
    # read schema tolerates NULL config as {}.

    op.create_index("ix_customer_notification_route_scope", "customer_notification_route", ["scope"])

    op.alter_column("customer_notification_route", "scope", existing_type=sa.String(16), server_default=None)
    op.alter_column("customer_notification_route", "recipient_mode", existing_type=sa.String(16), server_default=None)
    op.alter_column(
        "customer_notification_route",
        "notify_on_self_assign",
        existing_type=sa.Boolean(),
        server_default=None,
    )


def downgrade() -> None:
    """Non-lossy: the legacy per-channel columns were never touched.

    Any route created or edited while this revision was applied still has its
    settings in those columns, because the application dual-writes them.
    """
    op.drop_index("ix_customer_notification_route_scope", table_name="customer_notification_route")

    # Internal-scope routes have no customer_code and cannot exist under the
    # old NOT NULL constraint. They can only have been created while this
    # revision was applied, and have no representation to revert to.
    op.execute("DELETE FROM customer_notification_route WHERE customer_code IS NULL")

    op.alter_column(
        "customer_notification_route",
        "customer_code",
        existing_type=sa.String(64),
        nullable=False,
    )

    op.drop_column("customer_notification_route", "notify_on_self_assign")
    op.drop_column("customer_notification_route", "recipient_mode")
    op.drop_column("customer_notification_route", "scope")
    op.drop_column("customer_notification_route", "config")
