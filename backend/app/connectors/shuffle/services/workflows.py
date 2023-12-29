from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.shuffle.schema.workflows import WorkflowExecutionBodyModel
from app.connectors.shuffle.schema.workflows import WorkflowExecutionStatusResponseModel
from app.connectors.shuffle.schema.workflows import WorkflowsResponse
from app.connectors.shuffle.utils.universal import send_get_request


def remove_large_images_from_actions(workflows: List) -> List:
    """
    Removes the `large_image` keys from actions in each workflow.

    Args:
        workflows (List): A list of workflows.

    Returns:
        List: The updated list of workflows with `large_image` keys removed from actions.
    """
    for workflow in workflows:
        if "actions" in workflow:
            for action in workflow["actions"]:
                action.pop("large_image", None)  # Use pop to avoid KeyError if 'large_image' does not exist
    return workflows


async def get_workflows() -> WorkflowsResponse:
    """
    Returns a list of workflows.

    :return: WorkflowsResponse object containing the list of workflows.
    :rtype: WorkflowsResponse
    """
    logger.info("Getting workflows")

    try:
        response = await send_get_request("/api/v1/workflows")
        if response is None:
            return WorkflowsResponse(success=False, message="Failed to get workflows", workflows=[])

        workflows = response.get("data")
        workflows_without_large_images = remove_large_images_from_actions(workflows)

        return WorkflowsResponse(success=True, message="Successfully fetched workflows", workflows=workflows_without_large_images)

    except Exception as e:
        logger.error(f"Failed to get workflows with error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflows with error: {e}")


async def get_workflow_executions(exection_body: WorkflowExecutionBodyModel) -> WorkflowExecutionStatusResponseModel:
    """
    Returns a list of workflow executions.

    Parameters:
    - exection_body (WorkflowExecutionBodyModel): The body of the workflow execution request.

    Returns:
    - WorkflowExecutionStatusResponseModel: The response model containing the status of the last run.

    Raises:
    - HTTPException: If there is an error while getting the workflow executions.
    """
    logger.info("Getting workflow executions")
    response = await send_get_request(f"/api/v1/workflows/{exection_body.workflow_id}/executions")
    try:
        executions = response["data"]
        if executions:
            status = executions[0]["status"]
            if status is None:
                status = "Never Ran"
        else:
            status = "No executions found"
        return WorkflowExecutionStatusResponseModel(last_run=status)
    except Exception as e:
        logger.error(f"Failed to get workflow executions with error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow executions with error: {e}")
