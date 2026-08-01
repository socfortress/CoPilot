"""generalize notification dispatch log

Revision ID: 459ad67895be
Revises: 87cd5b105199
Create Date: 2026-08-01 14:50:28.452469

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "459ad67895be"
down_revision: Union[str, None] = "87cd5b105199"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # server_default is only needed to add a NOT NULL column to a populated
    # table; it is dropped once the rows are settled (see below), so the column
    # matches the model, which carries a Python-side default only.
    op.add_column("notification_dispatch_log", sa.Column("entity_type", sa.String(32), nullable=False, server_default="alert"))

    op.add_column("notification_dispatch_log", sa.Column("entity_id", sa.Integer(), nullable=True))
    op.execute("UPDATE notification_dispatch_log SET entity_id = alert_id")
    op.alter_column("notification_dispatch_log", "entity_id", existing_type=sa.Integer(), nullable=False)

    op.add_column("notification_dispatch_log", sa.Column("dedupe_key", sa.String(255), nullable=True))
    # `trigger` is a MySQL reserved word and must be backticked in raw SQL.
    # SQLAlchemy quotes identifiers automatically in generated DDL, which is why
    # the column could be created unquoted — but op.execute() passes this string
    # through verbatim. Without the backticks this fails mid-migration, and
    # since MySQL DDL is non-transactional the ADD COLUMNs above would already
    # have committed while alembic_version stayed behind.
    op.execute("UPDATE notification_dispatch_log SET dedupe_key = CONCAT('alert:', alert_id, ':', `trigger`)")
    op.alter_column("notification_dispatch_log", "dedupe_key", existing_type=sa.String(255), nullable=False)

    op.alter_column("notification_dispatch_log", "alert_id", existing_type=sa.Integer(), nullable=True)

    op.alter_column(
        "notification_dispatch_log",
        "shuffle_execution_id",
        new_column_name="provider_reference",
        existing_type=sa.String(128),
        existing_nullable=True,
    )

    op.drop_constraint("uq_notif_dispatch_idem", "notification_dispatch_log", type_="unique")
    op.create_unique_constraint("uq_notif_dispatch_idem", "notification_dispatch_log", ["route_id", "dedupe_key"])

    op.create_index("ix_notification_dispatch_log_entity_type", "notification_dispatch_log", ["entity_type"])
    op.create_index("ix_notification_dispatch_log_entity_id", "notification_dispatch_log", ["entity_id"])
    op.create_index("ix_notification_dispatch_log_dedupe_key", "notification_dispatch_log", ["dedupe_key"])

    # Every row now has entity_type, and the application always sets it, so the
    # scaffolding default comes off — otherwise the column keeps a server_default
    # the model doesn't declare and autogenerate flags the drift later.
    op.alter_column("notification_dispatch_log", "entity_type", existing_type=sa.String(32), server_default=None)


def downgrade() -> None:
    op.drop_index("ix_notification_dispatch_log_dedupe_key", table_name="notification_dispatch_log")
    op.drop_index("ix_notification_dispatch_log_entity_id", table_name="notification_dispatch_log")
    op.drop_index("ix_notification_dispatch_log_entity_type", table_name="notification_dispatch_log")

    op.drop_constraint("uq_notif_dispatch_idem", "notification_dispatch_log", type_="unique")

    op.alter_column(
        "notification_dispatch_log",
        "provider_reference",
        new_column_name="shuffle_execution_id",
        existing_type=sa.String(128),
        existing_nullable=True,
    )

    # LOSSY, unavoidably: rows for non-alert entities (case, case_task) have no
    # alert_id and cannot satisfy the old NOT NULL column or its unique tuple.
    # They are audit rows for events the pre-migration schema could not
    # represent at all, so reverting necessarily discards them.
    #
    # This makes downgrade an escape hatch for "the migration went wrong right
    # now", not a routine rollback to run once case/task notifications are live.
    op.execute("DELETE FROM notification_dispatch_log WHERE alert_id IS NULL")

    op.alter_column("notification_dispatch_log", "alert_id", existing_type=sa.Integer(), nullable=False)

    op.create_unique_constraint("uq_notif_dispatch_idem", "notification_dispatch_log", ["customer_code", "alert_id", "route_id", "trigger"])

    op.drop_column("notification_dispatch_log", "dedupe_key")
    op.drop_column("notification_dispatch_log", "entity_id")
    op.drop_column("notification_dispatch_log", "entity_type")
