import json
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.connectors.grafana.schema.dashboards import GrafanaDashboard
from app.connectors.grafana.schema.dashboards import GrafanaDashboardResponse
from app.connectors.grafana.schema.dashboards import WazuhDashboard
from app.connectors.grafana.utils.universal import create_grafana_client


def get_dashboard_path(dashboard_info: tuple) -> Path:
    """Returns the path to the dashboard JSON file."""
    folder_name, file_name = dashboard_info
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the 'grafana' directory
    return base_dir / "dashboards" / folder_name / file_name


def load_dashboard_json(dashboard_info: tuple) -> dict:
    file_path = get_dashboard_path(dashboard_info)
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"Dashboard JSON file not found at {file_path}")
        raise HTTPException(status_code=404, detail="Dashboard JSON file not found")
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from file")
        raise HTTPException(status_code=500, detail="Error decoding JSON from file")


async def update_dashboard(dashboard_json: dict) -> dict:
    try:
        grafana_client = await create_grafana_client("Grafana")
        dashboard_update_payload = {"dashboard": dashboard_json, "folderId": 0, "overwrite": True}
        return grafana_client.dashboard.update_dashboard(dashboard_update_payload)
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating dashboard: {e}")


async def provision_dashboards() -> GrafanaDashboardResponse:
    logger.info("Provisioning Grafana dashboards")

    provisioned_dashboards: List[GrafanaDashboard] = []
    errors = []

    for dashboard in WazuhDashboard:
        try:
            logger.info(f"Loading dashboard from {dashboard.value[1]} in folder {dashboard.value[0]}")
            dashboard_json = load_dashboard_json(dashboard.value)
            updated_dashboard = await update_dashboard(dashboard_json)
            logger.info(f"Successfully updated dashboard: {updated_dashboard}")
            provisioned_dashboards.append(GrafanaDashboard(**updated_dashboard))
        except HTTPException as e:
            error_message = f"Failed to update dashboard {dashboard.value[1]}: {e.detail}"
            logger.error(error_message)
            errors.append(error_message)
            raise HTTPException(status_code=500, detail=error_message)

    success = len(errors) == 0
    message = "All dashboards provisioned successfully" if success else "Some dashboards failed to provision"

    return GrafanaDashboardResponse(provisioned_dashboards=provisioned_dashboards, success=success, message=message)
