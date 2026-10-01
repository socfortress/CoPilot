"""Lifecycle milestones: which human actions move an item's SLA clocks, and how.

Every alert and case carries a tracking row with write-once milestones. This module
decides *what* an action writes; ``services/lifecycle.py`` executes it.

**Acknowledgement is the first SOC action** (decision on #1187): the earliest of an
assignment, a status change, a comment, a verdict, an escalation, a case link or a case
severity change — or creating the item, when a SOC user created it by hand. Two
deliberate exclusions:

- *Automation never acknowledges.* Ingest writes comments signed ``admin``
  (Velociraptor payloads, SOCFortress AI analysis), so authorship cannot tell a person
  from a pipeline. Actions are therefore recorded where a person is known to be acting
  — the API routes — never inside the shared services automation also calls.
- *A customer is not the SOC.* A portal user commenting on, or even closing, their own
  alert does not acknowledge it: the clock measures the SOC's response. Closing still
  resolves the item — it is resolved, whoever did it — and ``resolved_by`` records who.

**Writes are guarded, not read-modify-write.** Each milestone is a single
``UPDATE … WHERE <column> IS NULL`` (or ``IS NOT NULL`` for a reopen), so two analysts
acting on the same alert at the same instant can never both claim the first response.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from typing import List
from typing import Mapping
from typing import Optional

from app.soc_management.domain.policy import SlaTargets

CLOSED = "CLOSED"


class LifecycleAction(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"
    VERDICT_SET = "verdict_set"
    ESCALATED = "escalated"
    LINKED_TO_CASE = "linked_to_case"
    SEVERITY_CHANGED = "severity_changed"


#: Every action a person takes on an item counts as responding to it.
RESPONSE_ACTIONS = frozenset(LifecycleAction)

#: Role ids (``RoleEnum``) whose actions are the SOC's: admin and analyst.
SOC_ROLE_IDS = frozenset({1, 2})


@dataclass(frozen=True)
class Actor:
    """Who acted. ``username=None`` is automation (ingest, schedulers)."""

    username: Optional[str]
    is_soc: bool

    @classmethod
    def system(cls) -> "Actor":
        return cls(username=None, is_soc=False)

    @classmethod
    def from_user(cls, user: Any) -> "Actor":
        """From anything shaped like ``User`` (``username``, ``role_id``)."""
        role_id = getattr(user, "role_id", None)
        role_value = getattr(role_id, "value", role_id)
        return cls(username=getattr(user, "username", None), is_soc=role_value in SOC_ROLE_IDS)


@dataclass(frozen=True)
class LifecycleEvent:
    action: LifecycleAction
    actor: Actor
    at: datetime
    #: The status the item moved to, for STATUS_CHANGED.
    to_status: Optional[str] = None
    #: The new assignee, for ASSIGNED (``None``/empty means unassigned).
    assignee: Optional[str] = None


@dataclass(frozen=True)
class Increment:
    """Column value meaning ``column + by`` — for the reopen counter."""

    by: int = 1


@dataclass(frozen=True)
class GuardedUpdate:
    """One atomic write: set ``values`` only where ``guard_column`` is (not) NULL."""

    values: Mapping[str, Any]
    guard_column: str
    guard_is_null: bool = True
    #: Human-readable intent, for logs and test failure messages.
    reason: str = field(default="", compare=False)


def retarget_values(
    opened_at: datetime,
    targets: SlaTargets,
    *,
    ack_running: bool,
    resolve_running: bool,
) -> dict:
    """New due times for an item whose targets changed (severity change, policy re-apply).

    Only clocks still running move. A clock already achieved keeps the due time it was
    judged against: raising a case to Critical after it was acknowledged in 50 minutes
    must not turn that on-time High acknowledgement into a retroactive Critical breach.
    """
    values: dict = {}
    if ack_running:
        values["ack_due_at"] = targets.ack_due(opened_at)
    if resolve_running:
        values["resolve_due_at"] = targets.resolve_due(opened_at)
    return values


def acknowledges(event: LifecycleEvent) -> bool:
    return event.actor.is_soc and event.action in RESPONSE_ACTIONS


def plan_milestones(event: LifecycleEvent) -> List[GuardedUpdate]:
    """The guarded writes ``event`` implies, in the order they must run.

    Order matters for the reopen/close pair: a reopen clears ``resolved_at`` before any
    later close in the same plan could see it set. (A single event never produces both,
    but keeping resolve-side writes last keeps that true if one ever does.)
    """
    plan: List[GuardedUpdate] = []

    if acknowledges(event):
        plan.append(
            GuardedUpdate(
                values={"first_ack_at": event.at, "first_ack_by": event.actor.username, "first_ack_action": event.action.value},
                guard_column="first_ack_at",
                reason="first SOC response",
            ),
        )

    if event.action is LifecycleAction.ASSIGNED and event.assignee:
        plan.append(GuardedUpdate(values={"first_assigned_at": event.at}, guard_column="first_assigned_at", reason="first assignment"))

    if event.action is LifecycleAction.STATUS_CHANGED and event.to_status:
        if event.to_status == CLOSED:
            plan.append(
                GuardedUpdate(
                    values={"resolved_at": event.at, "resolved_by": event.actor.username},
                    guard_column="resolved_at",
                    reason="resolution",
                ),
            )
            plan.append(GuardedUpdate(values={"first_resolved_at": event.at}, guard_column="first_resolved_at", reason="first resolution"))
        else:
            plan.append(
                GuardedUpdate(
                    values={"resolved_at": None, "resolved_by": None, "reopen_count": Increment()},
                    guard_column="resolved_at",
                    guard_is_null=False,
                    reason="reopen",
                ),
            )

    return plan
