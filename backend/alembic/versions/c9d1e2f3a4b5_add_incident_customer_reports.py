"""Add incident management customer reports table

Revision ID: c9d1e2f3a4b5
Revises: 649e1a544188
Create Date: 2026-07-20 09:00:00.000000

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d1e2f3a4b5"
down_revision: Union[str, None] = "649e1a544188"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "incident_management_customer_reports"


def upgrade() -> None:
    # This migration is idempotent. MySQL DDL is non-transactional and auto-commits,
    # so if a previous run created the table but crashed before stamping the revision,
    # a plain CREATE TABLE would fail with "table already exists". Guard on the live
    # schema so re-running simply skips what is already present and lets Alembic stamp
    # the revision, self-healing that half-applied state.
    inspector = inspect(op.get_bind())
    if TABLE_NAME not in inspector.get_table_names():
        op.create_table(
            TABLE_NAME,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("report_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column("customer_code", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column("bucket_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column("object_key", sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=False),
            sa.Column("file_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("file_hash", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=False),
            sa.Column("generated_at", sa.DateTime(), nullable=False),
            sa.Column("generated_by", sa.Integer(), nullable=False),
            sa.Column("generated_by_role", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
            sa.Column("date_from", sa.DateTime(), nullable=False),
            sa.Column("date_to", sa.DateTime(), nullable=False),
            sa.Column("filters_json", sa.Text(), nullable=True),
            sa.Column("total_alerts", sa.Integer(), nullable=False),
            sa.Column("total_cases", sa.Integer(), nullable=False),
            sa.Column("open_cases", sa.Integer(), nullable=False),
            sa.Column("closed_cases", sa.Integer(), nullable=False),
            sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {ix["name"] for ix in inspect(op.get_bind()).get_indexes(TABLE_NAME)}
    for column in ("customer_code", "generated_at", "status"):
        index_name = op.f(f"ix_{TABLE_NAME}_{column}")
        if index_name not in existing_indexes:
            op.create_index(index_name, TABLE_NAME, [column], unique=False)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if TABLE_NAME in inspector.get_table_names():
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(TABLE_NAME)}
        for column in ("status", "generated_at", "customer_code"):
            index_name = op.f(f"ix_{TABLE_NAME}_{column}")
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=TABLE_NAME)
        op.drop_table(TABLE_NAME)
