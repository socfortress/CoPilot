import httpx
from loguru import logger

from app.integrations.modules.schema.mimecast import CollectMimecast


async def post_to_copilot_mimecast_module(data: CollectMimecast, license_key: str):
    """
    Send a POST request to the copilot-mimecast-module Docker container.

    Args:
        data (CollectMimecast): The data to send to the copilot-mimecast-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-huntress-module/collect with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-mimecast-module/collect",
            json=data.dict(),
            params={"license_key": license_key, "feature_name": "MIMECAST"},
            timeout=120,
        )
    return None
