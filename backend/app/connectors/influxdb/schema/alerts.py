from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class SeverityFilter(str, Enum):
    """Severity levels for filtering"""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status"""

    ACTIVE = "active"
    CLEARED = "cleared"
    ALL = "all"


class GetInfluxDBAlertQueryParams(BaseModel):
    """
    Query parameters for getting InfluxDB alerts with filtering
    """

    days: int = Field(default=7, ge=1, le=90, description="Number of days to look back")
    severity: Optional[list[SeverityFilter]] = Field(default=None, description="Filter by severity levels (can specify multiple)")
    check_name: Optional[str] = Field(default=None, description="Filter by specific check name")
    sensor_type: Optional[str] = Field(default=None, description="Filter by sensor type")
    status: AlertStatus = Field(default=AlertStatus.ALL, description="Filter by alert status (active/cleared/all)")
    latest_only: bool = Field(default=False, description="Return only the latest alert per check")
    exclude_ok: bool = Field(default=False, description="Exclude alerts with 'ok' status")


class InfluxDBAlert(BaseModel):
    """
    Single InfluxDB alert
    """

    time: datetime
    check_name: str
    sensor_type: str
    severity: str
    message: str
    status: Optional[str] = None  # active or cleared
    check_id: Optional[str] = None  # For internal filtering

    class Config:
        from_attributes = True


class InfluxDBAlertResponse(BaseModel):
    """
    Response for InfluxDB alerts query
    """

    success: bool
    message: str
    alerts: list[InfluxDBAlert]
    total_count: int
    filtered_count: int
    active_alerts_count: int = 0
    cleared_alerts_count: int = 0

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully retrieved alerts",
                "alerts": [
                    {
                        "time": "2025-12-01T10:30:00Z",
                        "check_name": "CPU CHECK",
                        "sensor_type": "CPU",
                        "severity": "warning",
                        "message": "CPU usage high",
                        "status": "active",
                    },
                ],
                "total_count": 150,
                "filtered_count": 25,
                "active_alerts_count": 5,
                "cleared_alerts_count": 20,
            },
        }


class InfluxDBAlertsResponse(BaseModel):
    alerts: list[InfluxDBAlert]
    success: bool
    message: str


class InfluxDBCheckNamesResponse(BaseModel):
    """
    Response for available check names query
    """

    success: bool
    message: str
    check_names: list[str]
    total_count: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully retrieved check names",
                "check_names": ["CPU CHECK", "Host Offline", "Memory Usage", "Disk Space"],
                "total_count": 4,
            },
        }
