"""Pydantic response/query shapes for the audit log read API (Phase 2).

Defined now so the model/service/schema split mirrors the rest of the backend; the read
routes that consume these land in Phase 2 (see docs/audit-log-plan.md).
"""
from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    customer_code: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    result: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    source_ip: Optional[str] = None
    details: Optional[str] = None


class AuditLogResponse(BaseModel):
    audit_logs: List[AuditLogEntry]
    pagination: dict
    success: bool
    message: str


class AuditLogDetailResponse(BaseModel):
    audit_log: AuditLogEntry
    success: bool
    message: str
