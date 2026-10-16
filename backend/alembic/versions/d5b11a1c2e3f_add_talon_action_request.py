"""add talon_action_request (the mirror of talon-analyst's action proposals)

Revision ID: d5b11a1c2e3f
Revises: d54a0c1b2e3f
Create Date: 2026-10-16 18:00:00.000000

One row per talon-analyst action proposal (talon-analyst SPEC §5.3 M5-11, §9.5, D46, D47; plan
M5-11a), filled only from talon-analyst's ``GET /v2/actions/{id}``. The id is talon-analyst's.
``customer_code`` has no foreign key: like ``audit_log``, the row is the record of who approved
what (INV-ACT-1) and outlives the customer. ``copilot_ref`` is unique: one claim, one reference.
Nothing is written here; the table fills only while the "Talon v2" setting is on.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b11a1c2e3f"
down_revision: Union[str, None] = "d54a0c1b2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "talon_action_request"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("tool_call_id", sa.String(length=255), nullable=False),
        sa.Column("customer_code", sa.String(length=64), nullable=False),
        sa.Column("requester_user_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("side_effect", sa.String(length=32), nullable=False),
        sa.Column("executes_through", sa.String(length=128), nullable=True),
        sa.Column("target", sa.JSON(), nullable=False),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("links", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("talon_status", sa.String(length=16), nullable=False),
        sa.Column("talon_decided_by", sa.String(length=64), nullable=True),
        sa.Column("talon_decided_at", sa.DateTime(), nullable=True),
        sa.Column("talon_reported_at", sa.DateTime(), nullable=True),
        sa.Column("talon_created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("result_due_by", sa.DateTime(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("approver_user_id", sa.Integer(), nullable=True),
        sa.Column("approver_username", sa.String(length=256), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("copilot_ref", sa.String(length=255), nullable=True),
        sa.Column("state_reason", sa.String(length=255), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_posted_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_outcome_error", sa.String(length=255), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("copilot_ref", name="uq_talon_action_request_copilot_ref"),
    )
    op.create_index(f"ix_{TABLE}_thread_id", TABLE, ["thread_id"], unique=False)
    op.create_index(f"ix_{TABLE}_customer_code", TABLE, ["customer_code"], unique=False)
    op.create_index(f"ix_{TABLE}_requester_user_id", TABLE, ["requester_user_id"], unique=False)
    op.create_index(f"ix_{TABLE}_state", TABLE, ["state"], unique=False)
    op.create_index(f"ix_{TABLE}_approver_user_id", TABLE, ["approver_user_id"], unique=False)
    op.create_index(f"ix_{TABLE}_next_attempt_at", TABLE, ["next_attempt_at"], unique=False)


def downgrade() -> None:
    for column in ("next_attempt_at", "approver_user_id", "state", "requester_user_id", "customer_code", "thread_id"):
        op.drop_index(f"ix_{TABLE}_{column}", table_name=TABLE)
    op.drop_table(TABLE)
