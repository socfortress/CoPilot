"""cascade the agents.agent_id FK to agent_vulnerabilities and agent_datastore

Revision ID: 344a0d58f444
Revises: b151c7ebbb95
Create Date: 2026-08-24 11:42:07.293041

Agent sync failed with a 500 whenever Wazuh reassigned an agent_id.

`agents.agent_id` is the Wazuh-assigned id, not the surrogate PK, and it is
mutable: re-registering an agent gets it a new one. The sync matches agents on
hostname and updates that column in place, but both child tables carry a foreign
key against it that was left at the MySQL default of RESTRICT, so the UPDATE was
rejected with errno 1451 and the whole sync aborted at the affected agent —
every agent after it went unprocessed.

Both child tables are affected, not just the one in the bug report: whichever
constraint MySQL evaluates first is the one that surfaces, so a deployment with
Velociraptor artifacts hits `agent_datastore` and one without hits
`agent_vulnerabilities`.

ON DELETE differs between the two, deliberately:

- `agent_vulnerabilities` cascades. Vulnerabilities are derived data, rebuilt
  from the Wazuh Indexer on the next scan, and hold no external reference. This
  also fixes agent deletion, which hit the same 1451 for any agent that had ever
  been scanned.
- `agent_datastore` stays RESTRICT. Every row is a pointer to a MinIO object
  that has to be removed explicitly, so a silent cascade would orphan the blob.
  `delete_agent_from_database` deletes those rows itself, in order.

See issue #1086.

"""
from typing import Sequence
from typing import Union

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "344a0d58f444"
down_revision: Union[str, None] = "b151c7ebbb95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REFERRED = "agents"
COLUMN = "agent_id"

# (table, new constraint name, ondelete)
TARGETS = [
    ("agent_vulnerabilities", "fk_agent_vulnerabilities_agent_id", "CASCADE"),
    ("agent_datastore", "fk_agent_datastore_agent_id", None),
]


def _agent_fk_names(conn, table: str) -> list:
    """Every FK on `table` pointing at `agents.agent_id`.

    Looked up rather than hardcoded: the original constraints were never named,
    so MySQL auto-named them `<table>_ibfk_N`, and the number depends on the
    order constraints were created — `agent_vulnerabilities_ibfk_1` is correct
    on some installs and not others. Returning a list also makes this a no-op on
    SQLite, which never enforced the constraint.
    """
    return [
        fk["name"]
        for fk in inspect(conn).get_foreign_keys(table)
        if fk.get("referred_table") == REFERRED and fk.get("constrained_columns") == [COLUMN] and fk.get("name")
    ]


def _recreate(conn, table: str, name: str, onupdate: Union[str, None], ondelete: Union[str, None]) -> None:
    for existing in _agent_fk_names(conn, table):
        op.drop_constraint(existing, table, type_="foreignkey")

    op.create_foreign_key(
        name,
        table,
        REFERRED,
        [COLUMN],
        [COLUMN],
        onupdate=onupdate,
        ondelete=ondelete,
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Named explicitly on the way in so later migrations have a stable target
    # instead of another auto-generated `_ibfk_N`.
    for table, name, ondelete in TARGETS:
        _recreate(conn, table, name, onupdate="CASCADE", ondelete=ondelete)


def downgrade() -> None:
    """Restore the RESTRICT behaviour.

    Agent sync will start failing again on re-registration — that is the bug
    this revision fixes, and the point of a downgrade.
    """
    conn = op.get_bind()

    for table, name, _ in TARGETS:
        _recreate(conn, table, name, onupdate=None, ondelete=None)
