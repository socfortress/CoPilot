from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.bitdefender.schema.provision import BitdefenderCustomerDetails
from app.integrations.bitdefender.schema.provision import ProvisionBitdefenderAuthKeys
from app.integrations.bitdefender.schema.provision import ProvisionBitdefenderRequest
from app.integrations.bitdefender.schema.provision import ProvisionBitdefenderResponse
from app.integrations.bitdefender.services.provision import provision_bitdefender
from app.integrations.routes import find_customer_integration
from app.integrations.routes import get_customer_integrations_by_customer_code
from app.integrations.schema import CustomerIntegrations
from app.integrations.schema import CustomerIntegrationsResponse
from loguru import logger

integration_bitdefender_router = APIRouter()


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


def extract_bitdefender_auth_keys(
    customer_integration: CustomerIntegrations,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for Bitdefender integration from the given customer integration.

    Args:
        customer_integration (CustomerIntegrations): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for Bitdefender integration.

    Raises:
        HTTPException: If no authentication keys are found for Bitdefender integration.
    """
    bitdefender_auth_keys = {}
    for subscription in customer_integration.integration_subscriptions:
        if subscription.integration_service.service_name == "BitDefender":
            for auth_key in subscription.integration_auth_keys:
                bitdefender_auth_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not bitdefender_auth_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for Bitdefender integration. Please create auth keys for Bitdefender integration.",
        )
    return bitdefender_auth_keys


@integration_bitdefender_router.post(
    "/provision",
    response_model=ProvisionBitdefenderResponse,
    description="Provision Bitdefender integration for a customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_bitdefender_route(
    provision_bitdefender_request: ProvisionBitdefenderRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionBitdefenderResponse:
    """
    Provisions Bitdefender integration for a customer.

    Args:
        provision_bitdefender_request (ProvisionBitdefenderRequest): The request object containing the necessary information for provisioning.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        ProvisionBitdefenderResponse: The response object containing the result of the provisioning.
    """
    customer_integration_response = await get_customer_integration_response(
        provision_bitdefender_request.customer_code,
        session,
    )

    customer_integration = await find_customer_integration(
        provision_bitdefender_request.customer_code,
        provision_bitdefender_request.integration_name,
        customer_integration_response,
    )

    bitdefender_auth_keys = extract_bitdefender_auth_keys(customer_integration)

    auth_keys = ProvisionBitdefenderAuthKeys(**bitdefender_auth_keys)


    return await provision_bitdefender(
        customer_details=BitdefenderCustomerDetails(
            customer_code=provision_bitdefender_request.customer_code,
            customer_name=customer_integration.customer_name,
            protocal_type="TCP",
            syslog_port=int(auth_keys.GRAYLOG_PORT),
            hot_data_retention=provision_bitdefender_request.hot_data_retention,
            index_replicas=provision_bitdefender_request.index_replicas,
        ),
        keys=auth_keys,
        session=session,
    )
