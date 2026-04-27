"""
Service layer for case template CRUD (issue #792, Phase 2).

Templates are scoped by ``customer_code`` (NULL = global) and ``source``
(NULL = any alert source). Rows are managed exclusively by admin/analyst
operators — the route layer enforces the auth scope, this layer is auth-
agnostic and only handles persistence and validation.

Tasks within a template are exposed via separate functions
(``add_template_task`` etc.) so the API can support incremental task
authoring without requiring a full template replacement.

Phase 3 will introduce ``pick_template`` for case-creation-time
selection and the snapshot-copy of CaseTemplateTask -> CaseTask.
"""

from datetime import datetime
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.incidents.models import CaseTemplate
from app.incidents.models import CaseTemplateTask
from app.incidents.schema.case_templates import CaseTemplateCreate
from app.incidents.schema.case_templates import CaseTemplateListResponse
from app.incidents.schema.case_templates import CaseTemplateOperationResponse
from app.incidents.schema.case_templates import CaseTemplateResponse
from app.incidents.schema.case_templates import CaseTemplateTaskCreate
from app.incidents.schema.case_templates import CaseTemplateTaskOperationResponse
from app.incidents.schema.case_templates import CaseTemplateTaskResponse
from app.incidents.schema.case_templates import CaseTemplateTaskUpdate
from app.incidents.schema.case_templates import CaseTemplateUpdate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _template_task_to_response(task: CaseTemplateTask) -> CaseTemplateTaskResponse:
    return CaseTemplateTaskResponse(
        id=task.id,
        template_id=task.template_id,
        title=task.title,
        description=task.description,
        guidelines=task.guidelines,
        mandatory=task.mandatory,
        order_index=task.order_index,
    )


def _template_to_response(template: CaseTemplate) -> CaseTemplateResponse:
    tasks_sorted = sorted(template.tasks or [], key=lambda t: (t.order_index, t.id))
    return CaseTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        customer_code=template.customer_code,
        source=template.source,
        is_default=template.is_default,
        created_by=template.created_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        tasks=[_template_task_to_response(t) for t in tasks_sorted],
    )


async def _load_template_with_tasks(
    template_id: int,
    session: AsyncSession,
) -> Optional[CaseTemplate]:
    stmt = (
        select(CaseTemplate)
        .where(CaseTemplate.id == template_id)
        .options(selectinload(CaseTemplate.tasks))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _enforce_single_default(
    customer_code: Optional[str],
    source: Optional[str],
    exclude_template_id: Optional[int],
    session: AsyncSession,
) -> None:
    """
    Demote any other ``is_default`` template that shares the same
    (customer_code, source) scope. Keeps default selection unambiguous.
    """
    stmt = (
        select(CaseTemplate)
        .where(CaseTemplate.is_default == True)  # noqa: E712 - SQL boolean
        .where(CaseTemplate.customer_code.is_(None) if customer_code is None else CaseTemplate.customer_code == customer_code)
        .where(CaseTemplate.source.is_(None) if source is None else CaseTemplate.source == source)
    )
    if exclude_template_id is not None:
        stmt = stmt.where(CaseTemplate.id != exclude_template_id)

    result = await session.execute(stmt)
    others = result.scalars().all()
    for other in others:
        other.is_default = False
        other.updated_at = datetime.utcnow()
        session.add(other)


# ---------------------------------------------------------------------------
# Template CRUD
# ---------------------------------------------------------------------------


async def create_template(
    request: CaseTemplateCreate,
    actor: str,
    session: AsyncSession,
) -> CaseTemplateOperationResponse:
    """Create a new template with optional initial tasks."""
    logger.info(f"Creating case template '{request.name}' by {actor}")

    try:
        if request.is_default:
            await _enforce_single_default(
                customer_code=request.customer_code,
                source=request.source,
                exclude_template_id=None,
                session=session,
            )

        template = CaseTemplate(
            name=request.name,
            description=request.description,
            customer_code=request.customer_code,
            source=request.source,
            is_default=request.is_default,
            created_by=actor,
        )
        session.add(template)
        await session.flush()  # populate template.id before adding tasks

        for task_payload in request.tasks:
            session.add(
                CaseTemplateTask(
                    template_id=template.id,
                    title=task_payload.title,
                    description=task_payload.description,
                    guidelines=task_payload.guidelines,
                    mandatory=task_payload.mandatory,
                    order_index=task_payload.order_index,
                ),
            )

        await session.commit()

        loaded = await _load_template_with_tasks(template.id, session)
        return CaseTemplateOperationResponse(
            template=_template_to_response(loaded),
            success=True,
            message=f"Created template '{loaded.name}' (id={loaded.id})",
        )

    except Exception as e:
        logger.error(f"Failed to create case template: {e}")
        await session.rollback()
        return CaseTemplateOperationResponse(
            template=None,
            success=False,
            message=f"Failed to create case template: {e}",
        )


async def list_templates(
    session: AsyncSession,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    include_global: bool = True,
) -> CaseTemplateListResponse:
    """
    List templates, optionally filtered. Filtering rules:

    - ``customer_code`` provided + ``include_global=True`` (default): returns
      templates for that customer plus all global templates (customer_code IS
      NULL). This matches the natural admin-UI need: "show me what's available
      for customer X".
    - ``customer_code`` provided + ``include_global=False``: customer-scoped
      only.
    - ``source`` provided: same logic for the source dimension.
    - Both omitted: returns everything (typical for admin Templates view).
    """
    try:
        stmt = select(CaseTemplate).options(selectinload(CaseTemplate.tasks))

        if customer_code is not None:
            if include_global:
                stmt = stmt.where(
                    (CaseTemplate.customer_code == customer_code) | (CaseTemplate.customer_code.is_(None)),
                )
            else:
                stmt = stmt.where(CaseTemplate.customer_code == customer_code)

        if source is not None:
            if include_global:
                stmt = stmt.where(
                    (CaseTemplate.source == source) | (CaseTemplate.source.is_(None)),
                )
            else:
                stmt = stmt.where(CaseTemplate.source == source)

        stmt = stmt.order_by(CaseTemplate.created_at.desc())

        result = await session.execute(stmt)
        templates = result.scalars().all()

        return CaseTemplateListResponse(
            templates=[_template_to_response(t) for t in templates],
            success=True,
            message=f"Retrieved {len(templates)} template(s)",
        )

    except Exception as e:
        logger.error(f"Failed to list case templates: {e}")
        return CaseTemplateListResponse(
            templates=[],
            success=False,
            message=f"Failed to list case templates: {e}",
        )


async def get_template(
    template_id: int,
    session: AsyncSession,
) -> CaseTemplateOperationResponse:
    template = await _load_template_with_tasks(template_id, session)
    if template is None:
        return CaseTemplateOperationResponse(
            template=None,
            success=False,
            message=f"Template id={template_id} not found",
        )

    return CaseTemplateOperationResponse(
        template=_template_to_response(template),
        success=True,
        message=f"Retrieved template id={template_id}",
    )


async def update_template(
    template_id: int,
    request: CaseTemplateUpdate,
    session: AsyncSession,
) -> CaseTemplateOperationResponse:
    """Partial update of template metadata. Tasks are managed separately."""
    try:
        template = await _load_template_with_tasks(template_id, session)
        if template is None:
            return CaseTemplateOperationResponse(
                template=None,
                success=False,
                message=f"Template id={template_id} not found",
            )

        fields_set = request.__fields_set__

        if "name" in fields_set and request.name is not None:
            template.name = request.name
        if "description" in fields_set:
            template.description = request.description
        if "customer_code" in fields_set:
            template.customer_code = request.customer_code
        if "source" in fields_set:
            template.source = request.source
        if "is_default" in fields_set and request.is_default is not None:
            template.is_default = request.is_default
            if template.is_default:
                await _enforce_single_default(
                    customer_code=template.customer_code,
                    source=template.source,
                    exclude_template_id=template.id,
                    session=session,
                )

        template.updated_at = datetime.utcnow()
        session.add(template)
        await session.commit()

        refreshed = await _load_template_with_tasks(template_id, session)
        return CaseTemplateOperationResponse(
            template=_template_to_response(refreshed),
            success=True,
            message=f"Updated template id={template_id}",
        )

    except Exception as e:
        logger.error(f"Failed to update case template id={template_id}: {e}")
        await session.rollback()
        return CaseTemplateOperationResponse(
            template=None,
            success=False,
            message=f"Failed to update case template: {e}",
        )


async def delete_template(
    template_id: int,
    session: AsyncSession,
) -> CaseTemplateOperationResponse:
    """
    Delete a template and its template tasks. Existing CaseTask rows on
    real cases are preserved (they're snapshots) and have their
    ``template_task_id`` FK set to NULL implicitly via a manual update —
    we don't rely on cascade because the column is nullable by design.
    """
    try:
        template = await _load_template_with_tasks(template_id, session)
        if template is None:
            return CaseTemplateOperationResponse(
                template=None,
                success=False,
                message=f"Template id={template_id} not found",
            )

        snapshot = _template_to_response(template)

        # Null out the soft FK on any CaseTask snapshots that pointed here.
        # Doing this explicitly so that a future change to ON DELETE behavior
        # doesn't silently clobber audit trails.
        from app.incidents.models import CaseTask

        task_ids = [t.id for t in template.tasks]
        if task_ids:
            stmt = select(CaseTask).where(CaseTask.template_task_id.in_(task_ids))
            result = await session.execute(stmt)
            for case_task in result.scalars().all():
                case_task.template_task_id = None
                session.add(case_task)

        for task in list(template.tasks):
            await session.delete(task)
        await session.delete(template)
        await session.commit()

        return CaseTemplateOperationResponse(
            template=snapshot,
            success=True,
            message=f"Deleted template id={template_id}",
        )

    except Exception as e:
        logger.error(f"Failed to delete case template id={template_id}: {e}")
        await session.rollback()
        return CaseTemplateOperationResponse(
            template=None,
            success=False,
            message=f"Failed to delete case template: {e}",
        )


# ---------------------------------------------------------------------------
# Template task CRUD
# ---------------------------------------------------------------------------


async def add_template_task(
    template_id: int,
    request: CaseTemplateTaskCreate,
    session: AsyncSession,
) -> CaseTemplateTaskOperationResponse:
    try:
        template = await _load_template_with_tasks(template_id, session)
        if template is None:
            return CaseTemplateTaskOperationResponse(
                task=None,
                success=False,
                message=f"Template id={template_id} not found",
            )

        task = CaseTemplateTask(
            template_id=template_id,
            title=request.title,
            description=request.description,
            guidelines=request.guidelines,
            mandatory=request.mandatory,
            order_index=request.order_index,
        )
        session.add(task)

        template.updated_at = datetime.utcnow()
        session.add(template)

        await session.commit()
        await session.refresh(task)

        return CaseTemplateTaskOperationResponse(
            task=_template_task_to_response(task),
            success=True,
            message=f"Added task id={task.id} to template id={template_id}",
        )

    except Exception as e:
        logger.error(f"Failed to add task to template id={template_id}: {e}")
        await session.rollback()
        return CaseTemplateTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to add template task: {e}",
        )


async def update_template_task(
    task_id: int,
    request: CaseTemplateTaskUpdate,
    session: AsyncSession,
) -> CaseTemplateTaskOperationResponse:
    try:
        result = await session.execute(select(CaseTemplateTask).where(CaseTemplateTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return CaseTemplateTaskOperationResponse(
                task=None,
                success=False,
                message=f"Template task id={task_id} not found",
            )

        fields_set = request.__fields_set__
        if "title" in fields_set and request.title is not None:
            task.title = request.title
        if "description" in fields_set:
            task.description = request.description
        if "guidelines" in fields_set:
            task.guidelines = request.guidelines
        if "mandatory" in fields_set and request.mandatory is not None:
            task.mandatory = request.mandatory
        if "order_index" in fields_set and request.order_index is not None:
            task.order_index = request.order_index

        session.add(task)

        # Touch the parent template so updated_at reflects the change.
        template_result = await session.execute(
            select(CaseTemplate).where(CaseTemplate.id == task.template_id),
        )
        parent = template_result.scalar_one_or_none()
        if parent is not None:
            parent.updated_at = datetime.utcnow()
            session.add(parent)

        await session.commit()
        await session.refresh(task)

        return CaseTemplateTaskOperationResponse(
            task=_template_task_to_response(task),
            success=True,
            message=f"Updated template task id={task_id}",
        )

    except Exception as e:
        logger.error(f"Failed to update template task id={task_id}: {e}")
        await session.rollback()
        return CaseTemplateTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to update template task: {e}",
        )


async def delete_template_task(
    task_id: int,
    session: AsyncSession,
) -> CaseTemplateTaskOperationResponse:
    try:
        result = await session.execute(select(CaseTemplateTask).where(CaseTemplateTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return CaseTemplateTaskOperationResponse(
                task=None,
                success=False,
                message=f"Template task id={task_id} not found",
            )

        snapshot = _template_task_to_response(task)
        template_id = task.template_id

        # Null out any CaseTask soft FKs that pointed at this template task.
        from app.incidents.models import CaseTask

        case_task_result = await session.execute(
            select(CaseTask).where(CaseTask.template_task_id == task_id),
        )
        for case_task in case_task_result.scalars().all():
            case_task.template_task_id = None
            session.add(case_task)

        await session.delete(task)

        template_result = await session.execute(
            select(CaseTemplate).where(CaseTemplate.id == template_id),
        )
        parent = template_result.scalar_one_or_none()
        if parent is not None:
            parent.updated_at = datetime.utcnow()
            session.add(parent)

        await session.commit()

        return CaseTemplateTaskOperationResponse(
            task=snapshot,
            success=True,
            message=f"Deleted template task id={task_id}",
        )

    except Exception as e:
        logger.error(f"Failed to delete template task id={task_id}: {e}")
        await session.rollback()
        return CaseTemplateTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to delete template task: {e}",
        )


async def reorder_template_tasks(
    template_id: int,
    ordered_task_ids: List[int],
    session: AsyncSession,
) -> CaseTemplateOperationResponse:
    """
    Reorder tasks within a template by passing the task IDs in the desired
    order. Tasks not included in the list keep their existing order_index
    value (effectively pushed to the end of the explicit list).

    Validates that every passed ID belongs to the named template.
    """
    try:
        template = await _load_template_with_tasks(template_id, session)
        if template is None:
            return CaseTemplateOperationResponse(
                template=None,
                success=False,
                message=f"Template id={template_id} not found",
            )

        existing_ids = {t.id for t in template.tasks}
        bad = [tid for tid in ordered_task_ids if tid not in existing_ids]
        if bad:
            return CaseTemplateOperationResponse(
                template=None,
                success=False,
                message=f"Task ids do not belong to template id={template_id}: {bad}",
            )

        # Assign sequential indices to the explicit list so a renamed UI
        # drag-drop reflects clean 0..N ordering on subsequent loads.
        index_map = {tid: idx for idx, tid in enumerate(ordered_task_ids)}
        for task in template.tasks:
            if task.id in index_map:
                task.order_index = index_map[task.id]
                session.add(task)

        template.updated_at = datetime.utcnow()
        session.add(template)

        await session.commit()

        refreshed = await _load_template_with_tasks(template_id, session)
        return CaseTemplateOperationResponse(
            template=_template_to_response(refreshed),
            success=True,
            message=f"Reordered {len(ordered_task_ids)} task(s) on template id={template_id}",
        )

    except Exception as e:
        logger.error(f"Failed to reorder tasks on template id={template_id}: {e}")
        await session.rollback()
        return CaseTemplateOperationResponse(
            template=None,
            success=False,
            message=f"Failed to reorder template tasks: {e}",
        )
