"""index agents for the Talon action host re-check; talon_action_request.state_changed_at

Revision ID: d5b11a2b3c4d
Revises: d5b11a1c2e3f
Create Date: 2026-10-17 10:00:00.000000

The re-check before a Talon quarantine or release (talon-analyst M5-11a) locks the host's
``agents`` rows with ``SELECT … FOR UPDATE`` for as long as the route runs. Without an index every
such query scanned, and so X-locked, the whole table: a person's manual quarantine of another host
then waited and failed. Three indexes make each of the re-check's queries an index lookup, so only
the matching rows (and their gaps) are locked:

- ``ix_agents_hostname``: the host name as the column's collation compares it (the quarantine
  route's own lookup);
- ``ix_agents_lower_hostname``: ``lower(hostname)``, the comparison that doesn't rely on collation;
- ``ix_agents_velociraptor_client``: ``lower(substr(velociraptor_id, 1, 18))``, the ``C.`` + 16 hex
  digits any stored client id (any case, any org suffix) claims.

The last two are functional indexes (MySQL 8.0.13 or later; CoPilot's compose pins 8.0.46).

``talon_action_request.state_changed_at`` is set only when the row's state changes, so a card that
keeps reading the record can't keep a row a dead request left looking fresh.
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b11a2b3c4d"
down_revision: Union[str, None] = "d5b11a1c2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AGENTS = "agents"
ACTIONS = "talon_action_request"
FUNCTIONAL = {
    "ix_agents_lower_hostname": "lower(hostname)",
    "ix_agents_velociraptor_client": "lower(substr(velociraptor_id, 1, 18))",
}


def upgrade() -> None:
    op.create_index("ix_agents_hostname", AGENTS, ["hostname"], unique=False)
    for name, expression in FUNCTIONAL.items():
        if op.get_bind().dialect.name == "mysql":
            # A functional key part takes its own parentheses (MySQL 8.0.13+).
            op.execute(f"CREATE INDEX {name} ON {AGENTS} (({expression}))")
        else:
            op.create_index(name, AGENTS, [sa.text(expression)], unique=False)
    op.add_column(ACTIONS, sa.Column("state_changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index(f"ix_{ACTIONS}_state_changed_at", ACTIONS, ["state_changed_at"], unique=False)


def downgrade() -> None:
    op.drop_index(f"ix_{ACTIONS}_state_changed_at", table_name=ACTIONS)
    op.drop_column(ACTIONS, "state_changed_at")
    for name in FUNCTIONAL:
        op.drop_index(name, table_name=AGENTS)
    op.drop_index("ix_agents_hostname", table_name=AGENTS)
