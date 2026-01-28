from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import CreateSnapshotResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotRequest
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import RestoreSnapshotResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleCreate
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleListResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleOperationResponse
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotScheduleUpdate
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotStatusResponse
from app.connectors.wazuh_indexer.services.snapshot_and_restore import create_snapshot
from app.connectors.wazuh_indexer.services.snapshot_and_restore import create_snapshot_schedule
from app.connectors.wazuh_indexer.services.snapshot_and_restore import delete_snapshot_schedule
from app.connectors.wazuh_indexer.services.snapshot_and_restore import get_snapshot_schedule
from app.connectors.wazuh_indexer.services.snapshot_and_restore import get_snapshot_status
from app.connectors.wazuh_indexer.services.snapshot_and_restore import list_snapshot_repositories
from app.connectors.wazuh_indexer.services.snapshot_and_restore import list_snapshot_schedules
from app.connectors.wazuh_indexer.services.snapshot_and_restore import list_snapshots
from app.connectors.wazuh_indexer.services.snapshot_and_restore import restore_snapshot
from app.connectors.wazuh_indexer.services.snapshot_and_restore import update_snapshot_schedule
from app.db.db_session import get_db
from app.auth.routes.auth import AuthHandler
wazuh_indexer_snapshots_router = APIRouter()
auth_handler = AuthHandler()


@wazuh_indexer_snapshots_router.get(
    "/repositories",
    response_model=SnapshotRepositoryListResponse,
    summary="List Snapshot Repositories",
    description="Retrieve a list of all configured snapshot repositories in the Wazuh Indexer.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
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
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
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


@wazuh_indexer_snapshots_router.get(
    "/repositories/{repository}/snapshots",
    response_model=SnapshotListResponse,
    summary="List Snapshots",
    description="Retrieve a list of all snapshots in a specific repository.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],

)
async def get_snapshots(
    repository: str = Path(
        ...,
        description="Name of the repository to list snapshots from.",
    ),
) -> SnapshotListResponse:
    """
    List all snapshots in a repository.

    Args:
        repository: Name of the repository.

    Returns:
        SnapshotListResponse: List of snapshots in the repository.
    """
    logger.info(f"Received request to list snapshots in repository: {repository}")

    response = await list_snapshots(repository=repository)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response

@wazuh_indexer_snapshots_router.post(
    "/create",
    response_model=CreateSnapshotResponse,
    summary="Create Snapshot",
    description="Create a new snapshot in a repository.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def create_snapshot_endpoint(
    request: CreateSnapshotRequest,
) -> CreateSnapshotResponse:
    """
    Create a new snapshot in a repository.

    Args:
        request: CreateSnapshotRequest containing snapshot parameters.

    Returns:
        CreateSnapshotResponse: Details of the snapshot creation operation.
    """
    logger.info(
        f"Received request to create snapshot {request.snapshot} "
        f"in repository {request.repository}",
    )

    response = await create_snapshot(request=request)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.post(
    "/restore",
    response_model=RestoreSnapshotResponse,
    summary="Restore Snapshot",
    description="Restore a snapshot from a repository.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def restore_snapshot_endpoint(
    request: RestoreSnapshotRequest,
) -> RestoreSnapshotResponse:
    """
    Restore a snapshot from a repository.

    Args:
        request: RestoreSnapshotRequest containing restore parameters.

    Returns:
        RestoreSnapshotResponse: Details of the restoration operation.
    """
    logger.info(
        f"Received request to restore snapshot {request.snapshot} "
        f"from repository {request.repository}",
    )

    response = await restore_snapshot(request=request)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response

# Snapshot Schedule Routes
@wazuh_indexer_snapshots_router.post(
    "/schedules",
    response_model=SnapshotScheduleOperationResponse,
    summary="Create Snapshot Schedule",
    description="Create a new scheduled snapshot configuration.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def create_schedule_endpoint(
    request: SnapshotScheduleCreate,
    session: AsyncSession = Depends(get_db),
) -> SnapshotScheduleOperationResponse:
    """
    Create a new snapshot schedule.

    Args:
        request: SnapshotScheduleCreate containing schedule parameters.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Details of the created schedule.
    """
    logger.info(f"Received request to create snapshot schedule: {request.name}")

    response = await create_snapshot_schedule(request=request, session=session)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.get(
    "/schedules",
    response_model=SnapshotScheduleListResponse,
    summary="List Snapshot Schedules",
    description="Retrieve a list of all configured snapshot schedules.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def list_schedules_endpoint(
    enabled_only: bool = Query(
        False,
        description="If true, only return enabled schedules.",
    ),
    session: AsyncSession = Depends(get_db),
) -> SnapshotScheduleListResponse:
    """
    List all snapshot schedules.

    Args:
        enabled_only: Whether to filter to only enabled schedules.
        session: Database session.

    Returns:
        SnapshotScheduleListResponse: List of snapshot schedules.
    """
    logger.info("Received request to list snapshot schedules")

    response = await list_snapshot_schedules(session=session, enabled_only=enabled_only)

    if not response.success:
        raise HTTPException(
            status_code=500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.get(
    "/schedules/{schedule_id}",
    response_model=SnapshotScheduleOperationResponse,
    summary="Get Snapshot Schedule",
    description="Retrieve a specific snapshot schedule by ID.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_schedule_endpoint(
    schedule_id: int = Path(..., description="ID of the schedule to retrieve"),
    session: AsyncSession = Depends(get_db),
) -> SnapshotScheduleOperationResponse:
    """
    Get a snapshot schedule by ID.

    Args:
        schedule_id: ID of the schedule.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: The requested schedule.
    """
    logger.info(f"Received request to get snapshot schedule ID: {schedule_id}")

    response = await get_snapshot_schedule(schedule_id=schedule_id, session=session)

    if not response.success:
        raise HTTPException(
            status_code=404 if "not found" in response.message.lower() else 500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.put(
    "/schedules/{schedule_id}",
    response_model=SnapshotScheduleOperationResponse,
    summary="Update Snapshot Schedule",
    description="Update an existing snapshot schedule.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def update_schedule_endpoint(
    schedule_id: int = Path(..., description="ID of the schedule to update"),
    request: SnapshotScheduleUpdate = ...,
    session: AsyncSession = Depends(get_db),
) -> SnapshotScheduleOperationResponse:
    """
    Update a snapshot schedule.

    Args:
        schedule_id: ID of the schedule to update.
        request: SnapshotScheduleUpdate containing fields to update.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: The updated schedule.
    """
    logger.info(f"Received request to update snapshot schedule ID: {schedule_id}")

    response = await update_snapshot_schedule(
        schedule_id=schedule_id,
        request=request,
        session=session,
    )

    if not response.success:
        raise HTTPException(
            status_code=404 if "not found" in response.message.lower() else 500,
            detail=response.message,
        )

    return response


@wazuh_indexer_snapshots_router.delete(
    "/schedules/{schedule_id}",
    response_model=SnapshotScheduleOperationResponse,
    summary="Delete Snapshot Schedule",
    description="Delete a snapshot schedule.",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def delete_schedule_endpoint(
    schedule_id: int = Path(..., description="ID of the schedule to delete"),
    session: AsyncSession = Depends(get_db),
) -> SnapshotScheduleOperationResponse:
    """
    Delete a snapshot schedule.

    Args:
        schedule_id: ID of the schedule to delete.
        session: Database session.

    Returns:
        SnapshotScheduleOperationResponse: Confirmation of deletion.
    """
    logger.info(f"Received request to delete snapshot schedule ID: {schedule_id}")

    response = await delete_snapshot_schedule(schedule_id=schedule_id, session=session)

    if not response.success:
        raise HTTPException(
            status_code=404 if "not found" in response.message.lower() else 500,
            detail=response.message,
        )

    return response
