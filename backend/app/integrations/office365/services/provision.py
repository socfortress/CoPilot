from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.integrations.office365.schema.provision import ProvisionOffice365Request
from app.integrations.office365.schema.provision import ProvisionOffice365Response, ProvisionOffice365AuthKeys
from app.integrations.alert_escalation.services.general_alert import create_alert
from app.integrations.routes import get_customer_integrations_by_customer_code, find_customer_integration
from app.integrations.schema import CustomerIntegrationsResponse, CustomerIntegrations
from typing import Dict
from app.connectors.wazuh_manager.utils.universal import restart_service
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request

async def get_wazuh_configuration() -> str:
    endpoint = "manager/configuration"
    params = {"raw": True}
    response = await send_get_request(endpoint=endpoint, params=params)
    return response['data']

async def provision_office365(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys, session: AsyncSession) -> ProvisionOffice365Response:
    logger.info(f"Provisioning Office365 integration for customer {customer_code}.")
    # Get Wazuh configuration
    wazuh_config = await get_wazuh_configuration()

    logger.info(f"Wazuh configuration: {wazuh_config}")


