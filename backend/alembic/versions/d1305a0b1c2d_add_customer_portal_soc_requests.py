"""add customer portal soc requests and their per-customer switch

Revision ID: d1305a0b1c2d
Revises: d0b7e1a2c3f4
Create Date: 2026-10-24 09:00:00.000000

"Ask the SOC" in the Customer Portal (#1305): ``customer_portal_soc_request`` keeps each
question a portal user asks about an alert or a case (open until the SOC answers it), and
``customer_portal_soc_request_settings`` is the per-customer switch with an optional daily
limit. Opt-in: a customer with no settings row cannot ask, so existing deployments offer
nothing new on upgrade.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1305a0b1c2d"
down_revision: Union[str, None] = "d0b7e1a2c3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_soc_request_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("daily_request_limit", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_soc_request_settings_customer_code",
        "customer_portal_soc_request_settings",
        ["customer_code"],
        unique=True,
    )

    op.create_table(
        "customer_portal_soc_request",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("origin_alert_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("urgency", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.String(length=256), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("answered_by", sa.String(length=256), nullable=True),
        sa.Column("answered_via", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["incident_management_case.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["incident_management_alert.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_portal_soc_request_customer_code", "customer_portal_soc_request", ["customer_code"])
    op.create_index("ix_customer_portal_soc_request_case_id", "customer_portal_soc_request", ["case_id"])
    op.create_index("ix_customer_portal_soc_request_alert_id", "customer_portal_soc_request", ["alert_id"])
    op.create_index("ix_customer_portal_soc_request_status", "customer_portal_soc_request", ["status"])
    op.create_index("ix_customer_portal_soc_request_requested_at", "customer_portal_soc_request", ["requested_at"])


def downgrade() -> None:
    # Dropping a table drops its indexes; MySQL refuses to drop an index alone while a
    # foreign key relies on it.
    op.drop_table("customer_portal_soc_request")
    op.drop_table("customer_portal_soc_request_settings")
