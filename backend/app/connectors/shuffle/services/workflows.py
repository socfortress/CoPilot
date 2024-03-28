import asyncio
from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.shuffle.schema.workflows import ExecuteWorklow
from app.connectors.shuffle.schema.workflows import RequestWorkflowExecutionModel
from app.connectors.shuffle.schema.workflows import WorkflowExecutionBodyModel
from app.connectors.shuffle.schema.workflows import WorkflowExecutionStatusResponseModel
from app.connectors.shuffle.schema.workflows import WorkflowsResponse
from app.connectors.shuffle.utils.universal import send_get_request
from app.connectors.shuffle.utils.universal import send_post_request


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
                action.pop(
                    "large_image",
                    None,
                )  # Use pop to avoid KeyError if 'large_image' does not exist
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
            return WorkflowsResponse(
                success=False,
                message="Failed to get workflows",
                workflows=[],
            )

        workflows = response.get("data")
        workflows_without_large_images = remove_large_images_from_actions(workflows)

        return WorkflowsResponse(
            success=True,
            message="Successfully fetched workflows",
            workflows=workflows_without_large_images,
        )

    except Exception as e:
        logger.error(f"Failed to get workflows with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflows with error: {e}",
        )


async def get_workflow_executions(
    exection_body: WorkflowExecutionBodyModel,
) -> WorkflowExecutionStatusResponseModel:
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
    response = await send_get_request(
        f"/api/v1/workflows/{exection_body.workflow_id}/executions",
    )
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow executions with error: {e}",
        )


async def execute_workflow(workflow_execution_body: RequestWorkflowExecutionModel):
    """
    Execute a workflow.

    Args:
        workflow_execution_body (WorkflowExecutionBodyModel): The workflow execution body model.

    Returns:
        WorkflowExecutionResponseModel: The response model containing the workflow executions.

    Raises:
        HTTPException: If the workflow is not found.
    """
    logger.info(f"Executing workflow with ID: {workflow_execution_body.workflow_id}")
    response = ExecuteWorklow(
        **(
            await send_post_request(
                f"/api/v1/workflows/{workflow_execution_body.workflow_id}/execute",
                {"execution_argument": workflow_execution_body.execution_argument},
            )
        )["data"],
    )
    logger.info(f"Response from executing workflow: {response}")
    try:
        if response.success:
            workflow_completed = await wait_for_workflow_execution_results(response)
            if workflow_completed:
                logger.info(f"Successfully executed workflow with ID: {workflow_execution_body.workflow_id}")
                return await get_workflow_exectution_results(response)
        else:
            raise HTTPException(
                status_code=404,
                detail="Failed to execute workflow",
            )
    except Exception as e:
        logger.error(f"Failed to execute workflow with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute workflow with error: {e}",
        )


async def wait_for_workflow_execution_results(execution: ExecuteWorklow):
    """
    Function to get the workflow results until the status of `FINISHED` is reached.
    """
    logger.info(f"Retrieving workflow execution results for execution ID: {execution.execution_id}")
    for i in range(10):
        try:
            response = await send_post_request(
                "/api/v1/streams/results",
                {"execution_id": str(execution.execution_id), "authorization": str(execution.authorization)},
            )
            status = response.get("data", {}).get("status")
            if status == "FINISHED":
                logger.info(f"Workflow execution with ID {execution.execution_id} has finished")
                return True
        except Exception as e:
            logger.error(f"Error retrieving workflow execution results: {e}")
        await asyncio.sleep(2**i)
    logger.info(f"Workflow execution with ID {execution.execution_id} did not finish after 5 attempts")
    raise HTTPException(
        status_code=500,
        detail=f"Workflow execution with ID {execution.execution_id} did not finish after 5 attempts",
    )


async def get_workflow_exectution_results(execution: ExecuteWorklow):
    """
    Function to get the workflow results.
    """
    logger.info(f"Retrieving workflow execution results for execution ID: {execution.execution_id}")
    response = await send_post_request(
        "/api/v1/streams/results",
        {"execution_id": str(execution.execution_id), "authorization": str(execution.authorization)},
    )
    return response.get("data", {})
