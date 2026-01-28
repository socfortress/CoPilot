from typing import List
from typing import Optional

from loguru import logger

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreShardInfo
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotInfo
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepository
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatus
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatusResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotResponse
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


async def list_snapshots(repository: str) -> SnapshotListResponse:
    """
    List all snapshots in a repository.

    Args:
        repository: Name of the repository to list snapshots from.

    Returns:
        SnapshotListResponse: Response containing list of snapshots.
    """
    logger.info(f"Fetching snapshots from repository: {repository}")

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Get all snapshots in the repository
        response = es_client.snapshot.get(
            repository=repository,
            snapshot="_all",
            ignore_unavailable=True,
        )

        snapshots: List[SnapshotInfo] = []

        for snap_data in response.get("snapshots", []):
            snapshot_info = SnapshotInfo(
                snapshot=snap_data.get("snapshot", "unknown"),
                uuid=snap_data.get("uuid"),
                version_id=snap_data.get("version_id"),
                version=snap_data.get("version"),
                indices=snap_data.get("indices", []),
                include_global_state=snap_data.get("include_global_state"),
                state=snap_data.get("state", "unknown"),
                start_time=snap_data.get("start_time"),
                start_time_in_millis=snap_data.get("start_time_in_millis"),
                end_time=snap_data.get("end_time"),
                end_time_in_millis=snap_data.get("end_time_in_millis"),
                duration_in_millis=snap_data.get("duration_in_millis"),
                failures=snap_data.get("failures", []),
                shards=snap_data.get("shards", {}),
            )
            snapshots.append(snapshot_info)

        logger.info(f"Successfully retrieved {len(snapshots)} snapshots from repository {repository}")

        return SnapshotListResponse(
            repository=repository,
            snapshots=snapshots,
            success=True,
            message=f"Successfully retrieved {len(snapshots)} snapshots from repository {repository}",
        )

    except Exception as e:
        logger.error(f"Failed to list snapshots from repository {repository}: {e}")
        return SnapshotListResponse(
            repository=repository,
            snapshots=[],
            success=False,
            message=f"Failed to list snapshots: {str(e)}",
        )


async def restore_snapshot(request: RestoreSnapshotRequest) -> RestoreSnapshotResponse:
    """
    Restore a snapshot from a repository.

    Args:
        request: RestoreSnapshotRequest containing restore parameters.

    Returns:
        RestoreSnapshotResponse: Response containing restoration details.
    """
    logger.info(
        f"Restoring snapshot {request.snapshot} from repository {request.repository}",
    )

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Build the restore body
        body = {}

        if request.indices:
            body["indices"] = ",".join(request.indices)

        if request.ignore_unavailable is not None:
            body["ignore_unavailable"] = request.ignore_unavailable

        if request.include_global_state is not None:
            body["include_global_state"] = request.include_global_state

        if request.rename_pattern:
            body["rename_pattern"] = request.rename_pattern

        if request.rename_replacement:
            body["rename_replacement"] = request.rename_replacement

        if request.include_aliases is not None:
            body["include_aliases"] = request.include_aliases

        if request.partial is not None:
            body["partial"] = request.partial

        # Restore the snapshot
        response = es_client.snapshot.restore(
            repository=request.repository,
            snapshot=request.snapshot,
            body=body if body else None,
            wait_for_completion=False,
        )

        # Parse the response
        snapshot_data = response.get("snapshot", {})
        shards_data = snapshot_data.get("shards", {})

        shards_info = RestoreShardInfo(
            total=shards_data.get("total", 0),
            failed=shards_data.get("failed", 0),
            successful=shards_data.get("successful", 0),
        )

        restored_indices = snapshot_data.get("indices", [])

        logger.info(
            f"Successfully initiated restore of snapshot {request.snapshot} "
            f"({len(restored_indices)} indices)",
        )

        return RestoreSnapshotResponse(
            snapshot=request.snapshot,
            repository=request.repository,
            indices=restored_indices,
            shards=shards_info,
            success=True,
            message=f"Successfully initiated restore of snapshot {request.snapshot}",
        )

    except Exception as e:
        logger.error(f"Failed to restore snapshot {request.snapshot}: {e}")
        return RestoreSnapshotResponse(
            snapshot=request.snapshot,
            repository=request.repository,
            indices=[],
            shards=RestoreShardInfo(total=0, failed=0, successful=0),
            success=False,
            message=f"Failed to restore snapshot: {str(e)}",
        )

async def create_snapshot(request: CreateSnapshotRequest) -> CreateSnapshotResponse:
    """
    Create a snapshot in a repository.

    Args:
        request: CreateSnapshotRequest containing snapshot parameters.

    Returns:
        CreateSnapshotResponse: Response containing snapshot creation details.
    """
    logger.info(
        f"Creating snapshot {request.snapshot} in repository {request.repository}",
    )

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Build the snapshot body
        body = {}

        if request.indices:
            body["indices"] = ",".join(request.indices)

        if request.ignore_unavailable is not None:
            body["ignore_unavailable"] = request.ignore_unavailable

        if request.include_global_state is not None:
            body["include_global_state"] = request.include_global_state

        if request.partial is not None:
            body["partial"] = request.partial

        if request.metadata:
            body["metadata"] = request.metadata

        # Create the snapshot
        response = es_client.snapshot.create(
            repository=request.repository,
            snapshot=request.snapshot,
            body=body if body else None,
            wait_for_completion=request.wait_for_completion or False,
        )

        # Parse the response based on whether we waited for completion
        if request.wait_for_completion:
            snapshot_data = response.get("snapshot", {})
            shards_data = snapshot_data.get("shards", {})

            shards_info = RestoreShardInfo(
                total=shards_data.get("total", 0),
                failed=shards_data.get("failed", 0),
                successful=shards_data.get("successful", 0),
            )

            logger.info(
                f"Successfully created snapshot {request.snapshot} "
                f"in repository {request.repository}",
            )

            return CreateSnapshotResponse(
                snapshot=snapshot_data.get("snapshot", request.snapshot),
                repository=request.repository,
                uuid=snapshot_data.get("uuid"),
                state=snapshot_data.get("state"),
                indices=snapshot_data.get("indices", []),
                shards=shards_info,
                accepted=True,
                success=True,
                message=f"Successfully created snapshot {request.snapshot}",
            )
        else:
            # When not waiting, we get an accepted response
            accepted = response.get("accepted", False)

            logger.info(
                f"Snapshot {request.snapshot} creation initiated "
                f"in repository {request.repository} (accepted={accepted})",
            )

            return CreateSnapshotResponse(
                snapshot=request.snapshot,
                repository=request.repository,
                uuid=None,
                state="IN_PROGRESS",
                indices=request.indices or [],
                shards=None,
                accepted=accepted,
                success=accepted,
                message=f"Snapshot {request.snapshot} creation initiated" if accepted else "Snapshot request was not accepted",
            )

    except Exception as e:
        logger.error(f"Failed to create snapshot {request.snapshot}: {e}")
        return CreateSnapshotResponse(
            snapshot=request.snapshot,
            repository=request.repository,
            uuid=None,
            state=None,
            indices=[],
            shards=None,
            accepted=False,
            success=False,
            message=f"Failed to create snapshot: {str(e)}",
        )
