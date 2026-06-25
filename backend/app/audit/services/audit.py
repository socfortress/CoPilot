"""`record_audit_event` — the single entry point for writing audit-log rows (issue #943).

Callers (route handlers / services) invoke this AFTER their action has succeeded (or when it
fails, with result=FAILURE), passing the semantic details. Example:

    from fastapi import Request
    from app.audit.models.audit import AuditAction
    from app.audit.services.audit import record_audit_event

    await record_audit_event(
        action=AuditAction.AGENT_DELETE,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        customer_code=agent.customer_code,
        entity_type="agent",
        entity_id=agent_id,
        request=request,            # source_ip is extracted from here if not passed explicitly
    )

Transaction model: the helper writes the audit row in its OWN short-lived session, separate
from the caller's transaction. That keeps an audit-write failure from rolling back (or
500-ing) the business action, and avoids accidentally committing the caller's in-flight
changes. The trade-off is that the audit write is not atomic with the action — so instrument
AFTER the action's own commit, when the action is already durable.

Failure handling: best-effort. A failure to write the audit row is logged and swallowed, so
auditing never breaks a working feature. (If a future compliance requirement demands
fail-closed auditing, that becomes a deliberate policy change here.)
"""
from typing import Optional
from typing import Union

from fastapi import Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditLog
from app.audit.models.audit import AuditResult
from app.db.db_session import async_engine


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    # Prefer the proxy-forwarded client when present (CoPilot sits behind nginx).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def record_audit_event(
    *,
    action: Union[AuditAction, str],
    actor_user_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    customer_code: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[Union[str, int]] = None,
    result: Union[AuditResult, str] = AuditResult.SUCCESS,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    source_ip: Optional[str] = None,
    details: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    """Persist a single audit-log row. Never raises — failures are logged and swallowed."""
    try:
        entry = AuditLog(
            action=action.value if isinstance(action, AuditAction) else str(action),
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            customer_code=customer_code,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            result=result.value if isinstance(result, AuditResult) else str(result),
            old_value=old_value,
            new_value=new_value,
            source_ip=source_ip if source_ip is not None else _client_ip(request),
            details=details,
        )
        async with AsyncSession(async_engine) as session:
            session.add(entry)
            await session.commit()
    except Exception as e:  # noqa: BLE001 - auditing must never break the caller's action
        logger.error(f"Failed to record audit event '{action}': {e}")
