from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.syscollector.schema.packages import AgentPackagesResponse
from app.agents.wazuh.syscollector.schema.packages import PackageItem
from app.connectors.wazuh_manager.utils.universal import send_get_request


async def collect_agent_packages(
    agent_id: str,
    limit: int = 500,
    offset: int = 0,
    sort: Optional[str] = None,
    search: Optional[str] = None,
    select: Optional[List[str]] = None,
    vendor: Optional[str] = None,
    name: Optional[str] = None,
    architecture: Optional[str] = None,
    format: Optional[str] = None,
    version: Optional[str] = None,
    q: Optional[str] = None,
) -> AgentPackagesResponse:
    """
    Fetch installed packages for a specific agent from the Wazuh Manager
    syscollector API.

    Args:
        agent_id: The Wazuh agent ID.
        limit: Maximum number of packages to return (1-100000, default 500).
        offset: First element to return (pagination).
        sort: Sort field(s), prefixed with +/- for order.
        search: Free-text search string.
        select: List of fields to return.
        vendor: Filter by vendor.
        name: Filter by package name.
        architecture: Filter by architecture.
        format: Filter by package format (e.g. 'deb', 'rpm').
        version: Filter by package version.
        q: Advanced query filter string.

    Returns:
        AgentPackagesResponse with the list of packages.
    """
    params: Dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "wait_for_complete": True,
    }

    if sort is not None:
        params["sort"] = sort
    if search is not None:
        params["search"] = search
    if select is not None:
        params["select"] = ",".join(select)
    if vendor is not None:
        params["vendor"] = vendor
    if name is not None:
        params["name"] = name
    if architecture is not None:
        params["architecture"] = architecture
    if format is not None:
        params["format"] = format
    if version is not None:
        params["version"] = version
    if q is not None:
        params["q"] = q

    response = await send_get_request(
        endpoint=f"/syscollector/{agent_id}/packages",
        params=params,
    )

    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to fetch packages from Wazuh Manager"),
        )

    wazuh_data = response.get("data", {}).get("data", {})
    affected_items = wazuh_data.get("affected_items", [])
    total_affected_items = wazuh_data.get("total_affected_items", len(affected_items))

    packages = [PackageItem(**item) for item in affected_items]

    logger.info(f"Fetched {len(packages)} packages for agent {agent_id}")

    return AgentPackagesResponse(
        packages=packages,
        total_affected_items=total_affected_items,
        success=True,
        message=f"Successfully fetched {len(packages)} packages for agent {agent_id}",
    )
