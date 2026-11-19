from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class SonicwallProtocol(str, Enum):
    """
    How the customer's firewall sends its syslog, which decides the Graylog input deployed for it.

    The value is the suffix of the input's content pack (`SOCFORTRESS_SONICWALL_INPUT_SYSLOG_<value>`)
    and of the input's title.
    """

    # Syslog over TCP with TLS, normally from a syslog-ng collector in front of the firewall.
    TLS = "TLS"
    # Syslog over UDP, straight from the firewall.
    UDP = "UDP"


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
        description=(
            "Receive syslog over TCP with TLS, normally from a syslog-ng collector in front of the firewall. "
            "Needs the TLS_CERT_FILE and TLS_KEY_FILE keys. Used when neither transport is chosen."
        ),
        examples=[True],
    )
    udp_enabled: Optional[bool] = Field(
        False,
        description="Receive syslog over UDP, straight from the firewall.",
        examples=[False],
    )
    hot_data_retention: int = Field(
        ...,
        examples=[30],
        description="Number of days to retain hot data",
    )
    index_replicas: int = Field(
        ...,
        examples=[1],
        description="Number of replicas for the customer's Graylog instance",
    )

    # ensure the `integration_name` is always set to "Sonicwall"
    @model_validator(mode="before")
    @classmethod
    def set_integration_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["integration_name"] = "Sonicwall"
        return values

    @model_validator(mode="after")
    def one_transport(self) -> "ProvisionSonicwallRequest":
        if self.tls_enabled and self.udp_enabled:
            raise ValueError("Choose either TLS or UDP, not both.")
        return self

    @property
    def protocol(self) -> SonicwallProtocol:
        """
        UDP only when asked for. Before UDP existed every deploy was TLS, whatever the request said,
        so a request naming neither transport still gets TLS.
        """
        return SonicwallProtocol.UDP if self.udp_enabled else SonicwallProtocol.TLS


class ProvisionSonicwallResponse(BaseModel):
    success: bool
    message: str


class ProvisionSonicwallKeys(BaseModel):
    SYSLOG_PORT: str = Field(
        ...,
        description="The syslog port.",
        examples=["514"],
    )
    TLS_CERT_FILE: Optional[str] = Field(
        None,
        description="The TLS certificate file path. Only used by the TLS input.",
        examples=["/etc/graylog/server/certs/Sonicwall_cert.pem"],
    )
    TLS_KEY_FILE: Optional[str] = Field(
        None,
        description="The TLS key file path. Only used by the TLS input.",
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
    protocol_type: SonicwallProtocol = Field(
        SonicwallProtocol.TLS,
        description="The transport of the input deployed for the customer.",
        examples=[SonicwallProtocol.UDP],
    )
    syslog_port: int = Field(
        ...,
        description="The syslog port.",
        examples=[514],
    )
    tls_cert_file: Optional[str] = Field(
        None,
        description="The TLS certificate file path. Required for TLS, unused for UDP.",
        examples=["/etc/graylog/server/certs/Sonicwall_cert.pem"],
    )
    tls_key_file: Optional[str] = Field(
        None,
        description="The TLS key file path. Required for TLS, unused for UDP.",
        examples=["/etc/graylog/server/certs/Sonicwall_key.key"],
    )
    hot_data_retention: int = Field(
        ...,
        examples=[30],
        description="Number of days to retain hot data",
    )
    index_replicas: int = Field(
        ...,
        examples=[1],
        description="Number of replicas for the customer's Graylog instance",
    )
