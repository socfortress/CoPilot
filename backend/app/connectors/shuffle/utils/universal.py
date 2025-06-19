from typing import Any
from typing import Dict
from typing import Optional

import requests
from fastapi import HTTPException
from loguru import logger
from shufflepy import Singul

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def verify_shuffle_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Shuffle service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(
        f"Verifying the Shuffle connection to {attributes['connector_url']}",
    )
    try:
        headers = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        shuffle_apps = requests.get(
            f"{attributes['connector_url']}/api/v1/apps/authentication",
            headers=headers,
            verify=False,
        )
        if shuffle_apps.status_code == 200:
            logger.info(
                f"Connection to {attributes['connector_url']} successful",
            )
            return {
                "connectionSuccessful": True,
                "message": "Shuffle connection successful",
            }
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {shuffle_apps.text}",
            )
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed with error: {shuffle_apps.text}",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_shuffle_connection(connector_name: str) -> str:
    """
    Returns if connection to Shuffle service is successful.
    """
    logger.info("Getting Shuffle authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        return None
    return await verify_shuffle_credentials(attributes)


async def get_shuffle_org_id() -> Optional[str]:
    """
    Retrieves the organization ID from the Shuffle service.

    Returns:
        Optional[str]: The organization ID if found, otherwise None.
    """
    logger.info("Retrieving Shuffle organization ID")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db("Shuffle", session)
    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        return None

    return attributes.get("connector_extra_data", None)


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Shuffle",
) -> Dict[str, Any]:
    """
    Sends a GET request to the Shuffle service.

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
        logger.error("No Shuffle connector found in the database")
        return None
    logger.info(f"Attributes: {attributes}")
    try:
        HEADERS = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        response = requests.get(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            params=params,
            verify=False,
        )
        logger.info(f"Response from Shuffle API: {response.json()}")
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send GET request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send GET request to {endpoint} with error: {e}",
        )
        return {
            "success": False,
            "message": f"Failed to send GET request to {endpoint} with error: {e}",
        }


async def send_post_request(
    endpoint: str,
    data: Dict[str, Any] = None,
    connector_name: str = "Shuffle",
) -> Dict[str, Any]:
    """
    Sends a POST request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to {endpoint}")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        return None

    try:
        HEADERS = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        logger.info(f"Sending POST request to {attributes['connector_url']}{endpoint}")
        response = requests.post(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            json=data,
            verify=False,
        )

        if response.status_code == 204:
            return {
                "data": None,
                "success": True,
                "message": "Successfully completed request with no content",
            }
        else:
            return {
                "data": response.json(),
                "success": False if response.status_code >= 400 else True,
                "message": "Successfully retrieved data" if response.status_code < 400 else "Failed to retrieve data",
            }
    except Exception as e:
        logger.debug(f"Response: {response}")
        logger.error(f"Failed to send POST request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send POST request to {endpoint} with error: {e}",
        )
        return {
            "success": False,
            "message": f"Failed to send POST request to {endpoint} with error: {e}",
        }


def send_delete_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Shuffle",
) -> Dict[str, Any]:
    """
    Sends a DELETE request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the DELETE request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the DELETE request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    logger.info(f"Sending DELETE request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        return None
    try:
        HEADERS = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        response = requests.delete(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            params=params,
            verify=False,
        )
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send DELETE request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send DELETE request to {endpoint} with error: {e}",
        )
        return {
            "success": False,
            "message": f"Failed to send DELETE request to {endpoint} with error: {e}",
        }


def send_put_request(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    connector_name: str = "Shuffle",
) -> Dict[str, Any]:
    """
    Sends a PUT request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Optional[Dict[str, Any]]): The data to send with the PUT request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Dict[str, Any]: The response from the PUT request.
    """
    logger.info(f"Sending PUT request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        return None
    try:
        HEADERS = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        response = requests.put(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            json=data,
            verify=False,
        )
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.error(f"Failed to send PUT request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send PUT request to {endpoint} with error: {e}",
        )


async def get_singul_client(connector_name: str = "Shuffle") -> Singul:
    """
    Create and return a Singul client using database credentials.

    Args:
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Singul: An initialized Singul client instance.
    """
    logger.info("Creating Singul client from database credentials")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)

    if attributes is None:
        logger.error("No Shuffle connector found in the database")
        raise HTTPException(status_code=404, detail="Shuffle connector not found in database")

    try:
        singul_client = Singul(auth=attributes["connector_api_key"], url=attributes["connector_url"])
        logger.info(f"Singul client created successfully for {attributes['connector_url']}")
        return singul_client
    except Exception as e:
        logger.error(f"Failed to create Singul client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Singul client: {e}")
