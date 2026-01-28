from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SnapshotRepositorySettings(BaseModel):
    """Settings for a snapshot repository."""
    location: Optional[str] = Field(None, description="Repository location/path")
    compress: Optional[bool] = Field(None, description="Whether snapshots are compressed")
    chunk_size: Optional[str] = Field(None, description="Chunk size for snapshot files")
    max_restore_bytes_per_sec: Optional[str] = Field(None, description="Max restore rate")
    max_snapshot_bytes_per_sec: Optional[str] = Field(None, description="Max snapshot rate")
    readonly: Optional[bool] = Field(None, description="Whether repository is read-only")


class SnapshotRepository(BaseModel):
    """Model for a single snapshot repository."""
    name: str = Field(..., description="Name of the repository")
    type: str = Field(..., description="Type of the repository (fs, s3, etc.)")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Repository settings")


class SnapshotRepositoryListResponse(BaseModel):
    """Response model for listing snapshot repositories."""
    repositories: List[SnapshotRepository] = Field(
        default_factory=list,
        description="List of snapshot repositories",
    )
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class SnapshotShardStatus(BaseModel):
    """Status of a single shard in a snapshot."""
    stage: str = Field(..., description="Current stage of the shard snapshot")
    total_files: Optional[int] = Field(None, alias="total_file_count", description="Total number of files")
    total_size_in_bytes: Optional[int] = Field(None, description="Total size in bytes")
    processed_files: Optional[int] = Field(None, alias="processed_file_count", description="Processed files count")
    processed_size_in_bytes: Optional[int] = Field(None, alias="done_size_in_bytes", description="Processed size in bytes")


class SnapshotIndexStatus(BaseModel):
    """Status of an index within a snapshot."""
    shards_stats: Dict[str, Any] = Field(default_factory=dict, description="Shard statistics")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Index statistics")
    shards: Dict[str, SnapshotShardStatus] = Field(default_factory=dict, description="Individual shard statuses")


class SnapshotStatus(BaseModel):
    """Status of a single snapshot."""
    snapshot: str = Field(..., description="Name of the snapshot")
    repository: str = Field(..., description="Repository containing the snapshot")
    uuid: Optional[str] = Field(None, description="UUID of the snapshot")
    state: str = Field(..., description="Current state of the snapshot")
    include_global_state: Optional[bool] = Field(None, description="Whether global state is included")
    shards_stats: Dict[str, Any] = Field(default_factory=dict, description="Shard statistics")
    stats: Dict[str, Any] = Field(default_factory=dict, description="Snapshot statistics")
    indices: Dict[str, SnapshotIndexStatus] = Field(default_factory=dict, description="Index statuses")


class SnapshotStatusResponse(BaseModel):
    """Response model for snapshot status."""
    snapshots: List[SnapshotStatus] = Field(
        default_factory=list,
        description="List of snapshot statuses",
    )
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


# Models for listing snapshots
class SnapshotInfo(BaseModel):
    """Information about a single snapshot."""
    snapshot: str = Field(..., description="Name of the snapshot")
    uuid: Optional[str] = Field(None, description="UUID of the snapshot")
    version_id: Optional[int] = Field(None, description="Version ID")
    version: Optional[str] = Field(None, description="OpenSearch version")
    indices: List[str] = Field(default_factory=list, description="List of indices in the snapshot")
    include_global_state: Optional[bool] = Field(None, description="Whether global state is included")
    state: str = Field(..., description="State of the snapshot")
    start_time: Optional[str] = Field(None, description="Start time of the snapshot")
    start_time_in_millis: Optional[int] = Field(None, description="Start time in milliseconds")
    end_time: Optional[str] = Field(None, description="End time of the snapshot")
    end_time_in_millis: Optional[int] = Field(None, description="End time in milliseconds")
    duration_in_millis: Optional[int] = Field(None, description="Duration in milliseconds")
    failures: List[Dict[str, Any]] = Field(default_factory=list, description="List of failures")
    shards: Dict[str, Any] = Field(default_factory=dict, description="Shard information")


class SnapshotListResponse(BaseModel):
    """Response model for listing snapshots."""
    repository: str = Field(..., description="Repository name")
    snapshots: List[SnapshotInfo] = Field(
        default_factory=list,
        description="List of snapshots in the repository",
    )
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


# Models for restoring snapshots
class RestoreSnapshotRequest(BaseModel):
    """Request model for restoring a snapshot."""
    repository: str = Field(..., description="Repository name containing the snapshot")
    snapshot: str = Field(..., description="Name of the snapshot to restore")
    indices: Optional[List[str]] = Field(
        None,
        description="List of indices to restore. If not specified, all indices are restored.",
    )
    ignore_unavailable: Optional[bool] = Field(
        True,
        description="Whether to ignore unavailable indices",
    )
    include_global_state: Optional[bool] = Field(
        False,
        description="Whether to restore the global state",
    )
    rename_pattern: Optional[str] = Field(
        None,
        description="Pattern to match indices to rename",
        example="wazuh_(.+)",
    )
    rename_replacement: Optional[str] = Field(
        None,
        description="Replacement string for renamed indices",
        example="restored_wazuh_$1",
    )
    include_aliases: Optional[bool] = Field(
        True,
        description="Whether to restore aliases",
    )
    partial: Optional[bool] = Field(
        False,
        description="Whether to allow partial restore",
    )


class RestoreShardInfo(BaseModel):
    """Information about restored shards."""
    total: int = Field(..., description="Total number of shards")
    failed: int = Field(..., description="Number of failed shards")
    successful: int = Field(..., description="Number of successful shards")


class RestoreIndexInfo(BaseModel):
    """Information about a restored index."""
    index: str = Field(..., description="Index name")
    shards: RestoreShardInfo = Field(..., description="Shard restoration info")


class RestoreSnapshotResponse(BaseModel):
    """Response model for snapshot restoration."""
    snapshot: str = Field(..., description="Name of the restored snapshot")
    repository: str = Field(..., description="Repository name")
    indices: List[str] = Field(default_factory=list, description="List of restored indices")
    shards: RestoreShardInfo = Field(..., description="Overall shard restoration info")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")

# Models for creating snapshots
class IndexWriteStatus(BaseModel):
    """Status of an index regarding write activity."""
    index_name: str = Field(..., description="Name of the index")
    is_write_index: bool = Field(..., description="Whether this is the current write index")
    index_number: Optional[int] = Field(None, description="Extracted index number from naming convention")
    base_name: Optional[str] = Field(None, description="Base name without the index number")


class CreateSnapshotRequest(BaseModel):
    """Request model for creating a snapshot."""
    repository: str = Field(..., description="Repository name to store the snapshot")
    snapshot: str = Field(..., description="Name of the snapshot to create")
    indices: Optional[List[str]] = Field(
        None,
        description="List of indices to include in the snapshot. If not specified, all indices are included.",
    )
    ignore_unavailable: Optional[bool] = Field(
        False,
        description="Whether to ignore unavailable indices",
    )
    include_global_state: Optional[bool] = Field(
        True,
        description="Whether to include the global cluster state in the snapshot",
    )
    partial: Optional[bool] = Field(
        False,
        description="Whether to allow partial snapshots",
    )
    wait_for_completion: Optional[bool] = Field(
        False,
        description="Whether to wait for the snapshot to complete before returning",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom metadata to attach to the snapshot",
    )
    skip_write_indices: Optional[bool] = Field(
        True,
        description="Whether to skip indices that are currently being written to (Graylog active indices)",
    )


class CreateSnapshotResponse(BaseModel):
    """Response model for snapshot creation."""
    snapshot: str = Field(..., description="Name of the created snapshot")
    repository: str = Field(..., description="Repository name")
    uuid: Optional[str] = Field(None, description="UUID of the snapshot")
    state: Optional[str] = Field(None, description="Current state of the snapshot")
    indices: List[str] = Field(default_factory=list, description="List of indices in the snapshot")
    skipped_write_indices: List[str] = Field(
        default_factory=list,
        description="List of indices skipped because they are currently being written to",
    )
    shards: Optional[RestoreShardInfo] = Field(None, description="Shard information (if wait_for_completion=true)")
    accepted: bool = Field(..., description="Whether the snapshot request was accepted")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


# Models for scheduled snapshots
class SnapshotScheduleCreate(BaseModel):
    """Request model for creating a snapshot schedule."""
    name: str = Field(..., description="Friendly name for this schedule")
    index_pattern: str = Field(
        ...,
        description="Index pattern to snapshot (e.g., wazuh_customer_*)",
        example="wazuh_customer_*",
    )
    repository: str = Field(..., description="Repository to store snapshots")
    enabled: Optional[bool] = Field(True, description="Whether this schedule is active")
    snapshot_prefix: Optional[str] = Field(
        "scheduled",
        description="Prefix for snapshot names",
    )
    include_global_state: Optional[bool] = Field(
        False,
        description="Include global cluster state",
    )
    skip_write_indices: Optional[bool] = Field(
        True,
        description="Skip indices currently being written to",
    )
    retention_days: Optional[int] = Field(
        None,
        description="Number of days to retain snapshots (None = forever)",
    )


class SnapshotScheduleUpdate(BaseModel):
    """Request model for updating a snapshot schedule."""
    name: Optional[str] = Field(None, description="Friendly name for this schedule")
    index_pattern: Optional[str] = Field(None, description="Index pattern to snapshot")
    repository: Optional[str] = Field(None, description="Repository to store snapshots")
    enabled: Optional[bool] = Field(None, description="Whether this schedule is active")
    snapshot_prefix: Optional[str] = Field(None, description="Prefix for snapshot names")
    include_global_state: Optional[bool] = Field(None, description="Include global cluster state")
    skip_write_indices: Optional[bool] = Field(None, description="Skip indices currently being written to")
    retention_days: Optional[int] = Field(None, description="Number of days to retain snapshots")


class SnapshotScheduleResponse(BaseModel):
    """Response model for a snapshot schedule."""
    id: int = Field(..., description="Schedule ID")
    name: str = Field(..., description="Friendly name for this schedule")
    index_pattern: str = Field(..., description="Index pattern to snapshot")
    repository: str = Field(..., description="Repository to store snapshots")
    enabled: bool = Field(..., description="Whether this schedule is active")
    snapshot_prefix: str = Field(..., description="Prefix for snapshot names")
    include_global_state: bool = Field(..., description="Include global cluster state")
    skip_write_indices: bool = Field(..., description="Skip indices currently being written to")
    retention_days: Optional[int] = Field(None, description="Number of days to retain snapshots")
    last_execution_time: Optional[str] = Field(None, description="Last execution time")
    last_snapshot_name: Optional[str] = Field(None, description="Name of the last snapshot created")
    last_execution_status: Optional[str] = Field(None, description="Status of the last execution")
    created_at: str = Field(..., description="When this schedule was created")
    updated_at: str = Field(..., description="When this schedule was last updated")


class SnapshotScheduleListResponse(BaseModel):
    """Response model for listing snapshot schedules."""
    schedules: List[SnapshotScheduleResponse] = Field(
        default_factory=list,
        description="List of snapshot schedules",
    )
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class SnapshotScheduleOperationResponse(BaseModel):
    """Response model for snapshot schedule operations."""
    schedule: Optional[SnapshotScheduleResponse] = Field(
        None,
        description="The snapshot schedule",
    )
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")


class ScheduledSnapshotExecutionResponse(BaseModel):
    """Response model for scheduled snapshot execution."""
    schedule_id: int = Field(..., description="Schedule ID that was executed")
    schedule_name: str = Field(..., description="Schedule name")
    snapshot_name: Optional[str] = Field(None, description="Name of the created snapshot")
    indices_snapshotted: List[str] = Field(default_factory=list, description="Indices included in snapshot")
    skipped_write_indices: List[str] = Field(default_factory=list, description="Indices skipped")
    already_snapshotted_indices: List[str] = Field(
        default_factory=list,
        description="Indices skipped because they were already snapshotted",
    )
    success: bool = Field(..., description="Whether the execution was successful")
    message: str = Field(..., description="Status message")
