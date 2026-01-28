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


class CreateSnapshotResponse(BaseModel):
    """Response model for snapshot creation."""
    snapshot: str = Field(..., description="Name of the created snapshot")
    repository: str = Field(..., description="Repository name")
    uuid: Optional[str] = Field(None, description="UUID of the snapshot")
    state: Optional[str] = Field(None, description="Current state of the snapshot")
    indices: List[str] = Field(default_factory=list, description="List of indices in the snapshot")
    shards: Optional[RestoreShardInfo] = Field(None, description="Shard information (if wait_for_completion=true)")
    accepted: bool = Field(..., description="Whether the snapshot request was accepted")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
