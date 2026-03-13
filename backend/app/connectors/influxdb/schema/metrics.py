from datetime import datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class TimeSeriesPoint(BaseModel):
    """A single time-series data point."""

    time: datetime
    field: str
    value: float
    label: Optional[str] = None


class TimeSeriesData(BaseModel):
    """Time-series data grouped by field/label."""

    series: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="Mapping of series name to list of {time, value} points",
    )


class MetricsResponse(BaseModel):
    """Generic response for metrics endpoints."""

    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class HostsResponse(BaseModel):
    """Response for listing available hosts."""

    success: bool
    message: str
    hosts: list[str] = Field(default_factory=list)
