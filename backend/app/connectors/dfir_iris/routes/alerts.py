from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse, FilterAlertsRequest, CaseCreationResponse
from app.connectors.dfir_iris.services.alerts import bookmark_alert
from app.connectors.dfir_iris.services.alerts import get_alert
from app.connectors.dfir_iris.services.alerts import get_alerts
from app.connectors.dfir_iris.services.alerts import create_case
from app.connectors.dfir_iris.services.alerts import get_bookmarked_alerts
from app.connectors.dfir_iris.utils.universal import check_alert_exists

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
async def get_all_bookmarked_alerts() -> BookmarkedAlertsResponse:
    """
    Fetches all bookmarked alerts.

    Returns:
        BookmarkedAlertsResponse: The response containing the bookmarked alerts.
    """
    logger.info("Fetching all bookmarked alerts")
    return await get_bookmarked_alerts()


@dfir_iris_alerts_router.post(
    "",
    response_model=AlertsResponse,
    description="Get alerts from IRIS based on the provided filters",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alerts_filtered(request: FilterAlertsRequest) -> AlertsResponse:
    """
    Retrieve alerts from DFIR-IRIS based on the provided filters.

    Returns:
        AlertsResponse: The response containing all alerts.
    """
    logger.info("Fetching all alerts")
    return await get_alerts(request)


@dfir_iris_alerts_router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    description="Get an alert by ID",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alert_by_id(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    """
    Retrieve an alert by its ID.

    Args:
        alert_id (str): The ID of the alert to retrieve.

    Returns:
        AlertResponse: The response containing the alert information.
    """
    logger.info(f"Fetching alert {alert_id}")
    return await get_alert(alert_id=alert_id)


@dfir_iris_alerts_router.get(
    "/alerts_by_user/{user_id}",
    response_model=AlertsResponse,
    description="Get all alerts assigned to a user",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_assigned_to_user(user_id: int) -> AlertsResponse:
    """
    Fetches all alerts assigned to a specific user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        AlertsResponse: The response containing the fetched alerts assigned to the user.
    """
    logger.info(f"Fetching all alerts assigned to user {user_id}")
    alerts = (await get_alerts(request=FilterAlertsRequest(alert_owner_id=user_id,per_page=1000))).alerts
    alerts_assigned_to_user = []
    for alert in alerts:
        if alert["alert_owner_id"] == user_id:
            alerts_assigned_to_user.append(alert)

    return AlertsResponse(success=True, message="Successfully fetched alerts assigned to user", alerts=alerts_assigned_to_user)

@dfir_iris_alerts_router.post(
    "/create_case/{alert_id}",
    response_model=CaseCreationResponse,
    description="Assign an alert to a user",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_case_from_alert(alert_id: str = Depends(verify_alert_exists)) -> CaseCreationResponse:
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
async def bookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    """
    Bookmark an alert.

    Args:
        alert_id (str): The ID of the alert to be bookmarked.

    Returns:
        AlertResponse: The response containing the bookmarked alert.
    """
    logger.info(f"Bookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=True)


@dfir_iris_alerts_router.delete(
    "/bookmark/{alert_id}",
    response_model=AlertResponse,
    description="Unbookmark an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def unbookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    """
    Unbookmark an alert.

    Args:
        alert_id (str): The ID of the alert to unbookmark.

    Returns:
        AlertResponse: The response containing the unbookmarked alert.
    """
    logger.info(f"Unbookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=False)
