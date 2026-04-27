"""
Pydantic schemas for case templates, template tasks, case tasks, and the
case event timeline.

These schemas back the Phase 2+ routes (template CRUD, task lifecycle,
timeline GET). The underlying SQLModel rows live in ``app.incidents.models``:
``CaseTemplate``, ``CaseTemplateTask``, ``CaseTask``, ``CaseEvent``.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CaseTaskStatus(str, Enum):
    """Lifecycle status of a CaseTask."""

    TODO = "TODO"
    DONE = "DONE"
    NOT_NECESSARY = "NOT_NECESSARY"


class CaseEventType(str, Enum):
    """Allowed CaseEvent.event_type values. Kept in sync with the audit hooks
    added in Phase 4. Stored as a string column so unknown values don't fail
    reads, but writes should funnel through this enum."""

    CASE_CREATED = "case_created"
    CASE_STATUS_CHANGED = "case_status_changed"
    CASE_ASSIGNED = "case_assigned"
    CASE_ESCALATED = "case_escalated"
    ALERT_LINKED = "alert_linked"
    ALERT_UNLINKED = "alert_unlinked"
    COMMENT_ADDED = "comment_added"
    TEMPLATE_APPLIED = "template_applied"
    TASK_ADDED = "task_added"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_COMMENTED = "task_commented"


# ---------------------------------------------------------------------------
# CaseTemplateTask (template-side definition rows)
# ---------------------------------------------------------------------------


class CaseTemplateTaskCreate(BaseModel):
    """Payload for adding a task to a template."""

    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    guidelines: Optional[str] = Field(None, description="Best practices / step-by-step guidance for the analyst")
    mandatory: bool = False
    order_index: int = Field(0, ge=0)


class CaseTemplateTaskUpdate(BaseModel):
    """Partial update payload for a template task."""

    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    guidelines: Optional[str] = None
    mandatory: Optional[bool] = None
    order_index: Optional[int] = Field(None, ge=0)


class CaseTemplateTaskResponse(BaseModel):
    id: int
    template_id: int
    title: str
    description: Optional[str] = None
    guidelines: Optional[str] = None
    mandatory: bool
    order_index: int

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# CaseTemplate
# ---------------------------------------------------------------------------


class CaseTemplateCreate(BaseModel):
    """Payload for creating a new case template (admin/analyst only)."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    customer_code: Optional[str] = Field(
        None,
        max_length=50,
        description="Customer this template applies to. Omit for a global template.",
    )
    source: Optional[str] = Field(
        None,
        max_length=50,
        description="Alert source this template applies to (e.g., wazuh, velociraptor). Omit for any source.",
    )
    is_default: bool = Field(
        False,
        description="If true, this template is the fallback within its (customer_code, source) scope.",
    )
    tasks: List[CaseTemplateTaskCreate] = Field(
        default_factory=list,
        description="Initial task list. More can be added later via the task endpoints.",
    )


class CaseTemplateUpdate(BaseModel):
    """Partial update payload for template metadata. Tasks are managed via
    their own endpoints, not through this schema."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    customer_code: Optional[str] = Field(None, max_length=50)
    source: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None


class CaseTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    customer_code: Optional[str] = None
    source: Optional[str] = None
    is_default: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    tasks: List[CaseTemplateTaskResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True


class CaseTemplateListResponse(BaseModel):
    templates: List[CaseTemplateResponse] = Field(default_factory=list)
    success: bool
    message: str


class CaseTemplateOperationResponse(BaseModel):
    template: Optional[CaseTemplateResponse] = None
    success: bool
    message: str


class CaseTemplateTaskOperationResponse(BaseModel):
    task: Optional[CaseTemplateTaskResponse] = None
    success: bool
    message: str


# ---------------------------------------------------------------------------
# CaseTask (case-side instance rows)
# ---------------------------------------------------------------------------


class CaseTaskCreate(BaseModel):
    """Payload for adding a custom task to an existing case (analyst-driven)."""

    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    guidelines: Optional[str] = None
    mandatory: bool = False
    order_index: int = Field(0, ge=0)


class CaseTaskUpdate(BaseModel):
    """
    Partial update payload for a case task.

    Status transitions to NOT_NECESSARY are rejected at the service layer
    when the task is mandatory. ``evidence_comment`` is intended for free-form
    notes / log snippets / command output captured alongside the status change.
    """

    status: Optional[CaseTaskStatus] = None
    evidence_comment: Optional[str] = None

    @validator("status")
    def _status_must_be_known(cls, v: Optional[CaseTaskStatus]) -> Optional[CaseTaskStatus]:
        # Pydantic already enforces enum membership; this guard is for clarity
        # and to catch any future string-coercion shenanigans.
        if v is not None and v not in CaseTaskStatus:
            raise ValueError(f"Unknown task status: {v}")
        return v


class CaseTaskResponse(BaseModel):
    id: int
    case_id: int
    template_task_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    guidelines: Optional[str] = None
    mandatory: bool
    order_index: int
    status: CaseTaskStatus
    evidence_comment: Optional[str] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CaseTaskListResponse(BaseModel):
    tasks: List[CaseTaskResponse] = Field(default_factory=list)
    success: bool
    message: str


class CaseTaskOperationResponse(BaseModel):
    task: Optional[CaseTaskResponse] = None
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Soft-warning payload returned when an analyst tries to close a case with
# incomplete mandatory tasks. The route returns this object with HTTP 200 and
# the case is NOT closed; the caller re-submits with ?force=true to confirm.
# ---------------------------------------------------------------------------


class CaseCloseWarningResponse(BaseModel):
    """
    Soft-warning response when closing a case with incomplete mandatory tasks.

    The case is NOT closed when this response is returned. Re-submit the close
    request with ``force=true`` to override the warning.
    """

    success: bool = False
    requires_confirmation: bool = True
    message: str
    incomplete_mandatory_tasks: List[CaseTaskResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CaseEvent / Timeline
# ---------------------------------------------------------------------------


class CaseEventResponse(BaseModel):
    id: int
    case_id: int
    event_type: str
    actor: str
    timestamp: datetime
    payload: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class CaseTimelineResponse(BaseModel):
    case_id: int
    events: List[CaseEventResponse] = Field(default_factory=list)
    success: bool
    message: str
