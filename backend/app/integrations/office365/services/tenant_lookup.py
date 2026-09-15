from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.models.customer_integration_settings import IntegrationAuthKeys
from app.integrations.models.customer_integration_settings import IntegrationService
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)


async def resolve_customer_code_from_office365_tenant(
    tenant_id: str,
    session: AsyncSession,
) -> Optional[str]:
    """
    Map a Microsoft 365 organization ID to the CoPilot customer that owns it.

    Office365 alerts carry the tenant GUID where every other source carries a customer code (the
    `incident_management_customercodefieldname` row for the `office365` source points at
    `data_office365_OrganizationId`), so the ingest path has to translate it. It used to do that
    through `custom_alert_creation_settings.office365_organization_id`, a single column that can
    only ever name one tenant — which is exactly why a customer could not have a second one.

    The configured tenants are already on record as the `TENANT_ID` auth key of each Office365
    integration instance, so reading them back needs no new table and stays correct however many
    tenants a customer has. The legacy column is still consulted first by the callers, so a
    deployment that has not re-provisioned anything behaves exactly as before.
    """
    if not tenant_id:
        return None

    result = await session.execute(
        select(CustomerIntegrations.customer_code)
        .join(
            IntegrationSubscription,
            CustomerIntegrations.id == IntegrationSubscription.customer_id,
        )
        .join(
            IntegrationService,
            IntegrationSubscription.integration_service_id == IntegrationService.id,
        )
        .join(
            IntegrationAuthKeys,
            IntegrationAuthKeys.subscription_id == IntegrationSubscription.id,
        )
        .where(
            IntegrationService.service_name == "Office365",
            IntegrationAuthKeys.auth_key_name == "TENANT_ID",
            IntegrationAuthKeys.auth_value == tenant_id,
        ),
    )
    customer_code = result.scalars().first()

    if customer_code:
        logger.info(f"Resolved Microsoft 365 tenant {tenant_id} to customer {customer_code}.")

    return customer_code
