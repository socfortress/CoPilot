from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import User, UsersResponse
from app.connectors.dfir_iris.services.users import (
    assign_user_to_alert,
    delete_user_from_alert,
    get_users,
)
from app.connectors.dfir_iris.utils.universal import (
    check_alert_exists,
    check_user_exists,
)
from fastapi import APIRouter, Depends, HTTPException, Security
from loguru import logger


def verify_user_exists(user_id: int) -> int:
    """
    Verify if a user exists based on the provided user ID.

    Args:
        user_id (int): The ID of the user to verify.

    Returns:
        int: The verified user ID.

    Raises:
        HTTPException: If the user does not exist.
    """
    if not check_user_exists(user_id):
        raise HTTPException(status_code=400, detail=f"User {user_id} does not exist.")
    return user_id


async def verify_alert_exists(alert_id: str) -> str:
    """
    Verify if an alert exists based on the given alert ID.

    Args:
        alert_id (str): The ID of the alert to be verified.

    Returns:
        str: The verified alert ID.

    Raises:
        HTTPException: If the alert does not exist.
    """
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
    """
    Retrieves all users.

    Returns:
        UsersResponse: The response containing the list of users.
    """
    logger.info("Fetching all users")
    return await get_users()


@dfir_iris_users_router.post(
    "/assign/{alert_id}/{user_id}",
    response_model=AlertResponse,
    description="Assign a user to an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def assign_user_to_alert_route(
    alert_id: str = Depends(verify_alert_exists),
    user_id: int = Depends(verify_user_exists),
) -> User:
    """
    Assigns a user to an alert.

    Parameters:
    - alert_id (str): The ID of the alert.
    - user_id (int): The ID of the user.

    Returns:
    - User: The assigned user.

    Raises:
    - HTTPException: If the alert or user does not exist.
    """
    logger.info(f"Assigning user {user_id} to alert {alert_id}")
    return await assign_user_to_alert(alert_id, user_id)


@dfir_iris_users_router.delete(
    "/assign/{alert_id}/{user_id}",
    response_model=AlertResponse,
    description="Delete a user from an alert",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_user_from_alert_route(
    alert_id: str = Depends(verify_alert_exists),
    user_id: int = Depends(verify_user_exists),
) -> User:
    """
    Delete a user from an alert.

    Args:
        alert_id (str): The ID of the alert.
        user_id (int): The ID of the user.

    Returns:
        User: The deleted user.

    Raises:
        HTTPException: If the alert or user does not exist.
    """
    logger.info(f"Deleting user {user_id} from alert {alert_id}")
    return await delete_user_from_alert(alert_id, user_id)
