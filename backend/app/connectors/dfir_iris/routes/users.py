from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.alerts import AlertResponse
from app.connectors.dfir_iris.schema.users import User
from app.connectors.dfir_iris.schema.users import UserAddedToCustomerResponse
from app.connectors.dfir_iris.schema.users import UserRemovedFromCustomerResponse
from app.connectors.dfir_iris.schema.users import UsersResponse
from app.connectors.dfir_iris.services.users import assign_user_to_alert
from app.connectors.dfir_iris.services.users import delete_user_from_alert
from app.connectors.dfir_iris.services.users import get_users
from app.connectors.dfir_iris.utils.universal import add_user_to_customers
from app.connectors.dfir_iris.utils.universal import check_alert_exists
from app.connectors.dfir_iris.utils.universal import check_user_exists
from app.connectors.dfir_iris.utils.universal import collect_all_customers


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


@dfir_iris_users_router.post(
    "/add/{user_id}",
    response_model=AlertResponse,
    description="Add a user to a list of customers",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def add_user_to_customers_route(
    user_id: int,
) -> UserAddedToCustomerResponse:
    """
    Add a user to a list of customers.

    Parameters:
    - customers (List[str]): The list of customer IDs.
    - user_id (int): The ID of the user.

    Returns:
    - AlertResponse: The response containing the added user.

    Raises:
    - HTTPException: If the customer or user does not exist.
    """
    customers = await collect_all_customers()
    customer_ids = [str(customer["customer_id"]) for customer in customers]
    logger.info(f"Customer IDs: {customer_ids}")
    logger.info(f"Adding user {user_id} to customers {customer_ids}")
    success = await add_user_to_customers(customer_ids, user_id)
    if success:
        return UserAddedToCustomerResponse(message=f"User {user_id} added to customers {customers}", success=True)
    else:
        raise HTTPException(status_code=400, detail=f"Failed to add user {user_id} to customers {customers}")


@dfir_iris_users_router.delete(
    "/remove/{user_id}/{customer_id}",
    response_model=AlertResponse,
    description="Remove a user from a customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def remove_user_from_customer_route(
    user_id: int,
    customer_id: str,
) -> UserRemovedFromCustomerResponse:
    """
    Remove a user from a customer.

    Parameters:
    - customer_id (str): The ID of the customer.
    - user_id (int): The ID of the user.

    Returns:
    - AlertResponse: The response containing the removed user.

    Raises:
    - HTTPException: If the customer or user does not exist.
    """
    customers = await collect_all_customers()
    customer_ids = [str(customer["customer_id"]) for customer in customers]
    if customer_id in customer_ids:
        customer_ids.remove(customer_id)
    else:
        raise HTTPException(status_code=404, detail="Customer ID not found")
    logger.info(f"Customer IDs: {customer_ids}")
    logger.info(f"Removing user {user_id} from customers {customer_ids}")
    success = await add_user_to_customers(customer_ids, user_id)
    if success:
        return UserRemovedFromCustomerResponse(message=f"User {user_id} removed from customer {customer_id}", success=True)
    else:
        raise HTTPException(status_code=400, detail=f"Failed to remove user {user_id} from customer {customer_id}")


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
