"""drop the notification_dispatch_log -> customer_notification_route FK

Revision ID: b4c7e2a91f38
Revises: e5b8f31d0c47
Create Date: 2026-08-04 15:20:00.000000

Deleting a notification route failed for any route that had ever dispatched.
Two stacked causes: the ORM's default nullify-on-delete tried to set
`notification_dispatch_log.route_id = NULL`, which the column forbids, and the
foreign key itself was ON DELETE NO ACTION, so MySQL would have refused the
delete regardless.

The delete dialog promises "Dispatch log entries will be retained", and that is
the behaviour we want: the log is an append-only record of what was sent to
whom, so it has to outlive the route that wrote it.

`route_id` therefore becomes a plain indexed column, following the convention
already used by `incident_management_*.customer_code`, `monitoring_alerts` and
`customer_integrations` — orphans tolerated by design. It stays NOT NULL so an
orphaned row still records which route sent it, which is what an egress audit
trail needs.

See issue #1057.

"""
from typing import Sequence
from typing import Union

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c7e2a91f38"
down_revision: Union[str, None] = "e5b8f31d0c47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "notification_dispatch_log"
REFERRED = "customer_notification_route"
INDEX_NAME = "ix_notification_dispatch_log_route_id"


def _route_fk_names(conn) -> list:
    """Every FK on the log table that points at the routes table.

    Looked up rather than hardcoded because MySQL auto-names these
    (`notification_dispatch_log_ibfk_1` on our deployments) and the number
    depends on the order constraints were created — a name that is correct here
    is not guaranteed to be correct on another install. Returning a list also
    makes this a no-op on SQLite, which never created the constraint.
    """
    return [fk["name"] for fk in inspect(conn).get_foreign_keys(TABLE) if fk.get("referred_table") == REFERRED and fk.get("name")]


def upgrade() -> None:
    conn = op.get_bind()

    for name in _route_fk_names(conn):
        op.drop_constraint(name, TABLE, type_="foreignkey")

    # MySQL keeps the FK's backing index when the constraint is dropped, and
    # `route_id` is indexed by design (the dispatch-log view filters on it), so
    # the index is recreated only if this deployment somehow lost it.
    existing = {ix["name"] for ix in inspect(conn).get_indexes(TABLE)}
    if INDEX_NAME not in existing and not any(ix.get("column_names") == ["route_id"] for ix in inspect(conn).get_indexes(TABLE)):
        op.create_index(INDEX_NAME, TABLE, ["route_id"])


def downgrade() -> None:
    """Restore the foreign key.

    **This will fail if any log row references a route that has since been
    deleted** — which is precisely the state the upgrade makes reachable. That
    is deliberate: the alternative is silently deleting audit rows recording
    what was sent to a customer, which is worse than a loud failure.

    To downgrade, first decide what to do with the orphans:

        SELECT id, route_id, customer_code, dispatched_at
        FROM notification_dispatch_log l
        WHERE NOT EXISTS (
            SELECT 1 FROM customer_notification_route r WHERE r.id = l.route_id
        );
    """
    conn = op.get_bind()
    if not _route_fk_names(conn):
        op.create_foreign_key(
            "notification_dispatch_log_ibfk_1",
            TABLE,
            REFERRED,
            ["route_id"],
            ["id"],
        )
