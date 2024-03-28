from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


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
