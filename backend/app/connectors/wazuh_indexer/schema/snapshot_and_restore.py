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
