import json
from pathlib import Path

import aiofiles
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from fastapi.responses import JSONResponse
from loguru import logger

from app.active_response.schema.active_response import ActiveResponse
from app.active_response.schema.active_response import ActiveResponseCommand
from app.active_response.schema.active_response import ActiveResponseDetails
from app.active_response.schema.active_response import ActiveResponsesSupported
from app.active_response.schema.active_response import ActiveResponsesSupportedResponse
from app.active_response.schema.active_response import InvokeActiveResponseRequest
from app.active_response.schema.active_response import InvokeActiveResponseResponse
from app.active_response.schema.active_response import LinuxFirewallAlert
from app.active_response.schema.active_response import WindowsFirewallAlert
from app.auth.utils import AuthHandler
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.stack_provisioning.graylog.schema.provision import ProvisionGraylogResponse

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
    async with aiofiles.open(file_path, "r") as file:
        return await file.read()


def validate_alert_based_on_command(request: InvokeActiveResponseRequest):
    if request.command == ActiveResponseCommand.windows_firewall and not isinstance(request.alert, WindowsFirewallAlert):
        raise HTTPException(status_code=400, detail="Invalid alert parameters for windows_firewall command")
    elif request.command == ActiveResponseCommand.linux_firewall and not isinstance(request.alert, LinuxFirewallAlert):
        raise HTTPException(status_code=400, detail="Invalid alert parameters for linux_firewall command")


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
        supported_active_responses=[
            ActiveResponse(name=active_response.name, description=active_response.value) for active_response in ActiveResponsesSupported
        ],
        success=True,
        message="Supported Active Responses retrieved successfully",
    )


@active_response_router.post(
    "/invoke",
    response_model=InvokeActiveResponseResponse,
    description="Invoke an active response",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def invoke_active_response_route(
    request: InvokeActiveResponseRequest,
) -> InvokeActiveResponseResponse:
    """
    Invoke an active response.

    Args:
        request (InvokeActiveResponseRequest): The request object containing the command, custom, arguments, and alert.

    Returns:
        InvokeActiveResponseResponse: The response object indicating the success or failure of the active response invocation.
    """
    validate_alert_based_on_command(request)
    logger.info(f"Invoking Wazuh Active Response...")
    # Create a dictionary with the request data
    data_dict = {"command": request.command.value, "custom": request.custom, "arguments": request.arguments, "alert": request.alert.dict()}
    await send_put_request(
        endpoint=request.endpoint,
        data=json.dumps(data_dict),
        params=request.params,
    )

    return InvokeActiveResponseResponse(success=True, message="Wazuh Content Pack provisioned successfully")