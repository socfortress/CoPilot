import json
from pathlib import Path
import os
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
    # Get the header value from environment variable or use "ab73de7a-6f61-4dde-87cd-3af5175a7281" as default
    expected_header = os.getenv("GRAYLOG_API_HEADER_VALUE", "ab73de7a-6f61-4dde-87cd-3af5175a7281")

    if graylog != expected_header:
        raise HTTPException(status_code=403, detail="Invalid or missing Graylog header")
    return graylog

@active_response_graylog_router.post(
    "/invoke",
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
        4. Required Graylog Event Fields:
        COMMAND: str - this is the active response command to execute i.e 'domain_sinkhole' (do not include the '.py')
        AGENT_ID: str - the agent ID that triggered the alert
        ACTION: str - the action to take i.e 'sinkhole' - this is defined in the python script of the valid actions
        VALUE: str - the value to use i.e 'example.com' - this is the value that the action will be taken on

    #### IMPORTANT: IF THE MANAGERS ARE IN A CLUSTER, THE WORKER FOR THE AGENT MUST GET THE COMMAND AND ACTIVE RESPONSE BLOCKS

    Args:
        request (InvokeActiveResponseRequest): The request object containing the command, custom, arguments, and alert.

    Returns:
        InvokeActiveResponseResponse: The response object indicating the success or failure of the active response invocation.
    """
    logger.info("Invoking Wazuh Active Response...")
    # Append '0' to the command - This is required for Wazuh Active Response
    command = f"{request.event.fields.COMMAND}0"
    # Create a dictionary with the request data
    # {"endpoint":"active-response","arguments":[],"command":"windows_firewall","custom":true,"alert":{"action":"block","ip":"1.1.1.1"},"params":{"wait_for_complete":true,"agents_list":["086"]}}

    data_dict = {"command": command, "arguments": [], "alert": {"action": request.event.fields.ACTION, "value": request.event.fields.VALUE}}
    await send_put_request(
        endpoint='/active-response',
        data=json.dumps(data_dict),
        params={"wait_for_complete": True, "agents_list": [request.event.fields.AGENT_ID]},
        debug=True,
    )

    return InvokeActiveResponseResponse(success=True, message="Wazuh Active Response invoked successfully")
