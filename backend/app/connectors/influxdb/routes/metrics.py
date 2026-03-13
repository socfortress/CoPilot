from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.influxdb.schema.metrics import HostsResponse
from app.connectors.influxdb.schema.metrics import MetricsResponse
from app.connectors.influxdb.services.metrics import get_cpu_metrics
from app.connectors.influxdb.services.metrics import get_disk_metrics
from app.connectors.influxdb.services.metrics import get_hosts
from app.connectors.influxdb.services.metrics import get_kernel_metrics
from app.connectors.influxdb.services.metrics import get_memory_metrics
from app.connectors.influxdb.services.metrics import get_network_metrics
from app.connectors.influxdb.services.metrics import get_process_metrics
from app.connectors.influxdb.services.metrics import get_summary
from app.db.db_session import get_db

influxdb_metrics_router = APIRouter()


@influxdb_metrics_router.get(
    "/hosts",
    response_model=HostsResponse,
    description="Get available hosts from InfluxDB metrics",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_hosts_route(
    session: AsyncSession = Depends(get_db),
) -> HostsResponse:
    """
    Get a list of all hosts reporting metrics to InfluxDB.
    """
    return await get_hosts(session)


@influxdb_metrics_router.get(
    "/summary",
    response_model=MetricsResponse,
    description="Get system summary metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_summary_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get a summary of system metrics for a host including uptime, CPU count,
    memory, processes, swap, and system load time-series.
    """
    return await get_summary(host, range_h, session)


@influxdb_metrics_router.get(
    "/cpu",
    response_model=MetricsResponse,
    description="Get CPU metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_cpu_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get CPU usage time-series: system, user, iowait, and softirq.
    """
    return await get_cpu_metrics(host, range_h, session)


@influxdb_metrics_router.get(
    "/memory",
    response_model=MetricsResponse,
    description="Get memory metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_memory_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get memory usage time-series and swap info.
    """
    return await get_memory_metrics(host, range_h, session)


@influxdb_metrics_router.get(
    "/kernel",
    response_model=MetricsResponse,
    description="Get kernel metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_kernel_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get kernel metrics: interrupts and processes forked (rate per second).
    """
    return await get_kernel_metrics(host, range_h, session)


@influxdb_metrics_router.get(
    "/disks",
    response_model=MetricsResponse,
    description="Get disk metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_disks_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get disk metrics: total size, usage percent by path, I/O throughput by device,
    and inode usage.
    """
    return await get_disk_metrics(host, range_h, session)


@influxdb_metrics_router.get(
    "/processes",
    response_model=MetricsResponse,
    description="Get process metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_processes_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get process metrics: status time-series (running, sleeping, zombies, stopped, blocked)
    and current counts per state.
    """
    return await get_process_metrics(host, range_h, session)


@influxdb_metrics_router.get(
    "/network",
    response_model=MetricsResponse,
    description="Get network metrics for a host",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_network_route(
    host: str = Query(..., description="Hostname to retrieve metrics for"),
    range_h: str = Query("1", description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get network metrics: traffic (bytes/sec by interface), TCP established connections,
    and interface errors.
    """
    return await get_network_metrics(host, range_h, session)
