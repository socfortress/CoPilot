"""Construct `NotificationEvent`s for CoPilot-originated triggers.

Kept out of the incident modules so the emit points there stay one line, and out
of the notifications service so the dispatch loop has no knowledge of alerts or
cases. Each builder owns two things that are easy to get wrong in-line:

**The dedupe key**, which decides what counts as "the same notification". For
assignments it includes the assignee, so reassigning A → B → A notifies A again
while a no-op write does not.

**The severity**, which decides whether a route's `min_severity` lets it
through. Assignments have no inherent severity and use INFORMATIONAL so they are
governed by the route's trigger filter rather than accidentally suppressed.
"""

from __future__ import annotations

import os
from typing import Any
from typing import Optional

from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger

#: Assignments carry no security severity of their own. INFORMATIONAL means a
#: route filters them by trigger, not by an invented severity — anything higher
#: would silently drop them on routes tuned for real alerts.
_ASSIGNMENT_SEVERITY = NotificationSeverity.INFORMATIONAL


def _coerce_severity(value: Optional[str]) -> NotificationSeverity:
    """Map a payload severity string onto the enum, defaulting to Medium.

    `alert_payload.severity` is derived from the Wazuh rule level (issue #980)
    and is None for sources that carry no level. Medium rather than
    Informational so a severity-less alert isn't quietly filtered out of every
    route that gates above Informational.
    """
    if not value:
        return NotificationSeverity.MEDIUM
    try:
        return NotificationSeverity(value)
    except ValueError:
        return NotificationSeverity.MEDIUM


def _copilot_link(path: str) -> Optional[str]:
    """Build a deep link back into CoPilot, when the base URL is configured.

    CoPilot has never known its own public URL — Talon supplied `report_url` on
    the dispatches it pushed. Now that CoPilot emits `investigation_complete`
    itself (and wins the dedupe, since write-back happens first), the link has to
    come from somewhere.

    `COPILOT_URL` is optional: unset means no link, which is the same state as a
    Talon push that omitted one. Set it and every notification gains a working
    link, including triggers Talon never knew about.
    """
    base = (os.getenv("COPILOT_URL") or "").strip().rstrip("/")
    return f"{base}/{path.lstrip('/')}" if base else None


def investigation_complete_event(
    *,
    alert_id: int,
    customer_code: Optional[str],
    severity: Optional[str],
    summary: str,
    alert_name: Optional[str] = None,
) -> NotificationEvent:
    """An AI investigation finished and its report was written back.

    The dedupe key is identical to the one `event_from_dispatch_request` builds,
    which is what makes CoPilot's own emit and Talon's push converge on a single
    notification rather than two.
    """
    return NotificationEvent(
        customer_code=customer_code,
        trigger=NotificationTrigger.INVESTIGATION_COMPLETE,
        severity=_coerce_severity(severity),
        subject=alert_name or f"Alert #{alert_id}",
        summary=summary,
        entity_type=EntityType.ALERT,
        entity_id=alert_id,
        dedupe_key=f"{EntityType.ALERT}:{alert_id}:{NotificationTrigger.INVESTIGATION_COMPLETE.value}",
        link_url=_copilot_link(f"/alerts/{alert_id}"),
        context={"alert_name": alert_name},
    )


def ai_report_reviewed_event(
    *,
    alert_id: int,
    report_id: int,
    customer_code: Optional[str],
    severity: Optional[str],
    summary: str,
    reviewer: Optional[str] = None,
    verdict: Optional[str] = None,
) -> NotificationEvent:
    """An analyst signed off on an AI report.

    Exists as a separate trigger rather than a flag on the route so an operator
    can run an internal route on submission AND a customer-facing route only
    after review — two different audiences at two different moments, which a
    boolean could not express.

    Keyed on the alert, not the report: "this alert's findings have been
    reviewed" happens once. A second reviewer, or a revision, does not re-notify.
    """
    return NotificationEvent(
        customer_code=customer_code,
        trigger=NotificationTrigger.AI_REPORT_REVIEWED,
        severity=_coerce_severity(severity),
        subject=f"Reviewed: alert #{alert_id}",
        summary=summary,
        entity_type=EntityType.ALERT,
        entity_id=alert_id,
        dedupe_key=f"{EntityType.ALERT}:{alert_id}:{NotificationTrigger.AI_REPORT_REVIEWED.value}",
        link_url=_copilot_link(f"/alerts/{alert_id}"),
        actor_username=reviewer,
        context={"report_id": report_id, "reviewer": reviewer, "verdict": verdict},
    )


def alert_created_event(
    *,
    alert_id: int,
    customer_code: str,
    alert_title: Optional[str],
    severity: Optional[str] = None,
    rule_level: Optional[int] = None,
    asset_name: Optional[str] = None,
    link_url: Optional[str] = None,
) -> NotificationEvent:
    """A new alert landed.

    Only ever built for genuinely new alerts — `create_alert()` short-circuits
    on recurrence before reaching the emit point, so a repeated alert does not
    re-notify.
    """
    title = alert_title or f"Alert #{alert_id}"
    return NotificationEvent(
        customer_code=customer_code,
        trigger=NotificationTrigger.ALERT_CREATED,
        severity=_coerce_severity(severity),
        subject=title,
        summary=f"A new alert was created for {customer_code}.",
        entity_type=EntityType.ALERT,
        entity_id=alert_id,
        dedupe_key=f"{EntityType.ALERT}:{alert_id}:{NotificationTrigger.ALERT_CREATED.value}",
        link_url=link_url or _copilot_link(f"/alerts/{alert_id}"),
        context={"alert_name": title, "rule_level": rule_level, "asset_name": asset_name},
    )


def _assignment_event(
    *,
    trigger: NotificationTrigger,
    entity_type: str,
    entity_id: int,
    title: Optional[str],
    assignee: Optional[str],
    actor: Optional[str],
    customer_code: Optional[str],
    summary: str,
    link_url: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> NotificationEvent:
    """Shared shape for the three assignment triggers.

    The dedupe key includes the assignee on purpose: reassigning A → B → A
    should notify A the second time, which a key of just (entity, trigger)
    could not express. `unassigned` keeps a clear-out distinct from an
    assignment.
    """
    context: dict[str, Any] = {"title": title}
    if extra:
        context.update(extra)
    return NotificationEvent(
        customer_code=customer_code,
        trigger=trigger,
        severity=_ASSIGNMENT_SEVERITY,
        subject=title or f"{entity_type} #{entity_id}",
        summary=summary,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=f"{entity_type}:{entity_id}:{trigger.value}:{assignee or 'unassigned'}",
        link_url=link_url,
        assignee_username=assignee,
        actor_username=actor,
        context=context,
    )


def alert_assigned_event(
    *,
    alert_id: int,
    title: Optional[str],
    assignee: Optional[str],
    actor: Optional[str],
    customer_code: Optional[str] = None,
) -> NotificationEvent:
    return _assignment_event(
        trigger=NotificationTrigger.ALERT_ASSIGNED,
        entity_type=EntityType.ALERT,
        entity_id=alert_id,
        title=title,
        assignee=assignee,
        actor=actor,
        customer_code=customer_code,
        summary=(f"Alert #{alert_id} was assigned to {assignee}." if assignee else f"Alert #{alert_id} was unassigned."),
    )


def case_assigned_event(
    *,
    case_id: int,
    title: Optional[str],
    assignee: Optional[str],
    actor: Optional[str],
    customer_code: Optional[str] = None,
) -> NotificationEvent:
    return _assignment_event(
        trigger=NotificationTrigger.CASE_ASSIGNED,
        entity_type=EntityType.CASE,
        entity_id=case_id,
        title=title,
        assignee=assignee,
        actor=actor,
        customer_code=customer_code,
        summary=(f"Case #{case_id} was assigned to {assignee}." if assignee else f"Case #{case_id} was unassigned."),
    )


def case_task_assigned_event(
    *,
    task_id: int,
    case_id: int,
    title: Optional[str],
    assignee: Optional[str],
    actor: Optional[str],
    customer_code: Optional[str] = None,
) -> NotificationEvent:
    return _assignment_event(
        trigger=NotificationTrigger.CASE_TASK_ASSIGNED,
        entity_type=EntityType.CASE_TASK,
        entity_id=task_id,
        title=title,
        assignee=assignee,
        actor=actor,
        customer_code=customer_code,
        summary=(f"Task '{title}' on case #{case_id} was assigned to {assignee}." if assignee else f"Task '{title}' was unassigned."),
        extra={"case_id": case_id},
    )
