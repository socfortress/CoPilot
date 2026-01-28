from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
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
