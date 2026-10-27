"""add user_customer_access.read_only

Revision ID: f1312a0b1c2d
Revises: e1310a0b1c2d
Create Date: 2026-10-27 09:00:00.000000

Read-only portal users (#1312): ``read_only`` marks a ``customer_user`` who may only read one of
their customers' data from the Customer Portal; every write on it is refused. Set per customer by
the SOC or by a customer admin. Existing rows keep every write they had.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1312a0b1c2d"
down_revision: Union[str, None] = "e1310a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_customer_access", sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("user_customer_access", "read_only")
