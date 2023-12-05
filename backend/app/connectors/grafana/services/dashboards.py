import json
from pathlib import Path
from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.grafana.schema.dashboards import DashboardProvisionRequest
from app.connectors.grafana.schema.dashboards import GrafanaDashboard
from app.connectors.grafana.schema.dashboards import GrafanaDashboardResponse
from app.connectors.grafana.schema.dashboards import Office365Dashboard
from app.connectors.grafana.schema.dashboards import WazuhDashboard
from app.connectors.grafana.utils.universal import create_grafana_client


def get_dashboard_path(dashboard_info: tuple) -> Path:
    """Returns the path to the dashboard JSON file."""
    folder_name, file_name = dashboard_info
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the 'grafana' directory
    return base_dir / "dashboards" / folder_name / file_name


def load_dashboard_json(dashboard_info: tuple, datasource_uid: str) -> dict:
    file_path = get_dashboard_path(dashboard_info)
    try:
        with open(file_path, "r") as file:
            dashboard_data = json.load(file)

        # Search for 'uid' with 'wazuh_datasource_uid' and replace it
        replace_uid_value(dashboard_data, datasource_uid)

        return dashboard_data

    except FileNotFoundError:
        logger.error(f"Dashboard JSON file not found at {file_path}")
        raise HTTPException(status_code=404, detail="Dashboard JSON file not found")
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from file")
        raise HTTPException(status_code=500, detail="Error decoding JSON from file")


def replace_uid_value(obj, new_value, key_to_replace="uid", old_value="wazuh_datasource_uid"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key_to_replace and v == old_value:
                obj[k] = new_value
            elif isinstance(v, (dict, list)):
                replace_uid_value(v, new_value, key_to_replace, old_value)
    elif isinstance(obj, list):
        for item in obj:
            replace_uid_value(item, new_value, key_to_replace, old_value)


async def update_dashboard(dashboard_json: dict, organization_id: int, folder_id: int) -> dict:
    logger.info(f"Updating dashboards for organization {organization_id} and folder {folder_id}")
    try:
        grafana_client = await create_grafana_client("Grafana")
        # Switch to the newly created organization
        grafana_client.user.switch_actual_user_organisation(organization_id)
        logger.info(f"Updating dashboards for organization {organization_id} and folder {folder_id}")
        dashboard_update_payload = {"dashboard": dashboard_json, "folderId": folder_id, "overwrite": True}
        return grafana_client.dashboard.update_dashboard(dashboard_update_payload)
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating dashboard: {e}")


async def provision_dashboards(dashboard_request: DashboardProvisionRequest) -> GrafanaDashboardResponse:
    logger.info(f"Received dashboard provision request: {dashboard_request}")
    provisioned_dashboards = []
    errors = []

    valid_dashboards = {item.name: item for item in list(WazuhDashboard) + list(Office365Dashboard)}

    for dashboard_name in dashboard_request.dashboards:
        dashboard_enum = valid_dashboards[dashboard_name]
        try:
            dashboard_json = load_dashboard_json(dashboard_enum.value, datasource_uid=dashboard_request.datasourceUid)
            updated_dashboard = await update_dashboard(
                dashboard_json=dashboard_json,
                organization_id=dashboard_request.organizationId,
                folder_id=dashboard_request.folderId,
            )
            provisioned_dashboards.append(GrafanaDashboard(**updated_dashboard))
        except HTTPException as e:
            errors.append(f"Failed to update dashboard {dashboard_name}: {e.detail}")
            raise HTTPException(status_code=500, detail=f"Error updating dashboard: {e}")

    success = len(errors) == 0
    message = "All dashboards provisioned successfully" if success else "Some dashboards failed to provision"
    return GrafanaDashboardResponse(provisioned_dashboards=provisioned_dashboards, success=success, message=message)
