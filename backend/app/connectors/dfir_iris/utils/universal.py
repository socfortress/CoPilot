from typing import Any, Callable, Dict, Optional, Tuple, Union

import requests
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session
from dfir_iris_client.admin import AdminHelper
from dfir_iris_client.alert import Alert
from dfir_iris_client.case import Case
from dfir_iris_client.customer import Customer
from dfir_iris_client.helper.utils import assert_api_resp, get_data_from_resp
from dfir_iris_client.session import ClientSession
from dfir_iris_client.users import User
from fastapi import HTTPException
from loguru import logger


async def verify_dfir_iris_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to DFIR-IRIS service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the DFIR-IRIS connection to {attributes['connector_url']}")

    try:
        headers = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        dfir_iris = requests.get(
            f"{attributes['connector_url']}/api/ping",
            headers=headers,
            verify=False,
        )
        # See if 200 is returned
        if dfir_iris.status_code == 200:
            logger.info(
                f"Connection to {attributes['connector_url']} successful",
            )
        logger.debug("DFIR-IRIS connection successful")
        return {
            "connectionSuccessful": True,
            "message": "DFIR-IRIS connection successful",
        }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_dfir_iris_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the DFIR-IRIS service.

    Returns:
        str: Authentication token for the DFIR-IRIS service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No DFIR-IRIS connector found in the database")
        return None
    return await verify_dfir_iris_credentials(attributes)


async def create_dfir_iris_client(connector_name: str) -> ClientSession:
    """
    Creates a session with DFIR-IRIS.

    This method creates a session with DFIR-IRIS and returns a dictionary with a success status and the session object.
    If a session cannot be established, an error is logged and a dictionary with "success" set to False and an error message is
    returned.

    Returns:
        dict: A dictionary containing the success status and either the session object or an error message.
    """
    try:
        async with get_db_session() as session:  # This will correctly enter the context manager
            attributes = await get_connector_info_from_db(connector_name, session)
        logger.info("Creating session with DFIR-IRIS.")
        return ClientSession(
            host=attributes["connector_url"],
            apikey=attributes["connector_api_key"],
            agent="iris-client",
            ssl_verify=False,
            timeout=120,
            proxy=None,
        )
    except Exception as e:
        logger.error(f"Error creating session with DFIR-IRIS: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error creating session with DFIR-IRIS: {e}",
        )


async def fetch_and_parse_data(
    session: ClientSession, action: Callable, *args,
) -> Dict[str, Union[bool, Optional[Dict]]]:
    """
    Fetches and parses data from DFIR-IRIS using a specified action.

    Args:
        session (ClientSession): The DFIR-IRIS session object.
        action (Callable): The function to execute to fetch data from DFIR-IRIS. This function should accept *args.
        args: The arguments to pass to the action function.

    Returns:
        dict: A dictionary containing the success status and either the fetched data or None if the operation was unsuccessful.
    """
    try:
        logger.info(f"Executing {action.__name__}... on args: {args}")
        status = action(*args)
        assert_api_resp(status, soft_fail=False)
        data = get_data_from_resp(status)
        logger.info(f"Successfully executed {action.__name__}")
        return {"success": True, "data": data}
    except Exception as err:
        logger.error(f"Failed to execute {action.__name__}: {err}")
        raise HTTPException(
            status_code=500, detail=f"Failed to execute {action.__name__}: {err}",
        )


async def initialize_client_and_case(service_name: str) -> Tuple[Any, Case]:
    """
    Initializes the DFIR Iris client for case operations.

    Args:
        service_name (str): The name of the DFIR Iris service.

    Returns:
        Tuple[Any, Case]: A tuple containing the DFIR Iris client and the newly created case.
    """
    dfir_iris_client = await create_dfir_iris_client(service_name)
    case = Case(session=dfir_iris_client)
    return dfir_iris_client, case


async def initialize_client_and_alert(service_name: str) -> Tuple[Any, Alert]:
    """
    Initializes the DFIR Iris client for alert operations.

    Args:
        service_name (str): The name of the service.

    Returns:
        Tuple[Any, Alert]: A tuple containing the DFIR Iris client and the alert.
    """
    dfir_iris_client = await create_dfir_iris_client(service_name)
    alert = Alert(session=dfir_iris_client)
    return dfir_iris_client, alert


async def initialize_client_and_user(service_name: str) -> Tuple[Any, Alert]:
    """
    Initializes the DFIR Iris client for user operations.

    Args:
        service_name (str): The name of the service.

    Returns:
        Tuple[Any, Alert]: A tuple containing the DFIR Iris client and the user.
    """
    dfir_iris_client = await create_dfir_iris_client(service_name)
    user = User(session=dfir_iris_client)
    return dfir_iris_client, user


async def initialize_client_and_admin(service_name: str) -> Tuple[Any, Alert]:
    """
    Initializes the DFIR Iris client and admin helper.

    Args:
        service_name (str): The name of the service.

    Returns:
        Tuple[Any, Alert]: A tuple containing the DFIR Iris client and the admin helper.
    """
    dfir_iris_client = await create_dfir_iris_client(service_name)
    admin = AdminHelper(session=dfir_iris_client)
    return dfir_iris_client, admin


async def initialize_client_and_customer(service_name: str) -> Tuple[Any, Alert]:
    """
    Initializes the DFIR Iris client for customer operations.

    Args:
        service_name (str): The name of the service.

    Returns:
        Tuple[Any, Alert]: A tuple containing the DFIR Iris client and the customer.
    """
    dfir_iris_client = await create_dfir_iris_client(service_name)
    customer = Customer(session=dfir_iris_client)
    return dfir_iris_client, customer


def handle_error(error_message: str, status_code: int = 500):
    """
    Handles an error by logging the error message and raising an HTTPException.

    Args:
        error_message (str): The error message to be logged and included in the HTTPException detail.
        status_code (int, optional): The status code to be used in the HTTPException. Defaults to 500.
    """
    logger.error(error_message)
    raise HTTPException(status_code=status_code, detail=error_message)


async def fetch_and_validate_data(client: Any, func: Callable, *args: Any) -> Dict:
    """
    Fetches and validates data using the provided client, function, and arguments.

    Args:
        client (Any): The client object used to fetch the data.
        func (Callable): The function to be called to fetch the data.
        *args (Any): Variable length argument list for the function.

    Returns:
        Dict: The fetched and validated data.

    Raises:
        Exception: If the data fetching fails.
    """
    result = await fetch_and_parse_data(client, func, *args)
    if not result["success"]:
        handle_error(f"Failed to fetch data: {result['message']}")
    return result


async def check_case_exists(case_id: int) -> bool:
    """
    Check if a case exists in DFIR-IRIS.

    Args:
        case_id (int): The ID of the case to check.

    Returns:
        bool: True if the case exists, False otherwise.
    """
    try:
        logger.info(f"Checking if case {case_id} exists")
        dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
        case = Case(session=dfir_iris_client)
        data = case.get_case(case_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"Case {case_id} does not exist")
            return False
        logger.info(f"Case {case_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if case {case_id} exists: {e}")
        return False


async def check_alert_exists(alert_id: str) -> bool:
    """
    Check if an alert with the given ID exists.

    Args:
        alert_id (str): The ID of the alert to check.

    Returns:
        bool: True if the alert exists, False otherwise.
    """
    try:
        dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
    except Exception as e:
        logger.error(f"Failed to create DFIR-IRIS client: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create DFIR-IRIS client. Make sure the DFIR-IRIS connector is configured correctly.",
        )
    try:
        logger.info(f"Checking if alert {alert_id} exists")
        # dfir_iris_client = create_dfir_iris_client("DFIR-IRIS")
        alert = Alert(session=dfir_iris_client)
        data = alert.get_alert(alert_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"Alert {alert_id} does not exist")
            return False
        logger.info(f"Alert {alert_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if alert {alert_id} exists: {e}")
        return False


async def check_user_exists(user_id: int) -> bool:
    """
    Check if a user exists in the DFIR-IRIS system.

    Args:
        user_id (int): The ID of the user to check.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    try:
        logger.info(f"Checking if user {user_id} exists")
        dfir_iris_client = await create_dfir_iris_client("DFIR-IRIS")
        user = User(session=dfir_iris_client)
        data = user.get_user(user_id)
        assert_api_resp(data, soft_fail=False)
        result = get_data_from_resp(data)
        if result is None:
            logger.info(f"User {user_id} does not exist")
            return False
        logger.info(f"User {user_id} exists")
        return True
    except Exception as e:
        logger.error(f"Failed to check if user {user_id} exists: {e}")
        return False
