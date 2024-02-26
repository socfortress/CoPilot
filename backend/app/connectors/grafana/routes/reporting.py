from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.grafana.services.reporting import get_dashboards
from app.connectors.grafana.services.reporting import get_orgs

# App specific imports


grafana_reporting_router = APIRouter()


@grafana_reporting_router.get(
    "/orgs",
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
    return orgs


@grafana_reporting_router.get(
    "/dashboards",
    description="Get Grafana dashboards",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_grafana_dashboards():
    """
    Endpoint to get Grafana dashboards.

    Args:
        request (DashboardProvisionRequest): The request body containing the dashboard provisioning data.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    dashboards = await get_dashboards()
    return dashboards
