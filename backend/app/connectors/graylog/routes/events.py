from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.connectors.graylog.schema.events import AlertQuery
from app.connectors.graylog.schema.events import GraylogAlertsResponse
from app.connectors.graylog.schema.events import GraylogEventDefinitionsResponse
from app.connectors.graylog.services.events import get_alerts
from app.connectors.graylog.services.events import get_event_definitions
from app.connectors.graylog.services.events import keep_customer_events
from app.connectors.graylog.services.events import scoped_alert_query
from app.db.db_session import get_db
from app.middleware.document_access import scoped_codes

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
async def get_all_alerts(
    alert_query: AlertQuery,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GraylogAlertsResponse:
    """
    Fetches all graylog alerts based on the provided alert query.

    Args:
        alert_query (AlertQuery): The query parameters for filtering the alerts.

    Returns:
        GraylogAlertsResponse: The response containing the fetched alerts.
    """
    logger.info("Fetching all graylog alerts")
    codes = await scoped_codes(current_user, session)
    if codes is None:
        return await get_alerts(alert_query)
    # Graylog is asked for the caller's customers' events, and whatever comes back is checked again.
    query = scoped_alert_query(alert_query, codes) if codes else alert_query
    return keep_customer_events(await get_alerts(query), codes)
