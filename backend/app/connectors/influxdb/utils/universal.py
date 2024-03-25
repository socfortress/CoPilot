from typing import Any
from typing import Dict
from typing import List

from fastapi import HTTPException
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from loguru import logger

from app.connectors.influxdb.schema.alerts import InfluxDBAlert
from app.connectors.influxdb.schema.alerts import InfluxDBAlertsResponse
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session


async def verify_influxdb_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to InfluxDB service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(f"Verifying the InfluxDB connection to {attributes['connector_url']}")
    influxdb_client = InfluxDBClientAsync(
        url=attributes["connector_url"],
        token=attributes["connector_api_key"],
        org=await get_influxdb_organization(),
        verify_ssl=False,
    )
    try:
        ping = await influxdb_client.ping()
        logger.info(f"Response from InfluxDB: {ping}")
        if ping:
            logger.info(f"Connection to {attributes['connector_url']} successful")
            # Now try to fetch alerts
            await get_alerts()
            # logger.info(f"Alerts from InfluxDB: {alerts}")
            return {
                "connectionSuccessful": True,
                "message": "InfluxDB connection successful",
            }
        else:
            logger.error(f"Connection to {attributes['connector_url']} failed")
            return {
                "connectionSuccessful": False,
                "message": f"Connection to {attributes['connector_url']} failed",
            }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }
    finally:
        # Make sure to close the client session
        await influxdb_client.close()


async def verify_influxdb_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the InfluxDB service.

    Returns:
        str: Authentication token for the InfluxDB service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    logger.info(f"Verifying the InfluxDB connection to {attributes['connector_url']}")
    if attributes is None:
        logger.error("No InfluxDB connector found in the database")
        return None
    return await verify_influxdb_credentials(attributes)


async def create_influxdb_client(connector_name: str) -> InfluxDBClientAsync:
    """
    Returns an InfluxDBClientAsync client for the InfluxDB service.

    Returns:
        InfluxDBClientAsync: InfluxDBClientAsync client for the InfluxDB service.
    """
    # attributes = get_connector_info_from_db(connector_name)
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(
            status_code=500,
            detail=f"No {connector_name} connector found in the database",
        )
    try:
        return InfluxDBClientAsync(
            url=attributes["connector_url"],
            token=attributes["connector_api_key"],
            org=await get_influxdb_organization(),
            verify_ssl=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create InfluxDB client: {e}",
        )


async def get_influxdb_organization() -> str:
    """
    Read the `connector_extra_data` from the database and return the organization name.
    which is the first item. For example: `SOCFORTRESS,telegraf`.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db("InfluxDB", session)
    if attributes is None:
        raise HTTPException(
            status_code=500,
            detail="No InfluxDB connector found in the database",
        )
    return attributes["connector_extra_data"].split(",")[0]


# ! RUN A TEST QUERY TO FETCH ALERTS AND VERIFY THE CONNECTION
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
        logger.info(f"Fetching alerts from InfluxDB: {query}")
        result = await client.query_api().query(org=await get_influxdb_organization(), query=query)
        logger.info(f"Alerts from InfluxDB: {result}")
        alerts = await process_alert_records(result)
        return InfluxDBAlertsResponse(alerts=alerts, success=True, message="Alerts fetched successfully")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch alerts from InfluxDB: {e}",
        )
    finally:
        # Make sure to close the client session
        await client.close()
