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
