from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class ShuffleConnectorCredentialsResponse(BaseModel):
    """Minimal Shuffle connector creds for the frontend's `<ShuffleMCP>` /
    `<TryMcpSection>` embeds. We only expose URL + API key — not the full
    connector row — to keep the frontend surface narrow."""

    success: bool
    message: str
    base_url: str = Field(..., description="The Shuffle backend base URL (e.g. https://shuffler.io).")
    api_key: str = Field(..., description="The deployment-wide Shuffle API key from the connectors table.")


class IntegrationRequest(BaseModel):
    app_name: str = Field(..., description="The name of the application", examples=["PagerDuty"])
    category: str = Field(..., description="The category of the application", examples=["cases"])
    label: str = Field(..., description="The label of the application", examples=["create_ticket"])
    fields: Optional[List[Dict[str, Any]]] = Field(
        [],
        description="The fields of the application",
        examples=[
            [
                {"key": "title", "value": "This is the title"},
                {"key": "description", "value": "This is the description"},
                {"key": "source", "value": "Shuffle"},
            ],
        ],
    )
    skip_workflow: Optional[bool] = Field(
        False,
        description="Skip the workflow",
        examples=[True],
    )


class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str = Field(..., description="The ID of the workflow", examples=["workflow_id"])
    execution_arguments: Optional[Dict[str, Any]] = Field(
        {},
        description="The execution arguments",
        examples=[{"key": "value"}],
    )
    start: str = Field("", description="The start of the workflow", examples=["start"])

    @model_validator(mode="after")
    def check_customer_code(self):
        execution_arguments = self.execution_arguments or {}
        if "customer_code" not in execution_arguments or not execution_arguments["customer_code"]:
            raise HTTPException(status_code=400, detail="customer_code is required")
        return self
