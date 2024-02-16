from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from fastapi import Request
from typing import List
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.connectors.graylog.services.content_packs import get_content_packs
from app.connectors.graylog.schema.content_packs import ContentPack, ContentPackList
from app.db.db_session import get_db

stack_provisioning_graylog_router = APIRouter()

async def does_content_pack_exist(
    content_pack_name: str
) -> bool:
    """
    Check if the content pack exists in the list of content packs.

    Args:
        content_pack_name (str): The name of the content pack to check.

    Returns:
        bool: True if the content pack exists, False if it does not.
    """
    content_packs = await get_content_packs()
    for content_pack in content_packs:
        logger.info(f"Checking content pack {content_pack.name}")
        if content_pack.name == content_pack_name:
            logger.info(f"Content pack {content_pack_name} exists")
            raise HTTPException(
                status_code=400,
                detail=f"Content pack {content_pack_name} already exists",
            )
    logger.info(f"Content pack {content_pack_name} does not exist")
    return False

@stack_provisioning_graylog_router.post(
    "/graylog/wazuh",
    response_model=ProvisionGraylogResponse,
    description="Provision the Wazuh Content Pack in the Graylog instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_wazuh_content_pack(
    session: AsyncSession = Depends(get_db),
) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Provisioning Wazuh Content Pack...")
    await does_content_pack_exist("SOCFORTRESS_WAZUH_CONTENT_PACK_NOV_2023")
    return ProvisionGraylogResponse(
        success=True, message="Wazuh Content Pack provisioned successfully"
    )
