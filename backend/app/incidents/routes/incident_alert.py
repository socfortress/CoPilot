from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from typing import List
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertResponse, IndexNamesResponse
from app.incidents.services.incident_alert import create_alert
from app.incidents.schema.alert_collection import AlertsPayload, AlertPayloadItem
from app.connectors.wazuh_indexer.utils.universal import return_graylog_events_index_names
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.incidents.services.alert_collection import get_graylog_event_indices, get_alerts_not_created_in_copilot

incidents_alerts_router = APIRouter()


@incidents_alerts_router.get(
    "/index/names",
    response_model=IndexNamesResponse,
    description="Get the Graylog event indices",
)
async def get_index_names_route() -> IndexNamesResponse:
    """
    Get the Graylog event indices. Get the Graylog event indices for the Graylog events.

    Returns:
        List[str]: The list of Graylog event indices.
    """
    return await get_graylog_event_indices()

@incidents_alerts_router.get(
    "/alerts/not-created",
    description="Get alerts not created in CoPilot",
)
async def get_alerts_not_created_route() -> AlertsPayload:
    """
    Get alerts not created in CoPilot. Get all the results from the list of indices, where `copilot_alert_id` does not exist.

    Returns:
        List[dict]: The list of alerts not created in CoPilot.
    """
    #alerts = await get_alerts_not_created_in_copilot()
    #return alerts
    return await get_alerts_not_created_in_copilot()




@incidents_alerts_router.post(
    "/create/manual",
    response_model=CreateAlertResponse,
    description="Manually create an incident alert in CoPilot",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_alert_route(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession = Depends(get_db),
) -> CreateAlertResponse:
    """
    Create an incident alert in CoPilot. Manually create an incident alert within CoPilot.
    Used via the Alerts, for manual incident alert creation.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the details of the alert to be created.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_session).

    Returns:
        CreateAlertResponse: The response object containing the result of the alert creation.
    """
    logger.info(f"Creating alert {create_alert_request.alert_id} in CoPilot")
    return await create_alert(create_alert_request, session)
