import httpx
from loguru import logger

from app.integrations.modules.schema.duo import CollectDuo


async def post_to_copilot_duo_module(data: CollectDuo):
    """
    Send a POST request to the copilot-duo-module Docker container.

    Args:
        data (CollectDuo): The data to send to the copilot-duo-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-duo-module/auth with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-duo-module/auth",
            json=data.dict(),
            timeout=120,
        )
    return None
