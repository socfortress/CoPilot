"""
Service helpers for the case timeline / audit log (issue #792, Phase 4).

The ``CaseEvent`` table is append-only. Every meaningful case mutation
(status change, alert link, assignment, escalation, comment, template
application, task add/status change) writes one row here. The timeline
view (``GET /case/{id}/timeline``) reads from this table.

Design notes:
- Emits never raise — a failed audit write should not break the
  underlying mutation. We log and swallow.
- Service-side emits are used where the same logic is invoked from
  multiple call sites (e.g., ``apply_template_to_case`` runs from both
  the create-from-alert hook and the manual apply endpoint, so its
  emit lives in the service).
- Route-side emits are used where the actor is naturally available at
  the route layer (most case mutation routes already resolve
  ``current_user``). This keeps the service layer auth-agnostic.
"""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import CaseEvent
from app.incidents.schema.case_templates import CaseEventResponse
from app.incidents.schema.case_templates import CaseEventType
from app.incidents.schema.case_templates import CaseTimelineResponse


async def emit_case_event(
    session: AsyncSession,
    case_id: int,
    event_type: CaseEventType,
    actor: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    commit: bool = False,
) -> None:
    """
    Append one CaseEvent row.

    Set ``commit=True`` for top-level emits (the mutation has already
    persisted). Use ``commit=False`` when emitting from inside an
    existing transaction so the audit row lands atomically with the
    underlying mutation — the caller commits.

    Failures are logged but never raised: the audit log should not
    cause user-facing 500s.
    """
    try:
        event = CaseEvent(
            case_id=case_id,
            event_type=event_type.value if isinstance(event_type, CaseEventType) else str(event_type),
            actor=actor or "system",
            timestamp=datetime.utcnow(),
            payload=payload or None,
        )
        session.add(event)
        if commit:
            await session.commit()
    except Exception as e:
        logger.warning(
            f"Failed to emit CaseEvent (case_id={case_id}, type={event_type}, actor={actor}): {e}",
        )


async def list_case_events(
    case_id: int,
    session: AsyncSession,
    *,
    limit: int = 500,
    offset: int = 0,
) -> CaseTimelineResponse:
    """
    Return the case timeline ordered most-recent-first. The ``limit``
    cap protects the client; cases with very long histories can paginate
    via ``offset``.
    """
    try:
        stmt = (
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.timestamp.desc(), CaseEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        return CaseTimelineResponse(
            case_id=case_id,
            events=[
                CaseEventResponse(
                    id=e.id,
                    case_id=e.case_id,
                    event_type=e.event_type,
                    actor=e.actor,
                    timestamp=e.timestamp,
                    payload=e.payload,
                )
                for e in events
            ],
            success=True,
            message=f"Retrieved {len(events)} timeline event(s) for case id={case_id}",
        )
    except Exception as e:
        logger.error(f"Failed to load timeline for case id={case_id}: {e}")
        return CaseTimelineResponse(
            case_id=case_id,
            events=[],
            success=False,
            message=f"Failed to load case timeline: {e}",
        )


# ---------------------------------------------------------------------------
# Convenience constructors for the typed payloads we emit. Keeps the
# event_type/payload shapes consistent across emit sites.
# ---------------------------------------------------------------------------


def payload_status_change(from_status: Optional[str], to_status: str, forced: bool = False) -> Dict[str, Any]:
    return {"from": from_status, "to": to_status, "forced": forced}


def payload_assignment(from_assignee: Optional[str], to_assignee: Optional[str]) -> Dict[str, Any]:
    return {"from": from_assignee, "to": to_assignee}


def payload_escalation(escalated: bool) -> Dict[str, Any]:
    return {"escalated": escalated}


def payload_alert_link(alert_id: int) -> Dict[str, Any]:
    return {"alert_id": alert_id}


def payload_alert_links_bulk(alert_ids: List[int]) -> Dict[str, Any]:
    return {"alert_ids": list(alert_ids), "count": len(alert_ids)}


def payload_comment(comment_id: int, snippet: Optional[str] = None) -> Dict[str, Any]:
    """``snippet`` is a short preview (first ~140 chars) for the timeline UI."""
    out: Dict[str, Any] = {"comment_id": comment_id}
    if snippet:
        out["snippet"] = snippet[:140]
    return out


def payload_template_applied(template_id: int, template_name: str, tasks_added: int) -> Dict[str, Any]:
    return {
        "template_id": template_id,
        "template_name": template_name,
        "tasks_added": tasks_added,
    }


def payload_task(task_id: int, title: str, mandatory: bool, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"task_id": task_id, "title": title, "mandatory": mandatory}
    out.update(extra)
    return out
