from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.customer_provisioning.schema.decommission import DecommissionCustomerResponse
from app.customer_provisioning.services.decommission import decomission_wazuh_customer
from app.db.db_session import get_db
from app.db.universal_models import CustomersMeta

# App specific imports


customer_decommissioning_router = APIRouter()


async def check_customermeta_exists(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomersMeta:
    """
    Check if a customer exists in the database.

    Args:
        customer_code (str): The customer code of the customer to check.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomersMeta: The customer object if found.

    Raises:
        HTTPException: If the customer is not found.
    """
    logger.info(f"Checking if customer {customer_code} exists")
    result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = result.scalars().first()

    if not customer_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Customer: {customer_code} not found. Please create the customer first.",
        )

    return customer_meta


@customer_decommissioning_router.post(
    "/decommission",
    response_model=DecommissionCustomerResponse,
    description="Decommission Customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def decommission_customer_route(
    _customer: CustomersMeta = Depends(check_customermeta_exists),
    session: AsyncSession = Depends(get_db),
):
    """
    Decommission Customer Route

    This route is used to decommission a customer. It requires the user to have either the "admin" or "analyst" scope.

    Parameters:
    - _customer (CustomersMeta): The customer metadata.
    - session (AsyncSession): The database session.

    Returns:
    - DecommissionCustomerResponse: The response model containing the decommissioned customer information.
    """
    logger.info("Decommissioning customer")
    customer_decommission = await decomission_wazuh_customer(_customer, session=session)
    return customer_decommission
