from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.events import AlertQuery
from app.connectors.graylog.schema.events import GraylogAlertsResponse
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.connectors.graylog.services.events import get_alerts
from app.connectors.graylog.services.events import get_event_definitions

# App specific imports


graylog_events_router = APIRouter()


@graylog_events_router.get(
    "/event/definitions",
    response_model=GraylogEventDefinitionsResponse,
    description="Get all event definitions",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_event_definitions() -> GraylogEventDefinitionsResponse:
    logger.info("Fetching all graylog event definitions")
    return get_event_definitions()


@graylog_events_router.post(
    "/event/alerts",
    response_model=GraylogAlertsResponse,
    description="Get all alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts(alert_query: AlertQuery) -> GraylogAlertsResponse:
    logger.info("Fetching all graylog alerts")
    return get_alerts(alert_query)
