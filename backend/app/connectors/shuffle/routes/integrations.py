from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.integrations import ExecuteWorkflowRequest
from app.connectors.shuffle.schema.integrations import IntegrationRequest
from app.connectors.shuffle.services.integrations import execute_integration
from app.connectors.shuffle.services.integrations import execute_workflow

shuffle_integrations_router = APIRouter()


@shuffle_integrations_router.post(
    "/execute",
    description="Execute a Shuffle Integration.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def execute_integration_route(request: IntegrationRequest):
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing workflow")
    return await execute_integration(request)


@shuffle_integrations_router.post(
    "/invoke-workflow",
    description="Invoke a Shuffle Workflow.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def invoke_workflow_route(request: ExecuteWorkflowRequest):
    """
    Execute a workflow.

    Args:
        request (IntegrationRequest): The request object containing the workflow ID.

    Returns:
        dict: The response containing the execution ID.
    """
    logger.info("Executing workflow")
    return await execute_workflow(request)
