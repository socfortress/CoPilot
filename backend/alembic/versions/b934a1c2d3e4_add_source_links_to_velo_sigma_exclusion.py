"""add source alert / case links to velo sigma exclusions

Revision ID: b934a1c2d3e4
Revises: 4c460eb540ee
Create Date: 2026-09-16 13:10:00.000000

Exclusion rules can now be created in-context from the alert (and, later, the
case) that should have been suppressed (#934). Until now the only trace of that
provenance was whatever the analyst typed into `description`, so the Sources
list could not answer "which alert was this written for?" and an alert could
not show that a rule already covers it.

Two nullable integer columns, each a foreign key with ON DELETE SET NULL:

- `source_alert_id` -> `incident_management_alert.id`
- `source_case_id`  -> `incident_management_case.id`

SET NULL rather than CASCADE, deliberately: an exclusion rule is detection
tuning and must survive its originating alert being deleted (alerts are pruned
routinely, rules are not). SET NULL rather than "no FK" because, unlike the
`customer_code` string columns on this table family, both targets are CoPilot's
own tables that the alert never precedes - referential integrity costs nothing
here and keeps the link from dangling.

Both indexed: the alert page looks rules up by `source_alert_id` on every open.
Rules created before this revision keep NULL in both, which the UI reads as
"created from Sources".
"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b934a1c2d3e4"
down_revision: Union[str, None] = "4c460eb540ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "incident_management_velo_sigma_exclusion"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("source_alert_id", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("source_case_id", sa.Integer(), nullable=True))
    op.create_index("ix_velo_sigma_exclusion_source_alert_id", TABLE, ["source_alert_id"])
    op.create_index("ix_velo_sigma_exclusion_source_case_id", TABLE, ["source_case_id"])
    op.create_foreign_key(
        "fk_velo_sigma_exclusion_source_alert",
        TABLE,
        "incident_management_alert",
        ["source_alert_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_velo_sigma_exclusion_source_case",
        TABLE,
        "incident_management_case",
        ["source_case_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drops the provenance only. The rules themselves, and the comment the create path left on
    the originating alert, are untouched - the link just stops being navigable."""
    op.drop_constraint("fk_velo_sigma_exclusion_source_case", TABLE, type_="foreignkey")
    op.drop_constraint("fk_velo_sigma_exclusion_source_alert", TABLE, type_="foreignkey")
    op.drop_index("ix_velo_sigma_exclusion_source_case_id", table_name=TABLE)
    op.drop_index("ix_velo_sigma_exclusion_source_alert_id", table_name=TABLE)
    op.drop_column(TABLE, "source_case_id")
    op.drop_column(TABLE, "source_alert_id")
