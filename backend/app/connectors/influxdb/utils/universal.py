from typing import Any
from typing import Dict

from fastapi import HTTPException
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from loguru import logger

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
        org="SOCFORTRESS",
    )
    try:
        ping = await influxdb_client.ping()
        logger.info(f"Response from InfluxDB: {ping}")
        if ping:
            logger.info(f"Connection to {attributes['connector_url']} successful")
            return {"connectionSuccessful": True, "message": "InfluxDB connection successful"}
        else:
            logger.error(f"Connection to {attributes['connector_url']} failed")
            return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed"}
    except Exception as e:
        logger.error(f"Connection to {attributes['connector_url']} failed with error: {e}")
        return {"connectionSuccessful": False, "message": f"Connection to {attributes['connector_url']} failed with error: {e}"}
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
        raise HTTPException(status_code=500, detail=f"No {connector_name} connector found in the database")
    try:
        return InfluxDBClientAsync(
            url=attributes["connector_url"],
            token=attributes["connector_api_key"],
            org="SOCFORTRESS",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Elasticsearch client: {e}")


async def get_influxdb_organization() -> str:
    """
    Read the `connector_extra_data` from the database and return the organization name.
    which is the first item. For example: `SOCFORTRESS,telegraf`.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db("InfluxDB", session)
    if attributes is None:
        raise HTTPException(status_code=500, detail=f"No InfluxDB connector found in the database")
    return attributes["connector_extra_data"].split(",")[0]
