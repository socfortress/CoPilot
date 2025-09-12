from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.schema.groups import WazuhGroupsResponse
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def get_wazuh_groups(**params) -> WazuhGroupsResponse:
    """
    Fetch Wazuh groups from the Wazuh Manager API.

    Args:
        **params: All query parameters passed directly to the API

    Returns:
        WazuhGroupsResponse: Structured response with groups data

    Raises:
        HTTPException: If there's an error fetching the groups
    """
    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Handle list parameters that need to be joined as comma-separated strings
    if "groups_list" in clean_params and isinstance(clean_params["groups_list"], list):
        clean_params["groups_list"] = ",".join(clean_params["groups_list"])
    if "select" in clean_params and isinstance(clean_params["select"], list):
        clean_params["select"] = ",".join(clean_params["select"])

    logger.debug(f"Requesting Wazuh groups with params: {clean_params}")

    try:
        response = await send_get_request(endpoint="/groups", params=clean_params)

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", "Failed to fetch groups from Wazuh API")
            logger.error(f"Wazuh API error: {error_detail}")
            raise HTTPException(status_code=500, detail=error_detail)

        # Extract data from nested response structure
        wazuh_data = response.get("data", {}).get("data", {})
        groups = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(groups))

        logger.info(f"Retrieved {len(groups)} of {total_items} Wazuh groups")

        return WazuhGroupsResponse(
            success=True,
            message=f"Successfully retrieved {len(groups)} groups",
            results=groups,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching Wazuh groups: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")
