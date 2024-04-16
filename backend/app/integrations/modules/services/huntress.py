import httpx
from loguru import logger

from app.integrations.modules.schema.huntress import CollectHuntress


async def post_to_copilot_huntress_module(data: CollectHuntress, license_key: str):
    """
    Send a POST request to the copilot-huntress-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-huntress-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-huntress-module/collect with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-huntress-module/collect",
            json=data.dict(),
            params={"license_key": license_key, "feature_name": "HUNTRESS"},
            timeout=120,
        )
    return None
