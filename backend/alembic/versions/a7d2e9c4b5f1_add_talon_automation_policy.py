"""add talon_automation_policy, talon_automation_start and talon_connector_settings.automation_enabled (talon-analyst plan AP-2)

Revision ID: a7d2e9c4b5f1
Revises: c2a2a0b1d3e4
Create Date: 2026-10-21 18:00:00.000000

The per-customer automation policy (talon-analyst plan AP-2, SPEC D85): one row per customer, a mode
per level (``off``, ``shadow``, ``propose``, ``auto``), level 2's lists for later, cap overrides,
the admin's risk acknowledgement for levels 3-4, and who changed it when. **It starts empty, and no
row means every level off**: from this migration on, the Talon service account's collection starts
are refused until an admin creates the customer's row and turns the global switch on.

``talon_automation_start``: one row per automated start given a slot and per dry run; the caps count
it. ``talon_connector_settings.automation_enabled``: the global kill switch, off.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d2e9c4b5f1"
down_revision: Union[str, None] = "c2a2a0b1d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SETTINGS = "talon_connector_settings"
POLICY = "talon_automation_policy"
STARTS = "talon_automation_start"
INDEXES = {
    "ix_talon_automation_start_customer_created": ["customer_code", "created_at"],
    "ix_talon_automation_start_client_created": ["velociraptor_id", "created_at"],
    "ix_talon_automation_start_alert_created": ["alert_id", "created_at"],
}


def upgrade() -> None:
    op.add_column(SETTINGS, sa.Column("automation_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        POLICY,
        sa.Column("customer_code", sa.String(length=64), nullable=False),
        sa.Column("level_1_mode", sa.String(length=16), nullable=False),
        sa.Column("level_2_mode", sa.String(length=16), nullable=False),
        sa.Column("level_3_mode", sa.String(length=16), nullable=False),
        sa.Column("level_4_mode", sa.String(length=16), nullable=False),
        sa.Column("level_2_artifacts", sa.JSON(), nullable=True),
        sa.Column("file_allow_globs", sa.JSON(), nullable=True),
        sa.Column("caps", sa.JSON(), nullable=True),
        sa.Column("risk_acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("risk_acknowledged_by_username", sa.String(length=256), nullable=True),
        sa.Column("risk_acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("shadow_reviewed", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_username", sa.String(length=256), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("customer_code"),
    )
    op.create_table(
        STARTS,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=64), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(length=256), nullable=False),
        sa.Column("velociraptor_id", sa.String(length=64), nullable=False),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("artifact", sa.String(length=256), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("command_sha256", sa.String(length=64), nullable=True),
        sa.Column("command_length", sa.Integer(), nullable=True),
        sa.Column("file_bytes", sa.BigInteger(), nullable=True),
        sa.Column("trigger_id", sa.Integer(), nullable=True),
        sa.Column("trigger_source", sa.String(length=16), nullable=True),
        sa.Column("trigger_user_id", sa.Integer(), nullable=True),
        sa.Column("trigger_username", sa.String(length=256), nullable=True),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("flow_id", sa.String(length=80), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in INDEXES.items():
        op.create_index(name, STARTS, columns, unique=False)


def downgrade() -> None:
    for name in INDEXES:
        op.drop_index(name, table_name=STARTS)
    op.drop_table(STARTS)
    op.drop_table(POLICY)
    op.drop_column(SETTINGS, "automation_enabled")
