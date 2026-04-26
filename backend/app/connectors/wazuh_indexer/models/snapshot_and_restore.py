from datetime import datetime
from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class SnapshotSchedule(SQLModel, table=True):
    __tablename__ = "index_snapshot_schedules"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, description="Friendly name for this schedule")
    index_pattern: str = Field(nullable=False, description="Index pattern to snapshot (e.g., wazuh_customer_*)")
    repository: str = Field(nullable=False, description="Repository to store snapshots")
    enabled: bool = Field(default=True, description="Whether this schedule is active")
    snapshot_prefix: str = Field(default="scheduled", description="Prefix for snapshot names")
    include_global_state: bool = Field(default=False, description="Include global cluster state")
    skip_write_indices: bool = Field(default=True, description="Skip indices currently being written to")
    retention_days: Optional[int] = Field(default=None, description="Number of days to retain snapshots (None = forever)")
    last_execution_time: Optional[datetime] = Field(default=None, description="Last time this schedule was executed")
    last_snapshot_name: Optional[str] = Field(default=None, description="Name of the last snapshot created")
    last_execution_status: Optional[str] = Field(default=None, description="Status of the last execution")
    scheduled_hour: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Hour of day (0-23) when this schedule should run. NULL = any hour (legacy hourly behavior).",
    )
    scheduled_minute: Optional[int] = Field(
        default=None,
        ge=0,
        le=59,
        description="Minute of hour (0-59) when this schedule should run. NULL = any minute.",
    )
    interval_days: int = Field(
        default=1,
        ge=1,
        description="Minimum number of days between executions. Default 1 = at most once per day.",
    )
    day_of_week: Optional[int] = Field(
        default=None,
        ge=0,
        le=6,
        description=(
            "Day of week (0=Monday ... 6=Sunday) when this schedule is allowed to run. "
            "NULL = any day. Combines with interval_days for patterns like 'every other Sunday'."
        ),
    )
    timezone: str = Field(
        default="UTC",
        description="IANA timezone name used to evaluate scheduled_hour/minute (e.g., 'UTC', 'America/New_York').",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When this schedule was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When this schedule was last updated")
