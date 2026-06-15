"""Add WebAuthn passkey tables.

Revision ID: e4f5a6b7c8d9
Revises: a1960bcb4526
Create Date: 2026-06-12 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "a1960bcb4526"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webauthn_challenge",
        sa.Column("token", sa.String(length=64), primary_key=True),
        sa.Column("challenge", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("flow", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_webauthn_challenge_user_id", "webauthn_challenge", ["user_id"])
    op.create_index("ix_webauthn_challenge_expires_at", "webauthn_challenge", ["expires_at"])

    op.create_table(
        "user_passkey",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transports", sa.JSON(), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=False, server_default="Passkey"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_passkey_user_id", "user_passkey", ["user_id"])
    op.create_index("ix_user_passkey_credential_id", "user_passkey", ["credential_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_passkey_credential_id", table_name="user_passkey")
    op.drop_index("ix_user_passkey_user_id", table_name="user_passkey")
    op.drop_table("user_passkey")

    op.drop_index("ix_webauthn_challenge_expires_at", table_name="webauthn_challenge")
    op.drop_index("ix_webauthn_challenge_user_id", table_name="webauthn_challenge")
    op.drop_table("webauthn_challenge")
