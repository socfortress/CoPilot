"""Tables owned by SOC Management (#1187).

``soc_sla_policy`` holds the configured targets; ``soc_sla_alert_tracking`` and
``soc_sla_case_tracking`` hold one row per alert/case with its SLA clocks.

**Why tracking is not a set of columns on the alert.** ``alert_creation_time`` is not
an opening time: ingest moves it to the latest trigger every time a matching OPEN alert
fires again (``update_alert_creation_time``), so it reads "last seen". An SLA clock needs
an immutable start, and the milestones that follow it are owned by this feature, not by
the incident model every other module reads. One row per item, keyed by the item's id,
with ``ON DELETE CASCADE`` so deleting an alert or case takes its clocks with it.

**Targets are snapshotted.** ``ack_due_at`` / ``resolve_due_at`` are computed from the
policy in force when the item opened (the "snapshot at … time" convention used by case
tasks). Editing a policy changes what new items are promised; it rewrites open items
only when the operator explicitly asks for it, and never touches closed ones.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlmodel import Field
from sqlmodel import SQLModel

from app.soc_management.clock import utc_now


class SlaPolicy(SQLModel, table=True):
    """One configured cell of the SLA matrix: (scope, entity, severity) → targets.

    ``customer_code`` NULL is the global policy; set, it overrides the global policy for
    that customer only (hard FK, so deleting the customer removes its overrides). A cell
    with no row resolves to the next scope out — see ``domain/policy.py``.
    """

    __tablename__ = "soc_sla_policy"
    __table_args__ = (UniqueConstraint("customer_code", "entity_type", "severity", name="uq_soc_sla_policy_cell"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: Optional[str] = Field(
        default=None,
        sa_column=Column(String(50), ForeignKey("customers.customer_code", ondelete="CASCADE"), nullable=True, index=True),
    )
    entity_type: str = Field(max_length=10, nullable=False, description="alert | case")
    severity: str = Field(max_length=20, nullable=False)
    ack_minutes: Optional[int] = Field(default=None, nullable=True, description="NULL = no acknowledge promise")
    resolve_minutes: Optional[int] = Field(default=None, nullable=True, description="NULL = no resolve promise")
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_by: Optional[str] = Field(default=None, max_length=100, nullable=True)


class SlaTrackingBase(SQLModel):
    """The clocks shared by alerts and cases. Not a table on its own."""

    #: Effective severity the targets were computed for (alerts: resolved at open time,
    #: so a later DEFAULT_ALERT_SEVERITY change does not move a running clock).
    severity: str = Field(max_length=20, nullable=False, index=True)
    #: When the item reached CoPilot. Never updated.
    opened_at: datetime = Field(nullable=False, index=True)
    ack_due_at: Optional[datetime] = Field(default=None, nullable=True)
    resolve_due_at: Optional[datetime] = Field(default=None, nullable=True)

    first_ack_at: Optional[datetime] = Field(default=None, nullable=True)
    first_ack_by: Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    first_ack_action: Optional[str] = Field(default=None, max_length=32, nullable=True)
    first_assigned_at: Optional[datetime] = Field(default=None, nullable=True)

    #: Current resolution: cleared when the item is reopened.
    resolved_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    resolved_by: Optional[str] = Field(default=None, max_length=100, nullable=True, index=True)
    first_resolved_at: Optional[datetime] = Field(default=None, nullable=True)
    reopen_count: int = Field(default=0, nullable=False)

    #: True when the lifecycle was observed from the item's opening. False for rows
    #: backfilled for items that existed before tracking began: their opening time is
    #: approximate and their response history unknown, so they count in volumes but in
    #: no duration or compliance figure.
    tracked: bool = Field(default=True, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AlertSlaTracking(SlaTrackingBase, table=True):
    __tablename__ = "soc_sla_alert_tracking"

    alert_id: int = Field(
        sa_column=Column(Integer, ForeignKey("incident_management_alert.id", ondelete="CASCADE"), primary_key=True, autoincrement=False),
    )


class CaseSlaTracking(SlaTrackingBase, table=True):
    __tablename__ = "soc_sla_case_tracking"

    case_id: int = Field(
        sa_column=Column(Integer, ForeignKey("incident_management_case.id", ondelete="CASCADE"), primary_key=True, autoincrement=False),
    )
