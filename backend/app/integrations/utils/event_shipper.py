from loguru import logger
from app.integrations.utils.schema import EventShipperPayload, EventShipperPayloadResponse

from app.connectors.event_shipper.utils.universal import create_gelf_logger
from fastapi import HTTPException


async def get_gelf_logger():
    try:
        gelf_logger = await create_gelf_logger()
        return gelf_logger
    except Exception as e:
        logger.error(f"Failed to initialize GelfLogger: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize GelfLogger: {e}")

async def event_shipper_test(message: EventShipperPayload) -> EventShipperPayloadResponse:
    """
    Test the log shipper.
    """
    gelf_logger = await get_gelf_logger()

    try:
        await gelf_logger.tcp_handler(message=message)
    except Exception as e:
        logger.error(f"Failed to send test message to log shipper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test message to log shipper: {e}")

    return EventShipperPayloadResponse(success=True, message="Successfully sent test message to log shipper.")

