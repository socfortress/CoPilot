"""Add direct-webhook channel columns to customer_notification_route.

Adds three nullable columns so an AI-notification route can deliver
straight to a customer-chosen URL (n8n, Discord, Slack incoming webhook,
custom automation endpoint, …) instead of going through Shuffle's MCP:

  - webhook_url          : target URL (http/https), populated when channel='webhook'
  - webhook_method       : 'POST' (default) or 'PUT'
  - webhook_headers      : JSON-encoded custom request headers (auth tokens, …)
  - include_full_report  : when true, the dispatcher inlines the alert's full
                           AI analyst report (markdown + recommended actions +
                           IOCs) in the webhook JSON payload

All nullable / no server default — existing Shuffle routes are untouched
and read back NULL. The `channel` column is already a free-form varchar
(documented as kept that way precisely so direct channels could be added
without a migration), so only these new columns are needed.

Revision ID: a7b8c9d0e1f2
Revises: 649e1a544188
Create Date: 2026-06-27 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "649e1a544188"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_notification_route", sa.Column("webhook_url", sa.Text(), nullable=True))
    op.add_column("customer_notification_route", sa.Column("webhook_method", sa.String(length=8), nullable=True))
    op.add_column("customer_notification_route", sa.Column("webhook_headers", sa.Text(), nullable=True))
    op.add_column(
        "customer_notification_route",
        sa.Column("include_full_report", sa.Boolean(), nullable=True, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("customer_notification_route", "include_full_report")
    op.drop_column("customer_notification_route", "webhook_headers")
    op.drop_column("customer_notification_route", "webhook_method")
    op.drop_column("customer_notification_route", "webhook_url")
