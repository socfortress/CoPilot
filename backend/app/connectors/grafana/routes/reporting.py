from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.grafana.services.reporting import get_dashboards
from app.connectors.grafana.services.reporting import get_orgs, get_dashboard_details
from app.connectors.grafana.schema.reporting import GrafanaOrganizationsResponse, GrafanaDashboardResponse, GrafanaDashboardDetailsResponse, Panel, GrafanaDashboardPanelsResponse

# App specific imports


grafana_reporting_router = APIRouter()


@grafana_reporting_router.get(
    "/orgs",
    response_model=GrafanaOrganizationsResponse,
    description="Provision Grafana dashboards",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_grafana_orgs():
    """
    Endpoint to provision Grafana dashboards.

    Args:
        request (DashboardProvisionRequest): The request body containing the dashboard provisioning data.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    logger.info("Getting Grafana orgs")
    orgs = await get_orgs()
    return GrafanaOrganizationsResponse(
        message="Organizations collected from Grafana",
        orgs=orgs,
        success=True,
    )


@grafana_reporting_router.get(
    "/dashboards/{org_id}",
    response_model=GrafanaDashboardResponse,
    description="Get Grafana dashboards for reporting",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_grafana_dashboards(org_id: int):
    """
    Endpoint to get Grafana dashboards.

    Args:
        org_id (int): The ID of the organization.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    dashboards = await get_dashboards(org_id=org_id)
    return GrafanaDashboardResponse(
        message="Dashboards collected from Grafana",
        dashboards=dashboards,
        success=True,
    )

@grafana_reporting_router.get(
    "/dashboard/{dashboard_uid}",
    response_model=GrafanaDashboardDetailsResponse,
    description="Get Grafana dashboard",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_grafana_dashboard_details(dashboard_uid: str):
    """
    Endpoint to get Grafana dashboard.

    Args:
        dashboard_uid (str): The UID of the dashboard.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    dashboard_details = await get_dashboard_details(dashboard_uid=dashboard_uid)

    return GrafanaDashboardDetailsResponse(
        message="Dashboard details collected from Grafana",
        dashboard_details=dashboard_details,
        success=True,
    )


@grafana_reporting_router.get(
    "/dashboard_panels/{dashboard_uid}",
    response_model=GrafanaDashboardPanelsResponse,
    description="Get Grafana dashboard panels",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_grafana_dashboard_panels(dashboard_uid: str):
    """
    Endpoint to get Grafana dashboard panels.

    Args:
        dashboard_uid (str): The UID of the dashboard.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    dashboard_details = await get_dashboard_details(dashboard_uid=dashboard_uid)
    logger.info(f"Dashboard details: {dashboard_details}")

    # Get the panel id and panel title from the dashboard details for each panel
    panels = []
    logger.info("Fetching panels from dashboard details")
    for panel in dashboard_details['dashboard']['panels']:
        if panel["type"] != "row":
            panels.append(Panel(id=panel["id"], title=panel["title"]))
    logger.info(f"Panels: {panels}")
    return GrafanaDashboardPanelsResponse(
        message="Panels collected from Grafana",
        panels=panels,
        success=True,
    )


