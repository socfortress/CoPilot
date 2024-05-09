from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.stack_provisioning.graylog.schema.decommission import (
    DecommissionNetworkContentPackRequest,
)
from app.stack_provisioning.graylog.schema.decommission import (
    DecommissionNetworkContentPackResponse,
)
from app.stack_provisioning.graylog.services.decommission import (
    decommission_network_connector,
)

stack_decommissioning_graylog_router = APIRouter()


async def get_network_connectors_meta_by_customer_code_and_connector_name(
    customer_code: str,
    network_connector_name: str,
    session: AsyncSession,
) -> CustomerNetworkConnectorsMeta:
    """
    Retrieves the network connector meta by customer code and connector name.

    Args:
        customer_code (str): The code of the customer.
        network_connector_name (str): The name of the network connector.
        session (AsyncSession): The async session object for database operations.

    Returns:
        CustomerNetworkConnectorsMeta: The network connector meta for the customer.
    """
    stmt = select(CustomerNetworkConnectorsMeta).filter(
        CustomerNetworkConnectorsMeta.customer_code == customer_code,
        CustomerNetworkConnectorsMeta.network_connector_name == network_connector_name,
    )
    result = await session.execute(stmt)
    return result.scalars().first()


@stack_decommissioning_graylog_router.post(
    "/graylog/decommission/network_connector",
    response_model=DecommissionNetworkContentPackResponse,
    description="Decommission the Network Connector for the customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def decommission_network_connector_route(
    decommission_request: DecommissionNetworkContentPackRequest,
    session: AsyncSession = Depends(get_db),
) -> DecommissionNetworkContentPackResponse:
    """
    Decommission the Network Connector for the customer
    """
    logger.info(f"Decommissioning the Network Connector for {decommission_request.network_connector.name}...")
    network_connector_details = await get_network_connectors_meta_by_customer_code_and_connector_name(
        decommission_request.customer_code,
        decommission_request.network_connector.name,
        session,
    )
    if network_connector_details is None:
        raise HTTPException(
            status_code=404,
            detail=f"Network Connector {decommission_request.network_connector.name} not found for customer {decommission_request.customer_code}",
        )
    return await decommission_network_connector(network_connector_details, session)
