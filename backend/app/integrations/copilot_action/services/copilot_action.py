from typing import Optional

import httpx
from fastapi import HTTPException
from loguru import logger

from app.integrations.copilot_action.schema.copilot_action import ActionDetailResponse
from app.integrations.copilot_action.schema.copilot_action import (
    InventoryMetricsResponse,
)
from app.integrations.copilot_action.schema.copilot_action import InventoryResponse
from app.integrations.copilot_action.schema.copilot_action import Technology


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
        include: Optional[str] = None,
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

            headers = {"x-api-key": license_key, "module-version": cls.MODULE_VERSION, "Accept": "application/json"}

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
                response = await client.get(url, headers=headers, params=params, timeout=30.0)

                response.raise_for_status()

                try:
                    data = response.json()
                    logger.debug(f"Raw API response: {data}")
                except ValueError:
                    logger.error(f"Non-JSON response from inventory API: {response.text[:200]}")
                    return InventoryResponse(copilot_actions=[], message="Invalid response format from inventory API", success=False)

                logger.info(f"Successfully fetched inventory: {len(data.get('copilot_actions', []))} actions")

                # Calculate pagination metadata
                copilot_actions = data.get("copilot_actions", [])
                count = len(copilot_actions)

                # Try to get total from API response, with fallback parsing from message
                total = data.get("total")
                if total is None:
                    # Try to parse total from message like "Returned 1 of 44 matching items"
                    message = data.get("message", "")
                    import re

                    # Try multiple patterns to be more robust
                    patterns = [
                        r"(\d+) of (\d+) matching items",
                        r"Returned (\d+) of (\d+)",
                        r"(\d+)/(\d+) items",
                        r"showing (\d+) of (\d+)",
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, message, re.IGNORECASE)
                        if match:
                            total = int(match.group(2))
                            logger.info(f"Parsed total from message using pattern '{pattern}': {total}")
                            break
                    else:
                        # Fallback to count if we can't parse
                        total = count
                        logger.warning(f"Could not determine total count from message '{message}', using current count: {count}")

                has_more = (offset + count) < total
                next_offset = offset + limit if has_more else None
                prev_offset = max(0, offset - limit) if offset > 0 else None

                return InventoryResponse(
                    copilot_actions=copilot_actions,
                    message=data.get("message", "Successfully fetched inventory"),
                    success=data.get("success", True),
                    total=total,
                    count=count,
                    limit=limit,
                    offset=offset,
                    has_more=has_more,
                    next_offset=next_offset,
                    prev_offset=prev_offset,
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching inventory: {str(e)}")
            return InventoryResponse(
                copilot_actions=[],
                message=f"HTTP error fetching inventory: {str(e)}",
                success=False,
                total=0,
                count=0,
                limit=limit,
                offset=offset,
                has_more=False,
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching inventory: {str(e)}")
            return InventoryResponse(
                copilot_actions=[],
                message=f"Unexpected error: {str(e)}",
                success=False,
                total=0,
                count=0,
                limit=limit,
                offset=offset,
                has_more=False,
            )

    @classmethod
    async def get_action_by_name(cls, license_key: str, copilot_action_name: str) -> ActionDetailResponse:
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

            headers = {"x-api-key": license_key, "module-version": cls.MODULE_VERSION, "Accept": "application/json"}

            logger.info(f"Fetching action details for: {copilot_action_name}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)

                response.raise_for_status()

                try:
                    data = response.json()
                    logger.debug(f"Action detail response data: {data}")
                except ValueError:
                    logger.error(f"Non-JSON response from action API: {response.text[:200]}")
                    return ActionDetailResponse(copilot_action=None, message="Invalid response format from action API", success=False)

                logger.info(f"Successfully fetched action details for: {copilot_action_name}")
                return ActionDetailResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Action not found: {copilot_action_name}")
                raise HTTPException(status_code=404, detail=f"Action '{copilot_action_name}' not found")
            logger.error(f"HTTP error fetching action details: {str(e)}")
            return ActionDetailResponse(copilot_action=None, message=f"HTTP error fetching action details: {str(e)}", success=False)
        except Exception as e:
            logger.error(f"Unexpected error fetching action details: {str(e)}")
            return ActionDetailResponse(copilot_action=None, message=f"Unexpected error: {str(e)}", success=False)

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

            headers = {"x-api-key": license_key, "module-version": cls.MODULE_VERSION, "Accept": "application/json"}

            logger.info("Fetching inventory metrics")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError:
                    logger.error(f"Non-JSON response from metrics API: {response.text[:200]}")
                    return InventoryMetricsResponse(
                        status="error",
                        metrics={},
                        message="Invalid response format from metrics API",
                        success=False,
                    )

                logger.info("Successfully fetched inventory metrics")
                return InventoryMetricsResponse(
                    status=data.get("status", "unknown"),
                    metrics=data.get("metrics", {}),
                    message="Successfully retrieved inventory metrics",
                    success=True,
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching metrics: {str(e)}")
            return InventoryMetricsResponse(status="error", metrics={}, message=f"HTTP error fetching metrics: {str(e)}", success=False)
        except Exception as e:
            logger.error(f"Unexpected error fetching metrics: {str(e)}")
            return InventoryMetricsResponse(status="error", metrics={}, message=f"Unexpected error: {str(e)}", success=False)
