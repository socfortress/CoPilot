from typing import Any
from typing import Dict
from typing import Optional

import requests
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def verify_sublime_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Sublime service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(
        f"Verifying the Sublime connection to {attributes['connector_url']}",
    )
    try:
        headers = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
            "Content-Type": "application/json",
        }
        params = {
            "limit": 1,
        }
        sublime = requests.get(
            f"{attributes['connector_url']}/v0/rules",
            headers=headers,
            params=params,
            verify=False,
        )
        if sublime.status_code == 200:
            logger.info(
                f"Connection to {attributes['connector_url']} successful",
            )
            return {
                "connectionSuccessful": True,
                "message": "Sublime connection successful",
            }
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {sublime.text}",
            )
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed with error: {sublime.text}",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_sublime_connection(connector_name: str) -> str:
    """
    Returns if connection to Sublime service is successful.
    """
    logger.info("Getting Sublime authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Sublime connector found in the database")
        return None
    return await verify_sublime_credentials(attributes)


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Sublime",
) -> Dict[str, Any]:
    """
    Sends a GET request to the Sublime service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to {endpoint}")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Sublime connector found in the database")
        return None
    try:
        HEADERS = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            params=params,
            verify=False,
        )
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
