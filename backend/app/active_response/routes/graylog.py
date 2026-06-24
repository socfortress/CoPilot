import json
import os

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from loguru import logger

from app.active_response.schema.active_response import InvokeActiveResponseResponse
from app.active_response.schema.graylog import GraylogEventNotification
from app.connectors.wazuh_manager.utils.universal import send_put_request

active_response_graylog_router = APIRouter()


# Function to validate the Graylog header
# Fails closed: GRAYLOG_API_HEADER_VALUE must be configured or the route is denied for
# everyone. Previously this fell back to a constant hardcoded here and shipped in
# .env.example, so any default deployment was reachable unauthenticated (GHSA-x8gc-f8p4-frc2,
# same class of bug as the JWT_SECRET default in GHSA-4gxj-hw3c-3x2x). Mirrors
# verify_grafana_header (GHSA-xh98-w6qh-cr44).
async def verify_graylog_header(graylog: str = Header(None)):
    """Verify that the request has the correct Graylog header."""
    expected_header = os.getenv("GRAYLOG_API_HEADER_VALUE")
    if not expected_header:
        logger.error("GRAYLOG_API_HEADER_VALUE is not configured; denying Graylog webhook request")
        raise HTTPException(status_code=403, detail="Graylog header authentication is not configured")
    if graylog != expected_header:
        logger.error("Invalid or missing Graylog header")
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
        endpoint="/active-response",
        data=json.dumps(data_dict),
        params={"wait_for_complete": True, "agents_list": [request.event.fields.AGENT_ID]},
        debug=True,
    )

    return InvokeActiveResponseResponse(success=True, message="Wazuh Active Response invoked successfully")
