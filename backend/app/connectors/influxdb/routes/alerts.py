from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.influxdb.services.alerts import get_alerts
from fastapi import APIRouter, Security
from loguru import logger

# App specific imports


influxdb_alerts_router = APIRouter()


@influxdb_alerts_router.get(
    "/alerts",
    response_model=InfluxDBAlertsResponse,
    description="Get influxdb alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts():
    """
    Fetches all alerts from InfluxDB.

    Returns:
        InfluxDBAlertsResponse: The response model containing the alerts.
    """
    logger.info("Fetching all alerts from influxdb")
    return await get_alerts()
