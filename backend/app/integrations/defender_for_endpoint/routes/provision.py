from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.defender_for_endpoint.schema.provision import (
    DefenderForEndpointCustomerDetails,
)
from app.integrations.defender_for_endpoint.schema.provision import (
    ProvisionDefenderForEndpointAuthKeys,
)
from app.integrations.defender_for_endpoint.schema.provision import (
    ProvisionDefenderForEndpointRequest,
)
from app.integrations.defender_for_endpoint.schema.provision import (
    ProvisionDefenderForEndpointResponse,
)
from app.integrations.defender_for_endpoint.services.provision import (
    provision_defender_for_endpoint,
)
from app.integrations.routes import find_customer_integration
from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.schema import CustomerIntegrations
from app.integrations.schema import CustomerIntegrationsResponse

integration_defender_for_endpoint_router = APIRouter()


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


def extract_defender_for_endpoint_auth_keys(
    customer_integration: CustomerIntegrations,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for defender_for_endpoint integration from the given customer integration.

    Args:
        customer_integration (CustomerIntegrations): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for defender_for_endpoint integration.

    Raises:
        HTTPException: If no authentication keys are found for defender_for_endpoint integration.
    """
    defender_for_endpoint_auth_keys = {}
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == "DefenderForEndpoint":
            for auth_key in subscription.integration_auth_keys:
                defender_for_endpoint_auth_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not defender_for_endpoint_auth_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for defender_for_endpoint integration. Please create auth keys for defender_for_endpoint integration.",
        )
    return defender_for_endpoint_auth_keys


@integration_defender_for_endpoint_router.post(
    "/provision",
    response_model=ProvisionDefenderForEndpointResponse,
    description="Provision DefenderForEndpoint integration for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_defender_for_endpoint_route(
    provision_defender_for_endpoint_request: ProvisionDefenderForEndpointRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionDefenderForEndpointResponse:
    """
    Provisions DefenderForEndpoint integration for a customer.

    Args:
        provision_defender_for_endpoint_request (ProvisionDefenderForEndpointRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionDefenderForEndpointResponse: The response object containing the result of the provisioning.
    """
    customer_integration_response = await get_customer_integration_response(
        provision_defender_for_endpoint_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        provision_defender_for_endpoint_request.customer_code,
        provision_defender_for_endpoint_request.integration_name,
        customer_integration_response,
    )

    defender_for_endpoint_auth_keys = extract_defender_for_endpoint_auth_keys(customer_integration)

    auth_keys = ProvisionDefenderForEndpointAuthKeys(**defender_for_endpoint_auth_keys)

    return await provision_defender_for_endpoint(
        customer_details=DefenderForEndpointCustomerDetails(
            customer_code=provision_defender_for_endpoint_request.customer_code,
            customer_name=customer_integration.customer_name,
            protocal_type="TCP",
            syslog_port=int(auth_keys.SYSLOG_PORT),
            hot_data_retention=provision_defender_for_endpoint_request.hot_data_retention,
            index_replicas=provision_defender_for_endpoint_request.index_replicas,
        ),
        keys=auth_keys,
        session=session,
    )
