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
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.models import CaseTemplate
from app.incidents.schema.case_templates import CaseTemplateCreate
from app.incidents.schema.case_templates import CaseTemplateLibraryEntry
from app.incidents.schema.case_templates import CaseTemplateLibraryListResponse
from app.incidents.schema.case_templates import CaseTemplateLibraryRefreshResponse
from app.incidents.schema.case_templates import CaseTemplateLibraryTask
from app.incidents.schema.case_templates import CaseTemplateListResponse
from app.incidents.schema.case_templates import CaseTemplateOperationResponse
from app.incidents.schema.case_templates import CaseTemplateTaskCreate
from app.incidents.schema.case_templates import CaseTemplateTaskOperationResponse
from app.incidents.schema.case_templates import CaseTemplateTaskUpdate
from app.incidents.schema.case_templates import CaseTemplateUpdate
from app.incidents.services import case_templates as service
from app.incidents.services import template_library

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


# ---------------------------------------------------------------------------
# Case Template Library — read-only catalog of playbooks pulled from
# https://github.com/socfortress/CoPilot-Case-Templates. The Library tab in
# the admin UI calls these endpoints. Importing an entry creates a normal
# CaseTemplate row via the existing ``create_template`` service.
#
# IMPORTANT: these MUST be declared before the ``/{template_id}`` route below.
# FastAPI matches routes in registration order; if ``/{template_id}`` is first
# it would swallow ``/library`` and try to coerce "library" to int, returning
# HTTP 422 "Input is not a valid integer."
# ---------------------------------------------------------------------------


def _library_entry_to_response(entry: dict) -> CaseTemplateLibraryEntry:
    """Convert a parsed-and-normalised library entry dict into its API shape."""
    return CaseTemplateLibraryEntry(
        key=entry["key"],
        name=entry["name"],
        description=entry.get("description"),
        source=entry.get("source"),
        tags=entry.get("tags", {}),
        tasks=[CaseTemplateLibraryTask(**t) for t in entry.get("tasks", [])],
        file_path=entry.get("_file_path"),
    )


@case_templates_router.get(
    "/library",
    response_model=CaseTemplateLibraryListResponse,
    description=(
        "List investigation-playbook entries available in the Case-Templates "
        "library repo on GitHub. Read-only; nothing is persisted until an "
        "admin clicks Import."
    ),
)
async def list_library_entries_endpoint() -> CaseTemplateLibraryListResponse:
    try:
        entries = await template_library.list_library_entries()
        return CaseTemplateLibraryListResponse(
            entries=[_library_entry_to_response(e) for e in entries],
            invalid_paths=template_library.template_library_cache.invalid_paths,
            last_refresh=template_library.template_library_cache.last_refresh,
            success=True,
            message=f"Retrieved {len(entries)} library entr(ies)",
        )
    except Exception as e:
        return CaseTemplateLibraryListResponse(
            entries=[],
            invalid_paths=[],
            last_refresh=template_library.template_library_cache.last_refresh,
            success=False,
            message=f"Failed to load case-template library: {e}",
        )


@case_templates_router.post(
    "/library/refresh",
    response_model=CaseTemplateLibraryRefreshResponse,
    description="Force a re-fetch of the Case-Templates library repo (bypasses the 30-minute cache).",
)
async def refresh_library_endpoint() -> CaseTemplateLibraryRefreshResponse:
    try:
        result = await template_library.refresh_library()
        return CaseTemplateLibraryRefreshResponse(
            loaded=result["loaded"],
            invalid_paths=result["invalid_paths"],
            last_refresh=result["last_refresh"],
            success=True,
            message=f"Library refreshed: {result['loaded']} entr(ies) loaded, {len(result['invalid_paths'])} skipped",
        )
    except Exception as e:
        return CaseTemplateLibraryRefreshResponse(
            loaded=0,
            invalid_paths=[],
            last_refresh=template_library.template_library_cache.last_refresh,
            success=False,
            message=f"Failed to refresh case-template library: {e}",
        )


@case_templates_router.post(
    "/library/{key}/import",
    response_model=CaseTemplateOperationResponse,
    description=(
        "Import a library entry as a new CaseTemplate row. Imports as a "
        "**global** template (no customer_code, no source-scope) by default. "
        "If a CaseTemplate already exists with the same name, returns HTTP 409 "
        "— admins should rename or delete the existing one before re-importing."
    ),
)
async def import_library_entry_endpoint(
    key: str,
    db: AsyncSession = Depends(get_db),
    actor: str = Security(_require_admin_or_analyst),
) -> CaseTemplateOperationResponse:
    entry = await template_library.get_library_entry(key)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library entry '{key}' not found. Try POST /library/refresh if you just pushed it.",
        )

    existing = await db.execute(select(CaseTemplate).where(CaseTemplate.name == entry["name"]))
    if existing.scalars().first() is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A case template named '{entry['name']}' already exists. "
                "Rename or delete the existing template before re-importing this entry."
            ),
        )

    payload = CaseTemplateCreate(
        name=entry["name"],
        description=entry.get("description"),
        customer_code=None,
        source=entry.get("source"),
        is_default=False,
        tasks=[
            CaseTemplateTaskCreate(
                title=t["title"],
                description=t.get("description"),
                guidelines=t.get("guidelines"),
                mandatory=t.get("mandatory", False),
                order_index=t["order_index"],
            )
            for t in entry.get("tasks", [])
        ],
    )
    return await service.create_template(request=payload, actor=actor, session=db)


# ---------------------------------------------------------------------------
# Wildcard /{template_id} routes — must be declared AFTER the static
# /library routes above for the same reason FastAPI route ordering matters.
# ---------------------------------------------------------------------------


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
