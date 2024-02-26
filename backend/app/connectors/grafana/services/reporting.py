from fastapi import HTTPException
from loguru import logger
from typing import List

from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.grafana.schema.reporting import GrafanaOrganizations, GrafanaOrganizationDashboards, GrafanaDashboardDetails


async def get_orgs() -> List[GrafanaOrganizations]:
    """
    Update a dashboard in Grafana.

    Args:
        dashboard_json (dict): The updated dashboard JSON.
        organization_id (int): The ID of the organization.
        folder_id (int): The ID of the folder.

    Returns:
        dict: The updated dashboard response.

    Raises:
        HTTPException: If there is an error updating the dashboard.
    """
    logger.info("Getting organizations from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        orgs = grafana_client.organizations.list_organization()
        return orgs
    except Exception as e:
        logger.error(f"Failed to collect organizations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect organizations: {e}")


async def get_dashboards(org_id: int) -> List[GrafanaOrganizationDashboards]:
    """
    Get dashboards from Grafana.

    Returns:
        dict: The response containing the dashboards collected from Grafana.
    """
    logger.info("Getting dashboards from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        logger.info(f"Switching to organization {org_id}")
        grafana_client.user.switch_actual_user_organisation(org_id)
        dashboards = grafana_client.search.search_dashboards()
        return dashboards
    except Exception as e:
        logger.error(f"Failed to collect dashboards: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect dashboards: {e}")


async def get_dashboard_details(dashboard_uid: str) -> GrafanaDashboardDetails:
    """
    Get dashboard details from Grafana.

    Args:
        dashboard_uid (str): The UID of the dashboard.

    Returns:
        dict: The response containing the dashboard details collected from Grafana.
    """
    logger.info("Getting dashboard details from Grafana")
    try:
        grafana_client = await create_grafana_client("Grafana")
        dashboard_details = grafana_client.dashboard.get_dashboard(dashboard_uid)
        return dashboard_details
    except Exception as e:
        logger.error(f"Failed to collect dashboard details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect dashboard details: {e}")
