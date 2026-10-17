import json
import re
from typing import Any
from typing import Dict
from typing import Optional

import httpx
import requests
from loguru import logger

from app.blocking import run_blocking
from app.connectors.talon.utils import capped_body
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
        response = await run_blocking(requests.get, f"{attributes['connector_url']}/health", verify=False, timeout=10)
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
        response = await run_blocking(
            requests.get,
            f"{attributes['connector_url']}{endpoint}",
            headers=headers,
            params=params,
            verify=False,
            timeout=(5, 30),
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
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Sends a POST request to the Talon service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Optional[Dict[str, Any]]): The data to send with the POST request. Defaults to None.
        connector_name (str, optional): The name of the connector to use. Defaults to "Talon".
        timeout (int, optional): Request timeout in seconds. Defaults to 120.

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
        response = await run_blocking(
            requests.post,
            f"{attributes['connector_url']}{endpoint}",
            headers=headers,
            json=data,
            verify=False,
            timeout=timeout,
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


#: Most of a 4xx body read when looking for its reason. Talon's are a few dozen bytes.
MAX_REFUSAL_BODY_BYTES = 4096

#: What an upstream 4xx reason must look like to be shown to the user as it is: one line of
#: printable ASCII, at most 200 characters. Talon's refusals are fixed texts of that shape
#: ("message is required", "user_id is required ([A-Za-z0-9_-], max 48 chars)", "Unauthorized").
_REFUSAL_REASON = re.compile(r"[ -~]{1,200}")


def _sse_error(text: str) -> bytes:
    """One SSE error event in the wire format the chat UI reads: ``data: {"error": "…"}``."""
    return f"data: {json.dumps({'error': text})}\n\n".encode()


def refusal_reason(status_code: int, body: bytes) -> Optional[str]:
    """
    The reason Talon gave for refusing a request, when it is safe to show the user.

    Only a 4xx is a refusal: Talon declining the request as sent, with its own fixed text
    (FastAPI's ``{"detail": "…"}``, or ``{"error": "Unauthorized"}`` for a wrong API key).
    A 5xx body, a non-JSON body, a structured ``detail`` (a 422's list) or anything longer
    or stranger than one short printable line yields None, and the caller shows its own
    fixed text instead.
    """
    if not 400 <= status_code < 500:
        return None
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):  # ValueError includes UnicodeDecodeError
        return None
    if not isinstance(payload, dict):
        return None
    reason = payload.get("detail", payload.get("error"))
    if not isinstance(reason, str) or not _REFUSAL_REASON.fullmatch(reason):
        return None
    return reason


async def _read_capped(response: httpx.Response, limit: int = MAX_REFUSAL_BODY_BYTES) -> bytes:
    """At most ``limit`` raw bytes of a streamed response body; an encoded body reads as nothing
    (``capped_body``: httpx would inflate stacked gzip without a limit)."""
    return await capped_body.read_prefix(response, limit)


async def send_post_request_sse(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    connector_name: str = "Talon",
):
    """
    Sends a POST request to the Talon service and yields SSE chunks as they arrive.

    Uses httpx async streaming to avoid blocking the event loop and preserves
    the raw SSE wire format (including \\n\\n event boundaries).

    When Talon refuses the request with a 4xx and a short reason of its own, that reason
    is the error event's text, so the user learns why ("message is required"). Any other
    failure (a 5xx, an unreadable 4xx, a connection error) gets a fixed text: neither an
    upstream error body nor exception text reaches the user.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Optional[Dict[str, Any]]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Talon".

    Yields:
        bytes: Raw SSE bytes from the upstream response.
    """
    logger.info(f"Sending streaming POST request to Talon {endpoint}")
    async with get_db_session() as session:
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Talon connector found in the database")
        yield _sse_error("No Talon connector found in the database")
        return
    failed = f"Failed to stream from {endpoint}"
    try:
        headers = {**_build_headers(attributes["connector_api_key"]), "Accept-Encoding": "identity"}
        timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{attributes['connector_url']}{endpoint}",
                headers=headers,
                json=data,
            ) as response:
                if not response.is_success:
                    reason = refusal_reason(response.status_code, await _read_capped(response))
                    logger.error(f"Talon {endpoint} answered {response.status_code}" + (f": {reason}" if reason else ""))
                    yield _sse_error(f"Talon refused the request: {reason}" if reason else failed)
                    return
                if not capped_body.is_identity(response):  # Talon never compresses its stream
                    logger.error(f"Talon {endpoint}: the stream came with a Content-Encoding; refused")
                    yield _sse_error(failed)
                    return
                async for chunk in capped_body.raw_chunks(response):
                    yield chunk
    except Exception as e:
        logger.error(f"Failed to stream from Talon {endpoint} with error: {e}")
        yield _sse_error(failed)
