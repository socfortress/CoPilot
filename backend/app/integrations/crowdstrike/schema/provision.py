from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionCrowdstrikeRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00001"],
    )
    integration_name: str = Field(
        "Crowdstrike",
        description="The integration name.",
        examples=["Crowdstrike"],
    )
    hot_data_retention: Optional[int] = Field(
        30,
        example=30,
        description="Number of days to retain hot data",
    )
    index_replicas: Optional[int] = Field(
        0,
        example=1,
        description="Number of replicas for the customer's Graylog instance",
    )

    # ensure the `integration_name` is always set to "Crowdstrike"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Crowdstrike"
        return values


class ProvisionCrowdstrikeResponse(BaseModel):
    success: bool
    message: str


class ProvisionCrowdstrikeAuthKeys(BaseModel):
    CLIENT_ID: str = Field(
        ...,
        description="The client id.",
        examples=["00002"],
    )
    CLIENT_SECRET: str = Field(
        ...,
        description="The client secret.",
        examples=["00002"],
    )
    BASE_URL: str = Field(
        ...,
        description="The api type.",
        examples=["https://api.crowdstrike.com"],
    )
    SYSLOG_PORT: str = Field(
        ...,
        description="The syslog port.",
        examples=["5556"],
    )


class CrowdstrikeCustomerDetails(BaseModel):
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
    hot_data_retention: int = Field(
        ...,
        example=30,
        description="Number of days to retain hot data",
    )
    index_replicas: int = Field(
        ...,
        example=1,
        description="Number of replicas for the customer's Graylog instance",
    )
