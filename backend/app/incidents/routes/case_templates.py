"""
Routes for case template + template-task management (issue #792, Phase 2).

The entire router is gated on the ``admin`` or ``analyst`` scope — customers
(``customer_user`` scope) cannot view or modify templates. Customer-facing
visibility of *applied* tasks on cases is handled separately in Phase 3
where the read-only path is exposed under the case detail endpoints.
"""

from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.schema.case_templates import CaseTemplateCreate
from app.incidents.schema.case_templates import CaseTemplateListResponse
from app.incidents.schema.case_templates import CaseTemplateOperationResponse
from app.incidents.schema.case_templates import CaseTemplateTaskCreate
from app.incidents.schema.case_templates import CaseTemplateTaskOperationResponse
from app.incidents.schema.case_templates import CaseTemplateTaskUpdate
from app.incidents.schema.case_templates import CaseTemplateUpdate
from app.incidents.services import case_templates as service


# Scope guard applied to every route on this router. Returns the username,
# which we use as the audit actor for create operations.
_require_admin_or_analyst = AuthHandler().require_any_scope("admin", "analyst")

case_templates_router = APIRouter(
    dependencies=[Security(_require_admin_or_analyst)],
)


# ---------------------------------------------------------------------------
# Template CRUD
# ---------------------------------------------------------------------------


@case_templates_router.get(
    "",
    response_model=CaseTemplateListResponse,
    description="List case templates. Admin/analyst only.",
)
async def list_case_templates(
    customer_code: Optional[str] = Query(
        None,
        description="Filter to templates for this customer plus global templates (unless include_global=False).",
    ),
    source: Optional[str] = Query(
        None,
        description="Filter to templates for this alert source plus source-agnostic templates (unless include_global=False).",
    ),
    include_global: bool = Query(
        True,
        description="When filtering by customer_code/source, also include rows where that field is NULL (i.e., global / any).",
    ),
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateListResponse:
    return await service.list_templates(
        session=db,
        customer_code=customer_code,
        source=source,
        include_global=include_global,
    )


@case_templates_router.post(
    "",
    response_model=CaseTemplateOperationResponse,
    description="Create a new case template (with optional initial task list).",
)
async def create_case_template(
    request: CaseTemplateCreate,
    db: AsyncSession = Depends(get_db),
    actor: str = Security(_require_admin_or_analyst),
) -> CaseTemplateOperationResponse:
    return await service.create_template(request=request, actor=actor, session=db)


@case_templates_router.get(
    "/{template_id}",
    response_model=CaseTemplateOperationResponse,
    description="Fetch a single case template by ID, including its tasks.",
)
async def get_case_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateOperationResponse:
    return await service.get_template(template_id=template_id, session=db)


@case_templates_router.patch(
    "/{template_id}",
    response_model=CaseTemplateOperationResponse,
    description="Partial update of template metadata. Tasks are managed via the task endpoints.",
)
async def update_case_template(
    template_id: int,
    request: CaseTemplateUpdate,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateOperationResponse:
    return await service.update_template(template_id=template_id, request=request, session=db)


@case_templates_router.delete(
    "/{template_id}",
    response_model=CaseTemplateOperationResponse,
    description=(
        "Delete a template and its template tasks. Existing CaseTask snapshots on real cases "
        "are preserved (template_task_id is set to NULL on those rows so audit history survives)."
    ),
)
async def delete_case_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateOperationResponse:
    return await service.delete_template(template_id=template_id, session=db)


# ---------------------------------------------------------------------------
# Template task CRUD
# ---------------------------------------------------------------------------


@case_templates_router.post(
    "/{template_id}/tasks",
    response_model=CaseTemplateTaskOperationResponse,
    description="Add a task to an existing template.",
)
async def add_case_template_task(
    template_id: int,
    request: CaseTemplateTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateTaskOperationResponse:
    return await service.add_template_task(template_id=template_id, request=request, session=db)


@case_templates_router.patch(
    "/tasks/{task_id}",
    response_model=CaseTemplateTaskOperationResponse,
    description="Partial update of a template task definition.",
)
async def update_case_template_task(
    task_id: int,
    request: CaseTemplateTaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateTaskOperationResponse:
    return await service.update_template_task(task_id=task_id, request=request, session=db)


@case_templates_router.delete(
    "/tasks/{task_id}",
    response_model=CaseTemplateTaskOperationResponse,
    description="Delete a template task. Existing CaseTask snapshots on real cases keep their data.",
)
async def delete_case_template_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateTaskOperationResponse:
    return await service.delete_template_task(task_id=task_id, session=db)


@case_templates_router.post(
    "/{template_id}/tasks/reorder",
    response_model=CaseTemplateOperationResponse,
    description=(
        "Reorder tasks within a template. Pass the full ordered list of task IDs; "
        "tasks not included keep their existing order_index value."
    ),
)
async def reorder_case_template_tasks(
    template_id: int,
    ordered_task_ids: List[int],
    db: AsyncSession = Depends(get_db),
) -> CaseTemplateOperationResponse:
    return await service.reorder_template_tasks(
        template_id=template_id,
        ordered_task_ids=ordered_task_ids,
        session=db,
    )
