"""unique customers.customer_code

Revision ID: 38c2e85a670a
Revises: c0d98a0b1c2d
Create Date: 2026-11-20 12:00:00.000000

44 foreign keys point at ``customers.customer_code``, and its index allows duplicates. MySQL 8.4
deprecates foreign keys to such an index: while ``restrict_fk_on_non_standard_key`` is ON it refuses
a new one, and every ALTER TABLE on ``customers``. Once the index is unique, every one of those keys
is standard, whatever that setting.

The index keeps its name and is replaced in one ALTER TABLE, because the keys need an index at every
moment. Values are compared as the unique index compares them, with the column's collation
(case-insensitive by default): ``ACME`` and ``acme`` are one customer code, as the create route
already treats them.

If the column already holds duplicates, it is left as it is, with a warning naming a few of them and
the statement to run once they are resolved: the backend still starts, and nothing else changes.

``agents.agent_id`` (the other 2 such keys, from ``agent_datastore`` and ``agent_vulnerabilities``)
stays as it is: a Wazuh agent id is unique per manager only, and two customers' agents may share one
(the Customer Portal's Exposure page matches agents by id *and* name for that reason). Those two keys
still need ``restrict_fk_on_non_standard_key`` OFF for an ALTER TABLE on ``agents`` on MySQL 8.4.

The downgrade puts the non-unique index back, which MySQL 8.4 refuses while
``restrict_fk_on_non_standard_key`` is ON for the session.
"""

import logging
from typing import List
from typing import Sequence
from typing import Tuple
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "38c2e85a670a"
down_revision: Union[str, None] = "c0d98a0b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE, COLUMN, INDEX = "customers", "customer_code", "ix_customers_customer_code"
#: How many duplicate values the warning names.
SAMPLE = 5

log = logging.getLogger("alembic.runtime.migration")


def index_shape() -> List[Tuple[int, str]]:
    """``(non_unique, column)`` for each column of the index, in key order; [] if it doesn't exist."""
    rows = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT non_unique, column_name FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = :table AND index_name = :index ORDER BY seq_in_index",
            ),
            {"table": TABLE, "index": INDEX},
        )
        .fetchall()
    )
    return [(int(non_unique), column) for non_unique, column in rows]


def duplicate_values() -> list:
    """Up to ``SAMPLE`` customer codes held by more than one row, compared with the column's collation."""
    rows = op.get_bind().execute(sa.text(f"SELECT `{COLUMN}` FROM `{TABLE}` GROUP BY `{COLUMN}` HAVING COUNT(*) > 1 LIMIT {SAMPLE}"))
    return [row[0] for row in rows.fetchall()]


def replace_index(unique: bool) -> None:
    kind = "UNIQUE INDEX" if unique else "INDEX"
    op.execute(f"ALTER TABLE `{TABLE}` DROP INDEX `{INDEX}`, ADD {kind} `{INDEX}` (`{COLUMN}`)")


def upgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    shape = index_shape()
    if [name for _, name in shape] != [COLUMN]:
        log.warning("%s.%s: no index %s on that column alone, so it is left as it is", TABLE, COLUMN, INDEX)
        return
    if shape[0][0] == 0:
        return  # already unique
    duplicates = duplicate_values()
    if duplicates:
        log.warning(
            "%s.%s holds duplicate values (%s), so it stays non-unique. Once they are resolved, run: "
            "ALTER TABLE %s DROP INDEX %s, ADD UNIQUE INDEX %s (%s)",
            TABLE,
            COLUMN,
            ", ".join(repr(value) for value in duplicates),
            TABLE,
            INDEX,
            INDEX,
            COLUMN,
        )
        return
    replace_index(unique=True)


def downgrade() -> None:
    if op.get_bind().dialect.name != "mysql":
        return
    shape = index_shape()
    if [name for _, name in shape] == [COLUMN] and shape[0][0] == 0:
        replace_index(unique=False)
