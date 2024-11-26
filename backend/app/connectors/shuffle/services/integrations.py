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
    response = await send_post_request("/api/v1/apps/categories/run", request.dict())
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
    logger.info(f"Executing workflow: {request.dict()}")
    try:
        response = await send_post_request(f"/api/v1/workflows/{request.workflow_id}/execute", request.dict())
        logger.info(f"Response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        return {"error": str(e)}
