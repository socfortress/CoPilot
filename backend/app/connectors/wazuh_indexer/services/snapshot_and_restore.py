import re
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.models.snapshot_and_restore import SnapshotSchedule
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import IndexWriteStatus
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreShardInfo
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import ScheduledSnapshotExecutionResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotInfo
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepository
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleCreate
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleOperationResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleUpdate
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatus
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatusResponse
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client
from app.db.db_session import get_db_session

def parse_graylog_index_name(index_name: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parse a Graylog-style index name to extract the base name and index number.

    Graylog naming convention: {base_name}_{number}
    Examples:
        - wazuh_customer_01 -> ("wazuh_customer", 1)
        - wazuh_00002_307 -> ("wazuh_00002", 307)
        - graylog_0 -> ("graylog", 0)

    Args:
        index_name: The index name to parse.

    Returns:
        Tuple of (base_name, index_number) or (None, None) if pattern doesn't match.
    """
    # Match pattern: anything followed by underscore and a number at the end
    pattern = r"^(.+)_(\d+)$"
    match = re.match(pattern, index_name)

    if match:
        base_name = match.group(1)
        index_number = int(match.group(2))
        return base_name, index_number

    return None, None


def identify_write_indices(index_names: List[str]) -> Dict[str, IndexWriteStatus]:
    """
    Identify which indices are currently being written to based on Graylog naming convention.

    The index with the highest number for each base name is considered the write index.

    Args:
        index_names: List of index names to analyze.

    Returns:
        Dictionary mapping index names to their write status.
    """
    # Group indices by base name
    index_groups: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

    for index_name in index_names:
        base_name, index_number = parse_graylog_index_name(index_name)
        if base_name is not None and index_number is not None:
            index_groups[base_name].append((index_name, index_number))

    # Find the highest numbered index for each base name
    write_indices: Dict[str, IndexWriteStatus] = {}

    for base_name, indices in index_groups.items():
        # Sort by index number to find the highest
        sorted_indices = sorted(indices, key=lambda x: x[1], reverse=True)
        highest_index_name, highest_index_number = sorted_indices[0]

        # Mark all indices with their write status
        for index_name, index_number in indices:
            is_write_index = index_name == highest_index_name
            write_indices[index_name] = IndexWriteStatus(
                index_name=index_name,
                is_write_index=is_write_index,
                index_number=index_number,
                base_name=base_name,
            )

    # Handle indices that don't match the Graylog pattern
    for index_name in index_names:
        if index_name not in write_indices:
            write_indices[index_name] = IndexWriteStatus(
                index_name=index_name,
                is_write_index=False,  # Assume non-Graylog indices are not write indices
                index_number=None,
                base_name=None,
            )

    return write_indices


async def get_all_indices() -> List[str]:
    """
    Get all index names from the Wazuh Indexer.

    Returns:
        List of index names.
    """
    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
        indices = es_client.indices.get_alias(index="*")
        return list(indices.keys())
    except Exception as e:
        logger.error(f"Failed to get indices: {e}")
        return []


async def filter_write_indices(
    requested_indices: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """
    Filter out write indices from the requested indices list.

    Args:
        requested_indices: List of indices to filter. If None, all indices are considered.

    Returns:
        Tuple of (indices_to_snapshot, skipped_write_indices).
    """
    # Get all indices from the cluster
    all_indices = await get_all_indices()

    # Identify write indices
    write_status = identify_write_indices(all_indices)

    # Determine which indices to check
    if requested_indices:
        # Expand wildcards if present
        indices_to_check = []
        for pattern in requested_indices:
            if "*" in pattern:
                # Simple wildcard matching
                regex_pattern = pattern.replace("*", ".*")
                for index_name in all_indices:
                    if re.match(f"^{regex_pattern}$", index_name):
                        indices_to_check.append(index_name)
            else:
                indices_to_check.append(pattern)
    else:
        indices_to_check = all_indices

    # Separate write indices from non-write indices
    indices_to_snapshot = []
    skipped_write_indices = []

    for index_name in indices_to_check:
        status = write_status.get(index_name)
        if status and status.is_write_index:
            skipped_write_indices.append(index_name)
            logger.info(
                f"Skipping write index: {index_name} "
                f"(base: {status.base_name}, number: {status.index_number})",
            )
        else:
            indices_to_snapshot.append(index_name)

    return indices_to_snapshot, skipped_write_indices

def _schedule_to_response(schedule: SnapshotSchedule) -> SnapshotScheduleResponse:
    """Convert a SnapshotSchedule model to a response model."""
    return SnapshotScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        index_pattern=schedule.index_pattern,
        repository=schedule.repository,
        enabled=schedule.enabled,
        snapshot_prefix=schedule.snapshot_prefix,
        include_global_state=schedule.include_global_state,
        skip_write_indices=schedule.skip_write_indices,
        retention_days=schedule.retention_days,
        last_execution_time=schedule.last_execution_time.isoformat() if schedule.last_execution_time else None,
        last_snapshot_name=schedule.last_snapshot_name,
        last_execution_status=schedule.last_execution_status,
        created_at=schedule.created_at.isoformat(),
        updated_at=schedule.updated_at.isoformat(),
    )

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

        # Filter out write indices if requested
        skipped_write_indices = []
        indices_to_snapshot = request.indices

        if request.skip_write_indices:
            indices_to_snapshot, skipped_write_indices = await filter_write_indices(
                requested_indices=request.indices,
            )

            if skipped_write_indices:
                logger.info(
                    f"Skipping {len(skipped_write_indices)} write indices: {skipped_write_indices}",
                )

            if not indices_to_snapshot:
                logger.warning("No indices to snapshot after filtering write indices")
                return CreateSnapshotResponse(
                    snapshot=request.snapshot,
                    repository=request.repository,
                    uuid=None,
                    state=None,
                    indices=[],
                    skipped_write_indices=skipped_write_indices,
                    shards=None,
                    accepted=False,
                    success=False,
                    message="No indices to snapshot - all requested indices are currently being written to",
                )

        # Build the snapshot body
        body = {}

        if indices_to_snapshot:
            body["indices"] = ",".join(indices_to_snapshot)

        if request.ignore_unavailable is not None:
            body["ignore_unavailable"] = request.ignore_unavailable

        if request.include_global_state is not None:
            body["include_global_state"] = request.include_global_state

        if request.partial is not None:
            body["partial"] = request.partial

        if request.metadata:
            # Add skipped indices to metadata for reference
            metadata = request.metadata.copy()
            if skipped_write_indices:
                metadata["skipped_write_indices"] = skipped_write_indices
            body["metadata"] = metadata
        elif skipped_write_indices:
            body["metadata"] = {"skipped_write_indices": skipped_write_indices}

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

            message = f"Successfully created snapshot {request.snapshot}"
            if skipped_write_indices:
                message += f" (skipped {len(skipped_write_indices)} write indices)"

            logger.info(message)

            return CreateSnapshotResponse(
                snapshot=snapshot_data.get("snapshot", request.snapshot),
                repository=request.repository,
                uuid=snapshot_data.get("uuid"),
                state=snapshot_data.get("state"),
                indices=snapshot_data.get("indices", []),
                skipped_write_indices=skipped_write_indices,
                shards=shards_info,
                accepted=True,
                success=True,
                message=message,
            )
        else:
            # When not waiting, we get an accepted response
            accepted = response.get("accepted", False)

            message = f"Snapshot {request.snapshot} creation initiated"
            if skipped_write_indices:
                message += f" (skipped {len(skipped_write_indices)} write indices)"

            logger.info(message)

            return CreateSnapshotResponse(
                snapshot=request.snapshot,
                repository=request.repository,
                uuid=None,
                state="IN_PROGRESS",
                indices=indices_to_snapshot or [],
                skipped_write_indices=skipped_write_indices,
                shards=None,
                accepted=accepted,
                success=accepted,
                message=message if accepted else "Snapshot request was not accepted",
            )

    except Exception as e:
        logger.error(f"Failed to create snapshot {request.snapshot}: {e}")
        return CreateSnapshotResponse(
            snapshot=request.snapshot,
            repository=request.repository,
            uuid=None,
            state=None,
            indices=[],
            skipped_write_indices=[],
            shards=None,
            accepted=False,
            success=False,
            message=f"Failed to create snapshot: {str(e)}",
        )



async def create_snapshot_schedule(
    request: SnapshotScheduleCreate,
    session: AsyncSession,
) -> SnapshotScheduleOperationResponse:
    """
    Create a new snapshot schedule.

    Args:
        request: SnapshotScheduleCreate containing schedule parameters.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Response containing the created schedule.
    """
    logger.info(f"Creating snapshot schedule: {request.name}")

    try:
        schedule = SnapshotSchedule(
            name=request.name,
            index_pattern=request.index_pattern,
            repository=request.repository,
            enabled=request.enabled if request.enabled is not None else True,
            snapshot_prefix=request.snapshot_prefix or "scheduled",
            include_global_state=request.include_global_state if request.include_global_state is not None else False,
            skip_write_indices=request.skip_write_indices if request.skip_write_indices is not None else True,
            retention_days=request.retention_days,
        )

        session.add(schedule)
        await session.commit()
        await session.refresh(schedule)

        logger.info(f"Successfully created snapshot schedule: {schedule.name} (ID: {schedule.id})")

        return SnapshotScheduleOperationResponse(
            schedule=_schedule_to_response(schedule),
            success=True,
            message=f"Successfully created snapshot schedule: {schedule.name}",
        )

    except Exception as e:
        logger.error(f"Failed to create snapshot schedule: {e}")
        await session.rollback()
        return SnapshotScheduleOperationResponse(
            schedule=None,
            success=False,
            message=f"Failed to create snapshot schedule: {str(e)}",
        )


async def list_snapshot_schedules(
    session: AsyncSession,
    enabled_only: bool = False,
) -> SnapshotScheduleListResponse:
    """
    List all snapshot schedules.

    Args:
        session: Database session.
        enabled_only: If True, only return enabled schedules.

    Returns:
        SnapshotScheduleListResponse: Response containing list of schedules.
    """
    logger.info("Fetching snapshot schedules")

    try:
        query = select(SnapshotSchedule)
        if enabled_only:
            query = query.where(SnapshotSchedule.enabled == True)

        result = await session.execute(query)
        schedules = result.scalars().all()

        schedule_responses = [_schedule_to_response(s) for s in schedules]

        logger.info(f"Successfully retrieved {len(schedule_responses)} snapshot schedules")

        return SnapshotScheduleListResponse(
            schedules=schedule_responses,
            success=True,
            message=f"Successfully retrieved {len(schedule_responses)} snapshot schedules",
        )

    except Exception as e:
        logger.error(f"Failed to list snapshot schedules: {e}")
        return SnapshotScheduleListResponse(
            schedules=[],
            success=False,
            message=f"Failed to list snapshot schedules: {str(e)}",
        )


async def get_snapshot_schedule(
    schedule_id: int,
    session: AsyncSession,
) -> SnapshotScheduleOperationResponse:
    """
    Get a snapshot schedule by ID.

    Args:
        schedule_id: ID of the schedule to retrieve.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Response containing the schedule.
    """
    logger.info(f"Fetching snapshot schedule ID: {schedule_id}")

    try:
        result = await session.execute(
            select(SnapshotSchedule).where(SnapshotSchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            return SnapshotScheduleOperationResponse(
                schedule=None,
                success=False,
                message=f"Snapshot schedule with ID {schedule_id} not found",
            )

        return SnapshotScheduleOperationResponse(
            schedule=_schedule_to_response(schedule),
            success=True,
            message=f"Successfully retrieved snapshot schedule: {schedule.name}",
        )

    except Exception as e:
        logger.error(f"Failed to get snapshot schedule: {e}")
        return SnapshotScheduleOperationResponse(
            schedule=None,
            success=False,
            message=f"Failed to get snapshot schedule: {str(e)}",
        )


async def update_snapshot_schedule(
    schedule_id: int,
    request: SnapshotScheduleUpdate,
    session: AsyncSession,
) -> SnapshotScheduleOperationResponse:
    """
    Update a snapshot schedule.

    Args:
        schedule_id: ID of the schedule to update.
        request: SnapshotScheduleUpdate containing fields to update.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Response containing the updated schedule.
    """
    logger.info(f"Updating snapshot schedule ID: {schedule_id}")

    try:
        result = await session.execute(
            select(SnapshotSchedule).where(SnapshotSchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            return SnapshotScheduleOperationResponse(
                schedule=None,
                success=False,
                message=f"Snapshot schedule with ID {schedule_id} not found",
            )

        # Update fields if provided
        if request.name is not None:
            schedule.name = request.name
        if request.index_pattern is not None:
            schedule.index_pattern = request.index_pattern
        if request.repository is not None:
            schedule.repository = request.repository
        if request.enabled is not None:
            schedule.enabled = request.enabled
        if request.snapshot_prefix is not None:
            schedule.snapshot_prefix = request.snapshot_prefix
        if request.include_global_state is not None:
            schedule.include_global_state = request.include_global_state
        if request.skip_write_indices is not None:
            schedule.skip_write_indices = request.skip_write_indices
        if request.retention_days is not None:
            schedule.retention_days = request.retention_days

        schedule.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(schedule)

        logger.info(f"Successfully updated snapshot schedule: {schedule.name}")

        return SnapshotScheduleOperationResponse(
            schedule=_schedule_to_response(schedule),
            success=True,
            message=f"Successfully updated snapshot schedule: {schedule.name}",
        )

    except Exception as e:
        logger.error(f"Failed to update snapshot schedule: {e}")
        await session.rollback()
        return SnapshotScheduleOperationResponse(
            schedule=None,
            success=False,
            message=f"Failed to update snapshot schedule: {str(e)}",
        )


async def delete_snapshot_schedule(
    schedule_id: int,
    session: AsyncSession,
) -> SnapshotScheduleOperationResponse:
    """
    Delete a snapshot schedule.

    Args:
        schedule_id: ID of the schedule to delete.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Response indicating success or failure.
    """
    logger.info(f"Deleting snapshot schedule ID: {schedule_id}")

    try:
        result = await session.execute(
            select(SnapshotSchedule).where(SnapshotSchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            return SnapshotScheduleOperationResponse(
                schedule=None,
                success=False,
                message=f"Snapshot schedule with ID {schedule_id} not found",
            )

        schedule_name = schedule.name
        await session.delete(schedule)
        await session.commit()

        logger.info(f"Successfully deleted snapshot schedule: {schedule_name}")

        return SnapshotScheduleOperationResponse(
            schedule=None,
            success=True,
            message=f"Successfully deleted snapshot schedule: {schedule_name}",
        )

    except Exception as e:
        logger.error(f"Failed to delete snapshot schedule: {e}")
        await session.rollback()
        return SnapshotScheduleOperationResponse(
            schedule=None,
            success=False,
            message=f"Failed to delete snapshot schedule: {str(e)}",
        )

async def get_snapshotted_indices_for_schedule(
    schedule: SnapshotSchedule,
) -> set[str]:
    """
    Get all indices that have already been snapshotted for a given schedule.

    Args:
        schedule: The snapshot schedule to check.

    Returns:
        Set of index names that have already been snapshotted.
    """
    logger.info(f"Fetching previously snapshotted indices for schedule: {schedule.name}")

    snapshotted_indices: set[str] = set()

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # List all snapshots in the repository
        response = es_client.snapshot.get(
            repository=schedule.repository,
            snapshot="_all",
            ignore_unavailable=True,
        )

        # Build the prefix pattern for this schedule's snapshots
        prefix = f"{schedule.snapshot_prefix}_{schedule.name}_".lower().replace(" ", "_")

        for snap_data in response.get("snapshots", []):
            snapshot_name = snap_data.get("snapshot", "")

            # Only consider snapshots created by this schedule
            if snapshot_name.startswith(prefix):
                indices = snap_data.get("indices", [])
                snapshotted_indices.update(indices)

        logger.info(
            f"Found {len(snapshotted_indices)} previously snapshotted indices "
            f"for schedule {schedule.name}"
        )

        return snapshotted_indices

    except Exception as e:
        logger.error(f"Failed to get snapshotted indices for schedule {schedule.name}: {e}")
        return set()

async def get_indices_needing_snapshot(
    schedule: SnapshotSchedule,
) -> tuple[list[str], list[str], list[str]]:
    """
    Determine which indices need to be snapshotted based on the schedule's index pattern.

    This function:
    1. Gets all indices matching the schedule's pattern
    2. Filters out write indices (if configured)
    3. Filters out indices that have already been snapshotted

    Args:
        schedule: The snapshot schedule.

    Returns:
        Tuple of (indices_to_snapshot, skipped_write_indices, already_snapshotted_indices).
    """
    logger.info(f"Determining indices needing snapshot for schedule: {schedule.name}")

    # Get all indices from the cluster
    all_indices = await get_all_indices()

    # Filter indices matching the schedule's pattern
    matching_indices = []
    pattern = schedule.index_pattern
    if "*" in pattern:
        regex_pattern = pattern.replace("*", ".*")
        for index_name in all_indices:
            if re.match(f"^{regex_pattern}$", index_name):
                matching_indices.append(index_name)
    else:
        if pattern in all_indices:
            matching_indices.append(pattern)

    logger.info(f"Found {len(matching_indices)} indices matching pattern '{pattern}'")

    # Identify write indices
    write_status = identify_write_indices(all_indices)

    # Get previously snapshotted indices
    previously_snapshotted = await get_snapshotted_indices_for_schedule(schedule)

    # Categorize indices
    indices_to_snapshot = []
    skipped_write_indices = []
    already_snapshotted_indices = []

    for index_name in matching_indices:
        status = write_status.get(index_name)

        # Check if it's a write index
        if schedule.skip_write_indices and status and status.is_write_index:
            skipped_write_indices.append(index_name)
            logger.debug(f"Skipping write index: {index_name}")
            continue

        # Check if already snapshotted
        if index_name in previously_snapshotted:
            already_snapshotted_indices.append(index_name)
            logger.debug(f"Skipping already snapshotted index: {index_name}")
            continue

        # This index needs to be snapshotted
        indices_to_snapshot.append(index_name)

    logger.info(
        f"Schedule {schedule.name}: "
        f"{len(indices_to_snapshot)} to snapshot, "
        f"{len(skipped_write_indices)} write indices skipped, "
        f"{len(already_snapshotted_indices)} already snapshotted"
    )

    return indices_to_snapshot, skipped_write_indices, already_snapshotted_indices

async def execute_snapshot_schedule(
    schedule: SnapshotSchedule,
    session: AsyncSession,
) -> ScheduledSnapshotExecutionResponse:
    """
    Execute a single snapshot schedule.

    Args:
        schedule: The schedule to execute.
        session: Database session.

    Returns:
        ScheduledSnapshotExecutionResponse: Response containing execution details.
    """
    logger.info(f"Executing snapshot schedule: {schedule.name} (ID: {schedule.id})")

    try:
        # Determine which indices need to be snapshotted
        indices_to_snapshot, skipped_write_indices, already_snapshotted = await get_indices_needing_snapshot(
            schedule
        )

        # If no new indices to snapshot, skip this execution
        if not indices_to_snapshot:
            message = "No new indices to snapshot"
            if skipped_write_indices:
                message += f" ({len(skipped_write_indices)} write indices skipped)"
            if already_snapshotted:
                message += f" ({len(already_snapshotted)} already snapshotted)"

            logger.info(f"Schedule {schedule.name}: {message}")

            # Update schedule with execution results
            schedule.last_execution_time = datetime.utcnow()
            schedule.last_execution_status = f"SKIPPED: {message}"
            schedule.updated_at = datetime.utcnow()

            await session.commit()

            return ScheduledSnapshotExecutionResponse(
                schedule_id=schedule.id,
                schedule_name=schedule.name,
                snapshot_name=None,
                indices_snapshotted=[],
                skipped_write_indices=skipped_write_indices,
                success=True,  # Not a failure, just nothing to do
                message=message,
            )

        # Generate snapshot name with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"{schedule.snapshot_prefix}_{schedule.name}_{timestamp}".lower().replace(" ", "_")

        # Create the snapshot request with specific indices (not patterns)
        request = CreateSnapshotRequest(
            repository=schedule.repository,
            snapshot=snapshot_name,
            indices=indices_to_snapshot,  # Use the specific indices, not the pattern
            ignore_unavailable=True,
            include_global_state=schedule.include_global_state,
            partial=False,
            wait_for_completion=False,
            skip_write_indices=False,  # Already filtered above
            metadata={
                "schedule_id": schedule.id,
                "schedule_name": schedule.name,
                "created_by": "scheduled_job",
                "skipped_write_indices": skipped_write_indices,
                "already_snapshotted_count": len(already_snapshotted),
            },
        )

        # Execute the snapshot
        response = await create_snapshot(request)

        # Update schedule with execution results
        schedule.last_execution_time = datetime.utcnow()
        schedule.last_snapshot_name = snapshot_name if response.success else None
        schedule.last_execution_status = "SUCCESS" if response.success else f"FAILED: {response.message}"
        schedule.updated_at = datetime.utcnow()

        await session.commit()

        if response.success:
            logger.info(
                f"Successfully executed schedule {schedule.name}: "
                f"snapshot={snapshot_name}, "
                f"indices={len(indices_to_snapshot)}, "
                f"skipped_write={len(skipped_write_indices)}, "
                f"already_snapshotted={len(already_snapshotted)}"
            )
        else:
            logger.error(f"Failed to execute schedule {schedule.name}: {response.message}")

        return ScheduledSnapshotExecutionResponse(
            schedule_id=schedule.id,
            schedule_name=schedule.name,
            snapshot_name=snapshot_name if response.success else None,
            indices_snapshotted=indices_to_snapshot if response.success else [],
            skipped_write_indices=skipped_write_indices,
            success=response.success,
            message=response.message,
        )

    except Exception as e:
        logger.error(f"Failed to execute snapshot schedule {schedule.name}: {e}")

        # Update schedule with failure status
        schedule.last_execution_time = datetime.utcnow()
        schedule.last_execution_status = f"FAILED: {str(e)}"
        schedule.updated_at = datetime.utcnow()

        try:
            await session.commit()
        except Exception:
            pass

        return ScheduledSnapshotExecutionResponse(
            schedule_id=schedule.id,
            schedule_name=schedule.name,
            snapshot_name=None,
            indices_snapshotted=[],
            skipped_write_indices=[],
            success=False,
            message=f"Failed to execute snapshot schedule: {str(e)}",
        )


async def execute_all_enabled_schedules() -> List[ScheduledSnapshotExecutionResponse]:
    """
    Execute all enabled snapshot schedules.

    Returns:
        List of execution responses for each schedule.
    """
    logger.info("Executing all enabled snapshot schedules")

    results: List[ScheduledSnapshotExecutionResponse] = []

    async with get_db_session() as session:
        # Get all enabled schedules
        result = await session.execute(
            select(SnapshotSchedule).where(SnapshotSchedule.enabled == True)
        )
        schedules = result.scalars().all()

        logger.info(f"Found {len(schedules)} enabled snapshot schedules")

        for schedule in schedules:
            execution_result = await execute_snapshot_schedule(schedule, session)
            results.append(execution_result)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    logger.info(f"Completed scheduled snapshots: {successful} successful, {failed} failed")

    return results


async def cleanup_old_snapshots(
    schedule: SnapshotSchedule,
) -> Dict[str, any]:
    """
    Clean up old snapshots based on retention policy.

    Args:
        schedule: The schedule with retention settings.

    Returns:
        Dictionary with cleanup results.
    """
    if not schedule.retention_days:
        return {"deleted": 0, "message": "No retention policy configured"}

    logger.info(
        f"Cleaning up snapshots for schedule {schedule.name} "
        f"(retention: {schedule.retention_days} days)"
    )

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # List snapshots in the repository
        response = es_client.snapshot.get(
            repository=schedule.repository,
            snapshot="_all",
            ignore_unavailable=True,
        )

        snapshots_to_delete = []
        cutoff_time = datetime.utcnow() - timedelta(days=schedule.retention_days)
        cutoff_millis = int(cutoff_time.timestamp() * 1000)

        # Find snapshots matching this schedule's prefix that are older than retention
        prefix = f"{schedule.snapshot_prefix}_{schedule.name}_".lower().replace(" ", "_")

        for snap_data in response.get("snapshots", []):
            snapshot_name = snap_data.get("snapshot", "")
            end_time_millis = snap_data.get("end_time_in_millis", 0)

            if snapshot_name.startswith(prefix) and end_time_millis < cutoff_millis:
                snapshots_to_delete.append(snapshot_name)

        # Delete old snapshots
        deleted_count = 0
        for snapshot_name in snapshots_to_delete:
            try:
                es_client.snapshot.delete(
                    repository=schedule.repository,
                    snapshot=snapshot_name,
                )
                deleted_count += 1
                logger.info(f"Deleted old snapshot: {snapshot_name}")
            except Exception as e:
                logger.error(f"Failed to delete snapshot {snapshot_name}: {e}")

        return {
            "deleted": deleted_count,
            "message": f"Deleted {deleted_count} snapshots older than {schedule.retention_days} days",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup snapshots for schedule {schedule.name}: {e}")
        return {"deleted": 0, "message": f"Cleanup failed: {str(e)}"}
