from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.grafana.services.reporting import get_dashboards
from app.connectors.grafana.services.reporting import get_orgs
from app.connectors.grafana.schema.reporting import GrafanaOrganizationsResponse, GrafanaDashboardResponse

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
    description="Get Grafana dashboards",
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
