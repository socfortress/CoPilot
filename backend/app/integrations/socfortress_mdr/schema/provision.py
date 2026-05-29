from pydantic import BaseModel
from pydantic import Field


class ProvisionSOCFortressMDRRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00001"],
    )
    integration_name: str = Field(
        "SOCFortress MDR",
        description="The integration name.",
        examples=["SOCFortress MDR"],
    )


class ProvisionSOCFortressMDRResponse(BaseModel):
    success: bool
    message: str
