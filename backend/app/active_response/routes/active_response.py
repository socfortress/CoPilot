import json

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.graylog.services.content_packs import get_content_packs
from app.connectors.graylog.services.management import get_system_info
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.db.db_session import get_db
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.stack_provisioning.graylog.services.provision import (
    provision_wazuh_content_pack,
)

active_response_router = APIRouter()


@active_response_router.post(
    "/invoke",
    response_model=ProvisionGraylogResponse,
    description="Provision the Wazuh Content Pack in the Graylog instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_wazuh_content_pack_route(
    session: AsyncSession = Depends(get_db),
) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Invoking Wazuh Active Response...")
    await send_put_request(
        endpoint="active-response",
        data=json.dumps(
            {
                "arguments": [
                    "add",
                ],
                "command": "test0",
                "custom": True,
                "alert": {
                    "hello": "world",
                },
            },
        ),
    )

    return ProvisionGraylogResponse(success=True, message="Wazuh Content Pack provisioned successfully")
