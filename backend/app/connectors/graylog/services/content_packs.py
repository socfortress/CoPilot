from typing import List

from fastapi import HTTPException
from loguru import logger
from pydantic import parse_obj_as

from app.connectors.graylog.schema.content_packs import ContentPack
from app.connectors.graylog.schema.content_packs import ContentPackList
from app.connectors.graylog.utils.universal import send_get_request
from app.connectors.graylog.utils.universal import send_post_request


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
            logger.info("Content pack inserted successfully")
            return True
        else:
            raise HTTPException(status_code=500, detail="Content pack insertion unsuccessful")
    except HTTPException as e:
        if "Content pack" in e.detail and "already found" in e.detail and "PROCESSING_PIPELINE" in content_pack["name"]:
            logger.info("Content pack with PROCESSING_PIPELINE already exists, skipping")
            return False
        else:
            error_msg = f"Failed to insert content pack: {e}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
    except KeyError as e:
        error_msg = f"Failed to insert content pack key: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to insert content pack: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


async def install_content_pack(content_pack_id: str, revision: int) -> bool:
    """Install a content pack in Graylog.

    Args:
        content_pack_id (str): The ID of the content pack to install.
        revision (int): The revision of the content pack to install.

    Returns:
        bool: True if the content pack was installed successfully, False if it was not.

    Raises:
        HTTPException: If there is an error installing the content pack.
    """
    logger.info(f"Installing content pack {content_pack_id} in Graylog")
    try:
        content_pack_installed = await send_post_request(
            endpoint=f"/api/system/content_packs/{content_pack_id}/{revision}/installations",
            data={
                "comment": "Installed by SOCFortress CoPilot",
            },
        )
        logger.info(f"Content pack installed: {content_pack_installed}")
        if content_pack_installed["success"] is True:
            logger.info("Content pack installed successfully")
            return True
        else:
            raise HTTPException(status_code=500, detail="Content pack installation unsuccessful")
    except KeyError as e:
        error_msg = f"Failed to install content pack key: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to install content pack: {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
