from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.influxdb.services.alerts import get_alerts
from app.connectors.utils import is_connector_verified
from app.db.db_session import get_db_session

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
    async with get_db_session() as session:
        if not await is_connector_verified("InfluxDB", session):
            logger.warning("InfluxDB connector is not verified; skipping alerts fetch.")
            return InfluxDBAlertsResponse(
                alerts=[],
                success=False,
                message="InfluxDB connector is not verified.",
            )
    return await get_alerts()
