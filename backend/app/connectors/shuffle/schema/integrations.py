from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class IntegrationRequest(BaseModel):
    app_name: str = Field(..., description="The name of the application", example="PagerDuty")
    category: str = Field(..., description="The category of the application", example="cases")
    label: str = Field(..., description="The label of the application", example="create_ticket")
    fields: Optional[List[Dict[str, Any]]] = Field(
        [],
        description="The fields of the application",
        example=[
            {"key": "title", "value": "This is the title"},
            {"key": "description", "value": "This is the description"},
            {"key": "source", "value": "Shuffle"},
        ],
    )
    skip_workflow: Optional[bool] = Field(
        False,
        description="Skip the workflow",
        example=True,
    )


class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., description="The ID of the workflow", example="workflow_id")
    execution_arguments: Optional[Dict[str, Any]] = Field(
        {},
        description="The execution arguments",
        example={"key": "value"},
    )
    start: str = Field("", description="The start of the workflow", example="start")

    @root_validator
    def check_customer_code(cls, values):
        execution_arguments = values.get("execution_arguments", {})
        if "customer_code" not in execution_arguments or not execution_arguments["customer_code"]:
            raise HTTPException(status_code=400, detail="customer_code is required")
        return values
