from typing import List
from typing import Optional

from loguru import logger

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepository
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatus
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatusResponse
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client


async def list_snapshot_repositories() -> SnapshotRepositoryListResponse:
    """
    List all snapshot repositories configured in the Wazuh Indexer (OpenSearch).

    Returns:
        SnapshotRepositoryListResponse: Response containing list of repositories.
    """
    logger.info("Fetching snapshot repositories from Wazuh Indexer")

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Get all snapshot repositories using the _snapshot API
        response = es_client.snapshot.get_repository()

        repositories: List[SnapshotRepository] = []

        for repo_name, repo_data in response.items():
            repository = SnapshotRepository(
                name=repo_name,
                type=repo_data.get("type", "unknown"),
                settings=repo_data.get("settings", {}),
            )
            repositories.append(repository)

        logger.info(f"Successfully retrieved {len(repositories)} snapshot repositories")

        return SnapshotRepositoryListResponse(
            repositories=repositories,
            success=True,
            message=f"Successfully retrieved {len(repositories)} snapshot repositories",
        )

    except Exception as e:
        logger.error(f"Failed to list snapshot repositories: {e}")
        return SnapshotRepositoryListResponse(
            repositories=[],
            success=False,
            message=f"Failed to list snapshot repositories: {str(e)}",
        )


async def get_snapshot_status(
    repository: Optional[str] = None,
    snapshot: Optional[str] = None,
) -> SnapshotStatusResponse:
    """
    Get the status of snapshots in the Wazuh Indexer (OpenSearch).

    Args:
        repository: Optional repository name to filter by.
        snapshot: Optional snapshot name to filter by (requires repository).

    Returns:
        SnapshotStatusResponse: Response containing snapshot statuses.
    """
    logger.info(
        f"Fetching snapshot status from Wazuh Indexer "
        f"(repository={repository}, snapshot={snapshot})",
    )

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Build the request parameters
        repo_param = repository if repository else "_all"
        snapshot_param = snapshot if snapshot else "_all"

        # Get snapshot status using the _snapshot/_status API
        response = es_client.snapshot.status(
            repository=repo_param,
            snapshot=snapshot_param,
            ignore_unavailable=True,
        )

        snapshots: List[SnapshotStatus] = []

        for snap_data in response.get("snapshots", []):
            snapshot_status = SnapshotStatus(
                snapshot=snap_data.get("snapshot", "unknown"),
                repository=snap_data.get("repository", "unknown"),
                uuid=snap_data.get("uuid"),
                state=snap_data.get("state", "unknown"),
                include_global_state=snap_data.get("include_global_state"),
                shards_stats=snap_data.get("shards_stats", {}),
                stats=snap_data.get("stats", {}),
                indices=snap_data.get("indices", {}),
            )
            snapshots.append(snapshot_status)

        logger.info(f"Successfully retrieved status for {len(snapshots)} snapshots")

        return SnapshotStatusResponse(
            snapshots=snapshots,
            success=True,
            message=f"Successfully retrieved status for {len(snapshots)} snapshots",
        )

    except Exception as e:
        logger.error(f"Failed to get snapshot status: {e}")
        return SnapshotStatusResponse(
            snapshots=[],
            success=False,
            message=f"Failed to get snapshot status: {str(e)}",
        )
