from fastapi import HTTPException
from loguru import logger
from typing import List
import json
from pydantic import parse_obj_as


from app.connectors.graylog.schema.content_packs import ContentPack, ContentPackList
from app.connectors.graylog.utils.universal import send_get_request


async def get_content_packs() -> List[ContentPack]:
    """Get content packs from Graylog.

    Returns:
        List[ContentPack]: The list of collected content packs.

    Raises:
        HTTPException: If there is an error collecting the content packs.
    """
    logger.info("Getting content packs from Graylog")
    try:
        content_packs_collected = await send_get_request(
            endpoint="/api/system/content_packs",
        )
        if content_packs_collected.get("success"):
            logger.info("Content packs collected successfully")
            content_packs_list = parse_obj_as(ContentPackList, content_packs_collected.get("data"))
            return content_packs_list.content_packs
        else:
            raise HTTPException(status_code=500, detail="Content packs collection unsuccessful")
    except KeyError as e:
        error_msg = f"Failed to collect content packs key: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to collect content packs: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
