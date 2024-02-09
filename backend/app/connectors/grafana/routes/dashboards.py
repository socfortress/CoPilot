from fastapi import APIRouter
from fastapi import Body
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.schema.dashboards import GrafanaDashboardResponse
from app.connectors.grafana.services.dashboards import provision_dashboards

# App specific imports


grafana_dashboards_router = APIRouter()


@grafana_dashboards_router.post(
    "/dashboards",
    response_model=GrafanaDashboardResponse,
    description="Provision Grafana dashboards",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_dashboards_route(request: DashboardProvisionRequest = Body(...)):
    """
    Endpoint to provision Grafana dashboards.

    Args:
        request (DashboardProvisionRequest): The request body containing the dashboard provisioning data.

    Returns:
        GrafanaDashboardResponse: The response containing the result of the dashboard provisioning.
    """
    logger.info("Provisioning Grafana dashboards")
    provision = await provision_dashboards(request)
    return provision
