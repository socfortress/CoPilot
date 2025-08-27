import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Security
from loguru import logger

from app.auth.routes.auth import AuthHandler
from app.integrations.copilot_action.schema.copilot_action import (
    InventoryResponse,
    ActionDetailResponse,
    InventoryMetricsResponse,
    Technology
)
from app.integrations.copilot_action.services.copilot_action import CopilotActionService

copilot_action_router = APIRouter()
auth_handler = AuthHandler()


@copilot_action_router.get(
    "/inventory",
    response_model=InventoryResponse,
    description="Get inventory of available active response scripts",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_inventory(
    technology: Optional[Technology] = Query(None, description="Filter by technology type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    q: Optional[str] = Query(None, description="Free-text search query"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    refresh: bool = Query(False, description="Force refresh cache"),
    include: Optional[str] = Query(None, description="Comma-separated extra fields to include")
) -> InventoryResponse:
    """
    Retrieve inventory of available active response scripts.

    This endpoint fetches the catalog of active response scripts from the
    Copilot Action service, with optional filtering and pagination.

    Args:
        technology: Filter by technology type (e.g., Windows, Linux, Wazuh)
        category: Filter by category if present
        tag: Filter by tag contained in the tags list
        q: Free-text search in name/description
        limit: Maximum number of results (1-1000)
        offset: Offset for pagination
        refresh: Force refresh the remote cache
        include: Extra fields to include (e.g., 'category,tags')

    Returns:
        InventoryResponse: List of active response scripts with metadata
    """
    logger.info(f"Fetching active response inventory with filters: tech={technology}, category={category}, tag={tag}, q={q}")

    # Get license key from environment variable
    license_key = os.getenv('COPILOT_API_KEY')
    if not license_key:
        logger.error("COPILOT_API_KEY environment variable not set")
        raise HTTPException(status_code=500, detail="COPILOT_API_KEY environment variable not configured")

    # Fetch inventory from service
    try:
        response = await CopilotActionService.get_inventory(
            license_key=license_key,
            technology=technology,
            category=category,
            tag=tag,
            q=q,
            limit=limit,
            offset=offset,
            refresh=refresh,
            include=include
        )

        logger.info(f"Successfully fetched inventory: {len(response.copilot_actions)} actions")
        return response

    except Exception as e:
        logger.error(f"Error fetching inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching inventory: {str(e)}")


@copilot_action_router.get(
    "/inventory/{copilot_action_name}",
    response_model=ActionDetailResponse,
    description="Get details for a specific active response script",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_action_by_name(
    copilot_action_name: str
) -> ActionDetailResponse:
    """
    Get detailed information for a specific active response script.

    Args:
        copilot_action_name: Name of the action to retrieve

    Returns:
        ActionDetailResponse: Detailed information about the action
    """
    logger.info(f"Fetching action details for: {copilot_action_name}")

    # Get license key from environment variable
    license_key = os.getenv('COPILOT_API_KEY')
    if not license_key:
        logger.error("COPILOT_API_KEY environment variable not set")
        raise HTTPException(status_code=500, detail="COPILOT_API_KEY environment variable not configured")

    # Fetch action details from service
    try:
        response = await CopilotActionService.get_action_by_name(
            license_key=license_key,
            copilot_action_name=copilot_action_name
        )

        if not response.success:
            if "not found" in response.message.lower():
                raise HTTPException(status_code=404, detail=response.message)
            else:
                raise HTTPException(status_code=500, detail=response.message)

        logger.info(f"Successfully fetched action details for: {copilot_action_name}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching action details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching action details: {str(e)}")


@copilot_action_router.get(
    "/metrics",
    response_model=InventoryMetricsResponse,
    description="Get inventory metrics and status",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_metrics() -> InventoryMetricsResponse:
    """
    Get metrics and status information for the inventory service.

    Returns:
        InventoryMetricsResponse: Service metrics and status
    """
    logger.info("Fetching inventory metrics")

    # Get license key from environment variable
    license_key = os.getenv('COPILOT_API_KEY')
    if not license_key:
        logger.error("COPILOT_API_KEY environment variable not set")
        raise HTTPException(status_code=500, detail="COPILOT_API_KEY environment variable not configured")

    # Fetch metrics from service
    try:
        response = await CopilotActionService.get_metrics(license_key=license_key)

        logger.info("Successfully fetched inventory metrics")
        return response

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@copilot_action_router.get(
    "/technologies",
    description="Get available technology types",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_technologies() -> dict:
    """
    Get list of available technology types for filtering.

    Returns:
        Dictionary containing available technology types
    """
    technologies = [tech.value for tech in Technology]

    return {
        "technologies": technologies,
        "total": len(technologies),
        "message": "Successfully retrieved available technologies",
        "success": True
    }
