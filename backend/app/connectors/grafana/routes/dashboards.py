from typing import List

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from pathlib import Path
from loguru import logger
import json
import os

from app.auth.utils import AuthHandler
from app.connectors.grafana.utils.universal import create_grafana_client
from app.connectors.influxdb.utils.universal import create_influxdb_client
from app.connectors.wazuh_indexer.schema.alerts import AlertsByHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRulePerHostResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsByRuleResponse
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import AlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import HostAlertsSearchResponse
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchBody
from app.connectors.wazuh_indexer.schema.alerts import IndexAlertsSearchResponse
from app.connectors.wazuh_indexer.services.alerts import get_alerts
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_host
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule
from app.connectors.wazuh_indexer.services.alerts import get_alerts_by_rule_per_host
from app.connectors.wazuh_indexer.services.alerts import get_host_alerts
from app.connectors.wazuh_indexer.services.alerts import get_index_alerts
from app.connectors.wazuh_indexer.utils.universal import collect_indices

# App specific imports


grafana_dashboards_router = APIRouter()


@grafana_dashboards_router.get(
    "/dashboards",
    # response_model=InfluxDBAlertsResponse,
    description="Get influxdb alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_dashboard():
    logger.info("Updating Grafana dashboard")

    grafana_client = await create_grafana_client("Grafana")

    # ! GRAFANA DASHBOARD UID AND ID NEED TO BE NULL FOR THE DASHBOARD TO BE CREATED !

    # Construct the correct path to the dashboard JSON file
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up two levels to the 'grafana' directory
    dashboard_file_path = base_dir / 'dashboards' / 'edr_summary.json'
    logger.info(f"Correct path to the dashboard file: {dashboard_file_path}")

    # ! GRAFANA DASHBOARD UID AND ID NEED TO BE NULL FOR THE DASHBOARD TO BE CREATED !
    # Load the dashboard JSON from file
    try:
        with open(dashboard_file_path, 'r') as file:
            dashboard_json = json.load(file)
    except FileNotFoundError:
        logger.error("Dashboard JSON file not found")
        raise HTTPException(status_code=404, detail="Dashboard JSON file not found")
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from file")
        raise HTTPException(status_code=500, detail="Error decoding JSON from file")

    # ! GRAFANA DASHBOARD UID AND ID NEED TO BE NULL FOR THE DASHBOARD TO BE CREATED !

    # Prepare the dashboard update payload
    dashboard_update_payload = {
        "dashboard": dashboard_json,
        "folderId": 0,
        "overwrite": True
    }

    logger.info(f"Dashboard update payload: {dashboard_update_payload}")

    # ! GRAFANA DASHBOARD UID AND ID NEED TO BE NULL FOR THE DASHBOARD TO BE CREATED !

    # Update the dashboard
    try:
        #created_dashboard = grafana_client.dashboard.update_dashboard(dashboard={"dashboard": {"title": "LANDING"}, "folderId": 0, "overwrite": True})
        #logger.info(f"Dashboard created: {created_dashboard}")
        updated_dashboard = grafana_client.dashboard.update_dashboard(dashboard_update_payload)
        return updated_dashboard
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating dashboard: {e}")
