"""index agents for the Talon action host re-check; talon_action_request.state_changed_at

Revision ID: d5b11a2b3c4d
Revises: d5b11a1c2e3f
Create Date: 2026-10-17 10:00:00.000000

The re-check before a Talon quarantine or release (talon-analyst M5-11a) locks the host's
``agents`` rows with ``SELECT … FOR UPDATE`` for as long as the route runs. Without an index every
such query scanned, and so X-locked, the whole table: a person's manual quarantine of another host
then waited and failed. With these indexes each of the re-check's queries is an index lookup, and
the lock covers the host's rows plus the neighbouring index gaps (REPEATABLE READ's next-key locks,
which are what stop a same-name insert from changing the route's ``.first()``), for the length of
the run:

- ``ix_agents_hostname``: the host name as the column's collation compares it (the quarantine
  route's own lookup);
- ``ix_agents_lower_hostname``: ``lower(hostname)``, the comparison that doesn't rely on collation;
- ``ix_agents_velociraptor_client``: ``lower(substr(velociraptor_id, 1, 18))``, the ``C.`` + 16 hex
  digits any stored client id (any case, any org suffix) claims.

**Functional indexes** (the last two) need MySQL 8.0.13 or later; CoPilot's compose pins 8.0.46.
MariaDB (whose SQLAlchemy dialect is also ``mysql``) and older MySQL don't have them: there they are
skipped with a warning, and the re-check's ``lower()`` queries still work, scanning and so locking
more of the table while a run lasts.

**Every step is idempotent**: MySQL DDL isn't transactional, so a migration that fails half-way
leaves what it did, and a rerun must skip it (each index and the column are checked first; the
downgrade likewise).

**Building them blocks writes to ``agents``**: about 3 s on 400k rows, and an open transaction on
the table holds the metadata lock the build waits for. Run it at a quiet time on a large install.

``talon_action_request.state_changed_at`` is set only when the row's state changes, so a card that
keeps reading the record can't keep a row a dead request left looking fresh.
"""
import logging
import re
from typing import Optional
from typing import Sequence
from typing import Set
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
HOSTNAME_INDEX = "ix_agents_hostname"
STATE_INDEX = f"ix_{ACTIONS}_state_changed_at"
FUNCTIONAL = {
    "ix_agents_lower_hostname": "lower(hostname)",
    "ix_agents_velociraptor_client": "lower(substr(velociraptor_id, 1, 18))",
}
#: The first MySQL with functional key parts.
FUNCTIONAL_SINCE = (8, 0, 13)

log = logging.getLogger("alembic.runtime.migration")


def supports_functional_indexes(dialect: str, version: Optional[str]) -> bool:
    """Whether ``CREATE INDEX … ((expr))`` works: SQLite (expression indexes) or MySQL 8.0.13+, never
    MariaDB (it reports a ``…-MariaDB`` version under the ``mysql`` dialect)."""
    if dialect == "sqlite":
        return True
    if dialect != "mysql" or not version or "mariadb" in version.lower():
        return False
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    return bool(match) and tuple(int(part) for part in match.groups()) >= FUNCTIONAL_SINCE


def _indexes(table: str) -> Set[str]:
    """Index names on ``table``, functional ones included (SQLAlchemy's inspector skips those)."""
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        rows = bind.execute(
            sa.text("SELECT DISTINCT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"),
            {"t": table},
        )
    elif bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = :t"), {"t": table})
    else:
        return {index["name"] for index in sa.inspect(bind).get_indexes(table)}
    return {row[0] for row in rows}


def _columns(table: str) -> Set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _version() -> Optional[str]:
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        return None
    return bind.execute(sa.text("SELECT VERSION()")).scalar()


def upgrade() -> None:
    bind = op.get_bind()
    present = _indexes(AGENTS)
    if HOSTNAME_INDEX not in present:
        op.create_index(HOSTNAME_INDEX, AGENTS, ["hostname"], unique=False)
    version = _version()
    if supports_functional_indexes(bind.dialect.name, version):
        for name, expression in FUNCTIONAL.items():
            if name in present:
                continue
            if bind.dialect.name == "mysql":
                # A functional key part takes its own parentheses (MySQL 8.0.13+).
                op.execute(f"CREATE INDEX {name} ON {AGENTS} (({expression}))")
            else:
                op.create_index(name, AGENTS, [sa.text(expression)], unique=False)
    else:
        log.warning(
            "agents: no functional indexes on %s (%s); the Talon action re-check's lower() lookups will scan "
            "and lock more of the table while a quarantine runs",
            bind.dialect.name,
            version,
        )
    if "state_changed_at" not in _columns(ACTIONS):
        op.add_column(ACTIONS, sa.Column("state_changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    if STATE_INDEX not in _indexes(ACTIONS):
        op.create_index(STATE_INDEX, ACTIONS, ["state_changed_at"], unique=False)


def downgrade() -> None:
    if STATE_INDEX in _indexes(ACTIONS):
        op.drop_index(STATE_INDEX, table_name=ACTIONS)
    if "state_changed_at" in _columns(ACTIONS):
        op.drop_column(ACTIONS, "state_changed_at")
    present = _indexes(AGENTS)
    for name in (*FUNCTIONAL, HOSTNAME_INDEX):
        if name in present:
            op.drop_index(name, table_name=AGENTS)
