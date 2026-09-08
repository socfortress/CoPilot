"""make agents.hostname comparisons case- and accent-sensitive

Revision ID: 76f5e57eb47a
Revises: 344a0d58f444
Create Date: 2026-09-08 09:11:38.612704

Two endpoints whose hostnames differ only in case collapsed into a single agent
row, and the survivor kept the other one's Velociraptor client id.

Wazuh's duplicate-name check is case-sensitive, so `vDC01` and `VDC01` enroll as
two independent agents under two different customers — the manager is behaving
correctly and reports both. CoPilot then loses one of them, because the sync
looks an agent up with `Agents.hostname == wazuh_agent.agent_name` and that
comparison runs in MySQL under the server default `utf8mb4_0900_ai_ci`, which is
case- *and* accent-insensitive. The lookup for `VDC01` matches the stored
`vDC01` row, the sync takes its update path instead of its insert path, and the
second agent overwrites the first's `agent_id`, `hostname`, `label` and
`customer_code` in place. Two Wazuh agents, one CoPilot row; the second endpoint
is simply absent from the UI.

`velociraptor_id` is not written by that update path, so the surviving row keeps
the client id resolved back when it represented the *other* customer's endpoint
even though its customer association has since flipped — which is how an asset
ends up displaying, and acting on, a Velociraptor client belonging to a
different tenant. See issue #1120.

The fix belongs on the column, not on the sync query. Nineteen call sites look
agents up by hostname, and once both rows finally exist every one of them
becomes ambiguous under a case-insensitive collation while selecting `.first()`
— including `app/middleware/customer_access.py:verify_hostname_access`, which
resolves a hostname to its owning customer for the tenant check, and the
Velociraptor quarantine route. Fixing only the sync would create two rows for
those lookups to confuse and turn a visibility bug into a cross-tenant one.
Changing the collation fixes all nineteen at once, and keeps future call sites
correct by default.

Safe to apply in place:

- `hostname` carries no index and no unique constraint, so there is no index
  rebuild and the ALTER cannot fail on existing duplicate-modulo-case data.
- Every comparison against the column is column-vs-literal; there are no
  column-to-column joins on hostname anywhere in the codebase, so this cannot
  raise "illegal mix of collations".
- Rows already collapsed are not repaired here. The next sync inserts the agent
  that was missing, and `sync_agents_velociraptor` re-resolves the stale client
  id once hostname matching is preferred over the retained `velociraptor_id`.

`utf8mb4_0900_as_cs` requires MySQL 8.0. Deployments pointed at an external
MariaDB or MySQL 5.7 fall back to `utf8mb4_bin`, which is byte-comparison and
therefore also case- and accent-sensitive.

"""
from typing import Sequence
from typing import Union

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "76f5e57eb47a"
down_revision: Union[str, None] = "344a0d58f444"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "agents"
COLUMN = "hostname"
COLUMN_TYPE = "VARCHAR(256)"

# Preferred first, fallback second. Both are case- and accent-sensitive.
SENSITIVE = ("utf8mb4_0900_as_cs", "utf8mb4_bin")
# What the column had before: the MySQL 8 default, then the 5.7/MariaDB default.
INSENSITIVE = ("utf8mb4_0900_ai_ci", "utf8mb4_general_ci")


def _is_mysql(conn) -> bool:
    """SQLite compares strings byte-wise already, so it needs no change."""
    return conn.dialect.name in ("mysql", "mariadb")


def _first_supported(conn, candidates: Sequence[str]) -> Union[str, None]:
    """The first candidate this server actually offers.

    `utf8mb4_0900_*` landed in MySQL 8.0 and does not exist on MariaDB or 5.7,
    where the ALTER would fail with errno 1273 rather than degrade.
    """
    for collation in candidates:
        supported = conn.execute(
            text("SELECT 1 FROM information_schema.COLLATIONS WHERE COLLATION_NAME = :name"),
            {"name": collation},
        ).scalar()
        if supported:
            return collation
    return None


def _current_collation(conn) -> Union[str, None]:
    return conn.execute(
        text(
            "SELECT COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column",
        ),
        {"table": TABLE, "column": COLUMN},
    ).scalar()


def _apply(conn, candidates: Sequence[str]) -> None:
    collation = _first_supported(conn, candidates)
    if collation is None:
        # Nothing sensible to set. Leaving the column alone is preferable to
        # failing the whole startup migration run on an unusual server build.
        return

    if _current_collation(conn) == collation:
        return

    op.execute(
        f"ALTER TABLE {TABLE} MODIFY {COLUMN} {COLUMN_TYPE} " f"CHARACTER SET utf8mb4 COLLATE {collation} NOT NULL",
    )


def upgrade() -> None:
    conn = op.get_bind()
    if not _is_mysql(conn):
        return
    _apply(conn, SENSITIVE)


def downgrade() -> None:
    """Restore case-insensitive matching.

    Agents whose hostnames differ only by case will start collapsing into one
    row again — that is the bug this revision fixes, and the point of a
    downgrade. Rows inserted while the column was case-sensitive are left in
    place; they are valid rows, and the sync reconciles them on its next run.
    """
    conn = op.get_bind()
    if not _is_mysql(conn):
        return
    _apply(conn, INSENSITIVE)
