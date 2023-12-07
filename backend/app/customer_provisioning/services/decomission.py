import requests
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.universal_models import CustomersMeta
from app.customer_provisioning.schema.decomission import DecomissionCustomerResponse
from app.customer_provisioning.services.wazuh_manager import gather_wazuh_agents, delete_wazuh_agents, delete_wazuh_groups

async def decomission_wazuh_customer(customer_meta: CustomersMeta, session: AsyncSession) -> DecomissionCustomerResponse:
    logger.info(f"Decomissioning customer {customer_meta.customer_name}")

    # Delete the Wazuh Agents
    agents = await gather_wazuh_agents(customer_meta.customer_code)
    agents_deleted = await delete_wazuh_agents(agents)
    logger.info(f"Deleted {agents_deleted} agents for customer {customer_meta.customer_name}")

    # Delete Wazuh Group
    groups_deleted = await delete_wazuh_groups(customer_meta.customer_code)



    return DecomissionCustomerResponse(
        message=f"Customer {customer_meta.customer_name} decomissioned successfully.",
        success=True,
    )
