from typing import Any
from typing import Dict

from fastapi import HTTPException
from grafana_client import GrafanaApi
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def construct_grafana_url(connector_url: str, username: str, password: str, verify: bool = False) -> str:
    """
    Constructs a Grafana URL with embedded credentials.

    Args:
        connector_url (str): The base URL of the Grafana instance.
        username (str): Username for Grafana authentication.
        password (str): Password for Grafana authentication.
        verify (bool, optional): Whether to verify SSL certificates. Defaults to True.

    Returns:
        str: The complete Grafana URL with credentials.
    """
    if "http://" in connector_url:
        url = connector_url.replace("http://", f"http://{username}:{password}@")
    elif "https://" in connector_url:
        url = connector_url.replace("https://", f"https://{username}:{password}@")
    else:
        raise ValueError("Invalid connector URL format")

    # Add the verify parameter to the URL
    url += "?verify=" + str(verify).lower()

    return url


async def verify_grafana_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Grafana service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the Grafana connection to {attributes['connector_url']}")
    connector_url = attributes["connector_url"]
    username = attributes["connector_username"]
    password = attributes["connector_password"]

    grafana_url = await construct_grafana_url(connector_url, username, password, verify=False)

    grafana_client = GrafanaApi.from_url(grafana_url)
    try:
        create_user = grafana_client.admin.create_user(
            user={
                "name": "test",
                "email": "test@socfortress.co",
                "login": "test",
                "password": "this_is_a_test_user",
                "OrgID": 1,
            },
        )
        if create_user["message"] != "User created":
            raise Exception(f"Failed to create user: {create_user['message']}")

        grafana_client.admin.delete_user(
            user_id=create_user["id"],
        )

        logger.info(f"Connection to {grafana_url} successful")
        return {
            "connectionSuccessful": True,
            "message": "Grafana connection successful",
        }
    except Exception as e:
        logger.error(f"Connection to {grafana_url} failed with error: {e}")
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {grafana_url} failed with error: {e}",
        }


async def verify_grafana_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the Grafana service.

    Args:
        connector_name (str): The name of the Grafana connector.

    Returns:
        str: Authentication token for the Grafana service.

    Raises:
        None

    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    logger.info(f"Verifying the Grafana connection to {attributes['connector_url']}")
    if attributes is None:
        logger.error("No Grafana connector found in the database")
        return None
    return await verify_grafana_credentials(attributes)


async def create_grafana_client(connector_name: str) -> GrafanaApi:
    """
    Returns an GrafanaApi client for the Grafana service.

    Returns:
        GrafanaApi: GrafanaApi client for the Grafana service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(
            status_code=500,
            detail=f"No {connector_name} connector found in the database",
        )
    try:
        grafana_url = await construct_grafana_url(
            attributes["connector_url"],
            attributes["connector_username"],
            attributes["connector_password"],
            verify=False,
        )
        return GrafanaApi.from_url(grafana_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Grafana client: {e}",
        )
