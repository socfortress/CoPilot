import os

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
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
from app.incidents.schema.velo_sigma import VeloSigmaExclusionCreate
from app.incidents.schema.velo_sigma import VeloSigmaExclusionListResponse
from app.incidents.schema.velo_sigma import VeloSigmaExclusionUpdate
from app.incidents.schema.velo_sigma import VeloSigmaExlcusionRouteResponse
from app.incidents.services.alert_collection import add_copilot_alert_id
from app.incidents.services.alert_collection import get_alerts_not_created_in_copilot
from app.incidents.services.alert_collection import get_graylog_event_indices
from app.incidents.services.alert_collection import get_original_alert_id
from app.incidents.services.alert_collection import get_original_alert_index_name
from app.incidents.services.incident_alert import create_alert
from app.incidents.services.incident_alert import create_alert_full
from app.incidents.services.incident_alert import get_single_alert_details
from app.incidents.services.incident_alert import retrieve_alert_timeline
from app.incidents.services.velo_sigma import VeloSigmaExclusionService
from app.incidents.services.velo_sigma import create_velo_sigma_alert

incidents_alerts_router = APIRouter()


# Function to validate the Velociraptor header
async def verify_velociraptor_header(velociraptor: str = Header(None)):
    """Verify that the request has the correct Velociraptor header."""
    # Get the header value from environment variable or use "ab73de7a-6f61-4dde-87cd-3af5175a7281" as default
    expected_header = os.getenv("VELOCIRAPTOR_API_HEADER_VALUE", "ab73de7a-6f61-4dde-87cd-3af5175a7281")

    if velociraptor != expected_header:
        logger.error("Invalid or missing Velociraptor header")
        raise HTTPException(status_code=403, detail="Invalid or missing Velociraptor header")
    return velociraptor


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


# @incidents_alerts_router.post(
#     "/create/auto",
#     response_model=CreateAlertResponse,
#     description="Is invoked by the scheduler to create an incident alert in CoPilot",
# )
# async def create_alert_auto_route(
#     session: AsyncSession = Depends(get_db),
# ) -> AutoCreateAlertResponse:
#     """
#     Create an incident alert in CoPilot. Automatically create an incident alert within CoPilot.
#     This queries the `gl-events-*` indices for alerts that have not been created in CoPilot.
#     It is important to note that Graylog must be configured for the alerts.

#     Args:
#         create_alert_request (CreateAlertRequest): The request object containing the details of the alert to be created.
#         session (AsyncSession, optional): The database session. Defaults to Depends(get_session).

#     Returns:
#         CreateAlertResponse: The response object containing the result of the alert creation.
#     """
#     alerts = await get_alerts_not_created_in_copilot()
#     logger.info(f"Alerts to create in CoPilot: {alerts}")
#     if len(alerts.alerts) == 0:
#         return AutoCreateAlertResponse(success=False, message="No alerts to create in CoPilot")

#     created_alerts_count = 0

#     for alert in alerts.alerts:
#         try:
#             logger.info(f"Creating alert {alert} in CoPilot")
#             create_alert_request = CreateAlertRequest(
#                 index_name=await get_original_alert_index_name(origin_context=alert.source.origin_context),
#                 alert_id=await get_original_alert_id(alert.source.origin_context),
#             )
#             logger.info(f"Creating alert {create_alert_request.alert_id} in CoPilot")
#             alert_id = await create_alert(create_alert_request, session)
#             # ! ADD THE COPILOT ALERT ID TO GRAYLOG EVENT INDEX # !
#             await add_copilot_alert_id(index_data=CreateAlertRequest(index_name=alert.index, alert_id=alert.id), alert_id=alert_id)
#             created_alerts_count += 1
#         except Exception as e:
#             logger.error(f"Failed to create alert {alert} in CoPilot: {e}")


@incidents_alerts_router.post(
    "/create/auto",
    response_model=AutoCreateAlertResponse,
    description="Is invoked by the scheduler to create an incident alert in CoPilot",
)
async def create_alert_auto_route(
    batch_size: int = Query(default=100, ge=10, le=500, description="Number of alerts to process per batch"),
    max_batches: int = Query(default=10, ge=1, le=50, description="Maximum number of batches to process in one run"),
    session: AsyncSession = Depends(get_db),
) -> AutoCreateAlertResponse:
    """
    Create incident alerts in CoPilot in batches. Automatically create incident alerts within CoPilot.
    This queries the `gl-events-*` indices for alerts that have not been created in CoPilot.

    Processing is done in batches to prevent memory issues with large numbers of alerts.
    The scheduler will call this endpoint multiple times until all alerts are processed.

    Args:
        batch_size: Number of alerts to process per batch (default 100, max 500)
        max_batches: Maximum number of batches to process in one scheduler run (default 10, max 50)
        session (AsyncSession): The database session.

    Returns:
        AutoCreateAlertResponse: The response object containing the result of the alert creation.
    """
    total_created = 0
    total_failed = 0
    batches_processed = 0

    logger.info(f"Starting auto alert creation with batch_size={batch_size}, max_batches={max_batches}")

    for batch_num in range(max_batches):
        # Fetch the next batch
        alerts_payload, total_remaining = await get_alerts_not_created_in_copilot(batch_size=batch_size)

        if len(alerts_payload.alerts) == 0:
            logger.info(f"No more alerts to process after {batches_processed} batches")
            break

        logger.info(f"Processing batch {batch_num + 1}/{max_batches}: {len(alerts_payload.alerts)} alerts.)")
        logger.info(f"Total remaining alerts after this batch: {total_remaining}")

        # Process this batch
        batch_created = 0
        batch_failed = 0

        for alert in alerts_payload.alerts:
            try:
                create_alert_request = CreateAlertRequest(
                    index_name=await get_original_alert_index_name(origin_context=alert.source.origin_context),
                    alert_id=await get_original_alert_id(alert.source.origin_context),
                )

                alert_id = await create_alert(create_alert_request, session)

                # Add the CoPilot alert ID to Graylog event index
                await add_copilot_alert_id(index_data=CreateAlertRequest(index_name=alert.index, alert_id=alert.id), alert_id=alert_id)

                batch_created += 1
                total_created += 1

            except Exception as e:
                logger.error(f"Failed to create alert {alert.id} from index {alert.index}: {e}")
                batch_failed += 1
                total_failed += 1

        batches_processed += 1
        logger.info(f"Batch {batch_num + 1} complete: {batch_created} created, {batch_failed} failed")

        # If we processed fewer alerts than the batch size, we're done
        if len(alerts_payload.alerts) < batch_size:
            logger.info("Processed final batch (fewer alerts than batch size)")
            break

    message = f"Processed {batches_processed} batches: {total_created} alerts created, {total_failed} failed"

    if total_remaining > 0:
        message += f". {total_remaining} alerts remaining for next run"

    logger.info(message)

    return AutoCreateAlertResponse(
        success=True,
        message=message,
        alerts_created=total_created,
        alerts_failed=total_failed,
        batches_processed=batches_processed,
        alerts_remaining=max(0, total_remaining - len(alerts_payload.alerts)) if batches_processed < max_batches else total_remaining,
    )


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
    4. ASSET_NAME: str - the name of the asset

    # ! IMPORTANT: DO NOT ADD THE "COPILOT_ALERT_ID": "NONE" AS A CUSTOM FIELD WHEN CREATING THE ALERT IN GRAYLOG # !
        # ! THIS WILL BREAK THE AUTO-ALERT CREATION FUNCTIONALITY # !

    # ! Make sure the Graylog Notification is just the standard HTTP Notification Type and not the Custom HTTP Notification Type !

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
            asset_payload=request.event.fields.ASSET_NAME,
            timefield_payload=str(request.event.timestamp),
            alert_title_payload=request.event.message,
            source=request.event.fields.SOURCE,
            index_name="not_applicable",
            index_id="not_applicable",
        ),
        customer_code=request.event.fields.CUSTOMER_CODE,
        session=session,
        threshold_alert=True,
    )
    return CreateAlertResponse(success=True, message="Alert threshold Graylog invoked successfully", alert_id=alert_id)


@incidents_alerts_router.post(
    "/create/velo-sigma",
    response_model=VelociraptorSigmaAlertResponse,
    description="Creates an incident alert in CoPilot for a Velociraptor Sigma alert",
    dependencies=[Depends(verify_velociraptor_header)],
)
async def process_sigma_alert(alert: VelociraptorSigmaAlert, session: AsyncSession = Depends(get_db)) -> VelociraptorSigmaAlertResponse:
    """
    This route receives a Velociraptor Sigma alert. You must have defined the Windows.Hayabusa.Monitoring
    client Event defined which will search for the Sigma alert in the Velociraptor client.
    When a Sigma alert is found, Velociraptor will us the `CoPilot.Events.Upload` to send a POST
    request to this endpoint with the alert data.

    An issue is that we want to fetch the wazuh event that is related to the Sigma alert so that we can
    create the alert within CoPilot accordingly. To do this we extract the `computer` as the `agent_name`
    and the `EventRecordID` as the `data_win_system_eventRecordID` and then query the Wazuh Indexer
    to fetch this sepcific event with a timeframe of 1 hour.

    Then we progress through the CoPilot Alert Creation process as normal.
    """
    logger.info(f"Processing Velociraptor Sigma alert: {alert}")
    return await create_velo_sigma_alert(alert, session)


@incidents_alerts_router.post(
    "/create/velo-sigma/exclusion",
    response_model=VeloSigmaExlcusionRouteResponse,
    summary="Create a new Velociraptor Sigma exclusion rule",
)
async def create_exclusion(
    exclusion: VeloSigmaExclusionCreate,
    current_user: str = Depends(AuthHandler().return_username_for_logging),
    db: AsyncSession = Depends(get_db),
):
    """Create a new exclusion rule for Velociraptor Sigma alerts."""
    # Set the created_by field to the current user
    logger.info(f"Current user: {current_user}")

    # Take only needed fields from exclusion, excluding created_by
    exclusion_dict = exclusion.dict(exclude={"created_by"})
    # Create a new exclusion with the current user
    updated_exclusion = VeloSigmaExclusionCreate(**exclusion_dict, created_by=current_user)

    # Log the exclusion data for debugging
    logger.info(f"Exclusion data: {updated_exclusion.dict()}")

    service = VeloSigmaExclusionService(db)
    # return await service.create_exclusion(updated_exclusion)
    return VeloSigmaExlcusionRouteResponse(
        success=True,
        message="Exclusion rule created successfully",
        exclusion_response=await service.create_exclusion(updated_exclusion),
    )


@incidents_alerts_router.get(
    "/create/velo-sigma/exclusion/{exclusion_id}",
    response_model=VeloSigmaExlcusionRouteResponse,
    summary="Get an exclusion rule by ID",
)
async def get_exclusion(
    exclusion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(AuthHandler().get_current_user),
):
    """Retrieve details of a specific exclusion rule."""
    service = VeloSigmaExclusionService(db)
    exclusion = await service.get_exclusion(exclusion_id)

    if not exclusion:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    return VeloSigmaExlcusionRouteResponse(
        success=True,
        message="Exclusion rule retrieved successfully",
        exclusion_response=exclusion,
    )


@incidents_alerts_router.get(
    "/create/velo-sigma/exclusion",
    response_model=VeloSigmaExclusionListResponse,
    summary="List all exclusion rules",
)
async def list_exclusions(
    skip: int = Query(0, description="Number of items to skip for pagination"),
    limit: int = Query(100, description="Maximum number of items to return"),
    enabled_only: bool = Query(False, description="Only return enabled exclusions"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(AuthHandler().get_current_user),
):
    """List all exclusion rules with pagination."""
    service = VeloSigmaExclusionService(db)

    # Get exclusions and total count
    exclusions, total_count = await service.list_exclusions_with_count(skip=skip, limit=limit, enabled_only=enabled_only)

    return VeloSigmaExclusionListResponse(
        success=True,
        message="Exclusion rules retrieved successfully",
        exclusions=exclusions,
        pagination={"total": total_count, "skip": skip, "limit": limit},
    )


@incidents_alerts_router.patch(
    "/create/velo-sigma/exclusion/{exclusion_id}",
    response_model=VeloSigmaExlcusionRouteResponse,
    summary="Update an exclusion rule",
)
async def update_exclusion(
    exclusion_id: int,
    exclusion: VeloSigmaExclusionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(AuthHandler().get_current_user),
):
    """Update an existing exclusion rule."""
    service = VeloSigmaExclusionService(db)
    updated = await service.update_exclusion(exclusion_id, exclusion.dict(exclude_unset=True))

    if not updated:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    # return updated
    return VeloSigmaExlcusionRouteResponse(
        success=True,
        message="Exclusion rule updated successfully",
        exclusion_response=updated,
    )


@incidents_alerts_router.delete("/create/velo-sigma/exclusion/{exclusion_id}", summary="Delete an exclusion rule")
async def delete_exclusion(
    exclusion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(AuthHandler().get_current_user),
):
    """Delete an exclusion rule."""
    service = VeloSigmaExclusionService(db)
    deleted = await service.delete_exclusion(exclusion_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    return {"message": "Exclusion rule deleted successfully", "success": True}


@incidents_alerts_router.post(
    "/velo-sigma/exclusion/{exclusion_id}/toggle",
    response_model=VeloSigmaExlcusionRouteResponse,
    summary="Toggle an exclusion rule's enabled status",
)
async def toggle_exclusion(
    exclusion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(AuthHandler().get_current_user),
):
    """Enable or disable an exclusion rule."""
    service = VeloSigmaExclusionService(db)
    exclusion = await service.get_exclusion(exclusion_id)

    if not exclusion:
        raise HTTPException(status_code=404, detail="Exclusion rule not found")

    # Toggle the enabled status
    updated = await service.update_exclusion(exclusion_id, {"enabled": not exclusion.enabled})
    # return updated
    return VeloSigmaExlcusionRouteResponse(
        success=True,
        message="Exclusion rule toggled successfully",
        exclusion_response=updated,
    )
