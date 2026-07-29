"""Add custom_dashboard_templates table (UI-authored SIEM dashboards)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-27 00:00:00.000000

Custom dashboards are stored as templates here and enabled through the existing
``enabled_dashboards`` table with the reserved ``library_card = 'custom'``, so no
change is needed to that table and existing rows keep their meaning.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_dashboard_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=255), nullable=False),
        sa.Column("customer_code", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("vendor", sa.String(length=255), nullable=False, server_default="Custom"),
        sa.Column("product", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=50), nullable=False, server_default="Custom"),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("color", sa.String(length=9), nullable=False, server_default="#38bdf8"),
        sa.Column("icon", sa.String(length=50), nullable=False, server_default="dashboard"),
        sa.Column("default_query", sa.String(length=4096), nullable=False, server_default="*"),
        sa.Column("panels", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_custom_dashboard_templates_template_key"),
        "custom_dashboard_templates",
        ["template_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_custom_dashboard_templates_customer_code"),
        "custom_dashboard_templates",
        ["customer_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_custom_dashboard_templates_customer_code"), table_name="custom_dashboard_templates")
    op.drop_index(op.f("ix_custom_dashboard_templates_template_key"), table_name="custom_dashboard_templates")
    op.drop_table("custom_dashboard_templates")
