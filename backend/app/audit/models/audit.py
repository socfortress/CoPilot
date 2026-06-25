"""SQLModel table + action vocabulary for the SOC analyst audit log (issue #943).

This is a purpose-built, action-oriented audit trail — distinct from `log_entries`
(`app/db/universal_models.py:LogEntry`), which is an HTTP error log. The audit log records
*who did what, to which entity, when, and with what result*, with optional before/after
values, so the platform can answer accountability/compliance questions.

Design notes:
- `actor_user_id` is deliberately NOT a foreign key, and `actor_username` / `customer_code`
  are denormalized snapshots. An audit record must survive deletion or rename of the user
  or customer it references — a hard FK with cascade would erase history (the opposite of
  what an audit log is for).
- `old_value` / `new_value` are JSON so an action can capture a structured before/after
  (e.g. {"role_id": 2} -> {"role_id": 1}).
- The table is intended to be append-only. Do not expose a general-purpose purge/edit path
  on it (see the implementation plan); retention should be policy-driven, not ad hoc.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import JSON
from sqlmodel import Field
from sqlmodel import SQLModel


class AuditAction(str, Enum):
    """Canonical action identifiers, namespaced as `<domain>.<verb>`.

    Phase 1 covers authentication, user/role management, connectors, agents, response
    actions, cases and the file data store. Add new members here as coverage grows — the
    value is the stable string persisted to the `action` column.
    """

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"

    # Users / RBAC
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_UPDATE = "user.update"
    USER_ROLE_CHANGE = "user.role_change"

    # Connectors
    CONNECTOR_CREATE = "connector.create"
    CONNECTOR_UPDATE = "connector.update"
    CONNECTOR_DELETE = "connector.delete"

    # Agents / assets
    AGENT_DELETE = "agent.delete"
    AGENT_CRITICALITY_CHANGE = "agent.criticality_change"

    # Velociraptor response actions
    RESPONSE_QUARANTINE = "response.quarantine"
    RESPONSE_COMMAND_EXECUTE = "response.command_execute"
    ARTIFACT_COLLECT = "artifact.collect"

    # Cases
    CASE_CREATE = "case.create"

    # File data store
    DATASTORE_FILE_CREATE = "datastore.file_create"
    DATASTORE_FILE_DELETE = "datastore.file_delete"


class AuditResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Actor — snapshot, no FK (record must outlive the user).
    actor_user_id: Optional[int] = Field(default=None, index=True)
    actor_username: Optional[str] = Field(default=None, max_length=256, index=True)

    # Tenant — string snapshot, no FK (record must outlive the customer).
    customer_code: Optional[str] = Field(default=None, max_length=50, index=True)

    # What happened.
    action: str = Field(max_length=128, index=True)
    entity_type: Optional[str] = Field(default=None, max_length=128, index=True)
    entity_id: Optional[str] = Field(default=None, max_length=256)
    result: str = Field(default=AuditResult.SUCCESS.value, max_length=32, index=True)

    # Optional structured before/after and context.
    old_value: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    new_value: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    source_ip: Optional[str] = Field(default=None, max_length=64)
    details: Optional[str] = Field(default=None, max_length=5024)
