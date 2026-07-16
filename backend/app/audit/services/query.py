"""Read/query side of the audit log (issue #943, Phase 2).

Admin-only listing with filtering + pagination. The write side lives in
``app/audit/services/audit.py``; this module never mutates.
"""
from datetime import datetime
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditLog


async def list_audit_logs(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    actor_user_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    customer_code: Optional[str] = None,
    result: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    search: Optional[str] = None,
) -> Tuple[List[AuditLog], int]:
    """Return (rows, total_count) for the given filters, newest first.

    ``total`` is the count for the filter set (ignoring skip/limit) so the caller can
    paginate. ``search`` is a case-insensitive substring match across details, actor
    username and entity id.
    """
    filters = []
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if actor_username:
        filters.append(AuditLog.actor_username == actor_username)
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if customer_code:
        filters.append(AuditLog.customer_code == customer_code)
    if result:
        filters.append(AuditLog.result == result)
    if start_time is not None:
        filters.append(AuditLog.timestamp >= start_time)
    if end_time is not None:
        filters.append(AuditLog.timestamp <= end_time)
    if search:
        like = f"%{search}%"
        filters.append(
            or_(
                AuditLog.details.ilike(like),
                AuditLog.actor_username.ilike(like),
                AuditLog.entity_id.ilike(like),
            ),
        )

    count_stmt = select(func.count()).select_from(AuditLog)
    for f in filters:
        count_stmt = count_stmt.where(f)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = select(AuditLog)
    for f in filters:
        stmt = stmt.where(f)
    stmt = stmt.order_by(desc(AuditLog.timestamp), desc(AuditLog.id)).offset(skip).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    return list(rows), total


async def get_audit_log_by_id(session: AsyncSession, audit_id: int) -> AuditLog:
    row = await session.get(AuditLog, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Audit log {audit_id} not found")
    return row
