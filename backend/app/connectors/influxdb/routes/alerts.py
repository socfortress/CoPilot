from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.alerts import AlertStatus
from app.connectors.influxdb.schema.alerts import GetInfluxDBAlertQueryParams
from app.connectors.influxdb.schema.alerts import InfluxDBAlertResponse
from app.connectors.influxdb.schema.alerts import InfluxDBCheckNamesResponse
from app.connectors.influxdb.schema.alerts import SeverityFilter
from app.connectors.influxdb.services.alerts import get_influxdb_alerts
from app.connectors.influxdb.services.alerts import get_influxdb_check_names
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
    severity: Optional[List[SeverityFilter]] = Query(None, description="Filter by severity (can specify multiple)"),
    check_name: Optional[str] = Query(None, description="Filter by check name"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    status: AlertStatus = Query(AlertStatus.ALL, description="Filter by status: active, cleared, or all"),
    latest_only: bool = Query(False, description="Return only latest alert per check"),
    exclude_ok: bool = Query(False, description="Exclude alerts with 'ok' status"),
    limit: Optional[int] = Query(500, ge=1, le=1000, description="Limit the number of returned alerts"),
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
        limit=limit,
    )

    return await get_influxdb_alerts(query_params, session)


@influxdb_alerts_router.get(
    "/check-names",
    response_model=InfluxDBCheckNamesResponse,
    description="Get available check names from InfluxDB",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_check_names_route(
    session: AsyncSession = Depends(get_db),
) -> InfluxDBCheckNamesResponse:
    """
    Get a list of all available check names from InfluxDB.

    This endpoint retrieves unique check names from the last 30 days,
    useful for populating filter dropdowns or autocomplete fields.

    **Returns:**
    - List of unique check names (sorted alphabetically)
    - Total count of check names
    """
    return await get_influxdb_check_names(session)
