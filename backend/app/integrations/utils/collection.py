import httpx
from typing import Any, Dict, Optional

async def send_get_request(endpoint: str, headers: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            return {"data": response.json(), "success": True, "message": "Successfully retrieved data"}
        except httpx.HTTPError as e:
            return {"success": False, "message": f"Failed to retrieve data: {e}"}

async def send_post_request(endpoint: str, data: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send a POST request to the given endpoint.

    Args:
        endpoint (str): The endpoint to send the request to.
        data (Dict[str, Any]): The data to send with the request.

    Returns:
        Dict[str, Any]: The response from the request.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(endpoint, json=data, headers=headers)
            response.raise_for_status()
            return {"data": response.json(), "success": True, "message": "Successfully retrieved data"}
        except httpx.HTTPError as e:
            return {"success": False, "message": f"Failed to retrieve data: {e}"}

