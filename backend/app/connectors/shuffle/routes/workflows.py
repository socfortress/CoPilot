from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.workflows import RequestWorkflowExecutionModel
from app.connectors.shuffle.schema.workflows import RequestWorkflowExecutionResponse
from app.connectors.shuffle.schema.workflows import WorkflowExecutionBodyModel
from app.connectors.shuffle.schema.workflows import WorkflowExecutionResponseModel
from app.connectors.shuffle.schema.workflows import WorkflowsResponse
from app.connectors.shuffle.services.workflows import execute_workflow
from app.connectors.shuffle.services.workflows import get_workflow_executions
from app.connectors.shuffle.services.workflows import get_workflows

shuffle_workflows_router = APIRouter()


async def validate_execution_id(workflow_id: str) -> bool:
    """
    Validate the execution ID.

    Args:
        workflow_id (str): The workflow ID.

    Returns:
        bool: True if the workflow ID is valid, False otherwise.
    """
    workflows = await get_workflows()
    for workflow in workflows.workflows:
        logger.info(f"Workflow ID: {workflow['id']}")
        if workflow["id"] == workflow_id:
            logger.info("Workflow validation successful")
            return True
    raise HTTPException(status_code=404, detail="Workflow not found")


@shuffle_workflows_router.get(
    "",
    response_model=WorkflowsResponse,
    description="Get all workflows",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_workflows() -> WorkflowsResponse:
    """
    Retrieve all workflows.

    Returns:
        WorkflowsResponse: The response containing the list of workflows.
    """
    logger.info("Fetching all workflows")
    return await get_workflows()


@shuffle_workflows_router.get(
    "/executions",
    response_model=WorkflowExecutionResponseModel,
    description="Get all workflow executions",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_workflow_executions() -> WorkflowExecutionResponseModel:
    """
    Retrieve all workflow executions.

    Returns:
        WorkflowExecutionResponseModel: The response model containing the workflow executions.

    Raises:
        HTTPException: If no workflows are found.
    """
    logger.info("Fetching all workflow executions")

    # Initialize an empty list for storing workflow details
    workflow_details = []

    # Get the workflow response by awaiting the asynchronous function get_workflows()
    workflow_response = await get_all_workflows()

    # Access the workflows attribute from the response
    workflows = workflow_response.workflows

    # Check if workflows is not None before proceeding
    if workflows:
        for workflow in workflows:
            workflow_details.append(
                {
                    "workflow_id": workflow["id"],
                    "workflow_name": workflow["name"],
                    "status": await get_workflow_executions(
                        WorkflowExecutionBodyModel(workflow_id=workflow["id"]),
                    ),
                },
            )
        return WorkflowExecutionResponseModel(
            success=True,
            message="Successfully fetched workflow executions",
            workflows=workflow_details,
        )
    else:
        raise HTTPException(status_code=404, detail="No workflows found")


@shuffle_workflows_router.post(
    "/execute",
    response_model=RequestWorkflowExecutionResponse,
    description="Execute a workflow",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def execute_workflow_request(
    workflow_execution_body: RequestWorkflowExecutionModel,
) -> RequestWorkflowExecutionResponse:
    """
    Execute a workflow.

    Args:
        workflow_execution_body (WorkflowExecutionBodyModel): The workflow execution body model.

    Returns:
        RequestWorkflowExecutionResponse: The response model containing the workflow executions.

    Raises:
        HTTPException: If the workflow is not found.
    """
    logger.info(f"Executing workflow with ID: {workflow_execution_body.workflow_id}")

    await validate_execution_id(workflow_execution_body.workflow_id)

    return RequestWorkflowExecutionResponse(
        success=True,
        message="Successfully executed workflow",
        data=await execute_workflow(workflow_execution_body),
    )
