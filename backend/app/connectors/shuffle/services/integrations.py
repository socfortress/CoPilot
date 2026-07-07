from fastapi import HTTPException
from loguru import logger

from app.connectors.shuffle.schema.integrations import ExecuteWorkflowRequest
from app.connectors.shuffle.schema.integrations import IntegrationRequest
from app.connectors.shuffle.utils.universal import send_post_request


async def execute_integration(request: IntegrationRequest) -> dict:
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info(f"Executing integration: {request}")
    response = await send_post_request("/api/v1/apps/categories/run", request.model_dump())
    logger.info(f"Response: {response}")
    return response


async def execute_workflow(request: ExecuteWorkflowRequest) -> dict:
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info(f"Executing workflow: {request.model_dump()}")
    try:
        response = await send_post_request(f"/api/v1/workflows/{request.workflow_id}/execute", request.model_dump())
        logger.info(f"Response: {response}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach Shuffle while executing workflow {request.workflow_id}: {e}",
        )

    # `send_post_request` folds both the HTTP status and Shuffle's in-body
    # `success` flag into `response["success"]`. A workflow that can't be
    # retrieved/executed (e.g. wrong regional Shuffle API endpoint) comes back
    # here as success=false — surface it instead of reporting a phantom
    # success to the caller/UI. See GitHub issue #963.
    if not response or response.get("success") is not True:
        detail = (response or {}).get("message") or "Failed to execute Shuffle workflow"
        logger.error(f"Shuffle workflow {request.workflow_id} did not execute successfully: {response}")
        raise HTTPException(status_code=502, detail=detail)

    return response
