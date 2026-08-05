from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler
from app.middleware.customer_access import verify_optional_customer_code_access
from app.siem.schema.custom_dashboards import CustomDashboardCreateRequest
from app.siem.schema.custom_dashboards import CustomDashboardDeleteResponse
from app.siem.schema.custom_dashboards import CustomDashboardExportResponse
from app.siem.schema.custom_dashboards import CustomDashboardImportRequest
from app.siem.schema.custom_dashboards import CustomDashboardOperationResponse
from app.siem.schema.custom_dashboards import CustomDashboardPreviewRequest
from app.siem.schema.custom_dashboards import CustomDashboardPreviewResponse
from app.siem.schema.custom_dashboards import CustomDashboardResponse
from app.siem.schema.custom_dashboards import CustomDashboardsListResponse
from app.siem.schema.custom_dashboards import CustomDashboardUpdateRequest
from app.siem.schema.dashboards import DashboardCategoriesListResponse
from app.siem.schema.dashboards import DashboardCategoryDetailResponse
from app.siem.schema.dashboards import DisableDashboardResponse
from app.siem.schema.dashboards import EnableDashboardRequest
from app.siem.schema.dashboards import EnabledDashboardOperationResponse
from app.siem.schema.dashboards import EnabledDashboardResponse
from app.siem.schema.dashboards import EnabledDashboardsListResponse
from app.siem.schema.dashboards import PanelDataRequest
from app.siem.schema.dashboards import PanelDataResponse
from app.siem.services.custom_dashboards import create_custom_dashboard
from app.siem.services.custom_dashboards import delete_custom_dashboard
from app.siem.services.custom_dashboards import export_custom_dashboard
from app.siem.services.custom_dashboards import get_custom_dashboard
from app.siem.services.custom_dashboards import import_custom_dashboard
from app.siem.services.custom_dashboards import list_custom_dashboards
from app.siem.services.custom_dashboards import preview_custom_dashboard
from app.siem.services.custom_dashboards import update_custom_dashboard
from app.siem.services.dashboards import disable_dashboard
from app.siem.services.dashboards import enable_dashboard
from app.siem.services.dashboards import get_category_detail
from app.siem.services.dashboards import get_enabled_dashboards
from app.siem.services.dashboards import get_enabled_dashboards_for_customers
from app.siem.services.dashboards import get_panel_data
from app.siem.services.dashboards import list_categories

dashboards_router = APIRouter()


async def verify_customer_exists(customer_code: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )


# ── Browse available templates (filesystem) ─────────────────────


@dashboards_router.get(
    "/templates",
    response_model=DashboardCategoriesListResponse,
    description="List all available dashboard categories (e.g. wazuh_edr, fortinet_edr)",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_dashboard_categories() -> DashboardCategoriesListResponse:
    logger.info("Listing dashboard categories")
    categories = list_categories()
    return DashboardCategoriesListResponse(
        categories=categories,
        success=True,
        message="Dashboard categories retrieved successfully",
    )


@dashboards_router.get(
    "/templates/{category_id}",
    response_model=DashboardCategoryDetailResponse,
    description="Get a dashboard category with all its template definitions",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def get_dashboard_category(category_id: str) -> DashboardCategoryDetailResponse:
    logger.info(f"Getting dashboard category {category_id}")
    category = get_category_detail(category_id)
    return DashboardCategoryDetailResponse(
        category=category,
        success=True,
        message="Dashboard category retrieved successfully",
    )


# ── Enabled dashboards (per-customer, DB-backed) ────────────────


@dashboards_router.get(
    "/enabled",
    response_model=EnabledDashboardsListResponse,
    description="List enabled dashboards across the user's accessible customers (optionally narrowed to a subset via customer_codes).",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_enabled_dashboards_multi(
    customer_codes: Optional[List[str]] = Query(None, description="Optional subset of customer codes to scope the results to"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnabledDashboardsListResponse:
    # Resolve the requested subset against the user's access (never widens scope).
    logger.info(f"Listing enabled dashboards for user {current_user.username} with requested customer_codes={customer_codes}")
    effective_customers = await customer_access_handler.resolve_effective_customers(current_user, customer_codes, db)
    rows = await get_enabled_dashboards_for_customers(effective_customers, db)
    return EnabledDashboardsListResponse(
        enabled_dashboards=[EnabledDashboardResponse.from_orm(r) for r in rows],
        success=True,
        message="Enabled dashboards retrieved successfully",
    )


@dashboards_router.get(
    "/enabled/{customer_code}",
    response_model=EnabledDashboardsListResponse,
    description="List dashboards enabled for a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def list_enabled_dashboards(
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnabledDashboardsListResponse:
    logger.info(f"Listing enabled dashboards for customer {customer_code}")
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
    await verify_customer_exists(customer_code, db)
    rows = await get_enabled_dashboards(customer_code, db)
    return EnabledDashboardsListResponse(
        enabled_dashboards=[EnabledDashboardResponse.from_orm(r) for r in rows],
        success=True,
        message="Enabled dashboards retrieved successfully",
    )


@dashboards_router.post(
    "/enable",
    response_model=EnabledDashboardOperationResponse,
    description="Enable a dashboard template for a customer + event source",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def enable_dashboard_endpoint(
    request: EnableDashboardRequest,
    db: AsyncSession = Depends(get_db),
) -> EnabledDashboardOperationResponse:
    logger.info(f"Enabling dashboard for customer {request.customer_code}")
    await verify_customer_exists(request.customer_code, db)
    row = await enable_dashboard(request, db)
    return EnabledDashboardOperationResponse(
        enabled_dashboard=EnabledDashboardResponse.from_orm(row),
        success=True,
        message="Dashboard enabled successfully",
    )


@dashboards_router.delete(
    "/disable/{dashboard_id}",
    response_model=DisableDashboardResponse,
    description="Disable (remove) an enabled dashboard",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def disable_dashboard_endpoint(
    dashboard_id: int,
    db: AsyncSession = Depends(get_db),
) -> DisableDashboardResponse:
    logger.info(f"Disabling dashboard {dashboard_id}")
    await disable_dashboard(dashboard_id, db)
    return DisableDashboardResponse(
        success=True,
        message="Dashboard disabled successfully",
    )


# ── Custom dashboards (UI-authored templates, DB-backed) ─────────
#
# Route order matters: the static `/custom/import` and `/custom/preview` paths
# must be declared before `/custom/{template_key}`, otherwise the wildcard
# swallows them and treats "import" as a template key.


@dashboards_router.get(
    "/custom",
    response_model=CustomDashboardsListResponse,
    description="List custom dashboard templates. With customer_code, returns that customer's templates plus the globally shared ones.",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst")),
        Depends(verify_optional_customer_code_access),
    ],
)
async def list_custom_dashboards_endpoint(
    customer_code: Optional[str] = Query(None, description="Scope the listing to one customer (plus global templates)"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardsListResponse:
    logger.info(f"Listing custom dashboards (customer_code={customer_code})")
    accessible = await customer_access_handler.get_user_accessible_customers(current_user, db)
    rows = await list_custom_dashboards(customer_code, db, accessible_customers=accessible)
    return CustomDashboardsListResponse(
        custom_dashboards=[CustomDashboardResponse.model_validate(row) for row in rows],
        success=True,
        message="Custom dashboards retrieved successfully",
    )


@dashboards_router.post(
    "/custom",
    response_model=CustomDashboardOperationResponse,
    description="Create a custom dashboard template",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_custom_dashboard_endpoint(
    request: CustomDashboardCreateRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardOperationResponse:
    logger.info(f"Creating custom dashboard '{request.title}' for customer {request.customer_code or 'ALL'}")
    row = await create_custom_dashboard(request, db, current_user=current_user)
    return CustomDashboardOperationResponse(
        custom_dashboard=CustomDashboardResponse.model_validate(row),
        success=True,
        message="Custom dashboard created successfully",
    )


@dashboards_router.post(
    "/custom/import",
    response_model=CustomDashboardOperationResponse,
    description="Import a custom dashboard template from an exported definition",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def import_custom_dashboard_endpoint(
    request: CustomDashboardImportRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardOperationResponse:
    logger.info(f"Importing custom dashboard '{request.definition.title}' (overwrite={request.overwrite})")
    row = await import_custom_dashboard(request, db, current_user=current_user)
    return CustomDashboardOperationResponse(
        custom_dashboard=CustomDashboardResponse.model_validate(row),
        success=True,
        message="Custom dashboard imported successfully",
    )


@dashboards_router.post(
    "/custom/preview",
    response_model=CustomDashboardPreviewResponse,
    description="Run an unsaved panel set against an event source so the builder can show live data",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def preview_custom_dashboard_endpoint(
    request: CustomDashboardPreviewRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardPreviewResponse:
    logger.info(f"Previewing {len(request.panels)} panel(s) against event source {request.event_source_id}")
    data = await preview_custom_dashboard(request, db, current_user)
    return CustomDashboardPreviewResponse(
        panels=data["results"],
        template=data["template"],
        customer_code=data["customer_code"],
        source_name=data["source_name"],
        success=True,
        message="Preview generated successfully",
    )


@dashboards_router.get(
    "/custom/{template_key}",
    response_model=CustomDashboardOperationResponse,
    description="Get a single custom dashboard template",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_custom_dashboard_endpoint(
    template_key: str,
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardOperationResponse:
    logger.info(f"Getting custom dashboard {template_key}")
    row = await get_custom_dashboard(template_key, db)
    return CustomDashboardOperationResponse(
        custom_dashboard=CustomDashboardResponse.model_validate(row),
        success=True,
        message="Custom dashboard retrieved successfully",
    )


@dashboards_router.put(
    "/custom/{template_key}",
    response_model=CustomDashboardOperationResponse,
    description="Update a custom dashboard template",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_custom_dashboard_endpoint(
    template_key: str,
    request: CustomDashboardUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardOperationResponse:
    logger.info(f"Updating custom dashboard {template_key}")
    row = await update_custom_dashboard(template_key, request, db)
    return CustomDashboardOperationResponse(
        custom_dashboard=CustomDashboardResponse.model_validate(row),
        success=True,
        message="Custom dashboard updated successfully",
    )


@dashboards_router.delete(
    "/custom/{template_key}",
    response_model=CustomDashboardDeleteResponse,
    description="Delete a custom dashboard template and every dashboard enabled from it",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_custom_dashboard_endpoint(
    template_key: str,
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardDeleteResponse:
    logger.info(f"Deleting custom dashboard {template_key}")
    disabled = await delete_custom_dashboard(template_key, db)
    return CustomDashboardDeleteResponse(
        disabled_dashboards=disabled,
        success=True,
        message=(
            f"Custom dashboard deleted successfully along with {disabled} enabled dashboard(s)"
            if disabled
            else "Custom dashboard deleted successfully"
        ),
    )


@dashboards_router.get(
    "/custom/{template_key}/export",
    response_model=CustomDashboardExportResponse,
    description="Export a custom dashboard template as a portable definition",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def export_custom_dashboard_endpoint(
    template_key: str,
    db: AsyncSession = Depends(get_db),
) -> CustomDashboardExportResponse:
    logger.info(f"Exporting custom dashboard {template_key}")
    row = await get_custom_dashboard(template_key, db)
    return CustomDashboardExportResponse(
        definition=export_custom_dashboard(row),
        success=True,
        message="Custom dashboard exported successfully",
    )


# ── Panel data (execute queries and return chart-ready data) ─────


@dashboards_router.post(
    "/panel-data",
    response_model=PanelDataResponse,
    description="Execute all panel queries for an enabled dashboard and return chart-ready data",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def panel_data_endpoint(
    request: PanelDataRequest,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PanelDataResponse:
    logger.info(f"Fetching panel data for dashboard {request.dashboard_id} (timerange={request.timerange})")
    data = await get_panel_data(request.dashboard_id, request.timerange, db, current_user)
    return PanelDataResponse(
        panels=data["results"],
        template=data["template"],
        dashboard_id=request.dashboard_id,
        customer_code=data["customer_code"],
        source_name=data["source_name"],
        accent_color=data["accent_color"],
        success=True,
        message="Panel data retrieved successfully",
    )
