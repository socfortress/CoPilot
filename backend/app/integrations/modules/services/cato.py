import httpx
from loguru import logger

from app.integrations.modules.schema.cato import CollectCato


async def post_to_copilot_cato_module(data: CollectCato, license_key: str = None) -> None:
    """
    Send a POST request to the copilot-cato-module Docker container.

    Args:
        data (CollectCato): The data to send to the copilot-cato-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-cato-module/collect with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-cato-module/collect",
            json=data.dict(),
            timeout=120,
        )
    return None
