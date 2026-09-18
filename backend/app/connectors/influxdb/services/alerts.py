from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Tuple

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.influxdb.schema.alerts import AlertStatus
from app.connectors.influxdb.schema.alerts import GetInfluxDBAlertQueryParams
from app.connectors.influxdb.schema.alerts import InfluxDBAlert
from app.connectors.influxdb.schema.alerts import InfluxDBAlertResponse
from app.connectors.influxdb.schema.alerts import InfluxDBCheckNamesResponse
from app.connectors.influxdb.utils.universal import create_influxdb_client
from app.connectors.influxdb.utils.universal import get_influxdb_organization
from app.connectors.utils import get_connector_info_from_db

# InfluxDB level -> the severity vocabulary the API speaks.
SEVERITY_BY_LEVEL = {"crit": "critical", "warn": "warning", "info": "info", "ok": "ok"}
LEVELS_BY_SEVERITY = {"critical": "crit", "error": "crit", "warning": "warn", "ok": "ok"}

# Tags whose value *is* the monitored state rather than naming the monitored thing. Telegraf's
# systemd_units input tags every point with the unit's current load/active/sub state, so a unit
# that fails and recovers writes its CRIT rows under `active=failed` and its OK rows under
# `active=active` -- two different series (#1118). `mode` is the disk input's rw/ro, which a
# remount flips. Leaving these out of the identity is what lets a recovery clear the failure.
STATE_TAGS = frozenset({"active", "sub", "load", "mode"})

SeriesIdentity = Tuple[str, Tuple[Tuple[str, str], ...]]


def series_identity(values: Dict[str, Any]) -> SeriesIdentity:
    """Name the monitored thing a status row is about: its check plus the tags that say which one.

    One check evaluates many things at once -- CRITICAL SERVICES CHECK writes a status per host
    *and* unit every minute -- so `_check_id` alone is not an identity. Neither is the Influx series
    key: `_level` is a tag, so every level change starts a new series, and so do the STATE_TAGS.
    Everything Influx adds itself is underscore-prefixed, which leaves exactly the tags the check's
    query grouped by (host, name, path, cpu, ...), minus the ones that carry state.
    """
    tags = tuple(
        sorted(
            (key, str(value))
            for key, value in values.items()
            if value is not None and not key.startswith("_") and key not in STATE_TAGS and key not in ("result", "table")
        ),
    )
    return str(values.get("_check_id", "unknown")), tags


def latest_by_identity(records: Iterable[Any]) -> Dict[SeriesIdentity, Any]:
    """Collapse status records to the most recent one per monitored thing."""
    latest: Dict[SeriesIdentity, Any] = {}
    for record in records:
        identity = series_identity(record.values)
        current = latest.get(identity)
        if current is None or record.get_time() > current.get_time():
            latest[identity] = record
        elif record.get_time() == current.get_time() and current.values.get("_level") == "ok":
            # Two series of one identity evaluated at the same instant: never let OK hide a problem.
            latest[identity] = record
    return latest


def selected_levels(query_params: GetInfluxDBAlertQueryParams) -> Optional[frozenset]:
    """The InfluxDB levels the caller wants rows for, or None for all of them."""
    if query_params.severity:
        return frozenset(LEVELS_BY_SEVERITY.get(sev.value, sev.value) for sev in query_params.severity)
    return None


def flux_string(value: str) -> str:
    """Render `value` as a Flux string literal.

    InfluxDB OSS does not support parameterised queries (they are Cloud-only), so anything the
    caller supplies has to be escaped into the query text. `${` must be escaped as well as quotes
    and backslashes: Flux interpolates it inside string literals.
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("${", "\\${") + '"'


def build_status_query(bucket: str, query_params: GetInfluxDBAlertQueryParams) -> str:
    """The statuses stream every alert query starts from: range + check filters, no level filter.

    The level filter is deliberately absent. Current state has to be decided from *every* level --
    an `exclude_ok` applied here would hide the OK that says a failure has recovered (#1118).
    """
    lines = ['import "regexp"']
    filters = []
    # Caller text is matched literally (quoteMeta), never spliced into a regex or the query.
    if query_params.check_name:
        lines.append(f"check_name_pattern = regexp.compile(v: regexp.quoteMeta(v: {flux_string(query_params.check_name)}))")
        filters.append("|> filter(fn: (r) => r._check_name =~ check_name_pattern)")
    if query_params.sensor_type:
        lines.append(f"sensor_type_pattern = regexp.compile(v: regexp.quoteMeta(v: {flux_string(query_params.sensor_type)}))")
        filters.append("|> filter(fn: (r) => r._check_name =~ sensor_type_pattern)")
    lines += [
        f"from(bucket: {flux_string(bucket)})",
        f"    |> range(start: -{int(query_params.days)}d)",
        '    |> filter(fn: (r) => r._measurement == "statuses" and r._field == "_message")',
        "    |> filter(fn: (r) => exists r._check_id and exists r._check_name and exists r._level)",
    ]
    lines += [f"    {f}" for f in filters]
    return "\n".join(lines)


def build_alert(record: Any, current_level: str) -> InfluxDBAlert:
    """One status row, with `status` taken from the monitored thing's *current* level.

    A row is active only while its own level is a problem *and* the thing it describes has not
    recovered since. A CRIT that has been followed by an OK is history: still listed, but cleared.
    """
    level = record.values.get("_level", "unknown")
    check_name = record.values.get("_check_name", "unknown")
    return InfluxDBAlert(
        time=record.get_time(),
        check_name=check_name,
        sensor_type=check_name.split()[0] if " " in check_name else check_name,
        severity=SEVERITY_BY_LEVEL.get(level, level),
        message=record.values.get("_value", "No message"),
        status="active" if level != "ok" and current_level != "ok" else "cleared",
        check_id=str(record.values.get("_check_id", "unknown")),
    )


async def get_influxdb_alerts(
    query_params: GetInfluxDBAlertQueryParams,
    session: AsyncSession,
) -> InfluxDBAlertResponse:
    """
    Retrieve alerts from InfluxDB with advanced filtering

    Args:
        query_params: Query parameters for filtering
        session: Database session

    Returns:
        InfluxDBAlertResponse with filtered alerts
    """
    logger.info("Fetching InfluxDB alerts")

    # Get connector info to verify it exists
    connector_info = await get_connector_info_from_db("InfluxDB", session)
    if not connector_info:
        logger.error("InfluxDB connector not found")
        return InfluxDBAlertResponse(
            success=False,
            message="InfluxDB connector not found",
            alerts=[],
            total_count=0,
            filtered_count=0,
        )

    # Get org and bucket info
    try:
        influxdb_org = await get_influxdb_organization()
        # Use _monitoring bucket
        influxdb_bucket = "_monitoring"
    except Exception as e:
        logger.error(f"Error getting InfluxDB configuration: {e}")
        influxdb_org = "SOCFORTRESS"
        influxdb_bucket = "_monitoring"

    # Create InfluxDB client using existing function
    try:
        influxdb_client = await create_influxdb_client("InfluxDB")
    except Exception as e:
        logger.error(f"Failed to create InfluxDB client: {e}")
        return InfluxDBAlertResponse(
            success=False,
            message=f"Failed to connect to InfluxDB: {str(e)}",
            alerts=[],
            total_count=0,
            filtered_count=0,
        )

    query_api = influxdb_client.query_api()

    try:
        status_query = build_status_query(influxdb_bucket, query_params)

        # 1. Current state: the newest status of every series, with no level filter and no limit.
        #    `last()` runs per series, which is small (things monitored x levels seen) and cheap.
        state_query = status_query + "\n    |> last()"
        logger.info(f"Executing Flux state query:\n{state_query}")
        state_tables = await query_api.query(state_query, org=influxdb_org)
        latest = latest_by_identity(record for table in state_tables for record in table.records)
        current_level = {identity: record.values.get("_level") for identity, record in latest.items()}

        levels = selected_levels(query_params)
        limit = query_params.limit or 500

        def wanted(record) -> bool:
            level = record.values.get("_level")
            if levels is not None and level not in levels:
                return False
            return not (query_params.exclude_ok and level == "ok")

        # 2. The rows to display. Level filters only choose rows here; they never feed state.
        if query_params.latest_only:
            records = [record for record in latest.values() if wanted(record)]
            records.sort(key=lambda record: record.get_time(), reverse=True)
        else:
            rows_query = status_query
            if levels is not None:
                rows_query += (
                    "\n    |> filter(fn: (r) => " + " or ".join(f"r._level == {flux_string(level)}" for level in sorted(levels)) + ")"
                )
            if query_params.exclude_ok:
                rows_query += '\n    |> filter(fn: (r) => r._level != "ok")'
            # group() first: sort and limit act per table, and every series is its own table.
            rows_query += f'\n    |> group()\n    |> sort(columns: ["_time"], desc: true)\n    |> limit(n: {limit})'
            logger.info(f"Executing Flux rows query:\n{rows_query}")
            rows_tables = await query_api.query(rows_query, org=influxdb_org)
            records = [record for table in rows_tables for record in table.records]

        # A row written after the state query ran falls back to its own level.
        alerts = [
            build_alert(record, current_level.get(series_identity(record.values), record.values.get("_level", "unknown")))
            for record in records
        ]

        if query_params.status == AlertStatus.ACTIVE:
            alerts = [alert for alert in alerts if alert.status == "active"]
        elif query_params.status == AlertStatus.CLEARED:
            alerts = [alert for alert in alerts if alert.status == "cleared"]

        alerts = alerts[:limit]

        # Calculate counts
        total_count = len(alerts)
        active_count = sum(1 for a in alerts if a.status == "active")
        cleared_count = sum(1 for a in alerts if a.status == "cleared")

        logger.info(f"Retrieved {len(alerts)} alerts from InfluxDB (active: {active_count}, cleared: {cleared_count})")

        return InfluxDBAlertResponse(
            success=True,
            message="Successfully retrieved InfluxDB alerts",
            alerts=alerts,
            total_count=total_count,
            filtered_count=len(alerts),
            active_alerts_count=active_count,
            cleared_alerts_count=cleared_count,
        )

    except Exception as e:
        logger.error(f"Error querying InfluxDB alerts: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return InfluxDBAlertResponse(
            success=False,
            message=f"Error querying InfluxDB: {str(e)}",
            alerts=[],
            total_count=0,
            filtered_count=0,
        )
    finally:
        await influxdb_client.close()


async def get_influxdb_check_names(
    session: AsyncSession,
) -> InfluxDBCheckNamesResponse:
    """
    Retrieve unique check names from InfluxDB

    Args:
        session: Database session

    Returns:
        InfluxDBCheckNamesResponse with list of available check names
    """
    logger.info("Fetching InfluxDB check names")

    # Get connector info to verify it exists
    connector_info = await get_connector_info_from_db("InfluxDB", session)
    if not connector_info:
        logger.error("InfluxDB connector not found")
        return InfluxDBCheckNamesResponse(
            success=False,
            message="InfluxDB connector not found",
            check_names=[],
            total_count=0,
        )

    # Get org and bucket info
    try:
        influxdb_org = await get_influxdb_organization()
        influxdb_bucket = "_monitoring"
    except Exception as e:
        logger.error(f"Error getting InfluxDB configuration: {e}")
        influxdb_org = "SOCFORTRESS"
        influxdb_bucket = "_monitoring"

    # Create InfluxDB client
    try:
        influxdb_client = await create_influxdb_client("InfluxDB")
    except Exception as e:
        logger.error(f"Failed to create InfluxDB client: {e}")
        return InfluxDBCheckNamesResponse(
            success=False,
            message=f"Failed to connect to InfluxDB: {str(e)}",
            check_names=[],
            total_count=0,
        )

    query_api = influxdb_client.query_api()

    try:
        # Query to get unique check names from the last 30 days
        flux_query = f"""
        from(bucket: "{influxdb_bucket}")
            |> range(start: -30d)
            |> filter(fn: (r) => r._measurement == "statuses" and r._field == "_message")
            |> filter(fn: (r) => exists r._check_name)
            |> group(columns: ["_check_name"])
            |> distinct(column: "_check_name")
            |> keep(columns: ["_check_name"])
        """

        logger.info(f"Executing Flux query:\n{flux_query}")

        # Execute query
        result = await query_api.query(flux_query, org=influxdb_org)

        # Process results - collect unique check names
        check_names = set()
        for table in result:
            for record in table.records:
                check_name = record.values.get("_check_name")
                if check_name:
                    check_names.add(check_name)

        # Convert to sorted list
        check_names_list = sorted(list(check_names))

        logger.info(f"Retrieved {len(check_names_list)} unique check names")

        return InfluxDBCheckNamesResponse(
            success=True,
            message="Successfully retrieved check names",
            check_names=check_names_list,
            total_count=len(check_names_list),
        )

    except Exception as e:
        logger.error(f"Error querying InfluxDB check names: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return InfluxDBCheckNamesResponse(
            success=False,
            message=f"Error querying InfluxDB: {str(e)}",
            check_names=[],
            total_count=0,
        )
    finally:
        await influxdb_client.close()
