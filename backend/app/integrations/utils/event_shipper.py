import asyncio
from typing import Any
from typing import Dict

from fastapi import HTTPException
from loguru import logger

from app.connectors.event_shipper.utils.universal import create_gelf_logger
from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import get_db_session
from app.integrations.utils.schema import EventShipperPayload
from app.integrations.utils.schema import EventShipperPayloadResponse


async def get_gelf_logger():
    try:
        gelf_logger = await create_gelf_logger()
        return gelf_logger
    except Exception as e:
        logger.error(f"Failed to initialize GelfLogger: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize GelfLogger: {e}",
        )


async def event_shipper(message: EventShipperPayload) -> EventShipperPayloadResponse:
    """
    Test the log shipper.
    """
    gelf_logger = await get_gelf_logger()

    try:
        await gelf_logger.tcp_handler(message=message)
    except Exception as e:
        logger.error(f"Failed to send test message to log shipper: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test message to log shipper: {e}",
        )

    return EventShipperPayloadResponse(
        success=True,
        message="Successfully sent test message to log shipper.",
    )


async def send_json_test_message_to_event_shipper(message: EventShipperPayload) -> EventShipperPayloadResponse:
    """
    Sends a test message to the Graylog Input.
    """
    gelf_logger = await get_gelf_logger()

    try:
        await gelf_logger.tcp_handler(message=message)
    except Exception as e:
        logger.error(f"Failed to send test message to log shipper: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test message to log shipper: {e}",
        )

    return EventShipperPayloadResponse(
        success=True,
        message="Successfully sent test message to log shipper.",
    )


async def verify_event_shipper_healtcheck(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Graylog Input via a telnet connection.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status.
    """
    logger.info(
        f"Verifying the event shipper connection to {attributes['connector_url']}",
    )

    # Make a TCP connection to the Graylog Input
    try:
        reader, writer = await asyncio.open_connection(
            attributes["connector_url"],
            attributes["connector_extra_data"],
        )
        writer.close()
        await writer.wait_closed()
        await send_json_test_message_to_event_shipper(
            EventShipperPayload(
                message="Healthcheck successful",
                integration="event_shipper",
                customer_code="n/a",
            ),
        )
        return {
            "connectionSuccessful": True,
            "message": "Event shipper healthcheck successful",
        }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed",
        }


async def verify_event_shipper_connection(connector_name: str) -> str:
    """
    Returns the status of the connection to Graylog Input.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No attributes found for event shipper connector")
        return None
    return await verify_event_shipper_healtcheck(attributes)
