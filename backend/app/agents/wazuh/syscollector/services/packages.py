from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.agents.wazuh.syscollector.schema.packages import AgentPackagesResponse
from app.agents.wazuh.syscollector.schema.packages import IndexerPackageAgent
from app.agents.wazuh.syscollector.schema.packages import IndexerPackageDetail
from app.agents.wazuh.syscollector.schema.packages import IndexerPackageItem
from app.agents.wazuh.syscollector.schema.packages import IndexerPackagesResponse
from app.agents.wazuh.syscollector.schema.packages import PackageItem
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.connectors.wazuh_manager.utils.universal import send_get_request

PACKAGES_INDEX_PATTERN = "wazuh-states-inventory-packages-*"


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


async def search_packages_in_indexer(
    package_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    architecture: Optional[str] = None,
    package_type: Optional[str] = None,
    vendor: Optional[str] = None,
    package_version: Optional[str] = None,
    size: int = 500,
) -> IndexerPackagesResponse:
    """
    Search the Wazuh Indexer for package inventory data across all agents.

    Queries the ``wazuh-states-inventory-packages-*`` index pattern and returns
    matching documents with optional filters.

    Args:
        package_name: Filter by package name (wildcard match).
        agent_name: Filter by agent name (wildcard match).
        agent_id: Filter by agent ID (exact match).
        architecture: Filter by architecture (exact match).
        package_type: Filter by package type, e.g. ``deb``, ``rpm`` (exact match).
        vendor: Filter by vendor (wildcard match).
        package_version: Filter by package version (wildcard match).
        size: Maximum number of documents to return (default 500).

    Returns:
        IndexerPackagesResponse with the matching packages.
    """
    must_clauses: List[Dict[str, Any]] = []

    if package_name is not None:
        must_clauses.append({"wildcard": {"package.name": {"value": f"*{package_name}*", "case_insensitive": True}}})
    if agent_name is not None:
        must_clauses.append({"wildcard": {"agent.name": {"value": f"*{agent_name}*", "case_insensitive": True}}})
    if agent_id is not None:
        must_clauses.append({"term": {"agent.id": agent_id}})
    if architecture is not None:
        must_clauses.append({"term": {"package.architecture": architecture}})
    if package_type is not None:
        must_clauses.append({"term": {"package.type": package_type}})
    if vendor is not None:
        must_clauses.append({"wildcard": {"package.vendor": {"value": f"*{vendor}*", "case_insensitive": True}}})
    if package_version is not None:
        must_clauses.append({"wildcard": {"package.version": {"value": f"*{package_version}*", "case_insensitive": True}}})

    query: Dict[str, Any] = {"query": {"bool": {"must": must_clauses}}} if must_clauses else {"query": {"match_all": {}}}

    es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

    try:
        response = await es_client.search(
            index=PACKAGES_INDEX_PATTERN,
            body=query,
            size=size,
        )

        hits = response.get("hits", {})
        total = hits.get("total", {})
        total_value = total.get("value", 0) if isinstance(total, dict) else total

        packages: List[IndexerPackageItem] = []
        for hit in hits.get("hits", []):
            source = hit.get("_source", {})
            packages.append(
                IndexerPackageItem(
                    _index=hit.get("_index"),
                    _id=hit.get("_id"),
                    agent=IndexerPackageAgent(**source.get("agent", {})) if source.get("agent") else None,
                    package=IndexerPackageDetail(**source.get("package", {})) if source.get("package") else None,
                ),
            )

        logger.info(f"Indexer search returned {len(packages)} packages (total matched: {total_value})")

        return IndexerPackagesResponse(
            packages=packages,
            total=total_value,
            success=True,
            message=f"Successfully retrieved {len(packages)} packages from the indexer",
        )
    except Exception as e:
        logger.error(f"Error searching packages in Wazuh Indexer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search packages in Wazuh Indexer: {e}")
    finally:
        await es_client.close()
