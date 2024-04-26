from pydantic import BaseModel, Field
from pydantic import root_validator
from typing import Dict, Any, Optional

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
    tcp_enabled: Optional[bool] = Field(
        False,
        description="The tcp enabled.",
        examples=[True],
    )
    udp_enabled: Optional[bool] = Field(
        False,
        description="The udp enabled.",
        examples=[True],
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

class FortinetCustomerDetails(BaseModel):
    customer_name: str = Field(
        ...,
        description="The customer name.",
        examples=["Customer 1"],
    )
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    protocal_type: str = Field(
        ...,
        description="The protocal type.",
        examples=["TCP"],
    )
    syslog_port: int = Field(
        ...,
        description="The syslog port.",
        examples=[514],
    )

