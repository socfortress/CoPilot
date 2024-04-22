"""Added SchedulerJobMetadata Tables

Revision ID: 75dc1965a115
Revises: a15814e9a45e
Create Date: 2024-04-21 17:01:15.237030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '75dc1965a115'
down_revision: Union[str, None] = 'a15814e9a45e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('scheduled_job_metadata',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.String(length=256), nullable=False),
    sa.Column('last_success', sa.DateTime(), nullable=True),
    sa.Column('time_interval', sa.Integer(), nullable=False),
    sa.Column('extra_data', sa.String(length=1000), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheduled_job_metadata_job_id'), 'scheduled_job_metadata', ['job_id'], unique=False)
    op.alter_column('connectorhistory', 'change_description',
               existing_type=mysql.VARCHAR(length=1000),
               type_=sa.String(length=1000),
               existing_nullable=False)
    op.alter_column('customersmeta', 'customer_meta_index_retention',
               existing_type=mysql.VARCHAR(length=1024),
               type_=sa.String(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_wazuh_registration_port',
               existing_type=mysql.VARCHAR(length=1024),
               type_=sa.String(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_wazuh_log_ingestion_port',
               existing_type=mysql.VARCHAR(length=1024),
               type_=sa.String(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_wazuh_api_port',
               existing_type=mysql.VARCHAR(length=1024),
               type_=sa.String(length=1024),
               existing_nullable=True)
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
    op.alter_column('customersmeta', 'customer_meta_wazuh_api_port',
               existing_type=sa.String(length=1024),
               type_=mysql.VARCHAR(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_wazuh_log_ingestion_port',
               existing_type=sa.String(length=1024),
               type_=mysql.VARCHAR(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_wazuh_registration_port',
               existing_type=sa.String(length=1024),
               type_=mysql.VARCHAR(length=1024),
               existing_nullable=True)
    op.alter_column('customersmeta', 'customer_meta_index_retention',
               existing_type=sa.String(length=1024),
               type_=mysql.VARCHAR(length=1024),
               existing_nullable=True)
    op.alter_column('connectorhistory', 'change_description',
               existing_type=sa.String(length=1000),
               type_=mysql.VARCHAR(length=1000),
               existing_nullable=False)
    op.drop_index(op.f('ix_scheduled_job_metadata_job_id'), table_name='scheduled_job_metadata')
    op.drop_table('scheduled_job_metadata')
    # ### end Alembic commands ###