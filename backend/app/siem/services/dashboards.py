import json
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from elasticsearch7.exceptions import RequestError
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import AlertsQueryBuilder
from app.auth.models.users import User
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import EnabledDashboards
from app.db.universal_models import EventSources
from app.middleware.customer_access import customer_access_handler
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


async def get_enabled_dashboards_for_customers(
    customer_codes: List[str],
    db: AsyncSession,
) -> List[EnabledDashboards]:
    """Fetch enabled dashboards across a set of customers.

    ``customer_codes`` is the caller's already-resolved effective set: ``["*"]``
    means all customers (admin/analyst), an empty list means none.
    """
    logger.info(f"Fetching enabled dashboards for customers {customer_codes}")
    query = select(EnabledDashboards)
    if "*" not in customer_codes:
        query = query.where(EnabledDashboards.customer_code.in_(customer_codes))
    result = await db.execute(query)
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


def _is_text_field_agg_error(exc: RequestError) -> bool:
    """True iff the Elasticsearch error is the one raised when a terms agg
    targets a `text`-typed field (which lacks per-document field data by
    default). The error string is stable across ES 7.x and is the cue we
    use to retry the agg against `<field>.keyword`.

    Sample message body (in `exc.info`):
        "Text fields are not optimised for operations that require
         per-document field data like aggregations and sorting..."

    Note: `str(exc)` for elasticsearch7 RequestError only includes the
    error code ("search_phase_execution_exception"), NOT the message —
    the human-readable text lives on `exc.info`. We match against both
    so the type code and the specific cause both have to line up.
    """
    info = getattr(exc, "info", "") or ""
    return getattr(exc, "error", "") == "search_phase_execution_exception" and "Text fields are not optimised" in str(info)


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
    current_user: User,
) -> Dict[str, Any]:
    """Execute each panel's query and return aggregated data for ECharts."""

    # Load the enabled dashboard row
    result = await db.execute(
        select(EnabledDashboards).where(EnabledDashboards.id == dashboard_id),
    )
    dashboard = result.scalars().first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Enabled dashboard not found")

    # Enforce per-tenant access BEFORE running any indexer query. The dashboard's
    # customer_code is resolved server-side from the id, so a caller could
    # otherwise enumerate dashboard ids to read another tenant's panel data
    # (GHSA-ch48-63px-6wp2). admin/analyst are all-tenant; customer_user is
    # limited to their assigned customers.
    if not await customer_access_handler.check_customer_access(current_user, dashboard.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {dashboard.customer_code}")

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

                    def _build_terms_agg(agg_field: str) -> dict:
                        return {
                            "top_values": {
                                "terms": {"field": agg_field, "size": size},
                            },
                        }

                    body["aggs"] = _build_terms_agg(field)
                    try:
                        resp = await es_client.search(index=event_source.index_pattern, body=body)
                    except RequestError as exc:
                        # Elasticsearch refuses terms aggs on `text` fields by default.
                        # If the index maps `field` as text, retry with the conventional
                        # `field.keyword` subfield. Cheap one-shot fallback that handles
                        # the common case where customer index templates differ.
                        if _is_text_field_agg_error(exc) and not field.endswith(".keyword"):
                            logger.info(
                                f"Panel {pid}: '{field}' is text-typed in {event_source.index_pattern}; "
                                f"retrying with '{field}.keyword'",
                            )
                            body["aggs"] = _build_terms_agg(f"{field}.keyword")
                            resp = await es_client.search(index=event_source.index_pattern, body=body)
                        else:
                            raise
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
