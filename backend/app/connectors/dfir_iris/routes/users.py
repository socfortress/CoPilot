from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger

from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import User
from app.connectors.dfir_iris.schema.users import UsersResponse
from app.connectors.dfir_iris.services.users import assign_user_to_alert
from app.connectors.dfir_iris.services.users import get_users
from app.connectors.dfir_iris.utils.universal import check_alert_exists
from app.connectors.dfir_iris.utils.universal import check_user_exists


def verify_user_exists(user_id: int) -> int:
    if not check_user_exists(user_id):
        raise HTTPException(status_code=400, detail=f"User {user_id} does not exist.")
    return user_id


def verify_alert_exists(alert_id: str) -> str:
    if not check_alert_exists(alert_id):
        raise HTTPException(status_code=400, detail=f"Alert {alert_id} does not exist.")
    return alert_id


dfir_iris_users_router = APIRouter()


@dfir_iris_users_router.get("", response_model=UsersResponse, description="Get all users")
async def get_all_users() -> UsersResponse:
    logger.info("Fetching all users")
    return get_users()


@dfir_iris_users_router.post("/assign/{alert_id}/{user_id}", response_model=AlertResponse, description="Assign a user to an alert")
async def assign_user_to_alert_route(alert_id: str = Depends(verify_alert_exists), user_id: int = Depends(verify_user_exists)) -> User:
    logger.info(f"Assigning user {user_id} to alert {alert_id}")
    return assign_user_to_alert(alert_id, user_id)
