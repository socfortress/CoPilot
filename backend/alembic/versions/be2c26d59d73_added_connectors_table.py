"""Added Connectors Table

Revision ID: be2c26d59d73
Revises: 74373b4089f5
Create Date: 2024-04-21 10:42:35.302849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'be2c26d59d73'
down_revision: Union[str, None] = '74373b4089f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('connectors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('connector_name', sa.String(length=256), nullable=False),
    sa.Column('connector_type', sa.String(length=256), nullable=False),
    sa.Column('connector_url', sa.String(length=750), nullable=False),
    sa.Column('connector_last_updated', sa.DateTime(), nullable=False),
    sa.Column('connector_username', sa.String(length=256), nullable=True),
    sa.Column('connector_password', sa.String(length=256), nullable=True),
    sa.Column('connector_api_key', sa.String(length=750), nullable=True),
    sa.Column('connector_description', sa.String(length=1000), nullable=True),
    sa.Column('connector_supports', sa.String(length=1000), nullable=True),
    sa.Column('connector_configured', sa.Boolean(), nullable=False),
    sa.Column('connector_verified', sa.Boolean(), nullable=False),
    sa.Column('connector_accepts_host_only', sa.Boolean(), nullable=False),
    sa.Column('connector_accepts_api_key', sa.Boolean(), nullable=False),
    sa.Column('connector_accepts_username_password', sa.Boolean(), nullable=False),
    sa.Column('connector_accepts_file', sa.Boolean(), nullable=False),
    sa.Column('connector_accepts_extra_data', sa.Boolean(), nullable=False),
    sa.Column('connector_extra_data', sa.String(length=1000), nullable=True),
    sa.Column('connector_enabled', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('connectorhistory',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('connector_id', sa.Integer(), nullable=False),
    sa.Column('change_timestamp', sa.DateTime(), nullable=False),
    sa.Column('change_description', sa.String(length=1000), nullable=False),
    sa.ForeignKeyConstraint(['connector_id'], ['connectors.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.alter_column('smtp', 'email',
               existing_type=mysql.VARCHAR(length=256),
               type_=sa.String(length=256),
               existing_nullable=False)
    op.alter_column('user', 'email',
               existing_type=mysql.VARCHAR(length=256),
               type_=sa.String(length=256),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'email',
               existing_type=sa.String(length=256),
               type_=mysql.VARCHAR(length=256),
               existing_nullable=False)
    op.alter_column('smtp', 'email',
               existing_type=sa.String(length=256),
               type_=mysql.VARCHAR(length=256),
               existing_nullable=False)
    op.drop_table('connectorhistory')
    op.drop_table('connectors')
    # ### end Alembic commands ###
