from fastapi import APIRouter
from loguru import logger

from fastapi import HTTPException
from fastapi import Depends
import json
from app.integrations.utils.event_shipper import event_shipper_test
from app.integrations.utils.schema import EventShipperPayload

log_shipper_test_router = APIRouter()


@log_shipper_test_router.get("")
async def event_shipper_test_route():
    """
    Test the log shipper.
    """
    message = EventShipperPayload(
    customer_code="test",
    integration="test",
    version="1.1",
    host="example.org",
    )
    try:
        return await event_shipper_test(message)
    except Exception as e:
        logger.error(f"Failed to send test message to log shipper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test message to log shipper: {e}")

