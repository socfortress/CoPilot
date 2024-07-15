from pydantic import BaseModel
from pydantic import Field


class CreateAlertRequest(BaseModel):
    index_name: str = Field(
        ...,
        description="The name of the index to search alerts for.",
    )
    alert_id: str = Field(..., description="The alert id.")


class CreateAlertResponse(BaseModel):
    success: bool
    message: str
    alert_id: int = Field(..., description="The alert id as created in CoPilot.")
