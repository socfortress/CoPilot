from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.events import (
    AlertQuery,
    GraylogAlertsResponse,
    GraylogEventDefinitionsResponse,
)
from app.connectors.graylog.services.events import get_alerts, get_event_definitions
from fastapi import APIRouter, Security
from loguru import logger

# App specific imports


graylog_events_router = APIRouter()


@graylog_events_router.get(
    "/event/definitions",
    response_model=GraylogEventDefinitionsResponse,
    description="Get all event definitions",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_event_definitions() -> GraylogEventDefinitionsResponse:
    """
    Fetches all graylog event definitions.

    Returns:
        GraylogEventDefinitionsResponse: The response containing all event definitions.
    """
    logger.info("Fetching all graylog event definitions")
    return await get_event_definitions()


@graylog_events_router.post(
    "/event/alerts",
    response_model=GraylogAlertsResponse,
    description="Get all alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts(alert_query: AlertQuery) -> GraylogAlertsResponse:
    """
    Fetches all graylog alerts based on the provided alert query.

    Args:
        alert_query (AlertQuery): The query parameters for filtering the alerts.

    Returns:
        GraylogAlertsResponse: The response containing the fetched alerts.
    """
    logger.info("Fetching all graylog alerts")
    return await get_alerts(alert_query)
