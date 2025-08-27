from typing import Optional, List
import httpx
from loguru import logger

from app.integrations.copilot_action.schema.copilot_action import (
    InventoryQueryRequest,
    InventoryResponse,
    ActionDetailResponse,
    InventoryMetricsResponse,
    Technology
)


class CopilotActionService:
    """Service for interacting with the Copilot Action inventory API"""

    BASE_URL = "https://copilot-action.socfortress.co"
    MODULE_VERSION = "1.0.0"

    @classmethod
    async def get_inventory(
        cls,
        license_key: str,
        technology: Optional[Technology] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        refresh: bool = False,
        include: Optional[str] = None
    ) -> InventoryResponse:
        """
        Fetch inventory from the Copilot Action service.

        Args:
            license_key: API key for authentication
            technology: Filter by technology type
            category: Filter by category
            tag: Filter by tag
            q: Free-text search query
            limit: Maximum number of results
            offset: Offset for pagination
            refresh: Force refresh cache
            include: Comma-separated extra fields to include

        Returns:
            InventoryResponse: The inventory data
        """
        try:
            url = f"{cls.BASE_URL}/inventory"

            headers = {
                "x-api-key": license_key,
                "module-version": cls.MODULE_VERSION,
                "Accept": "application/json"
            }

            params = {}
            if technology:
                params["technology"] = technology.value
            if category:
                params["category"] = category
            if tag:
                params["tag"] = tag
            if q:
                params["q"] = q
            if limit != 100:
                params["limit"] = limit
            if offset != 0:
                params["offset"] = offset
            if refresh:
                params["refresh"] = "true"
            if include:
                params["include"] = include

            logger.info(f"Fetching inventory from {url} with params: {params}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError:
                    logger.error(f"Non-JSON response from inventory API: {response.text[:200]}")
                    return InventoryResponse(
                        copilot_actions=[],
                        message=f"Invalid response format from inventory API",
                        success=False
                    )

                logger.info(f"Successfully fetched inventory: {len(data.get('copilot_actions', []))} actions")
                return InventoryResponse(**data)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching inventory: {str(e)}")
            return InventoryResponse(
                copilot_actions=[],
                message=f"HTTP error fetching inventory: {str(e)}",
                success=False
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching inventory: {str(e)}")
            return InventoryResponse(
                copilot_actions=[],
                message=f"Unexpected error: {str(e)}",
                success=False
            )

    @classmethod
    async def get_action_by_name(
        cls,
        license_key: str,
        copilot_action_name: str
    ) -> ActionDetailResponse:
        """
        Fetch details for a specific action by name.

        Args:
            license_key: API key for authentication
            copilot_action_name: Name of the action to fetch

        Returns:
            ActionDetailResponse: The action details
        """
        try:
            url = f"{cls.BASE_URL}/inventory/{copilot_action_name}"

            headers = {
                "x-api-key": license_key,
                "module-version": cls.MODULE_VERSION,
                "Accept": "application/json"
            }

            logger.info(f"Fetching action details for: {copilot_action_name}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError:
                    logger.error(f"Non-JSON response from action API: {response.text[:200]}")
                    return ActionDetailResponse(
                        active_response=None,
                        message=f"Invalid response format from action API",
                        success=False
                    )

                logger.info(f"Successfully fetched action details for: {copilot_action_name}")
                return ActionDetailResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Action not found: {copilot_action_name}")
                return ActionDetailResponse(
                    active_response=None,
                    message=f"Action '{copilot_action_name}' not found",
                    success=False
                )
            logger.error(f"HTTP error fetching action details: {str(e)}")
            return ActionDetailResponse(
                active_response=None,
                message=f"HTTP error fetching action details: {str(e)}",
                success=False
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching action details: {str(e)}")
            return ActionDetailResponse(
                active_response=None,
                message=f"Unexpected error: {str(e)}",
                success=False
            )

    @classmethod
    async def get_metrics(cls, license_key: str) -> InventoryMetricsResponse:
        """
        Fetch inventory metrics.

        Args:
            license_key: API key for authentication

        Returns:
            InventoryMetricsResponse: The metrics data
        """
        try:
            url = f"{cls.BASE_URL}/metrics"

            headers = {
                "x-api-key": license_key,
                "module-version": cls.MODULE_VERSION,
                "Accept": "application/json"
            }

            logger.info("Fetching inventory metrics")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError:
                    logger.error(f"Non-JSON response from metrics API: {response.text[:200]}")
                    return InventoryMetricsResponse(
                        status="error",
                        metrics={},
                        message="Invalid response format from metrics API",
                        success=False
                    )

                logger.info("Successfully fetched inventory metrics")
                return InventoryMetricsResponse(
                    status=data.get("status", "unknown"),
                    metrics=data.get("metrics", {}),
                    message="Successfully retrieved inventory metrics",
                    success=True
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metrics: {str(e)}")
            return InventoryMetricsResponse(
                status="error",
                metrics={},
                message=f"HTTP error fetching metrics: {str(e)}",
                success=False
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching metrics: {str(e)}")
            return InventoryMetricsResponse(
                status="error",
                metrics={},
                message=f"Unexpected error: {str(e)}",
                success=False
            )
