"""add the notification outbox

Revision ID: d0b7e1a2c3f4
Revises: c1298a0b1c2d
Create Date: 2026-10-24 18:00:00.000000

``notification_outbox`` makes notification delivery survive a restart: every event is a row
here before it is dispatched, and the drain marks it ``done``, retries it with backoff, or
marks it ``dead`` (``app/notifications/services/outbox.py``).

- ``queued_key`` holds the dedupe key until the row's first attempt and is unique, so one key
  is never queued twice (MySQL lets any number of rows hold NULL);
- ``delivery_uuid`` is random per row, the install-unique part of Resend's idempotency key;
- ``(status, next_attempt_at)`` serves the drain, ``(status, updated_at)`` retention and the
  lease sweep, ``(customer_code, status)`` the counts beside a customer's dispatch log.

No foreign keys, like ``notification_dispatch_log``. A new, empty table: nothing to backfill.
The downgrade drops it, and with it any notification still queued.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0b7e1a2c3f4"
down_revision: Union[str, None] = "c1298a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("event_json", sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("queued_key", sa.String(length=255), nullable=True),
        sa.Column("delivery_uuid", sa.String(length=32), nullable=False),
        sa.Column("customer_code", sa.String(length=64), nullable=True),
        sa.Column("trigger", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("route_outcomes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("claimed_by", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("queued_key", name="uq_notification_outbox_queued_key"),
    )
    op.create_index("ix_notification_outbox_dedupe_key", "notification_outbox", ["dedupe_key"])
    op.create_index("ix_notification_outbox_status_next_attempt", "notification_outbox", ["status", "next_attempt_at"])
    op.create_index("ix_notification_outbox_status_updated", "notification_outbox", ["status", "updated_at"])
    op.create_index("ix_notification_outbox_customer_status", "notification_outbox", ["customer_code", "status"])


def downgrade() -> None:
    op.drop_table("notification_outbox")
