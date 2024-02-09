import asyncio
from typing import Any
from typing import Dict
from typing import Optional

import httpx
from loguru import logger


async def send_get_request(
    endpoint: str,
    headers: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a GET request to the given endpoint.

    Args:
        endpoint (str): The endpoint to send the request to.
        params (Optional[Dict[str, Any]], optional): The parameters to send with the request. Defaults to None.

    Returns:
        Dict[str, Any]: The response from the request.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(endpoint, params=params, headers=headers)
            response.raise_for_status()
            return {
                "data": response.json(),
                "success": True,
                "message": "Successfully retrieved data",
            }
        except httpx.HTTPError as e:
            return {"success": False, "message": f"Failed to retrieve data: {e}"}


async def send_post_request(
    endpoint: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send a POST request to the given endpoint.
    """
    async with httpx.AsyncClient() as client:
        try:
            logger.info(
                f"Sending POST request to {endpoint} with data: {data} and headers: {headers}",
            )
            response = await client.post(endpoint, json=data, headers=headers)

            if response.status_code == 429:
                retry_after = int(response.headers.get("X-RateLimit-Reset", 1))
                logger.warning(
                    f"Rate limit exceeded. Retrying after {retry_after} seconds.",
                )
                await asyncio.sleep(retry_after)
                response = await client.post(endpoint, json=data, headers=headers)

            if response.status_code != 200:
                error_message = f"Request failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                return {"success": False, "message": error_message}

            content_type = response.headers.get("Content-Type", "")
            logger.info(f"Content-Type: {content_type}")

            if "application/json" in content_type:
                logger.info(
                    f"Successfully retrieved data from {endpoint} with data: {data} and headers: {headers}",
                )
                return {
                    "data": response.json(),
                    "success": True,
                    "message": "Successfully retrieved data",
                }
            else:
                logger.info(
                    f"Successfully retrieved data from {endpoint} with data: {data} and headers: {headers}",
                )
                return {
                    "data": response.content,
                    "success": True,
                    "message": "Successfully retrieved data",
                }

        except Exception as e:
            error_message = f"Failed to send POST request: {str(e)}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
