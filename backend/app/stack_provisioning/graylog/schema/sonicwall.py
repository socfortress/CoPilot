from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class ProvisionSonicwallRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Sonicwall",
        description="The integration name.",
        examples=["Sonicwall"],
    )
    tls_enabled: Optional[bool] = Field(
        False,
        description="TLS enabled for secure log forwarding.",
        examples=[True],
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

    # ensure the `integration_name` is always set to "Sonicwall"
    @root_validator(pre=True)
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Sonicwall"
        return values


class ProvisionSonicwallResponse(BaseModel):
    success: bool
    message: str


class ProvisionSonicwallKeys(BaseModel):
    SYSLOG_PORT: str = Field(
        ...,
        description="The syslog port.",
        examples=["514"],
    )
    TLS_CERT_FILE: str = Field(
        ...,
        description="The TLS certificate file path.",
        examples=["/etc/graylog/server/certs/Sonicwall_cert.pem"],
    )
    TLS_KEY_FILE: str = Field(
        ...,
        description="The TLS key file path.",
        examples=["/etc/graylog/server/certs/Sonicwall_key.key"],
    )


class SonicwallCustomerDetails(BaseModel):
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
    syslog_port: int = Field(
        ...,
        description="The syslog port.",
        examples=[514],
    )
    tls_cert_file: str = Field(
        ...,
        description="The TLS certificate file path.",
        examples=["/etc/graylog/server/certs/Sonicwall_cert.pem"],
    )
    tls_key_file: str = Field(
        ...,
        description="The TLS key file path.",
        examples=["/etc/graylog/server/certs/Sonicwall_key.key"],
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
