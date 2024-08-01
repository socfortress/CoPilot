from fastapi import APIRouter

from loguru import logger


from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload

# App specific imports


graylog_receiver_router = APIRouter()


################## ! GRAYLOG FORWARDER ! ##################
# ! This function is meant to receive a JSON payload from Shuffle (or another tool)
# ! and forward it to a Graylog server.
@graylog_receiver_router.post(
    "/receiver",
    description="Forward a message to Graylog",
)
async def forward_to_graylog(payload: dict) -> dict:
    """
    Forward a message to Graylog.

    This endpoint forwards a message to Graylog.

    Returns:
        ConfiguredInputsResponse: The response containing the configured inputs.
    """
    logger.info("Forwarding message to Graylog")
    logger.info(f"Payload: {payload}")
    message = EventShipperPayload(
        **payload,
    )
    await event_shipper(message)
    return {"message": "Message forwarded to Graylog", "success": True}
