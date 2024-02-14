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


def extract_auth_keys(customer_integration: CustomerIntegrations, service_name: str) -> Dict[str, str]:
    """
    Extracts the authentication keys for the given service name from the customer integration.

    Args:
        customer_integration (CustomerIntegrations): The customer integration object.
        service_name (str): The name of the service to extract the authentication keys for.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for the service.

    Raises:
        HTTPException: If no authentication keys are found for the service.
    """
    auth_keys = {}
    try:
        for subscription in customer_integration.integration_subscriptions:
            if subscription.integration_service.service_name == service_name:
                for auth_key in subscription.integration_auth_keys:
                    auth_keys[auth_key.auth_key_name] = auth_key.auth_value
        if not auth_keys:
            raise HTTPException(
                status_code=404,
                detail=f"No auth keys found for {service_name} integration. Please create auth keys for {service_name} integration.",
            )
    except Exception as e:
        logger.error(f"Error extracting auth keys for {service_name} integration: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"No auth keys found for {service_name} integration. Please create auth keys for {service_name} integration.",
        )
    return auth_keys
