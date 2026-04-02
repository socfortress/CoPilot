"""Add Google OAuth2 SSO fields to sso_config table.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sso_config", sa.Column("google_enabled", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("sso_config", sa.Column("google_client_id", sa.String(256), nullable=True))
    op.add_column("sso_config", sa.Column("google_client_secret", sa.String(512), nullable=True))
    op.add_column("sso_config", sa.Column("google_redirect_uri", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("sso_config", "google_redirect_uri")
    op.drop_column("sso_config", "google_client_secret")
    op.drop_column("sso_config", "google_client_id")
    op.drop_column("sso_config", "google_enabled")
