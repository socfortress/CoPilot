from flask import Blueprint
from flask import jsonify

# from app.models.connectors import Connector
# from app.models.connectors import WazuhManagerConnector
# from app.services.agents.agents import AgentService
# from app.services.agents.agents import AgentSyncService
from app.services.Shuffle.workflows import WorkflowsService

# from flask import request
# from loguru import logger


bp = Blueprint("shuffle", __name__)


@bp.route("/shuffle/workflows", methods=["GET"])
def get_workflows() -> jsonify:
    """
    Endpoint to list all available Shuffle workflows.

    Returns:
        jsonify: A JSON response containing the list of all configured Workflows in Shuffle.
    """
    service = WorkflowsService()
    workflows = service.collect_workflows()
    return workflows


@bp.route("/shuffle/workflows/executions", methods=["GET"])
def get_workflows_executions() -> jsonify:
    """
    Endpoint to list all available Shuffle workflow execution status.

    This endpoint retrieves the status of the most recent execution for each workflow in Shuffle.

    Returns:
        jsonify: A JSON response containing the list of all configured workflows and their last execution status.
    """
    service = WorkflowsService()
    workflow_details = service.collect_workflow_details()
    if "workflows" not in workflow_details:
        message = "No workflows found"
        return jsonify({"message": message, "success": False}), 500
    for workflow in workflow_details["workflows"]:
        workflow["status"] = service.collect_workflow_executions_status(
            workflow["workflow_id"],
        )
    return workflow_details


@bp.route("/shuffle/workflows/executions/<workflow_id>", methods=["GET"])
def get_workflow_executions(workflow_id: str) -> jsonify:
    """
    Endpoint to list execution status of a specified Shuffle workflow.

    This endpoint retrieves the status of the most recent execution for a specific workflow in Shuffle.

    Args:
        workflow_id (str): The ID of the workflow to retrieve the execution status for.

    Returns:
        jsonify: A JSON response containing the last execution status of the specified workflow.
    """
    service = WorkflowsService()
    workflow_details = service.collect_workflow_executions_status(workflow_id)
    return workflow_details
