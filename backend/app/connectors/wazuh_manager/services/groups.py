from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_manager.schema.groups import WazuhGroupFileResponse
from app.connectors.wazuh_manager.schema.groups import WazuhGroupFilesResponse
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


async def get_wazuh_group_file(group_id: str, filename: str, **params) -> WazuhGroupFileResponse:
    """
    Fetch the content of a specific file from a Wazuh group.

    Args:
        group_id: The ID (name) of the group
        filename: The name of the file to fetch (e.g., "agent.conf")
        **params: All query parameters passed directly to the API

    Returns:
        WazuhGroupFileResponse: Structured response with group file content

    Raises:
        HTTPException: If there's an error fetching the group file
    """
    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Handle list parameters that need to be joined as comma-separated strings
    if "type" in clean_params and isinstance(clean_params["type"], list):
        clean_params["type"] = ",".join(clean_params["type"])

    # Check if raw content is requested
    is_raw = clean_params.get("raw", False)

    logger.debug(f"Requesting Wazuh group file '{filename}' for group '{group_id}' with params: {clean_params}")

    try:
        response = await send_get_request(endpoint=f"/groups/{group_id}/files/{filename}", params=clean_params)
        logger.info(f"Response: {response}")

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", f"Failed to fetch group file '{filename}' for group '{group_id}'")
            logger.error(f"Wazuh API error: {error_detail}")

            # Handle specific errors
            if "not found" in error_detail.lower():
                raise HTTPException(status_code=404, detail=f"Group file '{filename}' not found in group '{group_id}'")
            else:
                raise HTTPException(status_code=500, detail=error_detail)

        # Handle raw response differently
        if is_raw:
            # For raw responses, the content is in response["data"]
            content = response.get("data", "")
            logger.info(f"Retrieved raw content for group file '{filename}' in group '{group_id}' ({len(content)} characters)")

            return WazuhGroupFileResponse(
                success=True,
                message=f"Successfully retrieved raw content for group file '{filename}' in group '{group_id}'",
                group_id=group_id,
                filename=filename,
                content=content,
                is_raw=True,
                total_items=None,
            )

        # Handle structured response (non-raw)
        wazuh_data = response.get("data", {}).get("data", {})
        affected_items = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(affected_items))

        if not affected_items:
            raise HTTPException(status_code=404, detail=f"No content found for group file '{filename}' in group '{group_id}'")

        # Extract the content from the first affected item
        content = affected_items[0] if affected_items else {}

        logger.info(f"Retrieved structured content for group file '{filename}' in group '{group_id}' with {total_items} affected items")

        return WazuhGroupFileResponse(
            success=True,
            message=f"Successfully retrieved content for group file '{filename}' in group '{group_id}'",
            group_id=group_id,
            filename=filename,
            content=content,
            is_raw=False,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching Wazuh group file '{filename}' for group '{group_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching group file: {str(e)}")


async def get_wazuh_group_files(group_id: str, **params) -> WazuhGroupFilesResponse:
    """
    Fetch the list of files in a Wazuh group.

    Args:
        group_id: The ID (name) of the group
        **params: All query parameters passed directly to the API

    Returns:
        WazuhGroupFilesResponse: Structured response with group files data

    Raises:
        HTTPException: If there's an error fetching the group files
    """
    # Filter out None values
    clean_params = {k: v for k, v in params.items() if v is not None}

    # Handle list parameters that need to be joined as comma-separated strings
    if "select" in clean_params and isinstance(clean_params["select"], list):
        clean_params["select"] = ",".join(clean_params["select"])

    logger.debug(f"Requesting Wazuh group files for group '{group_id}' with params: {clean_params}")

    try:
        response = await send_get_request(endpoint=f"/groups/{group_id}/files", params=clean_params)

        # Check if the API request was successful
        if not response.get("success"):
            error_detail = response.get("message", f"Failed to fetch group files for group '{group_id}'")
            logger.error(f"Wazuh API error: {error_detail}")

            # Handle specific errors
            if "not found" in error_detail.lower():
                raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found")
            else:
                raise HTTPException(status_code=500, detail=error_detail)

        # Extract data from nested response structure
        wazuh_data = response.get("data", {}).get("data", {})
        files = wazuh_data.get("affected_items", [])
        total_items = wazuh_data.get("total_affected_items", len(files))

        logger.info(f"Retrieved {len(files)} of {total_items} Wazuh group files for group '{group_id}'")

        return WazuhGroupFilesResponse(
            success=True,
            message=f"Successfully retrieved {len(files)} files for group '{group_id}'",
            group_id=group_id,
            results=files,
            total_items=total_items,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching Wazuh group files for group '{group_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching group files: {str(e)}")
