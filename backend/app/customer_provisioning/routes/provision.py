from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.connectors.grafana.schema.dashboards import Office365Dashboard
from app.connectors.grafana.schema.dashboards import WazuhDashboard
from app.customer_provisioning.schema.provision import CustomerProvisionResponse
from app.customer_provisioning.schema.provision import CustomersMetaResponse
from app.customer_provisioning.schema.provision import CustomerSubsctipion
from app.customer_provisioning.schema.provision import GetDashboardsResponse
from app.customer_provisioning.schema.provision import GetSubscriptionsResponse
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.services.provision import provision_wazuh_customer
from app.db.db_session import get_session
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta

customer_provisioning_router = APIRouter()


def get_available_dashboards():
    try:
        wazuh_dashboards = [dashboard.name for dashboard in WazuhDashboard]
        office365_dashboards = [dashboard.name for dashboard in Office365Dashboard]
        return wazuh_dashboards + office365_dashboards
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available dashboards: {e}")


def get_available_subscriptions():
    try:
        return [subscription.value for subscription in CustomerSubsctipion]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available subscriptions: {e}")


async def check_customer_exists(customer_name: str, session: AsyncSession = Depends(get_session)) -> Customers:
    logger.info(f"Checking if customer {customer_name} exists")
    result = await session.execute(select(Customers).filter(Customers.customer_name == customer_name))
    customer = result.scalars().first()

    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer: {customer_name} not found. Please create the customer first.")

    return customer


# Get the customermeta based on the customer name
@customer_provisioning_router.get(
    "/provision/{customer_name}",
    response_model=CustomersMetaResponse,
    description="Get Customer Meta",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_meta(customer_name: str, session: AsyncSession = Depends(get_session)):
    logger.info(f"Getting customer meta for customer {customer_name}")
    result = await session.execute(select(CustomersMeta).filter(CustomersMeta.customer_name == customer_name))
    customer_meta = result.scalars().first()

    if not customer_meta:
        raise HTTPException(
            status_code=404, detail=f"Customer meta not found for customer: {customer_name}. Please provision the customer first.",
        )

    return CustomersMetaResponse(message="Customer meta retrieved successfully", success=True, customer_meta=customer_meta)


@customer_provisioning_router.post(
    "/provision",
    response_model=CustomerProvisionResponse,
    description="Provision New Customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_customer_route(
    request: ProvisionNewCustomer = Body(...),
    _customer: Customers = Depends(check_customer_exists),
    session: AsyncSession = Depends(get_session),
):
    logger.info("Provisioning new customer")
    customer_provision = await provision_wazuh_customer(request, session=session)
    return customer_provision


@customer_provisioning_router.get(
    "/provision/dashboards",
    response_model=GetDashboardsResponse,
    description="Return the list of dashboards available for provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_dashboards_route():
    logger.info("Getting list of dashboards")
    available_dashboards = get_available_dashboards()
    return GetDashboardsResponse(available_dashboards=available_dashboards, success=True, message="Dashboards retrieved successfully")


@customer_provisioning_router.get(
    "/provision/subscriptions",
    response_model=GetSubscriptionsResponse,
    description="Return the list of subscriptions available for provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_subscriptions_route():
    logger.info("Getting list of subscriptions")
    available_subscriptions = get_available_subscriptions()
    return GetSubscriptionsResponse(
        available_subscriptions=available_subscriptions,
        success=True,
        message="Subscriptions retrieved successfully",
    )
