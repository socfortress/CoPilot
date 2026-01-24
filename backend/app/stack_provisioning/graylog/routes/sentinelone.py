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
from app.stack_provisioning.graylog.schema.sentinelone import ProvisionSentinelOneKeys
from app.stack_provisioning.graylog.schema.sentinelone import ProvisionSentinelOneRequest
from app.stack_provisioning.graylog.schema.sentinelone import ProvisionSentinelOneResponse
from app.stack_provisioning.graylog.schema.sentinelone import SentinelOneCustomerDetails
from app.stack_provisioning.graylog.services.sentinelone import provision_sentinelone

stack_provisioning_graylog_sentinelone_router = APIRouter()


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


def extract_sentinelone_keys(
    customer_integration: CustomerNetworkConnectors,
) -> Dict[str, str]:
    """
    Extracts the authentication keys for SentinelOne integration from the given customer integration.

    Args:
        customer_integration (CustomerNetworkConnectors): The customer integration object.

    Returns:
        Dict[str, str]: A dictionary containing the authentication keys for SentinelOne integration.

    Raises:
        HTTPException: If no authentication keys are found for SentinelOne integration.
    """
    sentinelone_keys = {}
    for subscription in customer_integration.network_connectors_subscriptions:
        if subscription.network_connectors_service.service_name == "Sentinelone":
            for auth_key in subscription.network_connectors_keys:
                sentinelone_keys[auth_key.auth_key_name] = auth_key.auth_value
    if not sentinelone_keys:
        raise HTTPException(
            status_code=404,
            detail="No auth keys found for SentinelOne integration. Please create auth keys for SentinelOne network connector.",
        )
    return sentinelone_keys


@stack_provisioning_graylog_sentinelone_router.post(
    "/graylog/provision/sentinelone",
    response_model=ProvisionSentinelOneResponse,
    description="Provision SentinelOne for the customer.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_sentinelone_route(
    provision_sentinelone_request: ProvisionSentinelOneRequest,
    session: AsyncSession = Depends(get_db),
) -> ProvisionSentinelOneResponse:
    """
    Provision SentinelOne for the customer
    """
    customer_integration_response = await get_customer_integration_response(
        provision_sentinelone_request.customer_code,
        session,
    )

    customer_integration = await find_customer_network_connector(
        provision_sentinelone_request.customer_code,
        provision_sentinelone_request.integration_name,
        customer_integration_response,
    )

    sentinelone_keys = extract_sentinelone_keys(customer_integration)

    return await provision_sentinelone(
        customer_details=SentinelOneCustomerDetails(
            customer_code=provision_sentinelone_request.customer_code,
            customer_name=customer_integration.customer_name,
            tls_cert_file=sentinelone_keys["TLS_CERT_FILE"],
            tls_key_file=sentinelone_keys["TLS_KEY_FILE"],
            syslog_port=int(sentinelone_keys["SYSLOG_PORT"]),
            hot_data_retention=provision_sentinelone_request.hot_data_retention,
            index_replicas=provision_sentinelone_request.index_replicas,
        ),
        keys=ProvisionSentinelOneKeys(**sentinelone_keys),
        session=session,
    )
