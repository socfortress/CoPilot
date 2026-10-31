"""add customer portal chat settings and the Talon draft id of a SOC request

Revision ID: c0d97a0b1c2d
Revises: a1318a0b1c2d
Create Date: 2026-10-31 12:00:00.000000

Talon chat in the Customer Portal (talon-analyst SPEC D97, §5.3 "Portal chat: CoPilot's side",
plan PC-3):

- ``customer_portal_chat_settings``: one row per customer, the chat switch and the log-search
  switch (both off by default; no row is off), the daily message limits, and a ``version`` bumped
  by every write. talon-analyst reads it over its read-only MySQL user.
- ``customer_portal_soc_request.talon_draft_id``: the portal chat draft a SOC request was filed
  from, unique, so a draft is filed at most once and the SOC sees "drafted with Talon".
- ``customer_portal_ioc_lookup.reserved_by``: ``talon`` for a lookup Talon's portal chat meter
  reserved (NULL for the portal's own), so the meter completes only its own rows.

Opt-in: no settings row means no chat, so existing deployments offer nothing new on upgrade.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0d97a0b1c2d"
down_revision: Union[str, None] = "a1318a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_chat_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("portal_chat_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("log_search_enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("daily_message_limit", sa.Integer(), nullable=True),
        sa.Column("user_daily_message_limit", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_chat_settings_customer_code",
        "customer_portal_chat_settings",
        ["customer_code"],
        unique=True,
    )

    op.add_column("customer_portal_soc_request", sa.Column("talon_draft_id", sa.String(length=36), nullable=True))
    op.create_index(
        "ix_customer_portal_soc_request_talon_draft_id",
        "customer_portal_soc_request",
        ["talon_draft_id"],
        unique=True,
    )

    op.add_column("customer_portal_ioc_lookup", sa.Column("reserved_by", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("customer_portal_ioc_lookup", "reserved_by")
    op.drop_index("ix_customer_portal_soc_request_talon_draft_id", table_name="customer_portal_soc_request")
    op.drop_column("customer_portal_soc_request", "talon_draft_id")
    # Dropping a table drops its indexes; MySQL refuses to drop an index alone while a
    # foreign key relies on it.
    op.drop_table("customer_portal_chat_settings")
