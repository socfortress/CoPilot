import math
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.influxdb.schema.metrics import HostsResponse
from app.connectors.influxdb.schema.metrics import MetricsResponse
from app.connectors.influxdb.utils.universal import create_influxdb_client
from app.connectors.influxdb.utils.universal import get_influxdb_organization
from app.connectors.utils import get_connector_info_from_db


RANGE_WINDOWS = {
    "1": "1m",
    "3": "2m",
    "6": "5m",
    "12": "10m",
    "24": "20m",
    "48": "30m",
    "72": "1h",
    "168": "2h",
    "720": "12h",
}


async def _get_influxdb_bucket(session: AsyncSession) -> str:
    """
    Read the `connector_extra_data` from the database and return the bucket name.
    The extra data format is: `ORG,BUCKET` e.g. `SOCFORTRESS,telegraf`.
    """
    attributes = await get_connector_info_from_db("InfluxDB", session)
    if attributes is None:
        raise ValueError("No InfluxDB connector found in the database")
    parts = attributes["connector_extra_data"].split(",")
    if len(parts) < 2:
        raise ValueError(
            "InfluxDB connector_extra_data must contain 'ORG,BUCKET' "
            f"(got: {attributes['connector_extra_data']})",
        )
    return parts[1].strip()


def _window(range_h: str) -> str:
    """Return an appropriate aggregateWindow interval for the given hour range."""
    return RANGE_WINDOWS.get(range_h, "5m")


def _range_clause(range_h: str) -> str:
    return f"range(start: -{range_h}h)"


def _parse_ts_series(
    result,
    label_field: str = "_field",
) -> dict[str, list[dict[str, Any]]]:
    """
    Convert InfluxDB table results into a dict of named series.
    Each series is a list of {time, value} dicts.
    """
    series: dict[str, list[dict[str, Any]]] = {}
    for table in result:
        for record in table.records:
            label = record.values.get(label_field, record.values.get("_field", "unknown"))
            point = {
                "time": record.get_time().isoformat(),
                "value": record.get_value(),
            }
            series.setdefault(label, []).append(point)
    return series


def _last_value(result) -> Any:
    """Return the scalar _value from the last record, or None."""
    for table in result:
        for record in table.records:
            return record.get_value()
    return None


async def _run_queries(
    influxdb_client,
    org: str,
    queries: dict[str, str],
    ts_keys: set[str] | None = None,
    label_field: str = "_field",
) -> dict[str, Any]:
    """
    Execute a batch of Flux queries and return parsed results.
    Keys in *ts_keys* are parsed as time-series; others as last-value scalars.
    """
    ts_keys = ts_keys or set()
    query_api = influxdb_client.query_api()
    results: dict[str, Any] = {}
    for key, flux in queries.items():
        result = await query_api.query(flux, org=org)
        if key in ts_keys:
            results[key] = _parse_ts_series(result, label_field=label_field)
        else:
            results[key] = _last_value(result)
    return results


# ── Hosts ────────────────────────────────────────────────────────────────


async def get_hosts(session: AsyncSession) -> HostsResponse:
    """Retrieve the list of unique host tag values from the metrics bucket."""
    connector_info = await get_connector_info_from_db("InfluxDB", session)
    if not connector_info:
        return HostsResponse(success=False, message="InfluxDB connector not found", hosts=[])

    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        logger.error(f"Error getting InfluxDB config: {e}")
        return HostsResponse(success=False, message=str(e), hosts=[])

    influxdb_client = await create_influxdb_client("InfluxDB")
    try:
        flux = (
            f'import "influxdata/influxdb/schema"\n'
            f'schema.tagValues(bucket: "{bucket}", tag: "host")'
        )
        query_api = influxdb_client.query_api()
        result = await query_api.query(flux, org=org)
        hosts = sorted(
            {
                record.get_value()
                for table in result
                for record in table.records
                if record.get_value()
            },
        )
        return HostsResponse(success=True, message="Successfully retrieved hosts", hosts=hosts)
    except Exception as e:
        logger.error(f"Error fetching hosts: {e}")
        return HostsResponse(success=False, message=f"Error fetching hosts: {e}", hosts=[])
    finally:
        await influxdb_client.close()


# ── Summary ──────────────────────────────────────────────────────────────


async def get_summary(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve a summary of system metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "uptime": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["_field"] == "uptime")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "total_mem": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "mem")
  |> filter(fn: (r) => r["_field"] == "total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "cpus": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["_field"] == "n_cpus")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "total_processes": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "processes")
  |> filter(fn: (r) => r["_field"] == "total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "cpu_idle": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_idle")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "logged_on_users": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["_field"] == "n_users")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "swap_free": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "swap")
  |> filter(fn: (r) => r["_field"] == "free")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "load": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["_field"] == "load1" or r["_field"] == "load5" or r["_field"] == "load15")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    try:
        data = await _run_queries(influxdb_client, org, queries, ts_keys={"load"})
        return MetricsResponse(success=True, message="Successfully retrieved summary", data=data)
    except Exception as e:
        logger.error(f"Error fetching summary: {e}")
        return MetricsResponse(success=False, message=f"Error fetching summary: {e}")
    finally:
        await influxdb_client.close()


# ── CPU ──────────────────────────────────────────────────────────────────


async def get_cpu_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve CPU time-series metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "cpu_usage_system": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_system")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "cpu_usage_user": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_user")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "cpu_iowait": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_iowait")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "cpu_softirq": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "usage_softirq")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    try:
        data = await _run_queries(
            influxdb_client, org, queries,
            ts_keys=set(queries.keys()),
        )
        return MetricsResponse(success=True, message="Successfully retrieved CPU metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching CPU metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching CPU metrics: {e}")
    finally:
        await influxdb_client.close()


# ── Memory ───────────────────────────────────────────────────────────────


async def get_memory_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve memory metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "mem_used": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "mem")
  |> filter(fn: (r) => r["_field"] == "used" or r["_field"] == "total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "swap_total": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "swap")
  |> filter(fn: (r) => r["_field"] == "total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "swap_free": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "swap")
  |> filter(fn: (r) => r["_field"] == "free")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',
    }

    try:
        data = await _run_queries(influxdb_client, org, queries, ts_keys={"mem_used"})
        return MetricsResponse(success=True, message="Successfully retrieved memory metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching memory metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching memory metrics: {e}")
    finally:
        await influxdb_client.close()


# ── Kernel ───────────────────────────────────────────────────────────────


async def get_kernel_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve kernel metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "interrupts": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "kernel")
  |> filter(fn: (r) => r["_field"] == "interrupts")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "processes_forked": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "kernel")
  |> filter(fn: (r) => r["_field"] == "processes_forked")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    try:
        data = await _run_queries(
            influxdb_client, org, queries,
            ts_keys=set(queries.keys()),
        )
        return MetricsResponse(success=True, message="Successfully retrieved kernel metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching kernel metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching kernel metrics: {e}")
    finally:
        await influxdb_client.close()


# ── Disks ────────────────────────────────────────────────────────────────


async def get_disk_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve disk metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "disk_total": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "disk")
  |> filter(fn: (r) => r["_field"] == "total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "disk_usage": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "disk")
  |> filter(fn: (r) => r["_field"] == "used_percent")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "disk_io": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "diskio")
  |> filter(fn: (r) => r["_field"] == "read_bytes" or r["_field"] == "write_bytes")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "inodes": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "disk")
  |> filter(fn: (r) => r["_field"] == "inodes_used" or r["_field"] == "inodes_total")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    try:
        query_api = influxdb_client.query_api()
        data: dict[str, Any] = {}

        for key, flux in queries.items():
            result = await query_api.query(flux, org=org)
            if key == "disk_total":
                # Sum across all mount points
                total = 0.0
                for table in result:
                    for record in table.records:
                        try:
                            v = float(record.get_value())
                            if math.isfinite(v):
                                total += v
                        except (ValueError, TypeError):
                            pass
                data[key] = total
            elif key == "disk_io":
                data[key] = _parse_ts_series(result, label_field="name")
            elif key == "disk_usage" or key == "inodes":
                data[key] = _parse_ts_series(result, label_field="path")
            else:
                data[key] = _parse_ts_series(result)

        return MetricsResponse(success=True, message="Successfully retrieved disk metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching disk metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching disk metrics: {e}")
    finally:
        await influxdb_client.close()


# ── Processes ────────────────────────────────────────────────────────────


async def get_process_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve process metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "status": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "processes")
  |> filter(fn: (r) => r["_field"] == "running" or r["_field"] == "sleeping" or r["_field"] == "zombies" or r["_field"] == "stopped" or r["_field"] == "blocked")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    # Stat values
    for field in ("running", "sleeping", "unknown", "zombies"):
        queries[field] = f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "processes")
  |> filter(fn: (r) => r["_field"] == "{field}")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()'''

    try:
        data = await _run_queries(influxdb_client, org, queries, ts_keys={"status"})
        return MetricsResponse(success=True, message="Successfully retrieved process metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching process metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching process metrics: {e}")
    finally:
        await influxdb_client.close()


# ── Network ──────────────────────────────────────────────────────────────


async def get_network_metrics(host: str, range_h: str, session: AsyncSession) -> MetricsResponse:
    """Retrieve network metrics for a given host."""
    try:
        bucket = await _get_influxdb_bucket(session)
        org = await get_influxdb_organization()
    except Exception as e:
        return MetricsResponse(success=False, message=str(e))

    influxdb_client = await create_influxdb_client("InfluxDB")
    rng = _range_clause(range_h)
    win = _window(range_h)

    queries = {
        "traffic": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "net")
  |> filter(fn: (r) => r["_field"] == "bytes_recv" or r["_field"] == "bytes_sent")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',

        "tcp_established": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "netstat")
  |> filter(fn: (r) => r["_field"] == "tcp_established")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> last()''',

        "interface_errors": f'''from(bucket: "{bucket}") |> {rng}
  |> filter(fn: (r) => r["_measurement"] == "net")
  |> filter(fn: (r) => r["_field"] == "err_in" or r["_field"] == "err_out")
  |> filter(fn: (r) => r["host"] == "{host}")
  |> aggregateWindow(every: {win}, fn: mean, createEmpty: false)''',
    }

    try:
        query_api = influxdb_client.query_api()
        data: dict[str, Any] = {}

        for key, flux in queries.items():
            result = await query_api.query(flux, org=org)
            if key == "tcp_established":
                data[key] = _last_value(result)
            else:
                data[key] = _parse_ts_series(result, label_field="interface")

        return MetricsResponse(success=True, message="Successfully retrieved network metrics", data=data)
    except Exception as e:
        logger.error(f"Error fetching network metrics: {e}")
        return MetricsResponse(success=False, message=f"Error fetching network metrics: {e}")
    finally:
        await influxdb_client.close()
