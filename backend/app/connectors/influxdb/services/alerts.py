from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.influxdb.schema.alerts import (
    InfluxDBAlert,
    InfluxDBAlertResponse,
    GetInfluxDBAlertQueryParams,
    SeverityFilter,
    AlertStatus,
)
from app.connectors.influxdb.utils.universal import (
    create_influxdb_client,
    get_influxdb_organization,
)
from app.connectors.utils import get_connector_info_from_db


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
        extra_data = connector_info.get("connector_extra_data", "")
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

    # Build time range - use relative time for better performance
    days_ago = f"-{query_params.days}d"

    try:
        # Build Flux query - matching the actual InfluxDB structure
        flux_query = f'''
        from(bucket: "{influxdb_bucket}")
            |> range(start: {days_ago})
            |> filter(fn: (r) => r._measurement == "statuses" and r._field == "_message")
            |> filter(fn: (r) => exists r._check_id and exists r._check_name and exists r._level)
        '''

        # Add severity/level filter
        if query_params.exclude_ok or query_params.severity:
            severity_filters = []

            if query_params.severity:
                # Map severity to InfluxDB levels (crit, warn, info, ok)
                level_mapping = {
                    "critical": "crit",
                    "error": "crit",
                    "warning": "warn",
                    "ok": "ok"
                }
                for sev in query_params.severity:
                    level = level_mapping.get(sev.value, sev.value)
                    severity_filters.append(f'r._level == "{level}"')
            elif query_params.exclude_ok:
                # Exclude 'ok' level
                severity_filters = [
                    'r._level == "warn"',
                    'r._level == "crit"',
                    'r._level == "info"'
                ]

            if severity_filters:
                severity_filter_str = " or ".join(severity_filters)
                flux_query += f'\n    |> filter(fn: (r) => {severity_filter_str})'

        # Add check name filter
        if query_params.check_name:
            flux_query += f'''
            |> filter(fn: (r) => r._check_name =~ /{query_params.check_name}/)
            '''

        # Add sensor type filter (if applicable)
        if query_params.sensor_type:
            flux_query += f'''
            |> filter(fn: (r) => r._check_name =~ /{query_params.sensor_type}/)
            '''

        # Get only latest per check if requested
        if query_params.latest_only:
            flux_query += '''
            |> group(columns: ["_check_name"])
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 1)
            |> group()
            '''
        else:
            flux_query += '''
            |> sort(columns: ["_time"], desc: true)
            '''

        logger.info(f"Executing Flux query:\n{flux_query}")

        # Execute query
        result = await query_api.query(flux_query, org=influxdb_org)

        # Process results
        alerts = []
        check_states = {}  # Track latest state per check for status calculation

        for table in result:
            for record in table.records:
                alert_time = record.get_time()
                check_name = record.values.get("_check_name", "unknown")
                check_id = record.values.get("_check_id", "unknown")
                level = record.values.get("_level", "unknown")
                message = record.values.get("_value", "No message")

                # Map InfluxDB levels to severity
                severity_mapping = {
                    "crit": "critical",
                    "warn": "warning",
                    "info": "info",
                    "ok": "ok"
                }
                severity = severity_mapping.get(level, level)

                # Track the latest state for this check ID
                if check_id not in check_states or alert_time > check_states[check_id]["time"]:
                    check_states[check_id] = {
                        "time": alert_time,
                        "level": level,
                        "check_name": check_name,
                    }

                # Status: if level is 'ok', it's cleared; otherwise active
                status = "cleared" if level == "ok" else "active"

                alerts.append(
                    InfluxDBAlert(
                        time=alert_time,
                        check_name=check_name,
                        sensor_type=check_name.split()[0] if " " in check_name else check_name,
                        severity=severity,
                        message=message,
                        status=status,
                        check_id=str(check_id),
                    )
                )

        # Apply status filter if requested
        if query_params.status != AlertStatus.ALL:
            if query_params.status == AlertStatus.ACTIVE:
                # Only keep alerts from checks that are currently NOT in 'ok' state
                active_check_ids = {
                    check_id
                    for check_id, state in check_states.items()
                    if state["level"] != "ok"
                }

                logger.info(f"Active check IDs: {active_check_ids}")

                alerts = [
                    alert for alert in alerts
                    if alert.check_id in active_check_ids
                ]
            elif query_params.status == AlertStatus.CLEARED:
                # Only keep alerts from checks that are currently in 'ok' state
                cleared_check_ids = {
                    check_id
                    for check_id, state in check_states.items()
                    if state["level"] == "ok"
                }

                alerts = [
                    alert for alert in alerts
                    if alert.check_id in cleared_check_ids
                ]

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
