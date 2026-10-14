"""add uba_provisioned_resource and uba_rollback tables

Revision ID: c1241a1b2c3d
Revises: c1219a2b3c4d
Create Date: 2026-10-13 12:00:00.000000

Safe per-customer UBA rollback (#1241).

- `uba_provisioned_resource`: every Graylog object (and the Wazuh rules file) UBA
  setup created or found for a customer, by Graylog id, unique on
  (customer_code, kind, graylog_id). Rollback removes what this table says the
  customer owns instead of deleting by title. A removed object keeps its row with
  `removed_at` set.
- `uba_rollback`: one row per rollback, with the Graylog snapshot taken before any
  change, the steps and the verification checks (JSON).

Both carry `customer_code` as a hard FK to `customers.customer_code` with ON DELETE
CASCADE (customer deletion only deletes the customer row; a plain FK would make every
customer with UBA undeletable).

New tables only: nothing is backfilled and no existing table is touched. Customers set
up before this have no rows; their first rollback takes their objects on by title and
structure. The downgrade drops both tables (losing the ownership records and the
rollback history).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1241a1b2c3d"
down_revision: Union[str, None] = "c1219a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RESOURCES = "uba_provisioned_resource"
ROLLBACKS = "uba_rollback"


def upgrade() -> None:
    op.create_table(
        RESOURCES,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("graylog_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("shared", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("removed_at", sa.DateTime(), nullable=True),
        sa.Column("removed_by_rollback_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
            name="fk_uba_provisioned_resource_customer_code",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code", "kind", "graylog_id", name="uq_uba_provisioned_resource"),
    )
    op.create_index("ix_uba_provisioned_resource_customer_code", RESOURCES, ["customer_code"], unique=False)

    op.create_table(
        ROLLBACKS,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_username", sa.String(length=256), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("verification", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
            name="fk_uba_rollback_customer_code",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uba_rollback_customer_code", ROLLBACKS, ["customer_code"], unique=False)


def downgrade() -> None:
    # drop_table takes its indexes with it; dropping the customer_code index first would
    # fail on MySQL, which refuses to drop an index backing a foreign key.
    op.drop_table(ROLLBACKS)
    op.drop_table(RESOURCES)
