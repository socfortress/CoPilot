from pydantic import BaseModel
from pydantic import Field

from app.customer_provisioning.models.default_settings import (
    CustomerProvisioningDefaultSettings,
)


class CustomerProvisioningDefaultSettingsResponse(BaseModel):
    message: str = Field(
        ...,
        example="Customer Provisioning Default Settings retrieved successfully",
        description="Message indicating the customer provisioning default settings were retrieved successfully",
    )
    success: bool = Field(
        ...,
        example=True,
        description="Whether the customer provisioning default settings were retrieved successfully or not",
    )
    customer_provisioning_default_settings: CustomerProvisioningDefaultSettings = Field(
        ...,
        description="Customer Provisioning Default Settings",
    )
