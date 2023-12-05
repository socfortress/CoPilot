import json
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.connectors.services import ConnectorServices
from app.customer_provisioning.schema.provision import ProvisionNewCustomer
from app.customer_provisioning.services.provision_wazuh import provision_wazuh_customer
from app.db.db_session import get_session
from app.db.universal_models import Customers

# App specific imports


customer_provisioning_router = APIRouter()


async def check_customer_exists(customer_name: str, session: AsyncSession = Depends(get_session)) -> Customers:
    logger.info(f"Checking if customer {customer_name} exists")
    result = await session.execute(select(Customers).filter(Customers.customer_name == customer_name))
    customer = result.scalars().first()

    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer: {customer_name} not found. Please create the customer first.")

    return customer


@customer_provisioning_router.post(
    "/provision",
    # response_model=GrafanaDashboardResponse,
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

    return {"message": "Provisioning new customer"}
