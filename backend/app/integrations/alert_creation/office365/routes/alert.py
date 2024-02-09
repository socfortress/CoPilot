# from app.alerts.office365.services.threat_intel import create_threat_intel_alert
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.alert_creation.office365.schema.exchange import (
    Office365ExchangeAlertBase,
)
from app.integrations.alert_creation.office365.schema.exchange import (
    Office365ExchangeAlertRequest,
)
from app.integrations.alert_creation.office365.schema.exchange import (
    Office365ExchangeAlertResponse,
)
from app.integrations.alert_creation.office365.schema.exchange import (
    ValidOffice365Workloads,
)
from app.integrations.alert_creation.office365.schema.threat_intel import (
    Office365ThreatIntelAlertRequest,
)
from app.integrations.alert_creation.office365.schema.threat_intel import (
    Office365ThreatIntelAlertResponse,
)
from app.integrations.alert_creation.office365.services.exchange import (
    create_exchange_alert,
)
from app.integrations.alert_creation.office365.services.threat_intel import (
    create_threat_intel_alert,
)
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)

office365_alerts_router = APIRouter()


async def is_office365_organization_id_valid(
    create_alert_request: Office365ExchangeAlertBase,
    session: AsyncSession,
) -> bool:
    """
    Checks if the given organization ID is valid for the specified customer.

    Args:
        create_alert_request (Office365ExchangeAlertRequest): The request object containing the organization ID and customer information.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the organization ID is valid for the customer, False otherwise.
    """
    logger.info(
        f"Checking if organization_id: {create_alert_request.data_office365_OrganizationId} is valid for customer: {create_alert_request.data_office365_OrganizationId}",
    )

    result = await session.execute(
        select(AlertCreationSettings).where(
            AlertCreationSettings.office365_organization_id == create_alert_request.data_office365_OrganizationId,
        ),
    )
    settings = result.scalars().first()
    if settings is None:
        raise HTTPException(
            status_code=400,
            detail="Office365 organization ID is not valid, make sure to provision the customer.",
        )

    return True


@office365_alerts_router.post(
    "/exchange",
    response_model=Office365ExchangeAlertResponse,
    description="Create an office365 exchange alert in IRIS.",
)
async def create_office365_exchange_alert(
    create_alert_request: Office365ExchangeAlertRequest,
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"create_alert_request: {create_alert_request}")
    if create_alert_request.data_office365_Workload not in [workload.value for workload in ValidOffice365Workloads]:
        logger.info(f"Invalid workload: {create_alert_request.data_office365_Workload}")
        raise HTTPException(status_code=400, detail="Invalid workload")
    logger.info(f"Workload is valid: {create_alert_request.data_office365_Workload}")
    await is_office365_organization_id_valid(create_alert_request, session)
    return await create_exchange_alert(alert=create_alert_request, session=session)


@office365_alerts_router.post(
    "/threat_intel",
    response_model=Office365ThreatIntelAlertResponse,
    description="Create an office365 threat intel alert in IRIS.",
)
async def create_office365_threat_intel_alert(
    create_alert_request: Office365ThreatIntelAlertRequest,
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"create_alert_request: {create_alert_request}")
    if create_alert_request.data_office365_Workload not in [workload.value for workload in ValidOffice365Workloads]:
        logger.info(f"Invalid workload: {create_alert_request.data_office365_Workload}")
        raise HTTPException(status_code=400, detail="Invalid workload")
    logger.info(f"Workload is valid: {create_alert_request.data_office365_Workload}")
    await is_office365_organization_id_valid(create_alert_request, session)
    return await create_threat_intel_alert(alert=create_alert_request, session=session)
