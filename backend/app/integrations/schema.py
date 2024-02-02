from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AuthKey(BaseModel):
    auth_key_name: str


class IntegrationWithAuthKeys(BaseModel):
    id: int
    integration_name: str
    description: str
    integration_details: str
    auth_keys: List[AuthKey]


class AvailableIntegrationsResponse(BaseModel):
    available_integrations: List[IntegrationWithAuthKeys]
    message: str
    success: bool


class CreateIntegrationService(BaseModel):
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


class CreateIntegrationAuthKeys(BaseModel):
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


class CustomerIntegrationCreate(BaseModel):
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
    integration_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )
    integration_config: CreateIntegrationService = Field(
        ...,
        description="The integration service.",
    )
    # integration_auth_key: CreateIntegrationAuthKeys = Field(
    #     ...,
    #     description="The integration metadata.",
    # )
    integration_auth_keys: List[CreateIntegrationAuthKeys] = Field(
        ...,
        description="The integration auth keys.",
    )


class CustomerIntegrationCreateResponse(BaseModel):
    message: str = Field(
        ...,
        description="The message.",
    )
    success: bool = Field(
        ...,
        description="The success status.",
    )


class CustomerIntegrationDeleteResponse(BaseModel):
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
#     integration_service_id: int
#     integration_service: IntegrationService
#     integration_config: IntegrationConfig

# class CustomerIntegrations(BaseModel):
#     customer_code: str
#     id: int
#     customer_name: str
#     integration_subscriptions: List[IntegrationSubscription]

# class CustomerIntegrationsResponse(BaseModel):
#     available_integrations: List[CustomerIntegrations]
#     message: str
#     success: bool


class IntegrationAuthKeys(BaseModel):
    id: int
    auth_key_name: str
    auth_value: str
    subscription_id: int


class IntegrationService(BaseModel):
    auth_type: str
    service_name: str
    id: int


class IntegrationSubscription(BaseModel):
    id: int
    customer_id: int
    integration_service_id: int
    integration_service: IntegrationService
    integration_auth_keys: List[IntegrationAuthKeys]  # Changed from IntegrationConfig


class CustomerIntegrations(BaseModel):
    customer_code: str
    id: int
    customer_name: str
    integration_subscriptions: List[IntegrationSubscription]
    integration_service_id: Optional[int] = Field(
        None,
        description="The integration service id.",
        examples=[1],
    )
    integration_service_name: Optional[str] = Field(
        ...,
        description="The integration service name.",
        examples=["Mimecast"],
    )
    deployed: Optional[bool] = Field(
        None,
        description="The deployment status.",
        examples=[True],
    )


class CustomerIntegrationsResponse(BaseModel):
    available_integrations: List[CustomerIntegrations]
    message: str
    success: bool


class DeleteCustomerIntegration(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )


class UpdateCustomerIntegration(BaseModel):
    integration_name: str = Field(
        ...,
        description="The integration name.",
        examples=["Mimecast"],
    )
    integration_auth_keys: List[CreateIntegrationAuthKeys] = Field(
        ...,
        description="The integration auth keys.",
    )


class CustomerIntegrationsMetaSchema(BaseModel):
    id: Optional[int] = None
    customer_code: str
    integration_name: str
    graylog_input_id: Optional[str] = None
    graylog_index_id: str
    graylog_stream_id: str
    grafana_org_id: str
    grafana_dashboard_folder_id: str

    class Config:
        orm_mode = True


class CustomerIntegrationsMetaResponse(BaseModel):
    message: str
    success: bool
    customer_integrations_meta: Optional[List[CustomerIntegrationsMetaSchema]] = Field(
        None,
        description="The customer integrations metadata.",
    )
