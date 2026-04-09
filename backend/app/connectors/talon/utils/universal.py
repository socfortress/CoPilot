from typing import Any
from typing import Dict
from typing import Optional

import requests
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def verify_talon_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to the Talon service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status.
    """
    logger.info(f"Verifying the Talon connection to {attributes['connector_url']}")
    try:
        response = requests.get(
            f"{attributes['connector_url']}/health",
            verify=False,
            timeout=10,
        )
        if response.status_code == 200:
            logger.info(f"Connection to {attributes['connector_url']} successful")
            return {
                "connectionSuccessful": True,
                "message": "Talon connection successful",
            }
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with status: {response.status_code}",
            )
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed with status {response.status_code}",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_talon_connection(connector_name: str = "Talon") -> Dict[str, Any]:
    """
    Verifies the connection to the Talon service using stored connector credentials.

    Args:
        connector_name (str): The name of the connector. Defaults to "Talon".

    Returns:
        Dict[str, Any]: Connection verification result.
    """
    logger.info("Verifying Talon connection")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Talon connector found in the database")
        return None
    return await verify_talon_credentials(attributes)


def _build_headers(api_key: str) -> Dict[str, str]:
    """Build request headers with API key authentication."""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Talon",
) -> Dict[str, Any]:
    """
    Sends a GET request to the Talon service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Talon".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to Talon {endpoint}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Talon connector found in the database")
        return {
            "success": False,
            "message": "No Talon connector found in the database",
        }
    try:
        headers = _build_headers(attributes["connector_api_key"])
        response = requests.get(
            f"{attributes['connector_url']}{endpoint}",
            headers=headers,
            params=params,
            verify=False,
            timeout=30,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send GET request to Talon {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send GET request to {endpoint} with error: {e}",
        }


async def send_post_request(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    connector_name: str = "Talon",
) -> Dict[str, Any]:
    """
    Sends a POST request to the Talon service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Optional[Dict[str, Any]]): The data to send with the POST request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Talon".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to Talon {endpoint}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Talon connector found in the database")
        return {
            "success": False,
            "message": "No Talon connector found in the database",
        }
    try:
        headers = _build_headers(attributes["connector_api_key"])
        response = requests.post(
            f"{attributes['connector_url']}{endpoint}",
            headers=headers,
            json=data,
            verify=False,
            timeout=120,
        )
        response.raise_for_status()
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send POST request to Talon {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send POST request to {endpoint} with error: {e}",
        }


async def send_post_request_sse(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    connector_name: str = "Talon",
):
    """
    Sends a POST request to the Talon service and yields SSE chunks as they arrive.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Optional[Dict[str, Any]]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Talon".

    Yields:
        str: Raw SSE lines from the upstream response.
    """
    logger.info(f"Sending streaming POST request to Talon {endpoint}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Talon connector found in the database")
        yield "data: {\"error\": \"No Talon connector found in the database\"}\n\n"
        return
    try:
        headers = _build_headers(attributes["connector_api_key"])
        with requests.post(
            f"{attributes['connector_url']}{endpoint}",
            headers=headers,
            json=data,
            verify=False,
            stream=True,
            timeout=120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if line is not None:
                    yield f"{line}\n"
    except Exception as e:
        logger.error(f"Failed to stream from Talon {endpoint} with error: {e}")
        yield f"data: {{\"error\": \"Failed to stream from {endpoint}\"}}\n\n"
