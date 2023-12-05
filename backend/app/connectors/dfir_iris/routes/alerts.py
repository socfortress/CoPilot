from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.alerts import AlertsResponse
from app.connectors.dfir_iris.schema.alerts import BookmarkedAlertsResponse
from app.connectors.dfir_iris.services.alerts import bookmark_alert
from app.connectors.dfir_iris.services.alerts import get_alert
from app.connectors.dfir_iris.services.alerts import get_alerts
from app.connectors.dfir_iris.services.alerts import get_bookmarked_alerts
from app.connectors.dfir_iris.utils.universal import check_alert_exists

# App specific imports


async def verify_alert_exists(alert_id: str) -> str:
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
    logger.info("Fetching all bookmarked alerts")
    return await get_bookmarked_alerts()


@dfir_iris_alerts_router.get(
    "",
    response_model=AlertsResponse,
    description="Get all alerts",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts() -> AlertsResponse:
    logger.info("Fetching all alerts")
    return await get_alerts()


@dfir_iris_alerts_router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    description="Get an alert by ID",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alert_by_id(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    logger.info(f"Fetching alert {alert_id}")
    return await get_alert(alert_id=alert_id)


@dfir_iris_alerts_router.get(
    "/alerts_by_user/{user_id}",
    response_model=AlertsResponse,
    description="Get all alerts assigned to a user",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_alerts_assigned_to_user(user_id: int) -> AlertsResponse:
    logger.info(f"Fetching all alerts assigned to user {user_id}")
    alerts = (await get_alerts()).alerts
    alerts_assigned_to_user = []
    for alert in alerts:
        if alert["alert_owner_id"] == user_id:
            alerts_assigned_to_user.append(alert)

    return AlertsResponse(success=True, message="Successfully fetched alerts assigned to user", alerts=alerts_assigned_to_user)


@dfir_iris_alerts_router.post(
    "/bookmark/{alert_id}",
    response_model=AlertResponse,
    description="Bookmark an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def bookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    logger.info(f"Bookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=True)


@dfir_iris_alerts_router.delete(
    "/bookmark/{alert_id}",
    response_model=AlertResponse,
    description="Unbookmark an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def unbookmark_alert_route(alert_id: str = Depends(verify_alert_exists)) -> AlertResponse:
    logger.info(f"Unbookmarking alert {alert_id}")
    return await bookmark_alert(alert_id, bookmarked=False)
