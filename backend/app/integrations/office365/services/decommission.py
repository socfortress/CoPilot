import os
import xml.etree.ElementTree as ET
from typing import Optional

import aiofiles
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.connectors.wazuh_manager.utils.universal import send_put_request
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)

# Written next to this module the same way `provision.get_wazuh_configuration` does, so both halves
# of the lifecycle work on the manager's live configuration rather than a stale copy.
WAZUH_CONFIG_FILE_NAME = "wazuh_decommission_config.xml"


async def get_office365_tenant_id(
    customer_code: str,
    session: AsyncSession,
    instance_name: Optional[str] = None,
) -> Optional[str]:
    """
    Read the Microsoft 365 tenant ID of one of a customer's Office365 instances.

    Must be called *before* the integration's subscriptions and auth keys are deleted — afterwards
    there is nothing left to say which tenant the Wazuh manager should stop polling.
    """
    instance_clause = (
        CustomerIntegrations.instance_name.is_(None) if instance_name is None else CustomerIntegrations.instance_name == instance_name
    )
    result = await session.execute(
        select(IntegrationAuthKeys.auth_value)
        .join(
            IntegrationSubscription,
            IntegrationAuthKeys.subscription_id == IntegrationSubscription.id,
        )
        .join(
            CustomerIntegrations,
            IntegrationSubscription.customer_id == CustomerIntegrations.id,
        )
        .join(
            IntegrationService,
            IntegrationSubscription.integration_service_id == IntegrationService.id,
        )
        .where(
            CustomerIntegrations.customer_code == customer_code,
            IntegrationService.service_name == "Office365",
            IntegrationAuthKeys.auth_key_name == "TENANT_ID",
            instance_clause,
        ),
    )
    return result.scalars().first()


def remove_api_auth_block(wazuh_config: str, tenant_id: str) -> Optional[str]:
    """
    Strip one tenant's `<api_auth>` block out of the manager configuration.

    Returns the new configuration, or ``None`` when the tenant was not configured — an already-clean
    manager is not an error, it just means there is nothing to push.

    When the removed block was the last one, the whole `<office365>` element goes too: Wazuh treats
    an `<office365>` block with no `<api_auth>` as invalid and would refuse the configuration.
    """
    try:
        root = ET.fromstring(wazuh_config)
    except ET.ParseError as e:
        logger.error(f"Could not parse the Wazuh configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not parse ossec.conf. Remove the Office365 api_auth block manually.",
        )

    removed = False
    for office365_block in root.findall("office365"):
        for api_auth in list(office365_block.findall("api_auth")):
            tenant_element = api_auth.find("tenant_id")
            if tenant_element is not None and (tenant_element.text or "").strip() == tenant_id:
                office365_block.remove(api_auth)
                removed = True

        if removed and not office365_block.findall("api_auth"):
            root.remove(office365_block)

    if not removed:
        return None

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


async def decommission_office365_tenant(
    customer_code: str,
    tenant_id: str,
) -> None:
    """
    Stop the Wazuh manager collecting from one Microsoft 365 tenant.

    Deleting the integration in CoPilot used to leave the `<api_auth>` block in place, so the
    manager kept polling a tenant nobody could see any more. With several tenants per customer that
    matters more: the surviving tenants' blocks must be left exactly as they are, which is why this
    edits the XML rather than dropping the whole `<office365>` element.
    """
    endpoint = "/manager/configuration"
    response = await send_get_request(endpoint=endpoint, params={"raw": True})
    wazuh_config = response["data"]

    updated_config = remove_api_auth_block(wazuh_config, tenant_id)
    if updated_config is None:
        logger.info(f"Microsoft 365 tenant {tenant_id} is not configured on the Wazuh manager; nothing to remove.")
        return

    # Keep a copy on disk for the same reason provisioning does: it is what an operator looks at
    # when the manager rejects a configuration.
    dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    async with aiofiles.open(os.path.join(dir_path, WAZUH_CONFIG_FILE_NAME), "w") as f:
        await f.write(updated_config)

    response = await send_put_request(
        endpoint=endpoint,
        data=updated_config.encode("utf-8"),
        binary_data=True,
    )
    if not (response.get("success") and response.get("data", {}).get("error") == 0):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove the Office365 api_auth block from ossec.conf: {response}",
        )

    logger.info(f"Removed Microsoft 365 tenant {tenant_id} from the Wazuh manager configuration; restarting it.")
    await send_put_request(endpoint="/manager/restart", data=None)
