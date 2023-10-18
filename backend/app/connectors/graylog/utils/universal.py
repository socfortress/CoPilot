from typing import Any
from typing import Dict
from typing import Optional

import requests
from fastapi import HTTPException
from loguru import logger

from app.connectors.utils import get_connector_info_from_db

HEADERS = {"X-Requested-By": "CoPilot"}


def verify_graylog_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Graylog service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(
        f"Verifying the graylog connection to {attributes['connector_url']}",
    )
    try:
        graylog_roles = requests.get(
            f"{attributes['connector_url']}/api/authz/roles/user/{attributes['connector_username']}",
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify=False,
        )
        if graylog_roles.status_code == 200:
            logger.info(
                f"Connection to {attributes['connector_url']} successful",
            )
            return {"connectionSuccessful": True, "message": "Graylog connection successful"}
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {graylog_roles.text}",
            )
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed with error: {graylog_roles.text}",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed with error: {e}"}


def verify_graylog_connection(connector_name: str) -> str:
    """
    Returns if connection to Graylog service is successful.
    """
    logger.info("Getting Graylog authentication token")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return None
    return verify_graylog_credentials(attributes)


def send_get_request(endpoint: str, params: Optional[Dict[str, Any]] = None, connector_name: str = "Graylog") -> Dict[str, Any]:
    """
    Sends a GET request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Graylogr".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return None
    try:
        response = requests.get(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            params=params,
            verify=False,
        )
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to send GET request to {endpoint} with error: {response.json()['message']}",
            )
        return {"data": response.json(), "success": True, "message": "Successfully retrieved data"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send GET request to {endpoint} with error: {e}")


def send_post_request(endpoint: str, data: Dict[str, Any] = None, connector_name: str = "Graylog") -> Dict[str, Any]:
    """
    Sends a POST request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return {"success": False, "message": "No Graylog connector found in the database"}

    try:
        response = requests.post(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            json=data,
            verify=False,
        )

        if response.status_code == 204:
            return {"data": None, "success": True, "message": "Successfully completed request with no content"}
        else:
            return {
                "data": response.json(),
                "success": False if response.status_code >= 400 else True,
                "message": "Successfully retrieved data" if response.status_code < 400 else "Failed to retrieve data",
            }
    except Exception as e:
        logger.debug(f"Response: {response}")
        logger.error(f"Failed to send POST request to {endpoint} with error: {e}")
        return {"success": False, "message": f"Failed to send POST request to {endpoint} with error: {e}"}


def send_delete_request(endpoint: str, params: Optional[Dict[str, Any]] = None, connector_name: str = "Graylog") -> Dict[str, Any]:
    """
    Sends a DELETE request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the DELETE request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the DELETE request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    logger.info(f"Sending DELETE request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return None
    try:
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
        return {"data": response.json(), "success": True, "message": "Successfully retrieved data"}
    except Exception as e:
        logger.error(f"Failed to send DELETE request to {endpoint} with error: {e}")
        return {"success": False, "message": f"Failed to send DELETE request to {endpoint} with error: {e}"}


def send_put_request(endpoint: str, data: Optional[Dict[str, Any]] = None, connector_name: str = "Graylog") -> Dict[str, Any]:
    """
    Sends a PUT request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Optional[Dict[str, Any]]): The data to send with the PUT request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the PUT request.
    """
    logger.info(f"Sending PUT request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return None
    try:
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
        return {"data": response.json(), "success": True, "message": "Successfully retrieved data"}
    except Exception as e:
        logger.error(f"Failed to send PUT request to {endpoint} with error: {e}")
        return {"success": False, "message": f"Failed to send PUT request to {endpoint} with error: {e}"}
