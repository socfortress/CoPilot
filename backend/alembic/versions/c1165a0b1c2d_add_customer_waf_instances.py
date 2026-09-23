"""add customer_waf_instances table

Revision ID: c1165a0b1c2d
Revises: b934a1c2d3e4
Create Date: 2026-09-23 12:00:00.000000

SOCFortress WAF deployments per customer (#1165 / #1166). A customer may run
several WAFs, so this is one row per WAF, unique on (customer_code, name).

- `customer_code` is a hard FK to `customers.customer_code` with ON DELETE
  CASCADE: customer deletion only deletes the customer row, so a plain FK would
  make every customer with a WAF undeletable, and the config is meaningless
  without its customer.
- `service_token_encrypted` is a Fernet ciphertext (WAF_TOKEN_ENCRYPTION_KEY),
  TEXT because ciphertext length follows the token; the plaintext is never
  stored. `ca_cert_pem` is TEXT because a PEM chain can exceed any sane VARCHAR.

New table only: nothing is backfilled and no existing table is touched, so the
downgrade simply drops it (losing any WAF configurations saved since).
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1165a0b1c2d"
down_revision: Union[str, None] = "b934a1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "customer_waf_instances"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("customer_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("api_url", sa.String(length=1024), nullable=False),
        sa.Column("service_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_prefix", sa.String(length=20), nullable=False),
        sa.Column("verify_tls", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("ca_cert_pem", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_verified_role", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_code"],
            ["customers.customer_code"],
            name="fk_customer_waf_instances_customer_code",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code", "name", name="uq_customer_waf_instances_customer_name"),
    )
    op.create_index("ix_customer_waf_instances_customer_code", TABLE, ["customer_code"], unique=False)


def downgrade() -> None:
    # drop_table takes its indexes with it; dropping the customer_code index first would
    # fail on MySQL, which refuses to drop an index backing a foreign key.
    op.drop_table(TABLE)
