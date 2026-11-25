"""add sysmon stats tables

Revision ID: d7a4c2e91b3f
Revises: c1328a0b1c2d
Create Date: 2026-11-24 12:00:00.000000

The weekly Sysmon noise statistics CoPilot sends to SOCFortress (app/active_response/services/sysmon_stats/): two new
tables.

- ``sysmon_stats_customer_settings``: one row per customer that an admin changed. **No row means sharing is on**, so
  existing deployments share by default on upgrade (each customer can be opted out). ``customer_code`` is a hard FK to
  ``customers.customer_code`` with ON DELETE CASCADE (customer deletion only deletes the customer row, so a plain FK
  would make the customer undeletable), and unique. ``install_dir_name`` and ``own_domains`` are optional redaction
  hints; ``withdrawn_at`` is the last withdraw SOCFortress confirmed.
- ``sysmon_stats_identity``: one row (id 1), this CoPilot's report secret (64 hex), created on first use. The customer
  pseudonyms in the reports are HMACs under it.

New tables only: nothing is backfilled and no existing table changes. The downgrade drops both tables, and with them
every opt-out: after a later upgrade again every customer shares, and a new report secret gives every customer a new
pseudonym (SOCFortress's copies of the old ones age out with its retention).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7a4c2e91b3f"
down_revision: Union[str, None] = "c1328a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sysmon_stats_customer_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("sharing_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("install_dir_name", sa.String(length=64), nullable=True),
        sa.Column("own_domains", sa.JSON(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["customer_code"], ["customers.customer_code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sysmon_stats_customer_settings_customer_code",
        "sysmon_stats_customer_settings",
        ["customer_code"],
        unique=True,
    )
    op.create_table(
        "sysmon_stats_identity",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=False),
        sa.Column("report_secret", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Dropping the table drops its index; MySQL refuses to drop the index alone while the foreign key on
    # customer_code relies on it.
    op.drop_table("sysmon_stats_identity")
    op.drop_table("sysmon_stats_customer_settings")
