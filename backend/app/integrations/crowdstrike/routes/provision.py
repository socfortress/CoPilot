from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.crowdstrike.schema.provision import CrowdstrikeCustomerDetails
from app.integrations.crowdstrike.schema.provision import ProvisionCrowdstrikeAuthKeys
from app.integrations.crowdstrike.schema.provision import ProvisionCrowdstrikeRequest
from app.integrations.crowdstrike.schema.provision import ProvisionCrowdstrikeResponse
from app.integrations.crowdstrike.services.provision import provision_crowdstrike
from app.integrations.routes import find_customer_integration
from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.schema import CustomerIntegrations
from app.integrations.schema import CustomerIntegrationsResponse

integration_crowdstrike_router = APIRouter()


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


def extract_crowdstrike_auth_keys(
    customer_integration: CustomerIntegrations,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for Crowdstrike integration from the given customer integration.

    Args:
        customer_integration (CustomerIntegrations): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for Crowdstrike integration.

    Raises:
        HTTPException: If no authentication keys are found for Crowdstrike integration.
    """
    crowdstrike_auth_keys = {}
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == "Crowdstrike":
            for auth_key in subscription.integration_auth_keys:
                crowdstrike_auth_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not crowdstrike_auth_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for Crowdstrike integration. Please create auth keys for Crowdstrike integration.",
        )
    return crowdstrike_auth_keys


@integration_crowdstrike_router.post(
    "/provision",
    response_model=ProvisionCrowdstrikeResponse,
    description="Provision Crowdstrike integration for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_crowdstrike_route(
    provision_crowdstrike_request: ProvisionCrowdstrikeRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionCrowdstrikeResponse:
    """
    Provisions Crowdstrike integration for a customer.

    Args:
        provision_crowdstrike_request (ProvisionCrowdstrikeRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionCrowdstrikeResponse: The response object containing the result of the provisioning.
    """
    customer_integration_response = await get_customer_integration_response(
        provision_crowdstrike_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        provision_crowdstrike_request.customer_code,
        provision_crowdstrike_request.integration_name,
        customer_integration_response,
    )

    crowdstrike_auth_keys = extract_crowdstrike_auth_keys(customer_integration)

    auth_keys = ProvisionCrowdstrikeAuthKeys(**crowdstrike_auth_keys)

    return await provision_crowdstrike(
        customer_details=CrowdstrikeCustomerDetails(
            customer_code=provision_crowdstrike_request.customer_code,
            customer_name=customer_integration.customer_name,
            protocal_type="TCP",
            syslog_port=int(auth_keys.SYSLOG_PORT),
            hot_data_retention=provision_crowdstrike_request.hot_data_retention,
            index_replicas=provision_crowdstrike_request.index_replicas,
        ),
        keys=auth_keys,
        session=session,
    )
