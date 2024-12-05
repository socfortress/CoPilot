"""Add case notification column to table

Revision ID: b453170bbefc
Revises: 21a945c2982b
Create Date: 2024-12-04 15:27:29.341675

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b453170bbefc"
down_revision: Union[str, None] = "21a945c2982b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("incident_management_case", sa.Column("notification_invoked_number", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("incident_management_case", "notification_invoked_number")
    # ### end Alembic commands ###