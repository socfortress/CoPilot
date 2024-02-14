from typing import Any
from typing import Dict

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionSapSiemRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    time_interval: int = Field(
        ...,
        description="The time interval for the scheduler.",
        examples=[5],
    )
    integration_name: str = Field(
        "SAP SIEM",
        description="The integration name.",
        examples=["SAP SIEM"],
    )

    # ensure the `integration_name` is always set to "Mimecast"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "SAP SIEM"
        return values


class ProvisionSapSiemResponse(BaseModel):
    success: bool
    message: str
