from typing import Any
from typing import Dict
from typing import Optional

import requests
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import AsyncSessionLocal
from app.db.db_session import get_db_session


async def verify_wazuh_manager_credentials(
    attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verifies the connection to Wazuh manager service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(
        f"Verifying the wazuh-manager connection to {attributes['connector_url']}",
    )

    try:
        wazuh_auth_token = requests.get(
            f"{attributes['connector_url']}/security/user/authenticate",
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify=False,
        )

        if wazuh_auth_token.status_code == 200:
            logger.debug("Wazuh Authentication Token successful")
            return {
                "connectionSuccessful": True,
                "message": "Wazuh Manager authentication successful",
            }
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {wazuh_auth_token.text}",
            )

            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )

        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error.",
        }


async def verify_wazuh_manager_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the Wazuh manager service.

    Returns:
        str: Authentication token for the Wazuh manager service.
    """
    logger.info("Getting Wazuh Manager authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    return await verify_wazuh_manager_credentials(attributes)


async def create_wazuh_manager_client(connector_name: str) -> str:
    """
    Returns the authentication token for the Wazuh manager service.

    Returns:
        str: Authentication token for the Wazuh manager service.
    """
    logger.info("Getting Wazuh Manager authentication token")
    # attributes = get_connector_info_from_db(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    logger.info(
        f"Verifying the wazuh-manager connection to {attributes['connector_url']}",
    )
    try:
        wazuh_auth_token = requests.get(
            f"{attributes['connector_url']}/security/user/authenticate",
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify=False,
        )

        if wazuh_auth_token.status_code == 200:
            logger.debug("Wazuh Authentication Token successful")
            wazuh_auth_token = wazuh_auth_token.json()
            wazuh_auth_token = wazuh_auth_token["data"]["token"]

            return {"Authorization": f"Bearer {wazuh_auth_token}"}
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {wazuh_auth_token.text}",
            )

            return None
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )

        return None


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Wazuh-Manager",
) -> Dict[str, Any]:
    """
    Sends a GET request to the Wazuh Manager service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to {endpoint}")
    wazuh_manager_client = await create_wazuh_manager_client(connector_name)
    # attributes = get_connector_info_from_db(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)

    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    try:
        # if params is {"raw": True} then we want to return the raw response
        if params == {"raw": True}:
            response = requests.get(
                f"{attributes['connector_url']}/{endpoint}",
                headers=wazuh_manager_client,
                params=params,
                verify=False,
            )
            response.raise_for_status()
            return {
                "data": response.text,
                "success": True,
                "message": "Successfully retrieved data",
            }
        response = requests.get(
            f"{attributes['connector_url']}/{endpoint}",
            headers=wazuh_manager_client,
            params=params,
            verify=False,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send GET request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send GET request to {endpoint} with error: {e}",
        }


async def send_post_request(
    endpoint: str,
    data: Dict[str, Any],
    connector_name: str = "Wazuh-Manager",
) -> Dict[str, Any]:
    """
    Sends a POST request to the Wazuh Manager service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to {endpoint}")
    wazuh_manager_client = await create_wazuh_manager_client(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    try:
        response = requests.post(
            f"{attributes['connector_url']}/{endpoint}",
            headers=wazuh_manager_client,
            json=data,
            verify=False,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send POST request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send POST request to {endpoint} with error: {e}",
        }


async def send_put_request(
    endpoint: str,
    data: Optional[Dict[str, Any]],
    params: Optional[Dict[str, str]] = None,
    xml_data: Optional[bool] = False,
    binary_data: Optional[bool] = False,
    connector_name: str = "Wazuh-Manager",
) -> Dict[str, Any]:
    """
    Sends a PUT request to the Wazuh Manager service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Dict[str, Any]): The data to send with the PUT request.
        params (Optional[Dict[str, str]], optional): The parameters to send with the PUT request. Defaults to None.
        xml_data (Optional[bool], optional): Whether or not the data is XML. Defaults to False.
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

    Returns:
        Dict[str, Any]: The response from the PUT request.
    """
    logger.info(f"Sending PUT request to {endpoint}")
    wazuh_manager_client = await create_wazuh_manager_client(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    # Add the default `Content-Type` header to the request
    wazuh_manager_client["Content-Type"] = "application/json"
    # Add the `Content-Type` header to the request if the data is XML
    if xml_data:
        wazuh_manager_client["Content-Type"] = "application/xml"
    if binary_data:
        wazuh_manager_client["Content-Type"] = "application/octet-stream"
    try:
        logger.debug(f"Sending PUT request to {endpoint} with data: {data}")
        response = requests.put(
            f"{attributes['connector_url']}/{endpoint}",
            headers=wazuh_manager_client,
            params=params,
            data=data,
            verify=False,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send PUT request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send PUT request to {endpoint} with error: {e}",
        }


async def send_delete_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Wazuh-Manager",
) -> Dict[str, Any]:
    """
    Sends a DELETE request to the Wazuh Manager service.

    Args:
        endpoint (str): The endpoint to send the DELETE request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the DELETE request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    logger.info(f"Sending DELETE request to {endpoint}")
    wazuh_manager_client = await create_wazuh_manager_client(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    try:
        response = requests.delete(
            f"{attributes['connector_url']}/{endpoint}",
            headers=wazuh_manager_client,
            params=params,
            verify=False,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully deleted data",
        }
    except Exception as e:
        logger.error(f"Failed to send DELETE request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send DELETE request to {endpoint} with error: {e}",
        }


async def restart_service(connector_name: str = "Wazuh-Manager") -> Dict[str, Any]:
    """
    Restarts the Wazuh Manager service.

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    logger.info("Restarting Wazuh Manager service")
    wazuh_manager_client = await create_wazuh_manager_client(connector_name)
    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None
    try:
        response = requests.put(
            f"{attributes['connector_url']}/manager/restart",
            headers=wazuh_manager_client,
            verify=False,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully restarted service",
        }
    except Exception as e:
        logger.error(f"Failed to restart Wazuh Manager service with error: {e}")
        return {
            "success": False,
            "message": f"Failed to restart Wazuh Manager service with error: {e}",
        }
