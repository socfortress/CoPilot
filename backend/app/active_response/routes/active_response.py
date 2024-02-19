import json

from fastapi import APIRouter
from pathlib import Path
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import Security
import aiofiles
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.graylog.services.content_packs import get_content_packs
from app.connectors.graylog.services.management import get_system_info
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.db.db_session import get_db
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse
from app.active_response.schema.active_response import ActiveResponsesSupported, ActiveResponsesSupportedResponse, ActiveResponse, ActiveResponseDetails, InvokeActiveResponseRequest

active_response_router = APIRouter()

async def verify_active_response_name(active_response_name: str) -> None:
    """
    Verify the active response name
    """
    active_response_name = active_response_name.upper()
    if active_response_name not in ActiveResponsesSupported.__members__:
        raise HTTPException(status_code=404, detail="Active Response not found")

def get_markdown_content_path(directory: str, filename: str) -> str:
    """
    Get the path to the markdown content
    """
    current_directory = Path(__file__).parent.parent
    return str(current_directory / f"scripts/{directory}/{filename}")

async def read_markdown_file(file_path: str) -> str:
    """
    Read the content of a markdown file
    """
    async with aiofiles.open(file_path, 'r') as file:
        return await file.read()

@active_response_router.get(
    "/describe/{active_response_name}",
    response_model=ActiveResponse,
    description="Get the details of a specific active response",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_active_response_details_route(active_response_name: str) -> ActiveResponse:
    """
    Get the details of a specific active response
    """
    await verify_active_response_name(active_response_name)
    directory = active_response_name.split("_")[0].lower()
    file_path = get_markdown_content_path(directory, f"{active_response_name}.md")
    logger.info(f"Reading markdown file: {file_path}")
    response = ActiveResponseDetails(
        name=active_response_name,
        description=ActiveResponsesSupported[active_response_name.upper()].value,
        markdown_content=await read_markdown_file(file_path),
    )
    return JSONResponse(content=response.dict())


@active_response_router.get(
    "/supported",
    response_model=ActiveResponsesSupportedResponse,
    description="Get the list of supported active responses",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_supported_active_responses_route() -> ActiveResponsesSupportedResponse:
    """
    Get the list of supported active responses
    """
    return ActiveResponsesSupportedResponse(
        supported_active_responses=[ActiveResponse(name=active_response.name, description=active_response.value) for active_response in ActiveResponsesSupported],
        success=True,
        message="Supported Active Responses retrieved successfully",
    )

@active_response_router.post(
    "/invoke",
    response_model=ProvisionGraylogResponse,
    description="Provision the Wazuh Content Pack in the Graylog instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_wazuh_content_pack_route(
    request: InvokeActiveResponseRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionGraylogResponse:
    """
    Provision the Wazuh Content Pack in the Graylog instance
    """
    logger.info(f"Invoking Wazuh Active Response...")
    logger.info(f"Request: {request}")
    return None
    await send_put_request(
        endpoint=request.endpoint,
        data=json.dumps(request.data.dict()),
        params=request.params,
    )
    # await send_put_request(
    #     endpoint="active-response",
    #     data=json.dumps(
    #         {
    #             "arguments": [
    #                 "add",
    #             ],
    #             "command": "windows_firewall0",
    #             "custom": True,
    #             "alert": {
    #                 "action": "unblock",
    #                 "ip": "3.3.3.3",
    #             },
    #         },
    #     ),
    #     params={"wait_for_complete": True, "agents_list": ["105"]},
    # )

    return ProvisionGraylogResponse(success=True, message="Wazuh Content Pack provisioned successfully")
