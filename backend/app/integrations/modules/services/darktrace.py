import httpx
from loguru import logger

from app.integrations.modules.schema.darktrace import CollectDarktrace


async def post_to_copilot_darktrace_module(data: CollectDarktrace):
    """
    Send a POST request to the copilot-darktrace-module Docker container.

    Args:
        data (CollectDarktrace): The data to send to the copilot-darktrace-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-darktrace-module/all_logs with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-darktrace-module/all_logs",
            json=data.dict(),
            timeout=120,
        )
    return None
