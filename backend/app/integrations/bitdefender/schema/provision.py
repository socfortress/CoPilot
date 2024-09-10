from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionBitdefenderRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00001"],
    )
    integration_name: str = Field(
        "Bitdefender",
        description="The integration name.",
        examples=["BitDefender"],
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

    # ensure the `integration_name` is always set to "Bitdefender"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "BitDefender"
        return values


class ProvisionBitdefenderResponse(BaseModel):
    success: bool
    message: str


class ProvisionBitdefenderAuthKeys(BaseModel):
    BASIC_AUTH_USERNAME: str = Field(
        ...,
        description="The basic auth username.",
        examples=["admin"],
    )
    BASIC_AUTH_PASSWORD: str = Field(
        ...,
        description="The basic auth password.",
        examples=["password"],
    )
    WEBSERVER_HOSTNAME: str = Field(
        ...,
        description="The webserver hostname.",
        examples=["firehose.socfortress.co"],
    )
    WEBSERVER_PORT: str = Field(
        ...,
        description="The webserver port.",
        examples=["3200"],
    )
    GRAYLOG_PORT: str = Field(
        ...,
        description="The Graylog port.",
        examples=["10514"],
    )
    API_KEY: str = Field(
        ...,
        description="The API key.",
        examples=["api_key"],
    )


class BitdefenderCustomerDetails(BaseModel):
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
