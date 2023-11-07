from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.shuffle.schema.workflows import WorkflowExecutionBodyModel
from app.connectors.shuffle.schema.workflows import WorkflowExecutionResponseModel
from app.connectors.shuffle.schema.workflows import WorkflowsResponse
from app.connectors.shuffle.services.workflows import get_workflow_executions
from app.connectors.shuffle.services.workflows import get_workflows

shuffle_workflows_router = APIRouter()


@shuffle_workflows_router.get(
    "",
    response_model=WorkflowsResponse,
    description="Get all workflows",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_workflows() -> WorkflowsResponse:
    logger.info("Fetching all workflows")
    return await get_workflows()


@shuffle_workflows_router.get(
    "/executions",
    response_model=WorkflowExecutionResponseModel,
    description="Get all workflow executions",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_workflow_executions() -> WorkflowExecutionResponseModel:
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
                    "status": await get_workflow_executions(WorkflowExecutionBodyModel(workflow_id=workflow["id"])),
                },
            )
        return WorkflowExecutionResponseModel(success=True, message="Successfully fetched workflow executions", workflows=workflow_details)
    else:
        raise HTTPException(status_code=404, detail="No workflows found")
