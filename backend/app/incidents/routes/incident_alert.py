from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.routes.graylog import verify_graylog_header
from app.active_response.schema.graylog import GraylogThresholdEventNotification
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.schema.alert_collection import AlertsPayload
from app.incidents.schema.incident_alert import AlertDetailsResponse
from app.incidents.schema.incident_alert import AlertTimelineResponse
from app.incidents.schema.incident_alert import AutoCreateAlertResponse
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.schema.incident_alert import CreateAlertResponse
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.incident_alert import IndexNamesResponse
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlertResponse
from app.incidents.schema.velo_sigma import SysmonEvent
from app.incidents.schema.velo_sigma import DefenderEvent
from app.incidents.schema.velo_sigma import GenericEvent
from app.incidents.services.velo_sigma import create_velo_sigma_alert

from app.incidents.services.alert_collection import add_copilot_alert_id
from app.incidents.services.alert_collection import get_alerts_not_created_in_copilot
from app.incidents.services.alert_collection import get_graylog_event_indices
from app.incidents.services.alert_collection import get_original_alert_id
from app.incidents.services.alert_collection import get_original_alert_index_name
from app.incidents.services.incident_alert import create_alert
from app.incidents.services.incident_alert import create_alert_full
from app.incidents.services.incident_alert import get_single_alert_details
from app.incidents.services.incident_alert import retrieve_alert_timeline

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
        List[AlertPayloadItem]: The list of alerts that have not been created in CoPilot.
    """
    return await get_alerts_not_created_in_copilot()


@incidents_alerts_router.post(
    "/alert/details",
    description="Get the details of a single alert",
)
async def get_single_alert_details_route(
    create_alert_request: CreateAlertRequestRoute,
) -> AlertDetailsResponse:
    """
    Get the details of a single alert. Get the details of a single alert based on the alert id.
    Takes the alert id and the index name as input.

    Args:
        create_alert_request (CreateAlertRequestRoute): The request object containing the details of the alert to be created.

    Returns:
        class AlertDetailsResponse(BaseModel): The response object containing the details of the alert.
    """
    return AlertDetailsResponse(
        success=True,
        message="Alert details retrieved",
        alert_details=await get_single_alert_details(
            CreateAlertRequest(index_name=create_alert_request.index_name, alert_id=create_alert_request.index_id),
        ),
    )


@incidents_alerts_router.post(
    "/alert/timeline",
    description="Get the timeline of an alert",
)
async def get_alert_timeline_route(
    alert: CreateAlertRequestRoute,
    session: AsyncSession = Depends(get_db),
) -> AlertTimelineResponse:
    """
    Get the timeline of an alert. This route obtains the process_id from the alert details if it exists
    and queries the Indexer for all events with the same process_id and hostname within a 24 hour period.

    Args:
        create_alert_request (CreateAlertRequestRoute): The request object containing the details of the alert to be created.


    Returns:
        class AlertTimelineResponse(BaseModel): The response object containing the details of the alert.
    """
    # await retrieve_alert_timeline(alert, session)
    return AlertTimelineResponse(
        success=True,
        message="Alert timeline retrieved",
        alert_timeline=await retrieve_alert_timeline(alert, session),
    )


@incidents_alerts_router.post(
    "/create/manual",
    response_model=CreateAlertResponse,
    description="Manually create an incident alert in CoPilot",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_alert_manual_route(
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
    return CreateAlertResponse(success=True, message="Alert created in CoPilot", alert_id=await create_alert(create_alert_request, session))


@incidents_alerts_router.post(
    "/create/auto",
    response_model=CreateAlertResponse,
    description="Is invoked by the scheduler to create an incident alert in CoPilot",
)
async def create_alert_auto_route(
    session: AsyncSession = Depends(get_db),
) -> AutoCreateAlertResponse:
    """
    Create an incident alert in CoPilot. Automatically create an incident alert within CoPilot.
    This queries the `gl-events-*` indices for alerts that have not been created in CoPilot.
    It is important to note that Graylog must be configured for the alerts.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the details of the alert to be created.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_session).

    Returns:
        CreateAlertResponse: The response object containing the result of the alert creation.
    """
    alerts = await get_alerts_not_created_in_copilot()
    logger.info(f"Alerts to create in CoPilot: {alerts}")
    if len(alerts.alerts) == 0:
        return AutoCreateAlertResponse(success=False, message="No alerts to create in CoPilot")

    created_alerts_count = 0

    for alert in alerts.alerts:
        try:
            logger.info(f"Creating alert {alert} in CoPilot")
            create_alert_request = CreateAlertRequest(
                index_name=await get_original_alert_index_name(origin_context=alert.source.origin_context),
                alert_id=await get_original_alert_id(alert.source.origin_context),
            )
            logger.info(f"Creating alert {create_alert_request.alert_id} in CoPilot")
            alert_id = await create_alert(create_alert_request, session)
            # ! ADD THE COPILOT ALERT ID TO GRAYLOG EVENT INDEX # !
            await add_copilot_alert_id(index_data=CreateAlertRequest(index_name=alert.index, alert_id=alert.id), alert_id=alert_id)
            created_alerts_count += 1
        except Exception as e:
            logger.error(f"Failed to create alert {alert} in CoPilot: {e}")


@incidents_alerts_router.post(
    "/create/threshold",
    response_model=CreateAlertResponse,
    description="Creates an incident alert in CoPilot for a Graylog configured threshold alert",
    dependencies=[Depends(verify_graylog_header)],
)
async def invoke_alert_threshold_graylog_route(
    request: GraylogThresholdEventNotification,
    session: AsyncSession = Depends(get_db),
) -> CreateAlertResponse:
    """
    This route accepts an HTTP Post from Graylog for any threshold alerts which needs a dedicated route
    because there is no individual alert with an _id that we can use to grab from the
    wazuh-indexer.
    REQUIRED FILEDS:
    1. CUSTOMER_CODE: str - the customer code
    2. SOURCE: str - the source of the alert
    3. ALERT_DESCRIPTION: str - the description of the alert

    # ! IMPORTANT: DO NOT ADD THE "COPILOT_ALERT_ID": "NONE" AS A CUSTOM FIELD WHEN CREATING THE ALERT IN GRAYLOG # !
        # ! THIS WILL BREAK THE AUTO-ALERT CREATION FUNCTIONALITY # !

    Args:
        request (InvokeActiveResponseRequest): The request object containing the command, custom, arguments, and alert.

    Returns:
        CreateAlertResponse: The response object containing the result of the alert creation.
    """
    logger.info("Invoking alert threshold Graylog...")
    logger.info(f"Timestamp: {request.event.timestamp}")
    alert_id = await create_alert_full(
        alert_payload=CreatedAlertPayload(
            alert_context_payload=request.event.fields.dict(),
            asset_payload=request.event.source,
            timefield_payload=str(request.event.timestamp),
            alert_title_payload=request.event.message,
            source=request.event.fields.SOURCE,
            index_name="gl-events_",
            index_id=request.event.id,
        ),
        customer_code=request.event.fields.CUSTOMER_CODE,
        session=session,
        threshold_alert=True,
    )
    return CreateAlertResponse(success=True, message="Alert threshold Graylog invoked successfully", alert_id=alert_id)


@incidents_alerts_router.post("/create/velo-sigma", response_model=VelociraptorSigmaAlertResponse)
async def process_sigma_alert(alert: VelociraptorSigmaAlert, session: AsyncSession = Depends(get_db)) -> VelociraptorSigmaAlertResponse:
    """
    Process a Velociraptor Sigma alert based on its channel type.
    Args:
        alert: The original Sigma alert
        session: The database session
    Returns:
        VelociraptorSigmaAlertResponse: The response object containing the result of the alert creation
    """
    logger.info(f"Processing Velociraptor Sigma alert: {alert}")
    return await create_velo_sigma_alert(alert, session)
