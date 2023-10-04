from typing import Dict, List, Optional, Any, Tuple, Union
import requests
import xmltodict
from loguru import logger
from pydantic import Field
import json

from app.connectors.shuffle.schema.workflows import (
    WorkflowsResponse, WorkflowExecutionResponseModel, WorkflowExecutionBodyModel, WorkflowExecutionStatusResponseModel
)

from app.connectors.shuffle.utils.universal import (
    send_get_request
)

def get_workflows() -> WorkflowsResponse:
    """
    Returns a list of workflows.
    """
    logger.info("Getting workflows")
    response = send_get_request("/api/v1/workflows")
    if response is None:
        return WorkflowsResponse(success=False, message="Failed to get workflows", workflows=[])
    return WorkflowsResponse(success=True, message="Successfully fetched workflows", workflows=response["data"])

def get_workflow_executions(exection_body: WorkflowExecutionBodyModel) -> WorkflowExecutionStatusResponseModel:
    """
    Returns a list of workflow executions.
    """
    logger.info("Getting workflow executions")
    response = send_get_request(f"/api/v1/workflows/{exection_body.workflow_id}/executions")
    executions = response["data"]
    if executions:
        status = executions[0]["status"]
        if status is None:
            status = "Never Ran"
    else:
        status = "No executions found"
    return WorkflowExecutionStatusResponseModel(last_run=status)
