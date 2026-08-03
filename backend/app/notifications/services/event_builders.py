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

from app.incidents.services.alert_severity import default_severity
from app.notifications.schema.events import EntityType
from app.notifications.schema.events import NotificationEvent
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger

#: Used when an assignment concerns something with no severity of its own — a
#: case or a task. Alerts now carry a stored severity (#1040), so an alert
#: assignment reports the alert's real seriousness instead.
#:
#: INFORMATIONAL rather than something higher: a case assignment is a workflow
#: event, and inventing a severity would let it trip routes tuned for real
#: alerts.
_ASSIGNMENT_SEVERITY = NotificationSeverity.INFORMATIONAL


def _coerce_severity(value: Optional[str]) -> NotificationSeverity:
    """Map a severity string onto the enum, falling back to the deployment default.

    Previously hardcoded Medium here, which is what made non-Wazuh alerts —
    Office 365, CrowdStrike, Carbon Black and the rest, none of which carry a
    rule level — silently invisible to any route gating at High and above.

    The fallback now comes from `DEFAULT_ALERT_SEVERITY` (High unless
    configured otherwise), so an unmapped source is loud by default and the
    behaviour is one setting away from whatever a given SOC wants. See #1040.
    """
    if value:
        try:
            return NotificationSeverity(value)
        except ValueError:
            pass
    return NotificationSeverity(default_severity())


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
    asset_name: Optional[str] = None,
) -> NotificationEvent:
    """An AI investigation finished and its report was written back.

    The dedupe key is identical to the one `event_from_dispatch_request` builds,
    which is what makes CoPilot's own emit and Talon's push converge on a single
    notification rather than two.

    `alert_name` and `asset_name` are optional because Talon's push has never
    carried an asset and may omit the name — but the CoPilot-side emit passes
    both (#1048). Without them the subject degrades to `Alert #14` and the
    seeded template's `{% if context.asset_name %}` can never fire, which is
    what customers were actually receiving.
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
        context={"alert_name": alert_name, "asset_name": asset_name},
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
    severity: NotificationSeverity = _ASSIGNMENT_SEVERITY,
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
        severity=severity,
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
    severity: Optional[str] = None,
) -> NotificationEvent:
    """An alert changed hands.

    Carries the alert's own severity when the caller supplies it — being handed
    a Critical alert is not the same event as being handed an Informational one,
    and a route gating at High should see the first. Falls back to the
    assignment default when unknown.
    """
    return _assignment_event(
        trigger=NotificationTrigger.ALERT_ASSIGNED,
        severity=_coerce_severity(severity) if severity else _ASSIGNMENT_SEVERITY,
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
