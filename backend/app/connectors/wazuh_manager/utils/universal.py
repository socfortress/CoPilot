import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from typing import Dict
from typing import Optional

import requests
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import AsyncSessionLocal
from app.db.db_session import get_db_session

# =============================================================================
# Token Cache Implementation
# =============================================================================

@dataclass
class CachedToken:
    """Cached authentication token with expiration"""
    token: str
    expires_at: datetime
    connector_url: str


class WazuhTokenCache:
    """
    Thread-safe cache for Wazuh Manager authentication tokens.

    Caches tokens per connector name to support multiple Wazuh Manager instances.
    Default TTL is 10 minutes (Wazuh tokens typically expire after 15-30 minutes).
    """

    def __init__(self, default_ttl_minutes: int = 10):
        self._cache: Dict[str, CachedToken] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = timedelta(minutes=default_ttl_minutes)

    async def get(self, connector_name: str) -> Optional[Dict[str, str]]:
        """
        Get cached token headers if valid.

        Returns:
            Dict with Authorization header if token is valid, None otherwise
        """
        async with self._lock:
            if connector_name not in self._cache:
                return None

            cached = self._cache[connector_name]

            # Check if token is expired (with 30 second buffer)
            if datetime.utcnow() >= (cached.expires_at - timedelta(seconds=30)):
                logger.debug(f"Cached token for {connector_name} has expired")
                del self._cache[connector_name]
                return None

            logger.debug(f"Using cached token for {connector_name}")
            return {"Authorization": f"Bearer {cached.token}"}

    async def set(
        self,
        connector_name: str,
        token: str,
        connector_url: str,
        ttl_minutes: Optional[int] = None
    ):
        """Cache a new token"""
        async with self._lock:
            ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else self._default_ttl
            expires_at = datetime.utcnow() + ttl

            self._cache[connector_name] = CachedToken(
                token=token,
                expires_at=expires_at,
                connector_url=connector_url,
            )
            logger.debug(
                f"Cached token for {connector_name}, expires at {expires_at.isoformat()}"
            )

    async def invalidate(self, connector_name: str):
        """Remove cached token for a connector"""
        async with self._lock:
            if connector_name in self._cache:
                del self._cache[connector_name]
                logger.debug(f"Invalidated cached token for {connector_name}")

    async def clear(self):
        """Clear all cached tokens"""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cleared all cached Wazuh tokens")


# Global token cache instance
_token_cache = WazuhTokenCache(default_ttl_minutes=10)


# =============================================================================
# Public Cache Management Functions
# =============================================================================

async def invalidate_wazuh_token_cache(connector_name: str = "Wazuh-Manager"):
    """
    Invalidate cached token for a connector.

    Call this when credentials are updated or if you receive auth errors.
    """
    await _token_cache.invalidate(connector_name)


# ============================================================================
# Existing Wazuh Manager Utility Functions
# ============================================================================

async def clear_all_wazuh_token_caches():
    """Clear all cached Wazuh tokens"""
    await _token_cache.clear()

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


# async def create_wazuh_manager_client(connector_name: str) -> str:
#     """
#     Returns the authentication token for the Wazuh manager service.

#     Returns:
#         str: Authentication token for the Wazuh manager service.
#     """
#     logger.info("Getting Wazuh Manager authentication token")
#     # attributes = get_connector_info_from_db(connector_name)
#     async with AsyncSessionLocal() as session:
#         attributes = await get_connector_info_from_db(connector_name, session)
#     if attributes is None:
#         logger.error("No Wazuh Manager connector found in the database")
#         return None
#     logger.info(
#         f"Verifying the wazuh-manager connection to {attributes['connector_url']}",
#     )
#     try:
#         wazuh_auth_token = requests.get(
#             f"{attributes['connector_url']}/security/user/authenticate",
#             auth=(
#                 attributes["connector_username"],
#                 attributes["connector_password"],
#             ),
#             verify=False,
#         )

#         if wazuh_auth_token.status_code == 200:
#             logger.debug("Wazuh Authentication Token successful")
#             wazuh_auth_token = wazuh_auth_token.json()
#             wazuh_auth_token = wazuh_auth_token["data"]["token"]

#             return {"Authorization": f"Bearer {wazuh_auth_token}"}
#         else:
#             logger.error(
#                 f"Connection to {attributes['connector_url']} failed with error: {wazuh_auth_token.text}",
#             )

#             return None
#     except Exception as e:
#         logger.error(
#             f"Connection to {attributes['connector_url']} failed with error: {e}",
#         )

#         return None

async def create_wazuh_manager_client(connector_name: str) -> Optional[Dict[str, str]]:
    """
    Returns the authentication token headers for the Wazuh manager service.

    Uses cached token if available and valid, otherwise fetches a new one.

    Returns:
        Dict with Authorization header, or None if authentication fails
    """
    # Check cache first
    cached_headers = await _token_cache.get(connector_name)
    if cached_headers is not None:
        return cached_headers

    logger.info(f"Fetching new Wazuh Manager authentication token for {connector_name}")

    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)

    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return None

    logger.info(
        f"Authenticating to wazuh-manager at {attributes['connector_url']}",
    )

    try:
        response = requests.get(
            f"{attributes['connector_url']}/security/user/authenticate",
            auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify=False,
        )

        if response.status_code == 200:
            logger.debug("Wazuh Authentication Token successful")
            token_data = response.json()
            token = token_data["data"]["token"]

            # Cache the token
            await _token_cache.set(
                connector_name=connector_name,
                token=token,
                connector_url=attributes['connector_url'],
            )

            return {"Authorization": f"Bearer {token}"}
        else:
            logger.error(
                f"Connection to {attributes['connector_url']} failed with error: {response.text}",
            )
            return None

    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return None


# async def send_get_request(
#     endpoint: str,
#     params: Optional[Dict[str, Any]] = None,
#     connector_name: str = "Wazuh-Manager",
# ) -> Dict[str, Any]:
#     """
#     Sends a GET request to the Wazuh Manager service.

#     Args:
#         endpoint (str): The endpoint to send the GET request to.
#         params (Optional[Dict[str, Any]], optional): The parameters to send with the GET request. Defaults to None.
#         connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

#     Returns:
#         Dict[str, Any]: The response from the GET request.
#     """
#     logger.info(f"Sending GET request to {endpoint}")
#     wazuh_manager_client = await create_wazuh_manager_client(connector_name)
#     # attributes = get_connector_info_from_db(connector_name)
#     async with AsyncSessionLocal() as session:
#         attributes = await get_connector_info_from_db(connector_name, session)

#     if attributes is None:
#         logger.error("No Wazuh Manager connector found in the database")
#         return None
#     try:
#         # Check if raw response is requested - support both old and new ways
#         # Old way: params == {"raw": True} (exact match for backward compatibility)
#         # New way: params contains "raw": True (for requests with multiple parameters)
#         is_raw_request = (params == {"raw": True}) or (params and params.get("raw", False))

#         if is_raw_request:
#             response = requests.get(
#                 f"{attributes['connector_url']}{endpoint}",
#                 headers=wazuh_manager_client,
#                 params=params,
#                 verify=False,
#             )
#             response.raise_for_status()
#             return {
#                 "data": response.text,
#                 "success": True,
#                 "message": "Successfully retrieved data",
#             }
#         response = requests.get(
#             f"{attributes['connector_url']}{endpoint}",
#             headers=wazuh_manager_client,
#             params=params,
#             verify=False,
#         )
#         response.raise_for_status()
#         return {
#             "data": response.json(),
#             "success": True,
#             "message": "Successfully retrieved data",
#         }
#     except Exception as e:
#         logger.error(f"Failed to send GET request to {endpoint} with error: {e}")
#         return {
#             "success": False,
#             "message": f"Failed to send GET request to {endpoint} with error: {e}",
#         }

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

    if wazuh_manager_client is None:
        logger.error("Failed to get Wazuh Manager client")
        return {
            "success": False,
            "message": "Failed to authenticate with Wazuh Manager",
        }

    async with AsyncSessionLocal() as session:
        attributes = await get_connector_info_from_db(connector_name, session)

    if attributes is None:
        logger.error("No Wazuh Manager connector found in the database")
        return {
            "success": False,
            "message": "No Wazuh Manager connector found in the database",
        }

    try:
        is_raw_request = (params == {"raw": True}) or (params and params.get("raw", False))

        if is_raw_request:
            response = requests.get(
                f"{attributes['connector_url']}{endpoint}",
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
            f"{attributes['connector_url']}{endpoint}",
            headers=wazuh_manager_client,
            params=params,
            verify=False,
        )

        # Handle 401 Unauthorized - token may have expired on server side
        if response.status_code == 401:
            logger.warning("Received 401 Unauthorized, invalidating cached token and retrying")
            await _token_cache.invalidate(connector_name)

            # Retry with fresh token
            wazuh_manager_client = await create_wazuh_manager_client(connector_name)
            if wazuh_manager_client is None:
                return {
                    "success": False,
                    "message": "Failed to re-authenticate with Wazuh Manager",
                }

            response = requests.get(
                f"{attributes['connector_url']}{endpoint}",
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
            f"{attributes['connector_url']}{endpoint}",
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


# async def send_put_request(
#     endpoint: str,
#     data: Optional[Dict[str, Any]],
#     params: Optional[Dict[str, str]] = None,
#     xml_data: Optional[bool] = False,
#     binary_data: Optional[bool] = False,
#     connector_name: str = "Wazuh-Manager",
# ) -> Dict[str, Any]:
#     """
#     Sends a PUT request to the Wazuh Manager service.

#     Args:
#         endpoint (str): The endpoint to send the PUT request to.
#         data (Dict[str, Any]): The data to send with the PUT request.
#         params (Optional[Dict[str, str]], optional): The parameters to send with the PUT request. Defaults to None.
#         xml_data (Optional[bool], optional): Whether or not the data is XML. Defaults to False.
#         connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

#     Returns:
#         Dict[str, Any]: The response from the PUT request.
#     """
#     logger.info(f"Sending PUT request to {endpoint}")
#     wazuh_manager_client = await create_wazuh_manager_client(connector_name)
#     async with AsyncSessionLocal() as session:
#         attributes = await get_connector_info_from_db(connector_name, session)
#     if attributes is None:
#         logger.error("No Wazuh Manager connector found in the database")
#         return None
#     # Add the default `Content-Type` header to the request
#     wazuh_manager_client["Content-Type"] = "application/json"
#     # Add the `Content-Type` header to the request if the data is XML
#     if xml_data:
#         wazuh_manager_client["Content-Type"] = "application/xml"
#     if binary_data:
#         wazuh_manager_client["Content-Type"] = "application/octet-stream"
#     try:
#         logger.debug(f"Sending PUT request to {endpoint} with data: {data}")
#         response = requests.put(
#             f"{attributes['connector_url']}{endpoint}",
#             headers=wazuh_manager_client,
#             params=params,
#             data=data,
#             verify=False,
#         )
#         response.raise_for_status()
#         return {
#             "data": response.json(),
#             "success": True,
#             "message": "Successfully retrieved data",
#         }
#     except Exception as e:
#         logger.error(f"Failed to send PUT request to {endpoint} with error: {e}")
#         return {
#             "success": False,
#             "message": f"Failed to send PUT request to {endpoint} with error: {e}",
#         }


async def send_put_request(
    endpoint: str,
    data: Optional[Dict[str, Any]],
    params: Optional[Dict[str, str]] = None,
    xml_data: Optional[bool] = False,
    binary_data: Optional[bool] = False,
    connector_name: str = "Wazuh-Manager",
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Sends a PUT request to the Wazuh Manager service.

    Args:
        endpoint (str): The endpoint to send the PUT request to.
        data (Dict[str, Any]): The data to send with the PUT request.
        params (Optional[Dict[str, str]], optional): The parameters to send with the PUT request. Defaults to None.
        xml_data (Optional[bool], optional): Whether or not the data is XML. Defaults to False.
        binary_data (Optional[bool], optional): Whether or not the data is binary. Defaults to False.
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".
        debug (bool, optional): Whether to enable detailed debug logging. Defaults to False.

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

    # Enhanced debugging
    if debug:
        logger.debug(f"Request URL: {attributes['connector_url']}{endpoint}")
        logger.debug(f"Request headers: {wazuh_manager_client}")
        logger.debug(f"Request params: {params}")
        logger.debug(f"Request data: {data}")

    try:
        logger.debug(f"Sending PUT request to {endpoint} with data: {data}")

        response = requests.put(
            f"{attributes['connector_url']}{endpoint}",
            headers=wazuh_manager_client,
            params=params,
            data=data,
            verify=False,
        )

        # Log response details before checking status
        if debug:
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
            try:
                logger.debug(f"Response body: {response.text}")
            except Exception as e:  # Specify Exception instead of bare except
                logger.debug(f"Could not parse response body: {str(e)}")

        # Handle HTTP errors with detailed logging
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            error_detail = ""
            try:
                error_json = response.json()
                if isinstance(error_json, dict):
                    # Extract Wazuh API specific error details
                    if "detail" in error_json:
                        error_detail = error_json["detail"]
                    elif "message" in error_json:
                        error_detail = error_json["message"]
                    elif "data" in error_json and "detail" in error_json["data"]:
                        error_detail = error_json["data"]["detail"]
            except (ValueError, json.JSONDecodeError) as e:  # Specify exceptions instead of bare except
                # If can't parse JSON, use text response
                error_detail = response.text
                logger.debug(f"Could not parse JSON response: {str(e)}")

            logger.error(f"HTTP error {response.status_code}: {error_detail}")
            return {
                "success": False,
                "status_code": response.status_code,
                "message": f"HTTP error {response.status_code}: {error_detail}",
                "error_detail": error_detail,
                "raw_response": response.text,
            }

        return {
            "data": response.json(),
            "success": True,
            "message": "Successfully retrieved data",
        }
    except Exception as e:
        logger.exception(f"Failed to send PUT request to {endpoint}")
        return {"success": False, "message": f"Failed to send PUT request to {endpoint} with error: {str(e)}", "exception": str(e)}


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
            f"{attributes['connector_url']}{endpoint}",
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


async def get_cluster_status(connector_name: str = "Wazuh-Manager") -> Dict[str, Any]:
    """
    Retrieves the cluster status of the Wazuh Manager service.

    Args:
        connector_name (str, optional): The name of the connector to use. Defaults to "Wazuh-Manager".

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info("Getting Wazuh Manager cluster status")
    return await send_get_request(
        endpoint="/cluster/status",
        connector_name=connector_name,
    )


async def restart_wazuh_manager_service() -> Dict[str, Any]:
    """
    Restarts the Wazuh Manager service.

    Returns:
        Dict[str, Any]: The response from the restart request.
    """
    logger.info("Restarting Wazuh Manager service")
    status_response = await get_cluster_status()

    # Check if the request was successful first
    if not status_response.get("success"):
        logger.error("Failed to get cluster status")
        return {
            "success": False,
            "message": "Failed to get cluster status before restart",
        }

    # Access the nested data structure correctly
    cluster_enabled = status_response.get("data", {}).get("data", {}).get("enabled", "unknown")

    if cluster_enabled == "no":
        logger.info("Wazuh Manager cluster is not enabled, restarting service")
        return await restart_service()
    elif cluster_enabled == "yes":
        logger.info("Wazuh Manager cluster is enabled, restarting cluster")
        response = await send_put_request(
            endpoint="/cluster/restart",
            data={},
        )
        if response.get("success"):
            return {
                "success": True,
                "message": "Wazuh Manager cluster restarted successfully",
            }
        else:
            return response
    else:
        logger.warning(f"Unknown cluster status: {cluster_enabled}, defaulting to service restart")
        return await restart_service()
