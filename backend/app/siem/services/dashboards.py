import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import EnabledDashboards
from app.db.universal_models import EventSources
from app.siem.schema.dashboards import DashboardCategory
from app.siem.schema.dashboards import DashboardCategoryWithTemplates
from app.siem.schema.dashboards import DashboardTemplate
from app.siem.schema.dashboards import EnableDashboardRequest
from app.siem.schema.dashboards import PanelResult

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
        f"Enabling dashboard {request.library_card}/{request.template_id} " f"for customer {request.customer_code}",
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


# ── Panel data (execute queries for dashboard rendering) ─────────


def _compute_histogram_interval(timerange: str) -> str:
    """Pick a reasonable date_histogram interval for the given timerange."""
    mapping = {
        "1h": "1m",
        "6h": "10m",
        "24h": "30m",
        "3d": "3h",
        "7d": "6h",
        "14d": "12h",
        "30d": "1d",
    }
    return mapping.get(timerange, "1h")


async def get_panel_data(
    dashboard_id: int,
    timerange: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Execute each panel's query and return aggregated data for ECharts."""

    # Load the enabled dashboard row
    result = await db.execute(
        select(EnabledDashboards).where(EnabledDashboards.id == dashboard_id),
    )
    dashboard = result.scalars().first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Enabled dashboard not found")

    # Load the event source to get index_pattern + time_field
    es_result = await db.execute(
        select(EventSources).where(EventSources.id == dashboard.event_source_id),
    )
    event_source = es_result.scalars().first()
    if not event_source:
        raise HTTPException(status_code=404, detail="Event source not found")
    if not event_source.enabled:
        raise HTTPException(status_code=400, detail="Event source is disabled")

    # Load template JSON from disk
    template_path = TEMPLATES_DIR / dashboard.library_card / f"{dashboard.template_id}.json"
    if not template_path.is_file():
        raise HTTPException(status_code=404, detail="Dashboard template file not found")

    template = json.loads(template_path.read_text())
    panels = template.get("panels", [])

    # Load category card for accent color
    card_path = TEMPLATES_DIR / dashboard.library_card / "_card.json"
    accent_color = "#38bdf8"
    if card_path.is_file():
        card = json.loads(card_path.read_text())
        accent_color = card.get("color", accent_color)

    # Build time range filter
    query_builder = AlertsQueryBuilder()
    query_builder.add_time_range(timerange=timerange, timestamp_field=event_source.time_field)
    time_filter = query_builder.query["query"]["bool"]["must"]

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
    results: Dict[str, PanelResult] = {}

    try:
        for panel in panels:
            pid = panel["id"]
            ptype = panel["type"]
            lucene = panel.get("lucene", "*")
            field = panel.get("field")
            size = panel.get("size", 10)

            try:
                # Build base query with time filter + Lucene
                body: dict = {
                    "query": {
                        "bool": {
                            "must": [
                                *time_filter,
                                {"query_string": {"query": lucene, "default_operator": "AND"}},
                            ],
                        },
                    },
                    "size": 0,
                }

                if ptype == "stat":
                    # Just need the total count
                    resp = await es_client.search(index=event_source.index_pattern, body=body)
                    total = resp["hits"]["total"]
                    count = total["value"] if isinstance(total, dict) else total
                    results[pid] = PanelResult(type="stat", value=count)

                elif ptype == "histogram":
                    interval = _compute_histogram_interval(timerange)
                    body["aggs"] = {
                        "over_time": {
                            "date_histogram": {
                                "field": event_source.time_field,
                                "fixed_interval": interval,
                                "min_doc_count": 0,
                            },
                        },
                    }
                    resp = await es_client.search(index=event_source.index_pattern, body=body)
                    buckets = resp["aggregations"]["over_time"]["buckets"]
                    labels = [b["key_as_string"] for b in buckets]
                    data = [b["doc_count"] for b in buckets]
                    results[pid] = PanelResult(type="histogram", labels=labels, data=data)

                elif ptype in ("pie", "bar_h"):
                    if not field:
                        results[pid] = PanelResult(type=ptype, error="No field specified for aggregation")
                        continue
                    body["aggs"] = {
                        "top_values": {
                            "terms": {
                                "field": field,
                                "size": size,
                            },
                        },
                    }
                    resp = await es_client.search(index=event_source.index_pattern, body=body)
                    buckets = resp["aggregations"]["top_values"]["buckets"]
                    labels = [str(b["key"]) for b in buckets]
                    data = [b["doc_count"] for b in buckets]
                    results[pid] = PanelResult(type=ptype, labels=labels, data=data)

                else:
                    results[pid] = PanelResult(type=ptype, error=f"Unknown panel type: {ptype}")

            except Exception as e:
                logger.error(f"Error querying panel {pid}: {e}")
                results[pid] = PanelResult(type=ptype, error=str(e))
    finally:
        await es_client.close()

    return {
        "results": results,
        "template": template,
        "accent_color": accent_color,
        "customer_code": dashboard.customer_code,
        "source_name": event_source.name,
    }
