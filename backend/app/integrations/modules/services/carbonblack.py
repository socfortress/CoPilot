import httpx
from loguru import logger

from app.integrations.modules.schema.carbonblack import CollectCarbonBlack


async def post_to_copilot_carbonblack_module(data: CollectCarbonBlack, license_key: str):
    """
    Send a POST request to the copilot-huntress-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-huntress-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-carbonblack-module/collect with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://copilot-carbonblack-module/collect",
            json=data.dict(),
            params={"license_key": license_key, "feature_name": "CARBONBLACK"},
            timeout=120,
        )
    return None
