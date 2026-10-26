"""add the customer portal's per-customer languages and the user's language

Revision ID: e1310a0b1c2d
Revises: d1305a0b1c2d
Create Date: 2026-10-26 09:00:00.000000

Customer Portal localization (#1310): ``customer_portal_language_settings`` holds the languages a
customer's portal users may pick (English always among them; a customer with no row has English
only), and ``user.locale`` the language a user picked (NULL: none, so English).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1310a0b1c2d"
down_revision: Union[str, None] = "d1305a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_portal_language_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("languages", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customer_portal_language_settings_customer_code",
        "customer_portal_language_settings",
        ["customer_code"],
        unique=True,
    )
    op.add_column("user", sa.Column("locale", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "locale")
    # Dropping the table drops its index; MySQL refuses to drop an index alone while a foreign
    # key relies on it.
    op.drop_table("customer_portal_language_settings")
