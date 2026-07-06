"""Admin-only read API for the SOC analyst audit log (issue #943, Phase 2).

Read-only: there is no create/update/delete here. Audit rows are written only by
``record_audit_event`` at the instrumented actions, and the table is append-only by
intent (no purge/edit endpoint — retention is a policy decision, not an API).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.schema.audit import AuditLogDetailResponse
from app.audit.schema.audit import AuditLogEntry
from app.audit.schema.audit import AuditLogResponse
from app.audit.services.query import get_audit_log_by_id
from app.audit.services.query import list_audit_logs
from app.auth.utils import AuthHandler
from app.db.db_session import get_db

audit_router = APIRouter()

# Cap page size so a caller cannot pull the whole table in one request.
MAX_LIMIT = 1000


@audit_router.get(
    "/actions",
    description="List the audit action and result vocabularies (for filter UIs)",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_audit_vocabularies():
    """Return the known action + result values so a UI can populate its filter dropdowns."""
    return {
        "actions": [a.value for a in AuditAction],
        "results": [r.value for r in AuditResult],
        "success": True,
        "message": "Audit vocabularies retrieved successfully",
    }


@audit_router.get(
    "",
    response_model=AuditLogResponse,
    description="List audit log entries (admin only) with filtering and pagination",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Rows to skip (pagination offset)"),
    limit: int = Query(100, ge=1, le=MAX_LIMIT, description="Max rows to return"),
    actor_user_id: Optional[int] = Query(None, description="Filter by acting user id"),
    actor_username: Optional[str] = Query(None, description="Filter by acting username (exact)"),
    action: Optional[str] = Query(None, description="Filter by action, e.g. 'agent.delete'"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type, e.g. 'agent'"),
    entity_id: Optional[str] = Query(None, description="Filter by entity id (exact)"),
    customer_code: Optional[str] = Query(None, description="Filter by customer code"),
    result: Optional[str] = Query(None, description="Filter by result: success | failure"),
    start_time: Optional[datetime] = Query(None, description="Only entries at/after this UTC time"),
    end_time: Optional[datetime] = Query(None, description="Only entries at/before this UTC time"),
    search: Optional[str] = Query(None, description="Substring search over details, username and entity id"),
    session: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    rows, total = await list_audit_logs(
        session,
        skip=skip,
        limit=limit,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        customer_code=customer_code,
        result=result,
        start_time=start_time,
        end_time=end_time,
        search=search,
    )
    return AuditLogResponse(
        audit_logs=[AuditLogEntry.model_validate(row) for row in rows],
        pagination={"total": total, "skip": skip, "limit": limit},
        success=True,
        message=f"Retrieved {len(rows)} of {total} audit log entries",
    )


@audit_router.get(
    "/{audit_id}",
    response_model=AuditLogDetailResponse,
    description="Get a single audit log entry by id",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_audit_log(
    audit_id: int,
    session: AsyncSession = Depends(get_db),
) -> AuditLogDetailResponse:
    row = await get_audit_log_by_id(session, audit_id)
    return AuditLogDetailResponse(
        audit_log=AuditLogEntry.model_validate(row),
        success=True,
        message="Audit log entry retrieved successfully",
    )
