from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import UUID4
from pydantic import BaseModel
from pydantic import Field


class WorkflowsResponse(BaseModel):
    message: str
    success: bool
    workflows: Optional[List[Dict[str, Any]]] = Field(
        [],
        description="The alerts returned from the search.",
    )


class WorkflowStatusExecutionModel(BaseModel):
    executions: Optional[str] = Field(None, description="Status of workflow executions")
    message: str = Field(..., description="Status message")
    success: bool = Field(..., description="Success status")


class WorkflowExecutionBodyModel(BaseModel):
    workflow_id: str = Field(..., description="Unique identifier for the workflow")


class WorkflowExecutionStatusResponseModel(BaseModel):
    last_run: Optional[str] = Field(..., description="Status of workflow executions")


class WorkflowExecutionModel(BaseModel):
    status: WorkflowExecutionStatusResponseModel = Field(
        ...,
        description="Status object",
    )
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    workflow_name: str = Field(..., description="Name of the workflow")


class WorkflowExecutionResponseModel(BaseModel):
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Success status")
    workflows: List[WorkflowExecutionModel] = Field(
        ...,
        description="List of workflow objects",
    )


class RequestWorkflowExecutionModel(BaseModel):
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    execution_argument: str = Field(..., description="Execution argument for the workflow")


class ExecuteWorklow(BaseModel):
    success: bool = Field(..., description="Indicates if the workflow execution was successful")
    execution_id: UUID4 = Field(..., description="The unique identifier for the workflow execution")
    authorization: UUID4 = Field(..., description="The authorization token for the workflow execution")


class RequestWorkflowExecutionResponse(BaseModel):
    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Success status")
    data: Dict[str, Any] = Field(..., description="Data object")
