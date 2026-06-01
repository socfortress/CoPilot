import time
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

import requests
from fastapi import HTTPException
from loguru import logger

from app.connectors.graylog.utils.routing import get_current_graylog_connector
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session

HEADERS = {"X-Requested-By": "CoPilot"}

# Cache of the detected Graylog major version, keyed by connector name.
# Graylog 7.0 introduced breaking changes to entity-creation POSTs (the
# CreateEntityRequest wrapper) and renamed urlwhitelist -> urlallowlist, so we
# branch on the server's major version. The short TTL lets an in-place Graylog
# upgrade be picked up without restarting CoPilot.
_GRAYLOG_VERSION_CACHE: Dict[str, Tuple[int, float]] = {}
_GRAYLOG_VERSION_TTL_SECONDS = 300


async def verify_graylog_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
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
            return {
                "connectionSuccessful": True,
                "message": "Graylog connection successful",
            }
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
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_graylog_connection(connector_name: str) -> str:
    """
    Returns if connection to Graylog service is successful.
    """
    logger.info("Getting Graylog authentication token")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Graylog connector found in the database")
        return None
    return await verify_graylog_credentials(attributes)


async def send_get_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    # connector_name: str = "Graylog",
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a GET request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the GET request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request.
        connector_name (Optional[str], optional): The name of the connector to use.
            If not provided, uses the current context or defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    # Use provided connector_name, or fall back to context-based resolution
    if connector_name is None:
        connector_name = get_current_graylog_connector()

    logger.info(f"Sending GET request to {endpoint} using connector: {connector_name}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(status_code=500, detail=f"Connector {connector_name} not found")
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
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send GET request to {endpoint} with error: {e}",
        )


async def send_post_request(
    endpoint: str,
    data: Dict[str, Any] = None,
    # connector_name: str = "Graylog",
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a POST request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (Optional[str], optional): The name of the connector to use.
            If not provided, uses the current context or defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    # Use provided connector_name, or fall back to context-based resolution
    if connector_name is None:
        connector_name = get_current_graylog_connector()

    logger.info(f"Sending POST request to {endpoint} using connector: {connector_name}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(status_code=500, detail=f"Connector {connector_name} not found")

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
        logger.info(
            f"Response from POST request: {response.status_code} {response.text}",
        )

        if response.status_code == 200:
            return {
                "data": response.json(),
                "success": True,
                "message": "Successfully completed request",
            }
        elif response.status_code == 204:
            return {
                "data": None,
                "success": True,
                "message": "Successfully completed request with no content",
            }
        elif response.status_code == 201:
            try:
                return {
                    "data": response.json(),
                    "success": True,
                    "message": "Successfully created data",
                }
            except ValueError:
                return {
                    "data": None,
                    "success": True,
                    "message": "Successfully created data, but no data returned",
                }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send POST request to {endpoint} with error: {response.json()['message']}",
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send POST request to {endpoint} with error: {e}",
        )


async def send_delete_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    # connector_name: str = "Graylog",
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a DELETE request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the DELETE request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the DELETE request.
        connector_name (Optional[str], optional): The name of the connector to use.
            If not provided, uses the current context or defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the DELETE request.
    """
    # Use provided connector_name, or fall back to context-based resolution
    if connector_name is None:
        connector_name = get_current_graylog_connector()

    logger.info(f"Sending DELETE request to {endpoint} using connector: {connector_name}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(status_code=500, detail=f"Connector {connector_name} not found")
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
        if response.status_code != 200 and response.status_code != 204:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to send DELETE request to {endpoint} with error: {response.json()['message']}",
            )
        return {
            "data": "No content returned",
            "success": True,
            "message": "Successfully deleted data",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to send DELETE request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send DELETE request to {endpoint} with error: {e}",
        }


async def send_put_request(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    # connector_name: str = "Graylog",
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a PUT request to the Graylog service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Optional[Dict[str, Any]], optional): The data to send with the PUT request.
        connector_name (Optional[str], optional): The name of the connector to use.
            If not provided, uses the current context or defaults to "Graylog".

    Returns:
        Dict[str, Any]: The response from the PUT request.
    """
    # Use provided connector_name, or fall back to context-based resolution
    if connector_name is None:
        connector_name = get_current_graylog_connector()

    logger.info(f"Sending PUT request to {endpoint} using connector: {connector_name}")
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
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
        logger.info(
            f"Response from PUT request: {response.status_code} {response.text}",
        )
        if response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to send PUT request to {endpoint} with error: {response.json().get('message', '')}",
            )
        if response.status_code == 204:
            return {
                "data": None,
                "success": True,
                "message": "Successfully sent PUT request, no content returned",
            }
        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to send PUT request to {endpoint} with error: {e}")
        return {
            "success": False,
            "message": f"Failed to send PUT request to {endpoint} with error: {e}",
        }


async def get_graylog_major_version(connector_name: Optional[str] = None) -> int:
    """
    Detects the major version of the configured Graylog server.

    Graylog 7.0 changed several entity-creation requests in a backwards-incompatible
    way (see ``send_post_request_create_entity``). Callers use this to build the
    correct request shape for the running server. The result is cached per connector
    for a short TTL.

    Falls back to major version ``6`` when the version cannot be determined, so
    existing Graylog 6.x deployments keep working unchanged.

    Args:
        connector_name (Optional[str]): The connector to probe. Falls back to the
            current context when not provided.

    Returns:
        int: The detected Graylog major version (e.g. ``6`` or ``7``).
    """
    if connector_name is None:
        connector_name = get_current_graylog_connector()

    cached = _GRAYLOG_VERSION_CACHE.get(connector_name)
    now = time.monotonic()
    if cached is not None and now - cached[1] < _GRAYLOG_VERSION_TTL_SECONDS:
        return cached[0]

    major = 6  # safe default — preserves pre-7.x behavior on detection failure
    try:
        response = await send_get_request(endpoint="/api/system", connector_name=connector_name)
        # version looks like "7.0.1+abc123" or "6.1.4"
        version_str = str(response["data"]["version"])
        major = int(version_str.split("+")[0].split(".")[0].strip())
    except Exception as e:
        logger.warning(
            f"Could not determine Graylog version for connector '{connector_name}', " f"defaulting to major version {major}: {e}",
        )

    _GRAYLOG_VERSION_CACHE[connector_name] = (major, now)
    logger.info(f"Detected Graylog major version {major} for connector '{connector_name}'")
    return major


async def send_post_request_create_entity(
    endpoint: str,
    entity: Dict[str, Any],
    share_request: Optional[Dict[str, Any]] = None,
    connector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends an entity-creation POST request, adapting the body to the Graylog version.

    Graylog 7.0 wraps entity-creation payloads in a ``CreateEntityRequest``
    (``{"entity": {...}, "share_request": {...}}``); Graylog 6.x expects the entity
    fields at the top level. Neither version accepts the other's shape, so this
    helper builds the correct body based on the detected server version, letting a
    single call site support both Graylog 6 and Graylog 7.

    Confirmed affected endpoints: ``POST /api/streams`` and content-pack installation
    (``POST /api/system/content_packs/{id}/{revision}/installations``). Index-set
    creation is NOT wrapped in either version and must keep using
    ``send_post_request`` directly.

    Args:
        endpoint (str): The entity-creation endpoint.
        entity (Dict[str, Any]): The entity fields (the flat Graylog 6.x body).
        share_request (Optional[Dict[str, Any]]): Optional Graylog 7.x sharing
            settings; omitted when ``None`` (it is nullable server-side).
        connector_name (Optional[str]): The connector to use. Falls back to context.

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    major = await get_graylog_major_version(connector_name)
    if major >= 7:
        body: Dict[str, Any] = {"entity": entity}
        if share_request is not None:
            body["share_request"] = share_request
    else:
        body = entity
    return await send_post_request(endpoint=endpoint, data=body, connector_name=connector_name)
