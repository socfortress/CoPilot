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

async def office365_template_with_api_type(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> str:
    """
    Returns a configured Office365 template for Wazuh.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        tenant_id (str): Office365 Tenant ID.
        client_id (str): Office365 Client ID.
        client_secret (str): Office365 Client Secret.
        api_type (str): The type of Office365 API.

    Returns:
        str: The Office365 template configured with the given parameters.
    """

    template = f"""
    <ossec_config>
    <office365>
        <enabled>yes</enabled>
        <interval>1m</interval>
        <curl_max_size>5M</curl_max_size>
        <only_future_events>yes</only_future_events>
        <!-- Office365 Integration For {customer_code} -->
        <api_auth>
            <tenant_id>{provision_office365_auth_keys.TENANT_ID}</tenant_id>
            <client_id>{provision_office365_auth_keys.CLIENT_ID}</client_id>
            <client_secret>{provision_office365_auth_keys.CLIENT_SECRET}</client_secret>
            <api_type>{provision_office365_auth_keys.API_TYPE}</api_type>
        </api_auth>
        <subscriptions>
            <subscription>Audit.SharePoint</subscription>
            <subscription>Audit.Exchange</subscription>
            <subscription>DLP.ALL</subscription>
            <subscription>Audit.General</subscription>
            <subscription>Audit.AzureActiveDirectory</subscription>
        </subscriptions>
    </office365>
    </ossec_config>
    """

    return template

async def office365_template(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> str:
    """
    Returns a configured Office365 template for Wazuh.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        tenant_id (str): Office365 Tenant ID.
        client_id (str): Office365 Client ID.
        client_secret (str): Office365 Client Secret.
        api_type (str): The type of Office365 API.

    Returns:
        str: The Office365 template configured with the given parameters.
    """

    template = f"""
    <ossec_config>
    <office365>
        <enabled>yes</enabled>
        <interval>1m</interval>
        <curl_max_size>5M</curl_max_size>
        <only_future_events>yes</only_future_events>
        <!-- Office365 Integration For {customer_code} -->
        <api_auth>
            <tenant_id>{provision_office365_auth_keys.TENANT_ID}</tenant_id>
            <client_id>{provision_office365_auth_keys.CLIENT_ID}</client_id>
            <client_secret>{provision_office365_auth_keys.CLIENT_SECRET}</client_secret>
        </api_auth>
        <subscriptions>
            <subscription>Audit.SharePoint</subscription>
            <subscription>Audit.Exchange</subscription>
            <subscription>DLP.ALL</subscription>
            <subscription>Audit.General</subscription>
            <subscription>Audit.AzureActiveDirectory</subscription>
        </subscriptions>
    </office365>
    </ossec_config>
    """

    return template

async def append_office365_template(wazuh_config: str, office365_template: str) -> str:
    """
    Appends the Office365 template to the Wazuh configuration.

    Args:
        wazuh_config (str): The current Wazuh configuration.
        office365_template (str): The Office365 template to append.

    Returns:
        str: The Wazuh configuration with the Office365 template appended.
    """

    return wazuh_config + office365_template

# async def update_wazuh_configuration(wazuh_config: str) -> None:
#     """
#     Updates the Wazuh configuration.

#     Args:
#         wazuh_config (str): The Wazuh configuration in string format.
#     """
#     endpoint = "manager/configuration"
#     # Convert the string config to bytes
#     data = wazuh_config.encode('utf-8')
#     response = await send_put_request(endpoint=endpoint, data=data, binary_data=True)
#     logger.info(f"Response from Wazuh: {response}")
#     response_data = response['data']
#     return response_data

async def update_wazuh_configuration(wazuh_config: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys) -> None:
    """
    Updates the Wazuh configuration. If it fails, remove the <api_type> tag and retry.

    Args:
        wazuh_config (str): The Wazuh configuration in string format.
        provision_office365_auth_keys (ProvisionOffice365AuthKeys): The Office365 authentication keys.
    """
    endpoint = "manager/configuration"
    data = wazuh_config.encode('utf-8')

    try:
        # First attempt to update configuration
        response = await send_put_request(endpoint=endpoint, data=data, binary_data=True)
        if response.get('success') and response['data'].get('error') == 0:
            logger.info("Wazuh configuration updated successfully.")
            return
        else:
            logger.error("Failed to update Wazuh configuration. Error: {}".format(response))

    except Exception as e:
        logger.error(f"Exception occurred during Wazuh configuration update: {e}")

    # Remove <api_type> tag and retry
    api_type_tag = f"<api_type>{provision_office365_auth_keys.API_TYPE}</api_type>"
    modified_wazuh_config = wazuh_config.replace(api_type_tag, "")
    data = modified_wazuh_config.encode('utf-8')

    try:
        response = await send_put_request(endpoint=endpoint, data=data, binary_data=True)
        if response.get('success') and response['data'].get('error') == 0:
            logger.info("Wazuh configuration updated successfully after removing <api_type> tag.")
        else:
            logger.error("Failed to update Wazuh configuration after removing <api_type> tag. Error: {}".format(response))

    except Exception as e:
        logger.error(f"Exception occurred during retry of Wazuh configuration update: {e}")


async def check_if_office365_is_already_provisioned(customer_code: str, wazuh_config: str) -> bool:
    """
    If the string "Office365 Integration For {customer_code}" is found in the Wazuh configuration, return True.

    Args:
        customer_code (str): The customer code.
        wazuh_config (str): The Wazuh configuration in string format.

    Returns:
        bool: True if the Office365 integration is already provisioned, False otherwise.
    """
    if f"Office365 Integration For {customer_code}" in wazuh_config:
        raise HTTPException(status_code=400, detail=f"Office365 integration already provisioned for customer {customer_code}.")



async def provision_office365(customer_code: str, provision_office365_auth_keys: ProvisionOffice365AuthKeys, session: AsyncSession) -> ProvisionOffice365Response:
    logger.info(f"Provisioning Office365 integration for customer {customer_code}.")
    # Get Wazuh configuration
    wazuh_config = await get_wazuh_configuration()

    # Check if Office365 is already provisioned
    await check_if_office365_is_already_provisioned(customer_code, wazuh_config)

    logger.info(f"Wazuh configuration: {wazuh_config}")

    # Create Office365 template
    office365_templated = await office365_template_with_api_type(customer_code, provision_office365_auth_keys)

    logger.info(f"Office365 template: {office365_templated}")

    # Append Office365 template to Wazuh configuration
    wazuh_config = await append_office365_template(wazuh_config, office365_templated)

    logger.info(f"New Wazuh configuration: {wazuh_config}")

    # Update Wazuh configuration
    await update_wazuh_configuration(wazuh_config, provision_office365_auth_keys)


