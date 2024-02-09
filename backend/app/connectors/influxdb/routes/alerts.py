from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.influxdb.services.alerts import get_alerts

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
