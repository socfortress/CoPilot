import json
from typing import List

from fastapi import HTTPException
from loguru import logger
from pydantic import parse_obj_as

from app.connectors.graylog.schema.content_packs import ContentPack
from app.connectors.graylog.schema.content_packs import ContentPackList
from app.connectors.graylog.utils.universal import send_get_request, send_post_request


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

async def insert_content_pack(content_pack: ContentPack) -> bool:
    """Insert a content pack into Graylog.

    Args:
        content_pack (ContentPack): The content pack to insert.

    Returns:
        bool: True if the content pack was inserted successfully, False if it was not.

    Raises:
        HTTPException: If there is an error inserting the content pack.
    """
    logger.info(f"Inserting content pack {content_pack} into Graylog")
    try:
        content_pack_inserted = await send_post_request(
            endpoint="/api/system/content_packs",
            data=content_pack,
        )
        logger.info(f"Content pack inserted: {content_pack_inserted}")
        if content_pack_inserted["success"] is True:
            logger.info(f"Content pack inserted successfully")
            return True
        else:
            raise HTTPException(status_code=500, detail=f"Content pack insertion unsuccessful")
    except KeyError as e:
        error_msg = f"Failed to insert content pack key: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to insert content pack: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
