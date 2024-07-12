from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.stack_provisioning.graylog.schema.provision import (
    AvailableContentPacksResponse,
)
from app.stack_provisioning.graylog.schema.provision import AvailbleContentPacksOverview
from app.stack_provisioning.graylog.schema.provision import ProvisionContentPackRequest
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.stack_provisioning.graylog.services.provision import check_pipeline_rules
from app.stack_provisioning.graylog.services.provision import provision_content_pack
from app.stack_provisioning.graylog.services.utils import does_content_pack_exist
from app.stack_provisioning.graylog.services.utils import system_version_check

stack_provisioning_graylog_router = APIRouter()


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
        available_content_packs=[{"name": pack.name, "description": pack.value} for pack in AvailbleContentPacksOverview],
        success=True,
        message="Available content packs retrieved successfully",
    )


@stack_provisioning_graylog_router.post(
    "/graylog/provision/content_pack",
    response_model=ProvisionGraylogResponse,
    description="Provision the Content Pack in the Graylog instance",
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
    await provision_content_pack(content_pack_request)
    await check_pipeline_rules()
    return ProvisionGraylogResponse(
        success=True,
        message=f"{content_pack_request.content_pack_name.name} Content Pack provisioned successfully",
    )
