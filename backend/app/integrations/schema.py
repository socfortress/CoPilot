from pydantic import BaseModel
from pydantic import Field
from app.integrations.models.customer_integration_settings import AvailableIntegrations

class AvailableIntegrationsResponse(BaseModel):
    """
    The response model for the /integrations/available_integrations endpoint.
    """
    available_integrations: list[AvailableIntegrations] = Field(
        ...,
        description="The available integrations.",
    )
    message: str = Field(
        ...,
        description="The message.",
    )
    success: bool = Field(
        ...,
        description="The success status.",
    )

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

class CreateIntegrationMetadata(BaseModel):
    metadata_key: str = Field(
        ...,
        description="The metadata key.",
        examples=["username"],
    )
    metadata_value: str = Field(
        ...,
        description="The metadata value.",
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
        examples=["mimecast"],
    )
    integration_details: CreateIntegrationService = Field(
        ...,
        description="The integration service.",
    )
    integration_metadata: CreateIntegrationMetadata = Field(
        ...,
        description="The integration metadata.",
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
