"""add SSO tables

Revision ID: a1b2c3d4e5f6
Revises: 72635705c067
Create Date: 2026-03-22 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "85ea2970828c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sso_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sso_enabled", sa.Boolean(), server_default="0", nullable=False),
        # Azure Entra ID
        sa.Column("azure_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("azure_tenant_id", sa.String(256), nullable=True),
        sa.Column("azure_client_id", sa.String(256), nullable=True),
        sa.Column("azure_client_secret", sa.String(512), nullable=True),
        sa.Column("azure_redirect_uri", sa.String(512), nullable=True),
        # Cloudflare Access
        sa.Column("cf_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("cf_team_domain", sa.String(256), nullable=True),
        sa.Column("cf_audience", sa.String(512), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "sso_allowed_email",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(256), nullable=False, index=True),
        sa.Column("role_id", sa.Integer(), server_default="2", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("sso_allowed_email")
    op.drop_table("sso_config")
