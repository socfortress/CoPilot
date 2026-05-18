"""
Service layer for case tasks (issue #792, Phase 3).

Responsibilities:
- Selecting a CaseTemplate for a newly-created Case based on
  ``(customer_code, source)`` with a documented priority order.
- Snapshot-copying ``CaseTemplateTask`` rows into ``CaseTask`` rows on
  case creation (or post-creation manual apply).
- CRUD on CaseTask rows (analyst-driven custom adds, status updates with
  evidence comments, deletes).
- The "soft-warning on close" check that's wired into the existing
  ``/case/status`` endpoint by the route layer.

Authorization is enforced at the route layer; this module is auth-agnostic.
"""

from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.incidents.models import Alert
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import CaseTask
from app.incidents.models import CaseTemplate
from app.incidents.schema.case_templates import CaseCloseWarningResponse
from app.incidents.schema.case_templates import CaseEventType
from app.incidents.schema.case_templates import CaseTaskCreate
from app.incidents.schema.case_templates import CaseTaskListResponse
from app.incidents.schema.case_templates import CaseTaskOperationResponse
from app.incidents.schema.case_templates import CaseTaskResponse
from app.incidents.schema.case_templates import CaseTaskStatus
from app.incidents.schema.case_templates import CaseTaskUpdate

# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------


def _case_task_to_response(task: CaseTask) -> CaseTaskResponse:
    return CaseTaskResponse(
        id=task.id,
        case_id=task.case_id,
        alert_id=task.alert_id,
        template_task_id=task.template_task_id,
        title=task.title,
        description=task.description,
        guidelines=task.guidelines,
        mandatory=task.mandatory,
        order_index=task.order_index,
        status=CaseTaskStatus(task.status),
        evidence_comment=task.evidence_comment,
        completed_by=task.completed_by,
        completed_at=task.completed_at,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ---------------------------------------------------------------------------
# Template selection (for case creation)
# ---------------------------------------------------------------------------


async def pick_template_for_case(
    customer_code: Optional[str],
    source: Optional[str],
    session: AsyncSession,
) -> Optional[CaseTemplate]:
    """
    Pick the most-specific applicable template for a newly created case.

    Priority order (each step short-circuits the next):

    1. ``customer_code`` + ``source`` exact match, prefer is_default
    2. ``customer_code`` only (source IS NULL), prefer is_default
    3. ``source`` only (customer_code IS NULL), prefer is_default
    4. Global default (both NULL, is_default=True)

    **Conditional templates are excluded from every tier.** A template with a
    ``match_field`` set is saying "fire only when this condition matches" — it
    participates in selection exclusively via ``pick_templates_for_alert``. If
    its condition is rejected, it must not silently re-enter via the fallback
    tier; that would defeat the whole point of having a condition.

    Returns the template with tasks eagerly loaded, or None if no match.
    """

    async def _query(customer_filter, source_filter) -> Optional[CaseTemplate]:
        stmt = (
            select(CaseTemplate)
            .options(selectinload(CaseTemplate.tasks))
            .where(CaseTemplate.match_field.is_(None))
            .where(customer_filter)
            .where(source_filter)
            .order_by(CaseTemplate.is_default.desc(), CaseTemplate.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    # Step 1 — both match
    if customer_code is not None and source is not None:
        match = await _query(
            CaseTemplate.customer_code == customer_code,
            CaseTemplate.source == source,
        )
        if match is not None:
            return match

    # Step 2 — customer only
    if customer_code is not None:
        match = await _query(
            CaseTemplate.customer_code == customer_code,
            CaseTemplate.source.is_(None),
        )
        if match is not None:
            return match

    # Step 3 — source only
    if source is not None:
        match = await _query(
            CaseTemplate.customer_code.is_(None),
            CaseTemplate.source == source,
        )
        if match is not None:
            return match

    # Step 4 — global default
    match = await _query(
        CaseTemplate.customer_code.is_(None),
        CaseTemplate.source.is_(None),
    )
    if match is not None and match.is_default:
        return match

    return None


# ---------------------------------------------------------------------------
# Conditional template selection (field-match against the raw Wazuh document)
# ---------------------------------------------------------------------------


async def _fetch_raw_event_for_alert(
    alert: Alert,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    Return the raw Wazuh document for this alert's first asset, or None if
    there is no asset or the OpenSearch fetch raises.

    Picks the lowest-id asset deterministically; the original-event coordinates
    are typically the same across an alert's assets, but if they diverge we
    prefer the asset that landed first. Talks to the Wazuh indexer directly
    rather than going through ``fetch_alert_details`` because we don't want
    its syslog_type validation gate — for field-match we only need a key/value
    bag.
    """
    asset_stmt = (
        select(Asset)
        .where(Asset.alert_linked == alert.id)
        .order_by(Asset.id.asc())
        .limit(1)
    )
    asset = (await session.execute(asset_stmt)).scalars().first()
    if asset is None:
        logger.info(
            f"pick_templates_for_alert: alert id={alert.id} has no asset row; "
            "field-match templates are skipped for this alert.",
        )
        return None

    try:
        from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client_async

        es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
        doc = await es_client.get(index=asset.index_name, id=asset.index_id)
        return doc.get("_source") or {}
    except Exception as e:
        logger.warning(
            f"pick_templates_for_alert: raw-event fetch failed for alert id={alert.id} "
            f"(index={asset.index_name}, id={asset.index_id}): {e}. "
            "Falling back to non-field-match templates.",
        )
        return None


async def pick_templates_for_alert(
    case: Case,
    alert: Alert,
    session: AsyncSession,
) -> List[CaseTemplate]:
    """
    Return every CaseTemplate that should auto-apply for this (case, alert).

    Two-stage selection:

    1. **Field-match templates** (both ``match_field`` and ``match_value``
       set) scoped to this case's customer + alert's source are evaluated
       against the raw Wazuh document fetched via the alert's first asset.
       Every template whose ``document[match_field] == match_value`` is
       included — they layer additively.
    2. **Fallback.** If zero field-match templates fired (no candidates, no
       matches, or the raw-event fetch raised), use the existing single-
       template tier picker (``customer+source > customer > source > global
       default``) and return its result as a one-element list.

    This split is deliberate: a generic "wazuh global" template shouldn't
    drown a specific "sysmon event 1" one. Returns an empty list if nothing
    applies.
    """
    field_match_stmt = (
        select(CaseTemplate)
        .options(selectinload(CaseTemplate.tasks))
        .where(CaseTemplate.match_field.is_not(None))
        .where(CaseTemplate.match_value.is_not(None))
        .where(
            (CaseTemplate.customer_code == case.customer_code) | (CaseTemplate.customer_code.is_(None)),
        )
        .where(
            (CaseTemplate.source == alert.source) | (CaseTemplate.source.is_(None)),
        )
    )
    candidates = list((await session.execute(field_match_stmt)).scalars().all())

    matched: List[CaseTemplate] = []
    if candidates:
        raw_event = await _fetch_raw_event_for_alert(alert, session)
        if raw_event is not None:
            for tmpl in candidates:
                doc_value = raw_event.get(tmpl.match_field)
                if doc_value is None:
                    continue
                # Wazuh top-level values arrive as strings already (numeric
                # fields like data_win_system_eventID are quoted: "1"). Coerce
                # defensively so a numeric value in the document still matches
                # the string in match_value.
                if str(doc_value) == tmpl.match_value:
                    matched.append(tmpl)

    if matched:
        logger.info(
            f"pick_templates_for_alert: {len(matched)} field-match template(s) fired "
            f"for case id={case.id} alert id={alert.id}: {[t.id for t in matched]}",
        )
        return matched

    fallback = await pick_template_for_case(
        customer_code=case.customer_code,
        source=alert.source,
        session=session,
    )
    return [fallback] if fallback is not None else []


# ---------------------------------------------------------------------------
# Template application (snapshot copy)
# ---------------------------------------------------------------------------


async def apply_template_to_case(
    case_id: int,
    template_id: int,
    actor: str,
    session: AsyncSession,
    *,
    alert_id: Optional[int] = None,
    commit: bool = True,
) -> List[CaseTask]:
    """
    Snapshot-copy every CaseTemplateTask on the named template into a new
    CaseTask row attached to the case.

    Tasks are *snapshots* — editing the source template later does not
    mutate the CaseTask rows. ``template_task_id`` is preserved as a soft
    link for analytics / future "this came from template X" UI hints.

    When ``alert_id`` is provided, every materialized CaseTask row is
    stamped with that alert id (so the Tasks UI can group tasks under
    their originating alert). The caller is responsible for ensuring the
    alert is linked to the case; this function trusts the caller. ``None``
    produces case-wide / general tasks.

    Set ``commit=False`` when calling from inside another transaction
    (e.g., immediately after a Case is created in the same flow); the
    caller is then responsible for the commit.
    """
    template_result = await session.execute(
        select(CaseTemplate).where(CaseTemplate.id == template_id).options(selectinload(CaseTemplate.tasks)),
    )
    template = template_result.scalar_one_or_none()
    if template is None:
        logger.warning(f"apply_template_to_case: template id={template_id} not found")
        return []

    case_result = await session.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    if case is None:
        logger.warning(f"apply_template_to_case: case id={case_id} not found")
        return []

    new_tasks: List[CaseTask] = []
    for tmpl_task in sorted(template.tasks, key=lambda t: (t.order_index, t.id)):
        case_task = CaseTask(
            case_id=case_id,
            alert_id=alert_id,
            template_task_id=tmpl_task.id,
            title=tmpl_task.title,
            description=tmpl_task.description,
            guidelines=tmpl_task.guidelines,
            mandatory=tmpl_task.mandatory,
            order_index=tmpl_task.order_index,
            status=CaseTaskStatus.TODO.value,
            evidence_comment=None,
            completed_by=None,
            completed_at=None,
            created_by=actor,
        )
        session.add(case_task)
        new_tasks.append(case_task)

    # Audit emits (Phase 4): one template_applied event for the operation,
    # plus one task_added event per snapshotted task. Imported lazily to
    # avoid a circular import — case_events doesn't depend on case_tasks
    # but isort/lint sometimes resolves these eagerly.
    from app.incidents.services.case_events import emit_case_event
    from app.incidents.services.case_events import payload_task
    from app.incidents.services.case_events import payload_template_applied

    await session.flush()  # ensure case_task.id is populated for the audit payloads

    template_applied_payload = payload_template_applied(
        template_id=template.id,
        template_name=template.name,
        tasks_added=len(new_tasks),
    )
    if alert_id is not None:
        template_applied_payload["alert_id"] = alert_id

    await emit_case_event(
        session=session,
        case_id=case_id,
        event_type=CaseEventType.TEMPLATE_APPLIED,
        actor=actor,
        payload=template_applied_payload,
        commit=False,
    )
    for ct in new_tasks:
        await emit_case_event(
            session=session,
            case_id=case_id,
            event_type=CaseEventType.TASK_ADDED,
            actor=actor,
            payload=payload_task(
                task_id=ct.id,
                title=ct.title,
                mandatory=ct.mandatory,
                source="template",
                template_id=template.id,
                alert_id=alert_id,
            ),
            commit=False,
        )

    if commit:
        await session.commit()
        for t in new_tasks:
            await session.refresh(t)
        logger.info(
            f"Applied template id={template_id} ('{template.name}') to case id={case_id}: " f"{len(new_tasks)} task(s) created by {actor}",
        )
    else:
        logger.info(
            f"Staged template id={template_id} ('{template.name}') for case id={case_id}: " f"{len(new_tasks)} task(s) (uncommitted)",
        )

    return new_tasks


async def auto_apply_template_for_new_case(
    case: Case,
    alert: Alert,
    actor: str,
    session: AsyncSession,
) -> List[Tuple[CaseTemplate, List[CaseTask]]]:
    """
    Run the per-alert auto-apply selection for a case and apply every
    template the new ``pick_templates_for_alert`` returns.

    Field-match templates (when present and the raw event matches) layer
    additively; otherwise the legacy tier picker contributes one fallback
    template. All materialized CaseTask rows are stamped with ``alert.id``
    so they group under the originating alert in the UI.

    Returns the list of (template, tasks) pairs applied. ``commit=False`` on
    each apply call — the caller's transaction stays in control.
    """
    templates = await pick_templates_for_alert(case=case, alert=alert, session=session)
    applied: List[Tuple[CaseTemplate, List[CaseTask]]] = []
    for template in templates:
        tasks = await apply_template_to_case(
            case_id=case.id,
            template_id=template.id,
            actor=actor,
            session=session,
            alert_id=alert.id,
            commit=False,
        )
        applied.append((template, tasks))
    return applied


# ---------------------------------------------------------------------------
# Case task CRUD
# ---------------------------------------------------------------------------


async def list_case_tasks(case_id: int, session: AsyncSession) -> CaseTaskListResponse:
    try:
        stmt = select(CaseTask).where(CaseTask.case_id == case_id).order_by(CaseTask.order_index, CaseTask.id)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        return CaseTaskListResponse(
            tasks=[_case_task_to_response(t) for t in tasks],
            success=True,
            message=f"Retrieved {len(tasks)} task(s) for case id={case_id}",
        )
    except Exception as e:
        logger.error(f"Failed to list tasks for case id={case_id}: {e}")
        return CaseTaskListResponse(
            tasks=[],
            success=False,
            message=f"Failed to list case tasks: {e}",
        )


async def is_alert_linked_to_case(
    case_id: int,
    alert_id: int,
    session: AsyncSession,
) -> bool:
    """True iff a CaseAlertLink row exists for this (case, alert) pair."""
    stmt = (
        select(CaseAlertLink.alert_id)
        .where(CaseAlertLink.case_id == case_id)
        .where(CaseAlertLink.alert_id == alert_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def add_case_task(
    case_id: int,
    request: CaseTaskCreate,
    actor: str,
    session: AsyncSession,
) -> CaseTaskOperationResponse:
    """Add a custom task to a case mid-investigation. template_task_id is NULL.

    When ``request.alert_id`` is provided, validates the alert is currently
    linked to the case — analysts shouldn't be able to attach tasks to alerts
    that aren't part of the case. Otherwise the task is created as case-wide.
    """
    try:
        case_result = await session.execute(select(Case).where(Case.id == case_id))
        if case_result.scalar_one_or_none() is None:
            return CaseTaskOperationResponse(
                task=None,
                success=False,
                message=f"Case id={case_id} not found",
            )

        if request.alert_id is not None:
            if not await is_alert_linked_to_case(case_id, request.alert_id, session):
                return CaseTaskOperationResponse(
                    task=None,
                    success=False,
                    message=(
                        f"Alert id={request.alert_id} is not linked to case id={case_id}; "
                        "link the alert first or omit alert_id for a case-wide task."
                    ),
                )

        task = CaseTask(
            case_id=case_id,
            alert_id=request.alert_id,
            template_task_id=None,
            title=request.title,
            description=request.description,
            guidelines=request.guidelines,
            mandatory=request.mandatory,
            order_index=request.order_index,
            status=CaseTaskStatus.TODO.value,
            created_by=actor,
        )
        session.add(task)
        await session.flush()

        from app.incidents.services.case_events import emit_case_event
        from app.incidents.services.case_events import payload_task

        await emit_case_event(
            session=session,
            case_id=case_id,
            event_type=CaseEventType.TASK_ADDED,
            actor=actor,
            payload=payload_task(
                task_id=task.id,
                title=task.title,
                mandatory=task.mandatory,
                source="custom",
                alert_id=task.alert_id,
            ),
            commit=False,
        )

        await session.commit()
        await session.refresh(task)

        return CaseTaskOperationResponse(
            task=_case_task_to_response(task),
            success=True,
            message=f"Added task id={task.id} to case id={case_id}",
        )
    except Exception as e:
        logger.error(f"Failed to add task to case id={case_id}: {e}")
        await session.rollback()
        return CaseTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to add case task: {e}",
        )


async def update_case_task(
    task_id: int,
    request: CaseTaskUpdate,
    actor: str,
    session: AsyncSession,
) -> CaseTaskOperationResponse:
    """
    Update task status and/or evidence comment. Validates that
    NOT_NECESSARY isn't applied to a mandatory task. Sets/unsets
    ``completed_by`` and ``completed_at`` based on the resulting status.
    """
    try:
        result = await session.execute(select(CaseTask).where(CaseTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return CaseTaskOperationResponse(
                task=None,
                success=False,
                message=f"Case task id={task_id} not found",
            )

        fields_set = request.__fields_set__
        previous_status = task.status
        status_changed = False

        if "status" in fields_set and request.status is not None:
            new_status = request.status
            if new_status == CaseTaskStatus.NOT_NECESSARY and task.mandatory:
                return CaseTaskOperationResponse(
                    task=_case_task_to_response(task),
                    success=False,
                    message="Mandatory tasks cannot be marked NOT_NECESSARY.",
                )
            if new_status.value != task.status:
                task.status = new_status.value
                status_changed = True

            # Maintain completed_by / completed_at to reflect the resulting state.
            if new_status in (CaseTaskStatus.DONE, CaseTaskStatus.NOT_NECESSARY):
                task.completed_by = actor
                task.completed_at = datetime.utcnow()
            else:
                # Returning to TODO clears the completion record.
                task.completed_by = None
                task.completed_at = None

        comment_set_this_call = "evidence_comment" in fields_set
        if comment_set_this_call:
            task.evidence_comment = request.evidence_comment

        task.updated_at = datetime.utcnow()
        session.add(task)

        # Audit emits (Phase 4): two distinct events when both fire — the UI
        # can render them as a single block but the data model keeps them
        # separate so a comment-only update still appears in the timeline.
        from app.incidents.services.case_events import emit_case_event
        from app.incidents.services.case_events import payload_task

        if status_changed:
            await emit_case_event(
                session=session,
                case_id=task.case_id,
                event_type=CaseEventType.TASK_STATUS_CHANGED,
                actor=actor,
                payload=payload_task(
                    task_id=task.id,
                    title=task.title,
                    mandatory=task.mandatory,
                    from_status=previous_status,
                    to_status=task.status,
                ),
                commit=False,
            )

        if comment_set_this_call and request.evidence_comment:
            await emit_case_event(
                session=session,
                case_id=task.case_id,
                event_type=CaseEventType.TASK_COMMENTED,
                actor=actor,
                payload=payload_task(
                    task_id=task.id,
                    title=task.title,
                    mandatory=task.mandatory,
                    snippet=request.evidence_comment[:140],
                ),
                commit=False,
            )

        await session.commit()
        await session.refresh(task)

        return CaseTaskOperationResponse(
            task=_case_task_to_response(task),
            success=True,
            message=f"Updated case task id={task_id}",
        )
    except Exception as e:
        logger.error(f"Failed to update case task id={task_id}: {e}")
        await session.rollback()
        return CaseTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to update case task: {e}",
        )


async def delete_case_task(
    task_id: int,
    session: AsyncSession,
) -> CaseTaskOperationResponse:
    """
    Delete a case task. Allowed against template-derived tasks too —
    if the analyst genuinely doesn't want the task tracked, deletion
    is more honest than NOT_NECESSARY (which is reserved for
    "intentionally skipped during this investigation").
    """
    try:
        result = await session.execute(select(CaseTask).where(CaseTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return CaseTaskOperationResponse(
                task=None,
                success=False,
                message=f"Case task id={task_id} not found",
            )
        snapshot = _case_task_to_response(task)
        await session.delete(task)
        await session.commit()
        return CaseTaskOperationResponse(
            task=snapshot,
            success=True,
            message=f"Deleted case task id={task_id}",
        )
    except Exception as e:
        logger.error(f"Failed to delete case task id={task_id}: {e}")
        await session.rollback()
        return CaseTaskOperationResponse(
            task=None,
            success=False,
            message=f"Failed to delete case task: {e}",
        )


# ---------------------------------------------------------------------------
# Soft-warning support
# ---------------------------------------------------------------------------


async def get_incomplete_mandatory_tasks(
    case_id: int,
    session: AsyncSession,
) -> List[CaseTask]:
    """
    Return mandatory tasks on the named case whose status is not DONE.
    Used by the close-case route to drive the soft-warning response.

    Note: NOT_NECESSARY is never a valid status for a mandatory task
    (enforced in update_case_task), so the only "completed" terminal
    state for a mandatory task is DONE.
    """
    stmt = (
        select(CaseTask)
        .where(CaseTask.case_id == case_id)
        .where(CaseTask.mandatory == True)  # noqa: E712
        .where(CaseTask.status != CaseTaskStatus.DONE.value)
        .order_by(CaseTask.order_index, CaseTask.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


def build_close_warning_response(incomplete: List[CaseTask]) -> CaseCloseWarningResponse:
    return CaseCloseWarningResponse(
        success=False,
        requires_confirmation=True,
        message=(f"{len(incomplete)} mandatory task(s) are not marked DONE. " "Re-submit with force=true to close anyway."),
        incomplete_mandatory_tasks=[_case_task_to_response(t) for t in incomplete],
    )


# ---------------------------------------------------------------------------
# Convenience: derive first-linked-alert source for create_case path
# ---------------------------------------------------------------------------


async def orphan_tasks_for_alert(
    case_id: int,
    alert_id: int,
    session: AsyncSession,
    *,
    commit: bool = True,
) -> int:
    """
    Set ``alert_id = NULL`` on every CaseTask in this case that was attached
    to the unlinked alert. Tasks survive (snapshot-preserving semantics) and
    become case-wide / general tasks.

    Returns the number of rows affected so the caller can include it in the
    timeline payload for the unlink event.
    """
    stmt = (
        update(CaseTask)
        .where(CaseTask.case_id == case_id)
        .where(CaseTask.alert_id == alert_id)
        .values(alert_id=None, updated_at=datetime.utcnow())
    )
    result = await session.execute(stmt)
    affected = result.rowcount or 0
    if commit:
        await session.commit()
    if affected:
        logger.info(
            f"Orphaned {affected} task(s) on case id={case_id} when alert id={alert_id} was unlinked",
        )
    return affected


async def get_first_alert_source_for_case(
    case_id: int,
    session: AsyncSession,
) -> Optional[str]:
    """
    Return the alert.source of the lowest-id alert linked to the case,
    or None if no alerts are linked. Used by the manual create_case path
    (which doesn't naturally know the source) AFTER the analyst links
    an alert and wants to apply a template.
    """
    stmt = (
        select(Alert.source)
        .join(CaseAlertLink, CaseAlertLink.alert_id == Alert.id)
        .where(CaseAlertLink.case_id == case_id)
        .order_by(Alert.id.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
