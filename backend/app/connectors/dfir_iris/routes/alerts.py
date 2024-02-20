from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertAssetsResponse
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse
from app.connectors.dfir_iris.schema.alerts import CaseCreationResponse
from app.connectors.dfir_iris.schema.alerts import DeleteAlertResponse
from app.connectors.dfir_iris.schema.alerts import DeleteMultipleAlertsRequest
from app.connectors.dfir_iris.schema.alerts import FilterAlertsRequest
from app.connectors.dfir_iris.schema.alerts import IrisAsset
from app.connectors.dfir_iris.services.alerts import bookmark_alert
from app.connectors.dfir_iris.services.alerts import create_case
from app.connectors.dfir_iris.services.alerts import delete_alert
from app.connectors.dfir_iris.services.alerts import get_alert
from app.connectors.dfir_iris.services.alerts import get_alerts
from app.connectors.dfir_iris.services.alerts import get_bookmarked_alerts
from app.connectors.dfir_iris.utils.universal import check_alert_exists
from app.db.db_session import get_db

# App specific imports


async def verify_alert_exists(alert_id: str) -> str:
    """
    Verifies if an alert with the given ID exists.

    Args:
        alert_id (str): The ID of the alert to verify.

    Returns:
        str: The ID of the alert if it exists.

    Raises:
        HTTPException: If the alert does not exist.
    """
    logger.info(f"Verifying alert {alert_id} exists")
    if not await check_alert_exists(alert_id):
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} does not exist.")
    return alert_id


dfir_iris_alerts_router = APIRouter()


@dfir_iris_alerts_router.get(
    "/bookmark",
    response_model=BookmarkedAlertsResponse,
    description="Get all bookmarked alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_bookmarked_alerts(
    session: AsyncSession = Depends(get_db),
) -> BookmarkedAlertsResponse:
    """
    Fetches all bookmarked alerts.

    Returns:
        BookmarkedAlertsResponse: The response containing the bookmarked alerts.
    """
    logger.info("Fetching all bookmarked alerts")
    return await get_bookmarked_alerts(session=session)


@dfir_iris_alerts_router.post(
    "",
    response_model=AlertsResponse,
    description="Get alerts from IRIS based on the provided filters",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alerts_filtered(
    request: FilterAlertsRequest,
    session: AsyncSession = Depends(get_db),
) -> AlertsResponse:
    """
    Retrieve alerts from DFIR-IRIS based on the provided filters.

    Returns:
        AlertsResponse: The response containing all alerts.
    """
    logger.info("Fetching all alerts")
    logger.info(f"Request: {request}")
    return await get_alerts(request, session=session)


@dfir_iris_alerts_router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    description="Get an alert by ID",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alert_by_id(
    alert_id: str = Depends(verify_alert_exists),
    session: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """
    Retrieve an alert by its ID.

    Args:
        alert_id (str): The ID of the alert to retrieve.

    Returns:
        AlertResponse: The response containing the alert information.
    """
    logger.info(f"Fetching alert {alert_id}")
    return await get_alert(alert_id=alert_id, session=session)


@dfir_iris_alerts_router.get(
    "/assets/{alert_id}",
    response_model=AlertAssetsResponse,
    description="Get all assets associated with an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_assets_by_alert_id(
    alert_id: str = Depends(verify_alert_exists),
    session: AsyncSession = Depends(get_db),
) -> AlertAssetsResponse:
    """
    Retrieve  the list of assets associated with an alert by its ID.

    Args:
        alert_id (str): The ID of the alert to retrieve.

    Returns:
        AlertResponse: The response containing the alert information.
    """
    logger.info(f"Fetching assets for alert {alert_id}")
    assets_data = (await get_alert(alert_id=alert_id, session=session)).alert["assets"]
    assets = [IrisAsset(**asset) for asset in assets_data]  # Parse the assets data into Asset objects
    return AlertAssetsResponse(
        success=True,
        message="Successfully fetched assets",
        assets=assets,
    )


@dfir_iris_alerts_router.get(
    "/alerts_by_user/{user_id}",
    response_model=AlertsResponse,
    description="Get all alerts assigned to a user",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_assigned_to_user(user_id: int, session: AsyncSession = Depends(get_db)) -> AlertsResponse:
    """
    Fetches all alerts assigned to a specific user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        AlertsResponse: The response containing the fetched alerts assigned to the user.
    """
    logger.info(f"Fetching all alerts assigned to user {user_id}")
    alerts = (
        await get_alerts(
            request=FilterAlertsRequest(alert_owner_id=user_id, per_page=1000),
            session=session,
        )
    ).alerts
    alerts_assigned_to_user = []
    for alert in alerts:
        if alert["alert_owner_id"] == user_id:
            alerts_assigned_to_user.append(alert)

    return AlertsResponse(
        success=True,
        message="Successfully fetched alerts assigned to user",
        alerts=alerts_assigned_to_user,
    )


@dfir_iris_alerts_router.post(
    "/create_case/{alert_id}",
    response_model=CaseCreationResponse,
    description="Assign an alert to a user",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_case_from_alert(
    alert_id: str = Depends(verify_alert_exists),
) -> CaseCreationResponse:
    """
    Create a case from an alert.

    Args:
        alert_id (str): The ID of the alert to create a case from.

    Returns:
        CaseCreationResponse: The response containing the created case.
    """
    logger.info(f"Creating case from alert {alert_id}")
    return await create_case(alert_id)


@dfir_iris_alerts_router.post(
    "/bookmark/{alert_id}",
    response_model=AlertResponse,
    description="Bookmark an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def bookmark_alert_route(
    alert_id: str = Depends(verify_alert_exists),
) -> AlertResponse:
    """
    Bookmark an alert.

    Args:
        alert_id (str): The ID of the alert to be bookmarked.

    Returns:
        DeleteAlertResponse: The response containing the bookmarked alert.
    """
    logger.info(f"Bookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=True)


@dfir_iris_alerts_router.delete(
    "/bookmark/{alert_id}",
    response_model=AlertResponse,
    description="Unbookmark an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def unbookmark_alert_route(
    alert_id: str = Depends(verify_alert_exists),
) -> AlertResponse:
    """
    Unbookmark an alert.

    Args:
        alert_id (str): The ID of the alert to unbookmark.

    Returns:
        AlertResponse: The response containing the unbookmarked alert.
    """
    logger.info(f"Unbookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=False)


@dfir_iris_alerts_router.post(
    "/delete_multiple",
    response_model=DeleteAlertResponse,
    description="Delete multiple alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_multiple_alerts_route(
    request: DeleteMultipleAlertsRequest,
) -> DeleteAlertResponse:
    """
    Delete multiple alerts.

    Args:
        request (DeleteMultipleAlertsRequest): The request containing the IDs of the alerts to delete.

    Returns:
        DeleteAlertResponse: The response containing the deleted alerts.
    """
    logger.info(f"Deleting alerts {request.alert_ids}")
    for alert_id in request.alert_ids:
        await verify_alert_exists(alert_id)
        await delete_alert(int(alert_id))
    return DeleteAlertResponse(success=True, message="Successfully deleted alerts.")


@dfir_iris_alerts_router.delete(
    "/purge",
    response_model=DeleteAlertResponse,
    description="Delete all alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def purge_alerts_route(
    session: AsyncSession = Depends(get_db),
) -> DeleteAlertResponse:
    """
    Delete all alerts.

    Returns:
        AlertResponse: The response containing the deleted alerts.
    """
    logger.info("Purging all alerts, up to 1000")
    alerts = (await get_alerts(request=FilterAlertsRequest(per_page=1000), session=session)).alerts
    for alert in alerts:
        await delete_alert(int(alert["alert_id"]))
    return DeleteAlertResponse(success=True, message="Successfully deleted alerts.")


@dfir_iris_alerts_router.delete(
    "/{alert_id}",
    response_model=DeleteAlertResponse,
    description="Delete an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_alert_route(
    alert_id: str = Depends(verify_alert_exists),
) -> DeleteAlertResponse:
    """
    Delete an alert.

    Args:
        alert_id (str): The ID of the alert to delete.

    Returns:
        AlertResponse: The response containing the deleted alert.
    """
    logger.info(f"Deleting alert {alert_id}")
    return await delete_alert(int(alert_id))
