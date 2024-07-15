"""Add timefield field name table

Revision ID: 8af27c21d10c
Revises: e90f3760fa40
Create Date: 2024-07-15 18:44:01.436938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '8af27c21d10c'
down_revision: Union[str, None] = 'e90f3760fa40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('incident_management_timestampfieldname',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('field_name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('incident_management_timestampfieldname')
    # ### end Alembic commands ###
