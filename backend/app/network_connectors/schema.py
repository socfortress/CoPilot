from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class AuthKey(BaseModel):
    auth_key_name: str


class NetworkConnectorsWithAuthKeys(BaseModel):
    id: int
    network_connector_name: str
    description: str
    network_connector_details: str
    network_connector_keys: List[AuthKey]


class AvailableNetworkConnectorsResponse(BaseModel):
    network_connector_keys: List[NetworkConnectorsWithAuthKeys]
    message: str
    success: bool


class AvailableNetworkConnectorDetailResponse(BaseModel):
    network_connector: NetworkConnectorsWithAuthKeys
    message: str
    success: bool


class CreateNetworkConnectorsService(BaseModel):
    auth_type: str = Field(
        ...,
        description="The authentication type.",
        examples=["OAuth"],
    )
    config_key: str = Field(
        ...,
        description="The configuration key.",
        examples=["endpoint"],
    )
    config_value: str = Field(
        ...,
        description="The configuration value.",
        examples=["https://api.mimecast.com"],
    )


class CreateNetworkConnectorsAuthKeys(BaseModel):
    auth_key_name: str = Field(
        ...,
        description="The auth key.",
        examples=["username"],
    )
    auth_value: str = Field(
        ...,
        description="The auth value.",
        examples=["test-user"],
    )


class CustomerNetworkConnectorsCreate(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    customer_name: str = Field(
        ...,
        description="The customer name.",
        examples=["SOCFortress"],
    )
    network_connector_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )
    network_connector_config: CreateNetworkConnectorsService = Field(
        ...,
        description="The integration service.",
        examples=[{"auth_type": "OAuth", "config_key": "endpoint", "config_value": "https://api.mimecast.com"}],
    )
    # network_connector_auth_key: CreateIntegrationAuthKeys = Field(
    #     ...,
    #     description="The integration metadata.",
    # )
    network_connector_auth_keys: List[CreateNetworkConnectorsAuthKeys] = Field(
        ...,
        description="The integration auth keys.",
    )


class CustomerNetworkConnectorsCreateResponse(BaseModel):
    message: str = Field(
        ...,
        description="The message.",
    )
    success: bool = Field(
        ...,
        description="The success status.",
    )


class CustomerNetworkConnectorsDeleteResponse(BaseModel):
    message: str = Field(
        ...,
        description="The message.",
    )
    success: bool = Field(
        ...,
        description="The success status.",
    )


# class IntegrationConfig(BaseModel):
#     config_id: int
#     config_value: str
#     config_key: str

# class IntegrationService(BaseModel):
#     auth_type: str
#     service_name: str
#     id: int

# class IntegrationSubscription(BaseModel):
#     id: int
#     customer_id: int
#     network_connector_service_id: int
#     network_connector_service: IntegrationService
#     network_connector_config: IntegrationConfig

# class CustomerNetworkConnectors(BaseModel):
#     customer_code: str
#     id: int
#     customer_name: str
#     network_connector_subscriptions: List[IntegrationSubscription]

# class CustomerNetworkConnectorsResponse(BaseModel):
#     available_integrations: List[CustomerNetworkConnectors]
#     message: str
#     success: bool


class NetworkConnectorsAuthKeys(BaseModel):
    id: int
    auth_key_name: str
    auth_value: str
    subscription_id: int

    model_config = ConfigDict(from_attributes=True)


class NetworkConnectorsService(BaseModel):
    auth_type: str
    service_name: str
    id: int

    model_config = ConfigDict(from_attributes=True)


class NetworkConnectorsSubscription(BaseModel):
    id: int
    customer_id: int
    network_connectors_service_id: int
    network_connectors_service: NetworkConnectorsService
    network_connectors_keys: List[NetworkConnectorsAuthKeys]

    model_config = ConfigDict(from_attributes=True)


class CustomerNetworkConnectors(BaseModel):
    customer_code: str
    id: int
    customer_name: str
    network_connectors_subscriptions: List[NetworkConnectorsSubscription]
    network_connector_service_id: Optional[int] = Field(
        None,
        description="The integration service id.",
        examples=[1],
    )
    network_connector_service_name: Optional[str] = Field(
        ...,
        description="The integration service name.",
        examples=["Mimecast"],
    )
    deployed: Optional[bool] = Field(
        None,
        description="The deployment status.",
        examples=[True],
    )

    model_config = ConfigDict(from_attributes=True)


class CustomerNetworkConnectorsResponse(BaseModel):
    available_network_connectors: List[CustomerNetworkConnectors]
    message: str
    success: bool


class DeleteCustomerNetworkConnectors(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    network_connector_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )


class UpdateCustomerNetworkConnectors(BaseModel):
    network_connector_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )
    network_connector_auth_keys: List[CreateNetworkConnectorsAuthKeys] = Field(
        ...,
        description="The integration auth keys.",
    )


class CustomerNetworkConnectorsMetaSchema(BaseModel):
    id: Optional[int] = None
    customer_code: str
    network_connector_name: str
    graylog_input_id: Optional[str] = None
    graylog_index_id: str
    graylog_stream_id: str
    grafana_org_id: str
    grafana_dashboard_folder_id: str
    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "graylog_input_id",
        "graylog_index_id",
        "graylog_stream_id",
        "grafana_org_id",
        "grafana_dashboard_folder_id",
        mode="before",
    )
    @classmethod
    def coerce_external_ids_to_str(cls, value):
        """Grafana and Graylog hand back numeric IDs; these columns are varchars.

        Mirrors `CustomerIntegrationsMetaSchema.coerce_external_ids_to_str` — Pydantic v2
        no longer coerces `int` -> `str`, so normalize here instead of at each call site.
        """
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return value


class CustomerNetworkConnectorsMetaResponse(BaseModel):
    message: str
    success: bool
    customer_network_connectors_meta: Optional[List[CustomerNetworkConnectorsMetaSchema]] = Field(
        None,
        description="The customer integrations metadata.",
    )
