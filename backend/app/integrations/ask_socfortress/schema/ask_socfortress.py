from pydantic import BaseModel
from pydantic import Field


class AskSocfortressRequest(BaseModel):
    index_name: str = Field(
        ...,
        description="The name of the index to search alerts for.",
    )
    alert_id: str = Field(..., description="The alert id.")


class AskSocfortressSigmaRequest(BaseModel):
    sigma_rule_name: str = Field(..., title="Sigma rule name")


class AskSocfortressSigmaResponse(BaseModel):
    message: str = Field(..., title="Message")
    success: bool = Field(..., title="Success")
