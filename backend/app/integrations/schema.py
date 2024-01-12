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
