from typing import Optional

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from loguru import logger

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatusResponse
from app.connectors.wazuh_indexer.services.snapshot_and_restore import get_snapshot_status
from app.connectors.wazuh_indexer.services.snapshot_and_restore import list_snapshot_repositories

wazuh_indexer_snapshots_router = APIRouter()


@wazuh_indexer_snapshots_router.get(
    "/repositories",
    response_model=SnapshotRepositoryListResponse,
    summary="List Snapshot Repositories",
    description="Retrieve a list of all configured snapshot repositories in the Wazuh Indexer.",
)
async def get_snapshot_repositories() -> SnapshotRepositoryListResponse:
    """
    List all snapshot repositories configured in the Wazuh Indexer.

    Returns:
        SnapshotRepositoryListResponse: List of snapshot repositories with their settings.
    """
    logger.info("Received request to list snapshot repositories")

    response = await list_snapshot_repositories()

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.get(
    "/status",
    response_model=SnapshotStatusResponse,
    summary="Get Snapshot Status",
    description="Retrieve the status of snapshots. Optionally filter by repository and snapshot name.",
)
async def get_snapshots_status(
    repository: Optional[str] = Query(
        None,
        description="Repository name to filter by. If not provided, all repositories are queried.",
    ),
    snapshot: Optional[str] = Query(
        None,
        description="Snapshot name to filter by. Requires repository to be specified.",
    ),
) -> SnapshotStatusResponse:
    """
    Get the status of snapshots in the Wazuh Indexer.

    Args:
        repository: Optional repository name to filter by.
        snapshot: Optional snapshot name to filter by.

    Returns:
        SnapshotStatusResponse: Status of the requested snapshots.
    """
    logger.info(
        f"Received request to get snapshot status "
        f"(repository={repository}, snapshot={snapshot})",
    )

    if snapshot and not repository:
        raise HTTPException(
            status_code=400,
            detail="Repository must be specified when filtering by snapshot name.",
        )

    response = await get_snapshot_status(repository=repository, snapshot=snapshot)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response
