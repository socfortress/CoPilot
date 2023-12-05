from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import User
from app.connectors.dfir_iris.schema.users import UsersResponse
from app.connectors.dfir_iris.services.users import assign_user_to_alert
from app.connectors.dfir_iris.services.users import delete_user_from_alert
from app.connectors.dfir_iris.services.users import get_users
from app.connectors.dfir_iris.utils.universal import check_alert_exists
from app.connectors.dfir_iris.utils.universal import check_user_exists


def verify_user_exists(user_id: int) -> int:
    if not check_user_exists(user_id):
        raise HTTPException(status_code=400, detail=f"User {user_id} does not exist.")
    return user_id


async def verify_alert_exists(alert_id: str) -> str:
    if not await check_alert_exists(alert_id):
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} does not exist.")
    return alert_id


dfir_iris_users_router = APIRouter()


@dfir_iris_users_router.get(
    "",
    response_model=UsersResponse,
    description="Get all users",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_users() -> UsersResponse:
    logger.info("Fetching all users")
    return await get_users()


@dfir_iris_users_router.post(
    "/assign/{alert_id}/{user_id}",
    response_model=AlertResponse,
    description="Assign a user to an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def assign_user_to_alert_route(alert_id: str = Depends(verify_alert_exists), user_id: int = Depends(verify_user_exists)) -> User:
    logger.info(f"Assigning user {user_id} to alert {alert_id}")
    return await assign_user_to_alert(alert_id, user_id)


@dfir_iris_users_router.delete(
    "/assign/{alert_id}/{user_id}",
    response_model=AlertResponse,
    description="Delete a user from an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_user_from_alert_route(alert_id: str = Depends(verify_alert_exists), user_id: int = Depends(verify_user_exists)) -> User:
    logger.info(f"Deleting user {user_id} from alert {alert_id}")
    return await delete_user_from_alert(alert_id, user_id)
