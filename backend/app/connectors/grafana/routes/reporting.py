from fastapi import APIRouter
from fastapi import Security
from loguru import logger
from typing import List
from fastapi import Depends
from datetime import datetime, timedelta
import time

from app.auth.utils import AuthHandler
from app.connectors.grafana.services.reporting import get_dashboards
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.db_session import get_db
from app.connectors.models import Connectors
from app.connectors.grafana.services.reporting import get_orgs, get_dashboard_details
from app.connectors.grafana.schema.reporting import GrafanaOrganizationsResponse, GrafanaDashboardResponse, GrafanaDashboardDetailsResponse, Panel, GrafanaDashboardPanelsResponse, GrafanaGenerateIframeLinksRequest, GrafanaGenerateIframeLinksResponse, TimeRange, GrafanaLinksList

# App specific imports


grafana_reporting_router = APIRouter()

async def get_grafana_url(session: AsyncSession):
    connector = await session.execute(select(Connectors).where(Connectors.connector_name == "Grafana"))
    connector = connector.scalars().first()
    return connector.connector_url

def calculate_unix_timestamps(time_range: TimeRange):
    now = datetime.now()
    if time_range.unit == "minutes":
        start_time = now - timedelta(minutes=time_range.value)
    elif time_range.unit == "hours":
        start_time = now - timedelta(hours=time_range.value)
    elif time_range.unit == "days":
        start_time = now - timedelta(days=time_range.value)

    timestamp_from = int(time.mktime(start_time.timetuple())) * 1000
    timestamp_to = int(time.mktime(now.timetuple())) * 1000

    return timestamp_from, timestamp_to


def generate_panel_urls(grafana_url: str, request: GrafanaGenerateIframeLinksRequest, timestamp_from: int, timestamp_to: int):
    panel_links: List[GrafanaLinksList] = []
    for panel_id in request.panel_ids:
        panel_url = f"{grafana_url}/d-solo/{request.dashboard_uid}/{request.dashboard_title}?orgId={request.org_id}&from={timestamp_from}&to={timestamp_to}&panelId={panel_id}"
        panel_links.append(GrafanaLinksList(panel_id=panel_id, panel_url=panel_url))
    return panel_links

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


@grafana_reporting_router.post(
    "/generate_iframe_links",
    response_model=GrafanaGenerateIframeLinksResponse,
    description="Generate Grafana dashboard iframe links",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def generate_grafana_iframe_links(request: GrafanaGenerateIframeLinksRequest, session: AsyncSession = Depends(get_db),):
    """
    Endpoint to generate Grafana dashboard iframe links.

    Args:
        request (GrafanaGenerateIframeLinksRequest): The request body containing the dashboard UID and organization ID.

    Returns:
        GrafanaDashboardPanelsResponse: The response containing the result of the dashboard provisioning.
    """
    # get the Grafana URL from the database
    grafana_url = await get_grafana_url(session)
    logger.info(f"Grafana URL: {grafana_url}")

    # calculate the Unix timestamps based on the current time and the provided time range
    timestamp_from, timestamp_to = calculate_unix_timestamps(request.time_range)

    # build the URL string for each panel_id
    panel_urls = generate_panel_urls(grafana_url, request, timestamp_from, timestamp_to)

    return GrafanaGenerateIframeLinksResponse(
        message="Iframe links generated from Grafana",
        links=panel_urls,
        success=True,
    )

