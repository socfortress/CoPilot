"""false positive alerts

Revision ID: b151c7ebbb95
Revises: b4c7e2a91f38
Create Date: 2026-08-20 19:48:12.209870

Alerts had no structured way to record that they were judged a false positive. Tags were
the workaround, but they are free-form and ACL-gated, so the monthly "how many false
positives, and from which detections" question could not be answered reliably.

See issue #1085.

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b151c7ebbb95"
down_revision: Union[str, None] = "b4c7e2a91f38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `verdict` is nullable with NO default and NO backfill, and that is the load-bearing
    # decision in this migration.
    #
    # NULL means "nobody has judged this alert yet", which is a different fact from
    # "judged, and not a false positive". A NOT NULL boolean defaulting to False -- the
    # obvious shape for a feature described as a false-positive flag -- would fold every
    # never-triaged alert into the true-positive side. The KPI a monthly service review
    # needs is "of the alerts we actually reviewed, X% were false positives", and that
    # ratio is only computable while unreviewed alerts remain distinguishable.
    #
    # Existing rows therefore stay NULL: they were never triaged under this scheme, and
    # inventing a verdict for them would put fabricated data into the first report anyone
    # runs. Backfilling from an existing "FP"-style tag was considered and rejected for
    # the same reason -- tag spelling is exactly what is not trustworthy here.
    op.add_column(
        "incident_management_alert",
        sa.Column("verdict", sa.String(length=20), nullable=True),
    )

    # Why it was judged a false positive. Only meaningful alongside verdict =
    # FALSE_POSITIVE; the application enforces that pairing, since a CHECK constraint here
    # would be unenforced on MySQL 5.7 and silently ignored rather than failing loudly.
    op.add_column(
        "incident_management_alert",
        sa.Column("verdict_reason", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "incident_management_alert",
        sa.Column("verdict_note", sa.String(length=1024), nullable=True),
    )

    # Who judged it and when. `verdict_by` is a username snapshot with no foreign key,
    # matching `assigned_to` on this table: the record of who made the call has to survive
    # that user being deleted. These carry the CURRENT verdict only -- the change history,
    # including a verdict later reversed, lives in `audit_log` under alert.verdict_set /
    # alert.verdict_clear.
    op.add_column(
        "incident_management_alert",
        sa.Column("verdict_by", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "incident_management_alert",
        sa.Column("verdict_at", sa.DateTime(), nullable=True),
    )

    # Filtering by verdict is the point of storing it -- including the untriaged slice,
    # which is an IS NULL scan an analyst runs against a whole review backlog.
    op.create_index("ix_incident_management_alert_verdict", "incident_management_alert", ["verdict"])

    # Every reporting query is per-tenant ("false positive rate for customer X last
    # month"), so the composite carries those rather than making them scan the
    # single-column index and filter. customer_code first: it is the more selective leg
    # and the one always present, while verdict may be absent from a query that only
    # counts a customer's alerts.
    op.create_index(
        "ix_incident_management_alert_customer_verdict",
        "incident_management_alert",
        ["customer_code", "verdict"],
    )


def downgrade() -> None:
    """Lossy: an analyst's triage judgement is not re-derivable from anything else.

    The audit_log rows written by alert.verdict_set / alert.verdict_clear survive this
    downgrade and hold the same information, so a re-upgrade could be reconstructed from
    them if it ever mattered. That reconstruction is deliberately not automated here --
    replaying it belongs in a one-off script written by whoever needs it, not in a
    downgrade path that would run silently.
    """
    op.drop_index("ix_incident_management_alert_customer_verdict", table_name="incident_management_alert")
    op.drop_index("ix_incident_management_alert_verdict", table_name="incident_management_alert")
    op.drop_column("incident_management_alert", "verdict_at")
    op.drop_column("incident_management_alert", "verdict_by")
    op.drop_column("incident_management_alert", "verdict_note")
    op.drop_column("incident_management_alert", "verdict_reason")
    op.drop_column("incident_management_alert", "verdict")
