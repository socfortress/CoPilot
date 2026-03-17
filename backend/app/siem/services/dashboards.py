import json
from pathlib import Path
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import EnabledDashboards
from app.db.universal_models import EventSources
from app.siem.schema.dashboards import DashboardCategory
from app.siem.schema.dashboards import DashboardCategoryWithTemplates
from app.siem.schema.dashboards import DashboardTemplate
from app.siem.schema.dashboards import EnableDashboardRequest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "dashboard_templates"


# ── Template browsing (filesystem) ──────────────────────────────


def list_categories() -> List[DashboardCategory]:
    """Return every category that has a valid _card.json."""
    categories: List[DashboardCategory] = []
    if not TEMPLATES_DIR.is_dir():
        return categories
    for child in sorted(TEMPLATES_DIR.iterdir()):
        card_path = child / "_card.json"
        if child.is_dir() and card_path.is_file():
            data = json.loads(card_path.read_text())
            categories.append(DashboardCategory(**data))
    return categories


def get_category_detail(category_id: str) -> DashboardCategoryWithTemplates:
    """Load one category card + all its dashboard templates."""
    category_dir = TEMPLATES_DIR / category_id
    card_path = category_dir / "_card.json"
    if not category_dir.is_dir() or not card_path.is_file():
        raise HTTPException(status_code=404, detail=f"Dashboard category '{category_id}' not found")

    card = json.loads(card_path.read_text())
    templates: List[DashboardTemplate] = []
    for tpl_file in sorted(category_dir.glob("*.json")):
        if tpl_file.name.startswith("_"):
            continue
        tpl_data = json.loads(tpl_file.read_text())
        templates.append(DashboardTemplate(**tpl_data))

    return DashboardCategoryWithTemplates(**card, templates=templates)


# ── Enabled dashboards (database) ───────────────────────────────


async def get_enabled_dashboards(
    customer_code: str,
    db: AsyncSession,
) -> List[EnabledDashboards]:
    logger.info(f"Fetching enabled dashboards for customer {customer_code}")
    result = await db.execute(
        select(EnabledDashboards).where(EnabledDashboards.customer_code == customer_code),
    )
    return result.scalars().all()


async def enable_dashboard(
    request: EnableDashboardRequest,
    db: AsyncSession,
) -> EnabledDashboards:
    logger.info(
        f"Enabling dashboard {request.library_card}/{request.template_id} "
        f"for customer {request.customer_code}",
    )

    # Verify the category and template exist on disk
    category_dir = TEMPLATES_DIR / request.library_card
    card_path = category_dir / "_card.json"
    template_path = category_dir / f"{request.template_id}.json"
    if not card_path.is_file():
        raise HTTPException(status_code=404, detail=f"Dashboard category '{request.library_card}' not found")
    if not template_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard template '{request.template_id}' not found in category '{request.library_card}'",
        )

    # Verify event source exists
    es_result = await db.execute(
        select(EventSources).where(EventSources.id == request.event_source_id),
    )
    if not es_result.scalars().first():
        raise HTTPException(status_code=404, detail=f"Event source {request.event_source_id} not found")

    # Check for duplicate
    result = await db.execute(
        select(EnabledDashboards).where(
            EnabledDashboards.customer_code == request.customer_code,
            EnabledDashboards.event_source_id == request.event_source_id,
            EnabledDashboards.library_card == request.library_card,
            EnabledDashboards.template_id == request.template_id,
        ),
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="This dashboard is already enabled for this customer and event source",
        )

    row = EnabledDashboards(
        customer_code=request.customer_code,
        event_source_id=request.event_source_id,
        library_card=request.library_card,
        template_id=request.template_id,
        display_name=request.display_name,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    await db.commit()
    return row


async def disable_dashboard(
    dashboard_id: int,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(EnabledDashboards).where(EnabledDashboards.id == dashboard_id),
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Enabled dashboard not found")
    await db.delete(row)
    await db.commit()
    logger.info(f"Disabled dashboard {dashboard_id}")
