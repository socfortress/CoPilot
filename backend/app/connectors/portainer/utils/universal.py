from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import urljoin

import requests
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session
from app.db.universal_models import CustomersMeta


async def get_endpoint_id() -> int:
    """
    Returns the ID of the endpoint.
    """
    logger.info("Getting endpoint ID")
    list_endpoints = await send_get_request("/api/endpoints")

    for endpoint in list_endpoints["data"]:
        if endpoint["Name"] == "local":
            # Convert the ID to an integer
            return int(endpoint["Id"])
    return None


async def get_swarm_id() -> int:
    """
    Returns the ID of the swarm.
    """
    logger.info("Getting swarm ID")
    endpoint_id = await get_endpoint_id()
    logger.info(f"Endpoint ID: {endpoint_id}")
    swarm_id = await send_get_request(f"/api/endpoints/{endpoint_id}/docker/swarm")
    return swarm_id["data"]["ID"]


async def get_portainer_jwt() -> str:
    """Get JWT token from Portainer API."""
    logger.info("Getting portainer authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db("Portainer", session)
    try:
        auth_endpoint = urljoin(attributes["connector_url"], "/api/auth")

        auth_payload = {"username": attributes["connector_username"], "password": attributes["connector_password"]}

        response = requests.post(auth_endpoint, json=auth_payload, verify=False)  # If using self-signed cert

        response.raise_for_status()
        # The JWT token is in response.json()["jwt"]
        jwt_token = response.json()["jwt"]
        logger.info(f"Authenticated with Portainer. JWT token: {jwt_token}")
        return jwt_token

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to authenticate with Portainer: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


async def verify_portainer_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to portainer service by attempting both API key and JWT authentication.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and authentication details.
    """
    logger.info(
        f"Verifying the portainer connection to {attributes['connector_url']}",
    )
    try:
        # First try API key authentication
        headers = {
            "Authorization": f"Bearer {attributes['connector_api_key']}",
        }
        portainer_apps = requests.get(
            f"{attributes['connector_url']}/api/v1/apps/authentication",
            headers=headers,
            verify=False,
        )

        # If API key auth fails, try JWT authentication
        if portainer_apps.status_code != 200:
            auth_endpoint = urljoin(attributes["connector_url"], "/api/auth")
            auth_payload = {"username": attributes["connector_username"], "password": attributes["connector_password"]}

            jwt_response = requests.post(auth_endpoint, json=auth_payload, verify=False)

            if jwt_response.status_code == 200:
                jwt_token = jwt_response.json()["jwt"]
                logger.info("JWT authentication successful")
                return {
                    "connectionSuccessful": True,
                    "message": "Portainer connection successful via JWT",
                    "authMethod": "jwt",
                    "jwt": jwt_token,
                }
            else:
                logger.error(f"Both API key and JWT authentication failed. JWT error: {jwt_response.text}")
                return {"connectionSuccessful": False, "message": "Both API key and JWT authentication failed", "authMethod": None}

        logger.info(
            f"Connection to {attributes['connector_url']} successful via API key",
        )
        return {"connectionSuccessful": True, "message": "Portainer connection successful via API key", "authMethod": "api_key"}

    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
            "authMethod": None,
        }


async def verify_portainer_connection(connector_name: str) -> str:
    """
    Returns if connection to portainer service is successful.
    """
    logger.info("Getting portainer authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No portainer connector found in the database")
        return None
    return await verify_portainer_credentials(attributes)


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Portainer",
) -> Dict[str, Any]:
    """
    Sends a GET request to the portainer service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "portainer".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to {endpoint}")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No portainer connector found in the database")
        return None
    jwt_token = await get_portainer_jwt()
    try:
        HEADERS = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"Sending GET request to {attributes['connector_url']}{endpoint}")
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
    connector_name: str = "Portainer",
) -> Dict[str, Any]:
    """
    Sends a POST request to the portainer service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "portainer".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to {endpoint}")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No portainer connector found in the database")
        return None
    jwt_token = await get_portainer_jwt()

    try:
        HEADERS = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
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


async def send_delete_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    connector_name: str = "Portainer",
) -> Dict[str, Any]:
    """
    Sends a DELETE request to the Portainer service.

    Args:
        endpoint (str): The endpoint to send the DELETE request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the DELETE request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Portainer".

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    logger.info(f"Sending DELETE request to {endpoint}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No portainer connector found in the database")
        return None

    jwt_token = await get_portainer_jwt()
    try:
        HEADERS = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }
        response = requests.delete(
            f"{attributes['connector_url']}{endpoint}",
            headers=HEADERS,
            params=params,
            verify=False,
        )

        # Check if response is empty or not JSON
        if response.status_code == 204 or not response.text.strip():
            return {
                "data": None,
                "success": True,
                "message": "Successfully deleted resource",
            }

        try:
            return {
                "data": response.json(),
                "success": True,
                "message": "Successfully retrieved data",
            }
        except ValueError:
            # Response is not JSON
            return {
                "data": None,
                "success": True if response.status_code < 400 else False,
                "message": f"Delete operation completed with status code {response.status_code}",
            }

    except Exception as e:
        logger.error(f"Failed to send DELETE request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send DELETE request to {endpoint} with error: {e}",
        )


def send_put_request(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    connector_name: str = "portainer",
) -> Dict[str, Any]:
    """
    Sends a PUT request to the portainer service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Optional[Dict[str, Any]]): The data to send with the PUT request.
        connector_name (str, optional): The name of the connector to use. Defaults to "portainer".

    Returns:
        Dict[str, Any]: The response from the PUT request.
    """
    logger.info(f"Sending PUT request to {endpoint}")
    attributes = get_connector_info_from_db(connector_name)
    if attributes is None:
        logger.error("No portainer connector found in the database")
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


async def get_customer_portainer_stack_id(customer_name: str, session: AsyncSession) -> int:
    """
    Get the Portainer stack ID for a customer.

    Args:
        customer_name (str): The name of the customer.
        session (AsyncSession): The database session.

    Returns:
        int: The Portainer stack ID.

    Raises:
        HTTPException: If the customer is not found or has no stack ID
    """
    logger.info(f"Getting Portainer stack ID for customer {customer_name}")

    # Get customer metadata
    stmt = select(CustomersMeta).where(CustomersMeta.customer_name == customer_name)
    result = await session.execute(stmt)
    customer_meta = result.scalar_one_or_none()

    if customer_meta is None:
        logger.error(f"Customer {customer_name} not found in database")
        raise HTTPException(status_code=404, detail=f"Customer {customer_name} not found in database")

    if not customer_meta.customer_meta_portainer_stack_id:
        logger.error(f"No Portainer stack ID found for customer {customer_name}")
        raise HTTPException(status_code=404, detail=f"No Portainer stack ID found for customer {customer_name}")

    logger.info(f"Found Portainer stack ID {customer_meta.customer_meta_portainer_stack_id} for customer {customer_name}")
    return customer_meta.customer_meta_portainer_stack_id


async def update_customer_portainer_stack_id(customer_name: str, stack_id: int, session: AsyncSession) -> None:
    """
    Update the Portainer stack ID for a customer.

    Args:
        customer_name (str): The name of the customer.
        stack_id (int): The Portainer stack ID.
        session (AsyncSession): The database session.
    """
    logger.info(f"Updating Portainer stack ID for customer {customer_name} to {stack_id}")

    # Get customer metadata
    stmt = select(CustomersMeta).where(CustomersMeta.customer_name == customer_name)
    result = await session.execute(stmt)
    customer_meta = result.scalar_one_or_none()

    if customer_meta is None:
        logger.error(f"Customer {customer_name} not found in database")
        raise HTTPException(status_code=404, detail=f"Customer {customer_name} not found in database")

    customer_meta.customer_meta_portainer_stack_id = stack_id
    await session.commit()

    logger.info(f"Updated Portainer stack ID for customer {customer_name} to {stack_id}")
    return stack_id
