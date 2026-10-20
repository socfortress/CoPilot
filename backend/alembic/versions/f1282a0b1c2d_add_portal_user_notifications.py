"""add the Customer Portal's user notifications

Revision ID: f1282a0b1c2d
Revises: f1278a0b1c2d
Create Date: 2026-10-20 09:00:00.000000

Email and in-app notifications for portal users (#1282):

- ``customer_portal_notification_settings``: the per-customer switch, off unless a row
  says otherwise (the same opt-in shape as the AI report and SLA switches);
- ``customer_portal_notification_pref``: a user's choice per event, written only when
  they save (a missing row reads as the defaults);
- ``customer_portal_notification``: one row per user and notification, the bell's feed
  and the email queue, unique on (user, dedupe key) so nothing is notified twice.

Users and customers cascade to their rows, so neither deletion is refused because of
them. The downgrade drops the three tables.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1282a0b1c2d"
down_revision: Union[str, None] = "f1278a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_notification_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_code", sa.String(50), sa.ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_customer_portal_notification_settings_customer_code",
        "customer_portal_notification_settings",
        ["customer_code"],
        unique=True,
    )

    op.create_table(
        "customer_portal_notification_pref",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email", sa.String(10), nullable=False, server_default="off"),
        sa.Column("min_severity", sa.String(20), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "event", name="uq_portal_notification_pref_user_event"),
    )
    op.create_index("ix_customer_portal_notification_pref_user_id", "customer_portal_notification_pref", ["user_id"])

    op.create_table(
        "customer_portal_notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_code", sa.String(50), sa.ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("dedupe_key", sa.String(191), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("in_app", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("email_mode", sa.String(10), nullable=False, server_default="none"),
        sa.Column("email_status", sa.String(10), nullable=True),
        sa.Column("emailed_at", sa.DateTime(), nullable=True),
        sa.Column("email_error", sa.String(500), nullable=True),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_portal_notification_user_dedupe"),
    )
    op.create_index("ix_customer_portal_notification_user_id", "customer_portal_notification", ["user_id"])
    op.create_index("ix_customer_portal_notification_customer_code", "customer_portal_notification", ["customer_code"])
    op.create_index("ix_customer_portal_notification_created_at", "customer_portal_notification", ["created_at"])
    op.create_index("ix_customer_portal_notification_email_status", "customer_portal_notification", ["email_status"])


def downgrade() -> None:
    # Dropping a table drops its indexes; dropping the unique index on its own first is
    # refused by MySQL, which needs it for the foreign key on customer_code.
    op.drop_table("customer_portal_notification")
    op.drop_table("customer_portal_notification_pref")
    op.drop_table("customer_portal_notification_settings")
