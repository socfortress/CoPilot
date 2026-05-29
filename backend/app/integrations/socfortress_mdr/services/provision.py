from loguru import logger
from sqlalchemy import and_
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.socfortress_mdr.schema.provision import (
    ProvisionSOCFortressMDRResponse,
)

INTEGRATION_NAME = "SOCFortress MDR"


async def update_customer_integration_table(
    customer_code: str,
    session: AsyncSession,
) -> None:
    """
    Set `deployed = True` on the customer's "SOCFortress MDR" integration row.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession): The async database session.
    """
    logger.info(f"Marking SOCFortress MDR integration deployed for customer {customer_code}")
    await session.execute(
        update(CustomerIntegrations)
        .where(
            and_(
                CustomerIntegrations.customer_code == customer_code,
                CustomerIntegrations.integration_service_name == INTEGRATION_NAME,
            ),
        )
        .values(deployed=True),
    )
    await session.commit()


async def provision_socfortress_mdr(
    customer_code: str,
    collector_uuid: str,
    session: AsyncSession,
) -> ProvisionSOCFortressMDRResponse:
    """
    Provision the SOCFortress MDR integration for a customer.

    Unlike most integrations there is no Graylog/Grafana infrastructure to stand
    up here — the MDR server and the customer's collector already exist. The MDR
    server pulls alerts on demand via the collector. Provisioning therefore just
    records the COLLECTOR_UUID (already validated by the route) and marks the
    integration deployed so alert forwarding is enabled for this customer.

    Args:
        customer_code (str): The customer code.
        collector_uuid (str): The MDR collector UUID for this customer.
        session (AsyncSession): The async database session.

    Returns:
        ProvisionSOCFortressMDRResponse
    """
    logger.info(
        f"Provisioning SOCFortress MDR integration for customer {customer_code} " f"(collector {collector_uuid})",
    )
    await update_customer_integration_table(customer_code, session)
    return ProvisionSOCFortressMDRResponse(
        success=True,
        message="SOCFortress MDR integration provisioned successfully.",
    )
