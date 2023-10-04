from typing import List
from fastapi import APIRouter, HTTPException, Security, Depends
from starlette.status import HTTP_401_UNAUTHORIZED
from loguru import logger
from datetime import timedelta
from typing import Union, Dict, Optional

# App specific imports
from app.auth.routes.auth import auth_handler
from app.db.db_session import session

from app.connectors.dfir_iris.schema.users import (
    UsersResponse, User
)

from app.connectors.dfir_iris.schema.alerts import (
    AlertResponse
)

from app.connectors.dfir_iris.services.users import get_users, assign_user_to_alert

from app.connectors.dfir_iris.utils.universal import check_user_exists, check_alert_exists


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
    logger.info(f"Fetching all users")
    return get_users()

@dfir_iris_users_router.post("/assign/{alert_id}/{user_id}", response_model=AlertResponse, description="Assign a user to an alert")
async def assign_user_to_alert_route(alert_id: str = Depends(verify_alert_exists), user_id: int = Depends(verify_user_exists)) -> User:
    logger.info(f"Assigning user {user_id} to alert {alert_id}")
    return assign_user_to_alert(alert_id, user_id)

