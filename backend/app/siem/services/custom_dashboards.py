from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.db.universal_models import CustomDashboardTemplates
from app.db.universal_models import Customers
from app.db.universal_models import EnabledDashboards
from app.db.universal_models import EventSources
from app.middleware.customer_access import customer_access_handler
from app.siem.schema.custom_dashboards import CUSTOM_LIBRARY_CARD
from app.siem.schema.custom_dashboards import CustomDashboardCreateRequest
from app.siem.schema.custom_dashboards import CustomDashboardDefinition
from app.siem.schema.custom_dashboards import CustomDashboardImportRequest
from app.siem.schema.custom_dashboards import CustomDashboardPreviewRequest
from app.siem.schema.custom_dashboards import CustomDashboardUpdateRequest
from app.siem.schema.custom_dashboards import slugify
from app.siem.schema.dashboards import PanelResult
from app.siem.services.dashboards import execute_panels


async def _verify_customer_exists(customer_code: str, db: AsyncSession) -> None:
    result = await db.execute(select(Customers).where(Customers.customer_code == customer_code))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")


async def _unique_template_key(candidate: str, db: AsyncSession) -> str:
    """Return `candidate`, suffixed with a counter until it is free.

    The key is what `enabled_dashboards.template_id` points at, so it must be
    unique deployment-wide even though two customers may want the same title.
    """
    key = candidate
    suffix = 2
    while True:
        result = await db.execute(
            select(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key == key),
        )
        if not result.scalars().first():
            return key
        key = f"{candidate}_{suffix}"
        suffix += 1


def _panels_as_dicts(panels: List[Any]) -> List[Dict[str, Any]]:
    """Pydantic panels → plain dicts for the JSON column.

    ``exclude_none`` keeps the stored template close to the hand-written on-disk
    ones (no `"field": null` noise) and makes export round-trip cleanly.
    """
    return [panel.model_dump(mode="json", exclude_none=True) if hasattr(panel, "model_dump") else dict(panel) for panel in panels]


# ── CRUD ────────────────────────────────────────────────────────


async def list_custom_dashboards(
    customer_code: Optional[str],
    db: AsyncSession,
) -> List[CustomDashboardTemplates]:
    """List custom templates.

    With ``customer_code`` set, returns the templates usable by that customer —
    its own plus every globally-shared one. Without it, returns all of them
    (the admin-wide view).
    """
    query = select(CustomDashboardTemplates)
    if customer_code:
        query = query.where(
            or_(
                CustomDashboardTemplates.customer_code == customer_code,
                CustomDashboardTemplates.customer_code.is_(None),
            ),
        )
    query = query.order_by(CustomDashboardTemplates.title)
    result = await db.execute(query)
    return result.scalars().all()


async def get_custom_dashboard(template_key: str, db: AsyncSession) -> CustomDashboardTemplates:
    result = await db.execute(
        select(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key == template_key),
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Custom dashboard '{template_key}' not found")
    return row


async def create_custom_dashboard(
    request: CustomDashboardCreateRequest,
    db: AsyncSession,
    current_user: Optional[User] = None,
    requested_key: Optional[str] = None,
    allow_key_suffix: bool = True,
) -> CustomDashboardTemplates:
    if request.customer_code:
        await _verify_customer_exists(request.customer_code, db)

    candidate = slugify(requested_key or request.template_key or request.title, fallback="custom_dashboard")[:255]
    if allow_key_suffix:
        template_key = await _unique_template_key(candidate, db)
    else:
        existing = await db.execute(
            select(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key == candidate),
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=409,
                detail=f"A custom dashboard with key '{candidate}' already exists",
            )
        template_key = candidate

    row = CustomDashboardTemplates(
        template_key=template_key,
        customer_code=request.customer_code,
        title=request.title,
        description=request.description,
        vendor=request.vendor,
        product=request.product,
        event_type=request.event_type,
        tags=request.tags or [],
        color=request.color,
        icon=request.icon,
        default_query=request.default_query,
        panels=_panels_as_dicts(request.panels),
        created_by=current_user.username if current_user else None,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    await db.commit()
    logger.info(f"Created custom dashboard '{template_key}' (customer={request.customer_code or 'global'})")
    return row


async def update_custom_dashboard(
    template_key: str,
    request: CustomDashboardUpdateRequest,
    db: AsyncSession,
) -> CustomDashboardTemplates:
    row = await get_custom_dashboard(template_key, db)
    data = request.model_dump(exclude_unset=True)

    if data.get("customer_code"):
        await _verify_customer_exists(data["customer_code"], db)
        # Narrowing a template to one customer would strand dashboards already
        # enabled for other tenants, so block it while they exist.
        others = await db.execute(
            select(EnabledDashboards).where(
                EnabledDashboards.library_card == CUSTOM_LIBRARY_CARD,
                EnabledDashboards.template_id == template_key,
                EnabledDashboards.customer_code != data["customer_code"],
            ),
        )
        if others.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="This dashboard is enabled for other customers; disable those first to scope it to a single customer",
            )

    for field in ("title", "description", "vendor", "product", "event_type", "tags", "color", "icon", "default_query", "customer_code"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])

    if data.get("share_globally"):
        row.customer_code = None

    if request.panels is not None:
        row.panels = _panels_as_dicts(request.panels)

    row.updated_at = datetime.utcnow()
    db.add(row)
    await db.flush()
    await db.refresh(row)
    await db.commit()
    logger.info(f"Updated custom dashboard '{template_key}'")
    return row


async def delete_custom_dashboard(template_key: str, db: AsyncSession) -> int:
    """Delete a custom template and every dashboard enabled from it.

    ``enabled_dashboards`` references custom templates by string, not by foreign
    key, so nothing cascades on its own — leaving the rows behind would show
    customers dashboards that 404 on open.
    """
    row = await get_custom_dashboard(template_key, db)

    enabled = await db.execute(
        select(EnabledDashboards).where(
            EnabledDashboards.library_card == CUSTOM_LIBRARY_CARD,
            EnabledDashboards.template_id == template_key,
        ),
    )
    disabled_count = len(enabled.scalars().all())

    if disabled_count:
        await db.execute(
            delete(EnabledDashboards).where(
                EnabledDashboards.library_card == CUSTOM_LIBRARY_CARD,
                EnabledDashboards.template_id == template_key,
            ),
        )

    await db.delete(row)
    await db.commit()
    logger.info(f"Deleted custom dashboard '{template_key}' along with {disabled_count} enabled dashboard(s)")
    return disabled_count


# ── Import / export ─────────────────────────────────────────────


async def import_custom_dashboard(
    request: CustomDashboardImportRequest,
    db: AsyncSession,
    current_user: Optional[User] = None,
) -> CustomDashboardTemplates:
    """Create (or replace) a template from an uploaded definition.

    Keeps the supplied ``template_key`` verbatim so a dashboard exported from one
    deployment keeps its identity in the next; a collision is a 409 unless the
    caller explicitly asked to overwrite.
    """
    definition = request.definition
    requested_key = slugify(definition.template_key or definition.title, fallback="custom_dashboard")[:255]

    existing_result = await db.execute(
        select(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key == requested_key),
    )
    existing = existing_result.scalars().first()

    if existing and not request.overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"A custom dashboard with key '{requested_key}' already exists. Re-import with overwrite to replace it.",
        )

    if existing:
        update = CustomDashboardUpdateRequest(
            title=definition.title,
            description=definition.description,
            vendor=definition.vendor,
            product=definition.product,
            event_type=definition.event_type,
            tags=definition.tags,
            color=definition.color,
            icon=definition.icon,
            default_query=definition.default_query,
            panels=definition.panels,
            customer_code=request.customer_code,
            share_globally=request.customer_code is None,
        )
        return await update_custom_dashboard(requested_key, update, db)

    create = CustomDashboardCreateRequest(
        **definition.model_dump(),
        customer_code=request.customer_code,
    )
    return await create_custom_dashboard(
        create,
        db,
        current_user=current_user,
        requested_key=requested_key,
        allow_key_suffix=False,
    )


def export_custom_dashboard(row: CustomDashboardTemplates) -> CustomDashboardDefinition:
    """Serialize a stored template back into its portable definition."""
    return CustomDashboardDefinition(
        template_key=row.template_key,
        title=row.title,
        description=row.description,
        vendor=row.vendor,
        product=row.product,
        event_type=row.event_type,
        tags=row.tags or [],
        color=row.color,
        icon=row.icon,
        default_query=row.default_query,
        panels=row.panels or [],
    )


# ── Preview (run panels without persisting anything) ─────────────


async def preview_custom_dashboard(
    request: CustomDashboardPreviewRequest,
    db: AsyncSession,
    current_user: User,
) -> Dict[str, Any]:
    """Execute an unsaved panel set against a real event source."""
    es_result = await db.execute(
        select(EventSources).where(EventSources.id == request.event_source_id),
    )
    event_source = es_result.scalars().first()
    if not event_source:
        raise HTTPException(status_code=404, detail=f"Event source {request.event_source_id} not found")

    # Same tenancy gate as the panel-data endpoint: the customer is resolved
    # server-side from the event source, never taken from the request body.
    if not await customer_access_handler.check_customer_access(current_user, event_source.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {event_source.customer_code}")
    if not event_source.enabled:
        raise HTTPException(status_code=400, detail="Event source is disabled")

    panels = _panels_as_dicts(request.panels)
    results: Dict[str, PanelResult] = await execute_panels(
        panels=panels,
        index_pattern=event_source.index_pattern,
        time_field=event_source.time_field,
        timerange=request.timerange,
        base_query=request.default_query,
    )

    return {
        "results": results,
        "template": {
            "id": "preview",
            "title": "Preview",
            "description": f"Preview against {event_source.name}",
            "panels": panels,
        },
        "customer_code": event_source.customer_code,
        "source_name": event_source.name,
    }
