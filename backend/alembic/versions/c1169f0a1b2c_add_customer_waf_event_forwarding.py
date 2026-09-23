"""add event-forwarding columns to customer_waf_instances

Revision ID: c1169f0a1b2c
Revises: c1165a0b1c2d
Create Date: 2026-09-23 22:00:00.000000

SOCFortress WAF events into the SIEM (#1169). Seven nullable columns recording what
"Set up event forwarding" provisions, so it can be torn down again:

- syslog_host / syslog_port: where this WAF sends syslog (TCP, no TLS). The host is
  what the WAF can reach, which is not necessarily CoPilot's Graylog API address.
- graylog_input_id: this WAF's own Syslog TCP input (static fields + extractors live
  on it, so deleting the input removes them).
- graylog_stream_id / graylog_index_set_id: the customer's WAF stream and waf-<code>
  index set, shared by sibling WAFs of the same customer.
- waf_forwarder_id: the log forwarder created on the WAF itself.
- forwarding_provisioned_at: set once provisioning completed.

All NULL for existing rows, nothing backfilled. The downgrade drops the columns only;
Graylog objects and WAF forwarders already provisioned are left in place.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1169f0a1b2c"
down_revision: Union[str, None] = "c1165a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "customer_waf_instances"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("syslog_host", sa.String(length=255), nullable=True))
    op.add_column(TABLE, sa.Column("syslog_port", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("graylog_input_id", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("graylog_stream_id", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("graylog_index_set_id", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("waf_forwarder_id", sa.String(length=64), nullable=True))
    op.add_column(TABLE, sa.Column("forwarding_provisioned_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for column in (
        "forwarding_provisioned_at",
        "waf_forwarder_id",
        "graylog_index_set_id",
        "graylog_stream_id",
        "graylog_input_id",
        "syslog_port",
        "syslog_host",
    ):
        op.drop_column(TABLE, column)
