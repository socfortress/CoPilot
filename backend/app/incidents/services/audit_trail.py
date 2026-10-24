"""Who changed an alert's or a case's status, and who commented on it, for the audit log (#1298).

The incidents routes call these after their own commit, for the SOC and for portal users alike,
with the object's own customer, so a customer's audit log (the portal's Audit page) answers who
closed what and who said what. A comment's text is never stored: only which comment it was.
"""
from typing import Optional

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.audit.services.audit import record_audit_events
from app.auth.models.users import User


def incident_event(
    action: AuditAction,
    user: User,
    *,
    customer_code: Optional[str],
    entity_type: str,
    entity_id: int,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> dict:
    """The audit row's fields for one action on one alert or case."""
    return {
        "action": action,
        "actor_user_id": user.id,
        "actor_username": user.username,
        "customer_code": customer_code,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_value": old_value,
        "new_value": new_value,
    }


async def record_incident_event(action: AuditAction, user: User, **fields) -> None:
    await record_audit_event(**incident_event(action, user, **fields))


async def record_status_changes(entity_type: str, user: User, changes: list[tuple[int, Optional[str], str, Optional[str]]]) -> None:
    """One row per object whose status really moved: (id, customer_code, old, new); unchanged ones are skipped."""
    action = AuditAction.ALERT_STATUS_CHANGE if entity_type == "alert" else AuditAction.CASE_STATUS_CHANGE
    await record_audit_events(
        [
            incident_event(
                action,
                user,
                customer_code=customer_code,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value={"status": old},
                new_value={"status": new},
            )
            for entity_id, customer_code, old, new in changes
            if old != new
        ],
    )
