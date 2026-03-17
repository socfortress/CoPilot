from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.middleware.customer_access import customer_access_handler
from app.siem.schema.dashboards import DashboardCategoriesListResponse
from app.siem.schema.dashboards import DashboardCategoryDetailResponse
from app.siem.schema.dashboards import DisableDashboardResponse
from app.siem.schema.dashboards import EnableDashboardRequest
from app.siem.schema.dashboards import EnabledDashboardOperationResponse
from app.siem.schema.dashboards import EnabledDashboardResponse
from app.siem.schema.dashboards import EnabledDashboardsListResponse
from app.siem.schema.dashboards import PanelDataRequest
from app.siem.schema.dashboards import PanelDataResponse
from app.siem.services.dashboards import disable_dashboard
from app.siem.services.dashboards import enable_dashboard
from app.siem.services.dashboards import get_category_detail
from app.siem.services.dashboards import get_enabled_dashboards
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


# ── Panel data (execute queries and return chart-ready data) ─────


@dashboards_router.post(
    "/panel-data",
    response_model=PanelDataResponse,
    description="Execute all panel queries for an enabled dashboard and return chart-ready data",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))],
)
async def panel_data_endpoint(
    request: PanelDataRequest,
    db: AsyncSession = Depends(get_db),
) -> PanelDataResponse:
    logger.info(f"Fetching panel data for dashboard {request.dashboard_id} (timerange={request.timerange})")
    data = await get_panel_data(request.dashboard_id, request.timerange, db)
    return PanelDataResponse(
        panels=data["results"],
        template=data["template"],
        dashboard_id=request.dashboard_id,
        accent_color=data["accent_color"],
        success=True,
        message="Panel data retrieved successfully",
    )
