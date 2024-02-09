from typing import Dict

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.schema import CustomerIntegrations
from app.integrations.schema import CustomerIntegrationsResponse


async def get_customer_integration_response(
    customer_code: str,
    session: AsyncSession,
) -> CustomerIntegrationsResponse:
    """
    Retrieves the integration response for a customer.

    Args:
        customer_code (str): The code of the customer.
        session (AsyncSession): The async session object for database operations.

    Returns:
        CustomerIntegrationsResponse: The integration response for the customer.

    Raises:
        HTTPException: If the customer integration settings are not found.
    """
    customer_integration_response = await get_customer_integrations_by_customer_code(
        customer_code,
        session,
    )
    if customer_integration_response.available_integrations == []:
        raise HTTPException(
            status_code=404,
            detail="Customer integration settings not found.",
        )
    return customer_integration_response


def extract_mimecast_auth_keys(
    customer_integration: CustomerIntegrations,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for Office365 integration from the given customer integration.

    Args:
        customer_integration (CustomerIntegrations): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for Office365 integration.

    Raises:
        HTTPException: If no authentication keys are found for Office365 integration.
    """
    mimecast_auth_keys = {}
    try:
        for subscription in customer_integration.integration_subscriptions:
            if subscription.integration_service.service_name == "Mimecast":
                for auth_key in subscription.integration_auth_keys:
                    mimecast_auth_keys[auth_key.auth_key_name] = auth_key.auth_value
        if not mimecast_auth_keys:
            raise HTTPException(
                status_code=404,
                detail="No auth keys found for Mimecast integration. Please create auth keys for Mimecast integration.",
            )
    except Exception as e:
        logger.error(f"Error extracting auth keys for Mimecast integration: {e}")
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for Mimecast integration. Please create auth keys for Mimecast integration.",
        )
    return mimecast_auth_keys
