from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.graylog.services.content_packs import get_content_packs
from app.connectors.graylog.services.management import get_system_info
from app.stack_provisioning.graylog.schema.provision import AvailableContentPacks
from app.stack_provisioning.graylog.schema.provision import (
    AvailableContentPacksResponse,
)
from app.stack_provisioning.graylog.schema.provision import ProvisionContentPackRequest
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.stack_provisioning.graylog.services.provision import provision_content_pack

stack_provisioning_graylog_router = APIRouter()


async def get_graylog_version() -> str:
    """
    Get the version of the Graylog instance.

    Returns:
        str: The version of the Graylog instance.
    """
    system_info = await get_system_info()
    return system_info.version


async def system_version_check(compatible_version: str) -> bool:
    """
    Check if the Graylog version is compatible with the content pack.

    Args:
        compatible_version (str): The version of the Graylog instance.

    Returns:
        bool: True if the version is compatible, False if it is not.
    """
    system_version = await get_graylog_version()
    logger.info(f"Graylog System version: {system_version}")

    # Split the version strings at the '+' character and compare the parts before the '+'
    system_version = system_version.split("+")[0]
    compatible_version = compatible_version.split("+")[0]

    # Split these parts at the '.' character and convert them to integers
    system_version_parts = list(map(int, system_version.split(".")))
    compatible_version_parts = list(map(int, compatible_version.split(".")))

    if system_version_parts >= compatible_version_parts:
        return True
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Graylog version {system_version} is not compatible with the content pack",
        )


async def is_content_pack_available(content_pack_name: str) -> bool:
    """
    Check if the content pack is available for provisioning.

    Args:
        content_pack_name (str): The name of the content pack to check.

    Returns:
        bool: True if the content pack is available, False if it is not.
    """
    available_content_packs = [pack.name for pack in AvailableContentPacks]
    if content_pack_name in available_content_packs:
        logger.info(f"Content pack {content_pack_name} is available")
        return True
    else:
        logger.info(f"Content pack {content_pack_name} is not available")
        raise HTTPException(
            status_code=400,
            detail=f"Content pack {content_pack_name} is not available",
        )


async def does_content_pack_exist(content_pack_name: str) -> bool:
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


@stack_provisioning_graylog_router.get(
    "/graylog/available/content_packs",
    response_model=AvailableContentPacksResponse,
    description="Get the available content packs for provisioning in Graylog",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_content_packs_route() -> AvailableContentPacksResponse:
    """
    Get the available content packs for provisioning in Graylog
    """
    logger.info("Getting available content packs...")
    return AvailableContentPacksResponse(
        available_content_packs=[{"name": pack.name, "description": pack.value} for pack in AvailableContentPacks],
        success=True,
        message="Available content packs retrieved successfully",
    )


@stack_provisioning_graylog_router.post(
    "/graylog/provision/content_pack",
    response_model=ProvisionGraylogResponse,
    description="Provision the Wazuh Content Pack in the Graylog instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_content_pack_route(
    content_pack_request: ProvisionContentPackRequest,
) -> ProvisionGraylogResponse:
    """
    Provision the Content Pack in the Graylog instance
    """
    logger.info(f"Provisioning content pack {content_pack_request.content_pack_name.name}...")
    await system_version_check(compatible_version="5.0.13+083613e")
    await does_content_pack_exist(content_pack_name=content_pack_request.content_pack_name.name)
    await provision_content_pack(content_pack_request.content_pack_name.name)
    return ProvisionGraylogResponse(
        success=True,
        message=f"{content_pack_request.content_pack_name.name} Content Pack provisioned successfully",
    )
