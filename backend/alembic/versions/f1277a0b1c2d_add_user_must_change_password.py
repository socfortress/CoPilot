"""add user.must_change_password

Revision ID: f1277a0b1c2d
Revises: d5b11a2b3c4d
Create Date: 2026-10-19 12:00:00.000000

A user whose password an admin chose (a temporary one emailed, a reset, a new account)
must replace it (#1277). The flag is set by those admin routes and cleared by the user's
own change; while it is set, the Customer Portal holds a customer_user to the password
change. Existing users get false: nothing is forced on accounts already in use. The
downgrade drops the column.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1277a0b1c2d"
down_revision: Union[str, None] = "d5b11a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("user", "must_change_password")
