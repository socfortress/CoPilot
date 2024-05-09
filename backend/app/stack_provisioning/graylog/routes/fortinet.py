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
from app.network_connectors.schema import CustomerNetworkConnectors
from app.network_connectors.schema import CustomerNetworkConnectorsResponse
from app.stack_provisioning.graylog.schema.fortinet import FortinetCustomerDetails
from app.stack_provisioning.graylog.schema.fortinet import ProvisionFortinetKeys
from app.stack_provisioning.graylog.schema.fortinet import ProvisionFortinetRequest
from app.stack_provisioning.graylog.schema.fortinet import ProvisionFortinetResponse
from app.stack_provisioning.graylog.services.fortinet import provision_fortinet

stack_provisioning_graylog_fortinet_router = APIRouter()


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
        CustomerIntegrationsResponse: The integration response for the customer.

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


def extract_fortinet_keys(
    customer_integration: CustomerNetworkConnectors,
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
    fortinet_keys = {}
    for subscription in customer_integration.network_connectors_subscriptions:
        if subscription.network_connectors_service.service_name == "Fortinet":
            for auth_key in subscription.network_connectors_keys:
                fortinet_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not fortinet_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for Fortinet integration. Please create auth keys for Fortinet network connector.",
        )
    return fortinet_keys


@stack_provisioning_graylog_fortinet_router.post(
    "/graylog/provision/fortinet",
    response_model=ProvisionFortinetResponse,
    description="Provision Fortinet for the customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_fortinet_route(
    provision_fortinet_request: ProvisionFortinetRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionFortinetResponse:
    """
    Provision Fortinet for the customer
    """
    customer_integration_response = await get_customer_integration_response(
        provision_fortinet_request.customer_code,
        session,
    )

    customer_integration = await find_customer_network_connector(
        provision_fortinet_request.customer_code,
        provision_fortinet_request.integration_name,
        customer_integration_response,
    )

    fortinet_keys = extract_fortinet_keys(customer_integration)

    if provision_fortinet_request.tcp_enabled and provision_fortinet_request.udp_enabled:
        raise HTTPException(
            status_code=400,
            detail="Both TCP and UDP are enabled. Please choose one of them.",
        )
    elif provision_fortinet_request.tcp_enabled:
        protocol_type = "TCP"
    elif provision_fortinet_request.udp_enabled:
        protocol_type = "UDP"
    else:
        raise HTTPException(
            status_code=400,
            detail="Either TCP or UDP should be enabled.",
        )

    return await provision_fortinet(
        customer_details=FortinetCustomerDetails(
            customer_code=provision_fortinet_request.customer_code,
            customer_name=customer_integration.customer_name,
            protocal_type=protocol_type,
            syslog_port=int(fortinet_keys["SYSLOG_PORT"]),
            hot_data_retention=provision_fortinet_request.hot_data_retention,
            index_replicas=provision_fortinet_request.index_replicas,
        ),
        keys=ProvisionFortinetKeys(**fortinet_keys),
        session=session,
    )
