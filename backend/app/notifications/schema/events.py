"""The trigger-agnostic event envelope every dispatch flows through.

``DispatchRequest`` (the body Talon POSTs to ``/notifications/dispatch``) is
shaped entirely around a completed AI investigation — it *requires* a severity
assessment and a summary, and offers a report URL. An "alert assigned to Bob"
event has none of those, so new triggers (#1006) cannot reuse it.

``NotificationEvent`` is the shape the dispatch loop and every channel provider
actually consume. ``DispatchRequest`` is adapted into one at the route boundary,
which keeps Talon's contract byte-for-byte unchanged while freeing the internals
to grow new event types.

This module is deliberately schema-only: no DB columns correspond to it. The
persisted side of the same generalization (``entity_type`` / ``entity_id`` /
``dedupe_key`` on the dispatch log) is #1019.
"""

from __future__ import annotations

from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.notifications.schema.notifications import DispatchRequest
from app.notifications.schema.notifications import NotificationSeverity
from app.notifications.schema.notifications import NotificationTrigger


class EntityType:
    """What kind of object an event is about.

    Plain string constants rather than an enum: the dispatch log column added in
    #1019 is a varchar, and new entity types should be a data-only change.
    """

    ALERT = "alert"
    CASE = "case"
    CASE_TASK = "case_task"


class NotificationEvent(BaseModel):
    """One thing that happened, in a form any channel can render.

    Field notes:

    ``customer_code`` is Optional because internal-scope routes (#1018) belong
    to no tenant. Today every event carries one.

    ``entity_id`` is the alert id for AI triggers, so it maps onto the existing
    ``notification_dispatch_log.alert_id`` column without a schema change.

    ``dedupe_key`` is carried on the envelope rather than derived at write time
    so each trigger owns its own idempotency semantics — notably, manual sends
    (#1010) need a per-invocation unique key to stay repeatable. Unused until
    #1019 puts it on the log; present here so the shape is settled first.

    ``context`` holds trigger-specific extras that would otherwise bloat the
    envelope — ``alert_name`` for investigations, task titles for assignments.
    Template rendering and the webhook payload read from it.
    """

    customer_code: Optional[str] = None
    trigger: NotificationTrigger
    severity: NotificationSeverity
    subject: str = Field(description="One-line title. Email subject, card title, chat message heading.")
    summary: str = Field(description="Human-readable body.")
    entity_type: str = EntityType.ALERT
    entity_id: int
    dedupe_key: str
    link_url: Optional[str] = Field(default=None, description="Deep link back into CoPilot.")
    assignee_username: Optional[str] = None
    actor_username: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    @property
    def alert_id(self) -> int:
        """Back-compat accessor while the log column is still ``alert_id``.

        Removed in #1019 when the column becomes ``entity_id``.
        """
        return self.entity_id


def event_from_dispatch_request(req: DispatchRequest) -> NotificationEvent:
    """Adapt Talon's request body into the internal envelope.

    Every field the pre-refactor dispatch loop read off ``DispatchRequest`` has
    to survive this mapping unchanged, because the rendered body and the webhook
    JSON payload are both external contracts. In particular ``alert_name`` and
    ``report_url`` keep their ``None``-vs-empty-string distinction: the webhook
    payload sends ``None``, while template substitution renders ``""``.
    """
    return NotificationEvent(
        customer_code=req.customer_code,
        trigger=req.trigger,
        severity=req.severity_assessment,
        subject=req.alert_name or f"Alert #{req.alert_id}",
        summary=req.summary,
        entity_type=EntityType.ALERT,
        entity_id=req.alert_id,
        dedupe_key=f"{EntityType.ALERT}:{req.alert_id}:{req.trigger.value}",
        link_url=req.report_url,
        context={"alert_name": req.alert_name},
    )
