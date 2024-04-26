from pydantic import BaseModel, Field
from pydantic import root_validator
from typing import Dict, Any

class ProvisionFortinetRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Fortinet",
        description="The integration name.",
        examples=["Fortinet"],
    )

    # ensure the `integration_name` is always set to "Fortinet"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Fortinet"
        return values


class ProvisionFortinetResponse(BaseModel):
    success: bool
    message: str

class ProvisionFortinetKeys(BaseModel):
    SYSLOG_PORT: str = Field(
        ...,
        description="The syslog port.",
        examples=["514"],
    )
