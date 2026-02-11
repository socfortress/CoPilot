from typing import Dict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.network_connectors.routes import find_customer_network_connector
from app.network_connectors.routes import (
    get_customer_network_connectors_by_customer_code,
)
from app.connectors.graylog.utils.routing import GraylogContext
from app.connectors.graylog.utils.routing import set_graylog_context
from app.connectors.graylog.utils.routing import clear_graylog_context
from app.network_connectors.schema import CustomerNetworkConnectors
from app.network_connectors.schema import CustomerNetworkConnectorsResponse
from app.stack_provisioning.graylog.schema.sonicwall import ProvisionSonicwallKeys
from app.stack_provisioning.graylog.schema.sonicwall import ProvisionSonicwallRequest
from app.stack_provisioning.graylog.schema.sonicwall import ProvisionSonicwallResponse
from app.stack_provisioning.graylog.schema.sonicwall import SonicwallCustomerDetails
from app.stack_provisioning.graylog.services.sonicwall import provision_sonicwall

stack_provisioning_graylog_sonicwall_router = APIRouter()


async def get_customer_integration_response(
    customer_code: str,
    session: AsyncSession,
) -> CustomerNetworkConnectorsResponse:
    """
    Retrieves the integration response for a customer.

    Args:
        customer_code (str): The code of the customer.
        session (AsyncSession): The async session object for database operations.

    Returns:
        CustomerNetworkConnectorsResponse: The integration response for the customer.

    Raises:
        HTTPException: If the customer integration settings are not found.
    """
    customer_integration_response = await get_customer_network_connectors_by_customer_code(
        customer_code,
        session,
    )
    if customer_integration_response.available_network_connectors == []:
        raise HTTPException(
            status_code=404,
            detail="Customer integration settings not found.",
        )
    return customer_integration_response


def extract_sonicwall_keys(
    customer_integration: CustomerNetworkConnectors,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for SonicWall integration from the given customer integration.

    Args:
        customer_integration (CustomerNetworkConnectors): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for SonicWall integration.

    Raises:
        HTTPException: If no authentication keys are found for SonicWall integration.
    """
    sonicwall_keys = {}
    for subscription in customer_integration.network_connectors_subscriptions:
        if subscription.network_connectors_service.service_name == "Sonicwall":
            for auth_key in subscription.network_connectors_keys:
                sonicwall_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not sonicwall_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for Sonicwall integration. Please create auth keys for Sonicwall network connector.",
        )
    return sonicwall_keys


@stack_provisioning_graylog_sonicwall_router.post(
    "/graylog/provision/sonicwall",
    response_model=ProvisionSonicwallResponse,
    description="Provision SonicWall for the customer. Uses Graylog-Network instance for all Graylog operations.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_sonicwall_route(
    provision_sonicwall_request: ProvisionSonicwallRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionSonicwallResponse:
    """
    Provision SonicWall for the customer.
    Uses Graylog-Network instance for all Graylog operations.
    """
    # Set the Graylog context for this request - all downstream Graylog calls will use Graylog-Network
    set_graylog_context(GraylogContext.NETWORK)

    try:
        customer_integration_response = await get_customer_integration_response(
            provision_sonicwall_request.customer_code,
            session,
        )

        customer_integration = await find_customer_network_connector(
            provision_sonicwall_request.customer_code,
            provision_sonicwall_request.integration_name,
            customer_integration_response,
        )

        sonicwall_keys = extract_sonicwall_keys(customer_integration)

        return await provision_sonicwall(
            customer_details=SonicwallCustomerDetails(
                customer_code=provision_sonicwall_request.customer_code,
                customer_name=customer_integration.customer_name,
                tls_cert_file=sonicwall_keys["TLS_CERT_FILE"],
                tls_key_file=sonicwall_keys["TLS_KEY_FILE"],
                syslog_port=int(sonicwall_keys["SYSLOG_PORT"]),
                hot_data_retention=provision_sonicwall_request.hot_data_retention,
                index_replicas=provision_sonicwall_request.index_replicas,
            ),
            keys=ProvisionSonicwallKeys(**sonicwall_keys),
            session=session,
        )
    finally:
        # Always clear the context when done
        clear_graylog_context()
