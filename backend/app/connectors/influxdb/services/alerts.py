from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.influxdb.schema.alerts import InfluxDBAlert
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.influxdb.utils.universal import create_influxdb_client
from app.connectors.influxdb.utils.universal import get_influxdb_organization

# Constants
BUCKET_NAME = "_monitoring"


def construct_query() -> str:
    """Constructs the InfluxDB query.

    Returns:
        str: The constructed InfluxDB query.
    """
    return """
        from(bucket: "{bucket_name}")
        |> range(start: -1h, stop: now())
        |> filter(fn: (r) => r._measurement == "statuses" and r._field == "_message")
        |> filter(fn: (r) => exists r._check_id and exists r._value and exists r._check_name and exists r._level)
        |> keep(columns: ["_time", "_value", "_check_id", "_check_name", "_level"])
        |> rename(columns: {{ "_time": "time", "_value": "message", "_check_id": "checkID", "_check_name": "checkName", "_level": "level" }})
        |> group()
        |> sort(columns: ["time"], desc: true)
        |> limit(n: 100, offset: 29)
    """.format(
        bucket_name=BUCKET_NAME,
    )


async def process_alert_records(result) -> List[InfluxDBAlert]:
    """Processes alert records from InfluxDB query result.

    Args:
        result: The query result from InfluxDB.

    Returns:
        A list of InfluxDBAlert objects representing the processed alert records.
    """
    alerts = []
    for table in result:
        for record in table.records:
            alert = InfluxDBAlert(
                time=record.values.get("time").isoformat() if record.values.get("time") else None,
                message=record.values.get("message"),
                checkID=record.values.get("checkID"),
                checkName=record.values.get("checkName"),
                level=record.values.get("level"),
            )
            alerts.append(alert)
    return alerts


async def get_alerts() -> InfluxDBAlertsResponse:
    """Fetches alerts from InfluxDB and returns them.

    Returns:
        InfluxDBAlertsResponse: The response object containing the fetched alerts.

    Raises:
        HTTPException: If there is an error fetching the alerts.
    """
    client = await create_influxdb_client("InfluxDB")
    try:
        query = construct_query()
        query_api = client.query_api()
        result = await query_api.query(
            org=await get_influxdb_organization(),
            query=query,
        )

        alerts = await process_alert_records(result)

        return InfluxDBAlertsResponse(
            alerts=alerts,
            success=True,
            message="Successfully fetched alerts",
        )

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {e}")
    finally:
        await client.close()
