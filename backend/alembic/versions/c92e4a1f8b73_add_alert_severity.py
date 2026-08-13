"""add severity to incident_management_alert

Revision ID: c92e4a1f8b73
Revises: b3f5a91c72d4
Create Date: 2026-08-02 14:50:00.000000

Alerts had no stored severity. It was derived at ingest from the Wazuh rule
level, used for the notification, and discarded — so anything after ingest
(assignment notifications, manual send, filtering, sorting) was blind to it.

See issue #1040.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c92e4a1f8b73"
down_revision: Union[str, None] = "b3f5a91c72d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable with NO default and NO backfill, both deliberate.
    #
    # NULL means "the source did not tell us", which is a different fact from
    # any particular severity — Wazuh alerts carry a rule level to map from,
    # while Office 365, CrowdStrike, Carbon Black and the rest carry no
    # equivalent. Resolution to the deployment default (DEFAULT_ALERT_SEVERITY)
    # happens at read time in `severity_of`.
    #
    # Stamping a value here would freeze it: changing the setting later would
    # then only affect alerts created afterwards, and "the source said High"
    # would become indistinguishable from "we guessed High".
    #
    # Existing rows therefore stay NULL and immediately resolve to the default,
    # which is why no backfill is needed. Recomputing from incident_management_
    # alertcontext would only help Wazuh-shaped rows anyway, and would bake in
    # exactly the guess this design avoids.
    op.add_column(
        "incident_management_alert",
        sa.Column("severity", sa.String(length=20), nullable=True),
    )
    # Filtering and sorting by severity is the point of storing it.
    op.create_index("ix_incident_management_alert_severity", "incident_management_alert", ["severity"])


def downgrade() -> None:
    """Non-lossy in any way that matters.

    The column only ever holds a value re-derivable from the source event, and
    the pre-migration code did not read it. Dropping it returns to deriving
    severity at ingest for notifications and having none thereafter.
    """
    op.drop_index("ix_incident_management_alert_severity", table_name="incident_management_alert")
    op.drop_column("incident_management_alert", "severity")
