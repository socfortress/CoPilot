"""add user_customer_access.is_customer_admin and user.disabled_at

Revision ID: b1296a0c1d2e
Revises: a1289e0b1c2d
Create Date: 2026-10-22 09:00:00.000000

Self-service management of a customer's portal users (#1296). ``is_customer_admin`` marks a
``customer_user`` as an administrator of one of their customers (set by the SOC only); such a user
manages that customer's other portal users from the Customer Portal. ``disabled_at`` disables an
account: no token is issued to it and every request it makes is refused. Existing rows are neither
admins nor disabled.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1296a0c1d2e"
down_revision: Union[str, None] = "a1289e0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_customer_access", sa.Column("is_customer_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user", sa.Column("disabled_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "disabled_at")
    op.drop_column("user_customer_access", "is_customer_admin")
