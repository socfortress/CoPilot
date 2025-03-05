import json
from pathlib import Path

import aiofiles
from fastapi import APIRouter
from fastapi import Depends, Header
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.graylog import GraylogEventNotification
from app.active_response.schema.active_response import InvokeActiveResponseResponse
from app.agents.routes.agents import get_agent
from app.auth.utils import AuthHandler
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.db.db_session import get_db

active_response_graylog_router = APIRouter()

# Function to validate the Graylog header
async def verify_graylog_header(graylog: str = Header(None)):
    """Verify that the request has the correct Graylog header."""
    if graylog != "test":
        raise HTTPException(status_code=403, detail="Invalid or missing Graylog header")
    return graylog

@active_response_graylog_router.post(
    "/graylog/invoke",
    response_model=InvokeActiveResponseResponse,
    description="Invoke an active response via a Graylog Alert notification.",
    dependencies=[Depends(verify_graylog_header)],
)
async def invoke_active_response_graylog_route(
    request: GraylogEventNotification,
) -> InvokeActiveResponseResponse:
    """
    This route accepts an HTTP Post from Graylog. Required fields are:
     1. Agent ID - The ID of the agent that triggered the alert
     2. Command - The command to execute (i.e. 'dns_block.py')
     3. Arguments - The arguments to pass to the command such as IP addresses, domains, etc.
     {
        "endpoint": "/active-response",
        "arguments": [
            "string"
        ],
        "command": "sysmon_config_reload",
        "custom": true,
        "alert": {
            "action": "sysmon_config_reload"
        },
        "params": {
            "wait_for_complete": true,
            "agents_list": [
            "085"
            ]
        }
        }

    Args:
        request (InvokeActiveResponseRequest): The request object containing the command, custom, arguments, and alert.

    Returns:
        InvokeActiveResponseResponse: The response object indicating the success or failure of the active response invocation.
    """
    logger.info("Invoking Wazuh Active Response...")
    # Append '0' to the command - This is required for Wazuh Active Response
    command = f"{request.event.fields.COMMAND}0"
    # Create a dictionary with the request data
    data_dict = {"command": command, "arguments": request.event.fields.ARGUMENTS, "alert": request.event.fields.COMMAND}
    await send_put_request(
        endpoint='/active-response',
        data=json.dumps(data_dict),
        params={"wait_for_complete": True, "agents_list": [request.event.fields.AGENT_ID]}
    )

    return InvokeActiveResponseResponse(success=True, message="Wazuh Active Response invoked successfully")
