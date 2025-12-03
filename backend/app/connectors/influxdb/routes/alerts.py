# from fastapi import APIRouter
# from fastapi import Security
# from loguru import logger

# from app.auth.utils import AuthHandler
# from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
# from app.connectors.influxdb.services.alerts import get_alerts

# # App specific imports


# influxdb_alerts_router = APIRouter()


# @influxdb_alerts_router.get(
#     "/alerts",
#     response_model=InfluxDBAlertsResponse,
#     description="Get influxdb alerts",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def get_all_alerts():
#     """
#     Fetches all alerts from InfluxDB.

#     Returns:
#         InfluxDBAlertsResponse: The response model containing the alerts.
#     """
#     logger.info("Fetching all alerts from influxdb")
#     return await get_alerts()

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.alerts import (
    GetInfluxDBAlertQueryParams,
    InfluxDBAlertResponse,
    SeverityFilter,
    AlertStatus,
)
from app.connectors.influxdb.services.alerts import get_influxdb_alerts
from app.db.db_session import get_db

influxdb_alerts_router = APIRouter()


@influxdb_alerts_router.get(
    "/alerts",
    response_model=InfluxDBAlertResponse,
    description="Get alerts from InfluxDB with advanced filtering",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_alerts_route(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    severity: Optional[List[SeverityFilter]] = Query(
        None,
        description="Filter by severity (can specify multiple)"
    ),
    check_name: Optional[str] = Query(None, description="Filter by check name"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    status: AlertStatus = Query(
        AlertStatus.ALL,
        description="Filter by status: active, cleared, or all"
    ),
    latest_only: bool = Query(
        False,
        description="Return only latest alert per check"
    ),
    exclude_ok: bool = Query(
        False,
        description="Exclude alerts with 'ok' status"
    ),
    session: AsyncSession = Depends(get_db),
) -> InfluxDBAlertResponse:
    """
    Get alerts from InfluxDB with advanced filtering options.

    The connector is always 'InfluxDB' and doesn't need to be specified.

    **Filtering Options:**
    - `severity`: Filter by severity levels (ok, warning, error, critical)
    - `check_name`: Filter by specific check name (e.g., "CPU CHECK", "Host Offline")
    - `sensor_type`: Filter by sensor type keyword
    - `status`: Show only active alerts, cleared alerts, or all
    - `latest_only`: Show only the latest alert per check
    - `exclude_ok`: Automatically exclude 'ok' status alerts for a cleaner view

    **Common Use Cases:**
    - See only current issues: `exclude_ok=true` or `status=active`
    - Latest status per check: `latest_only=true`
    - Active alerts only: `status=active` (shows alerts that haven't been cleared)
    """
    query_params = GetInfluxDBAlertQueryParams(
        days=days,
        severity=severity,
        check_name=check_name,
        sensor_type=sensor_type,
        status=status,
        latest_only=latest_only,
        exclude_ok=exclude_ok,
    )

    return await get_influxdb_alerts(query_params, session)
