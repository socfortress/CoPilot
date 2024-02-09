from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.db_session import get_db
from app.integrations.alert_creation.general.schema.alert import CreateAlertRequest
from app.integrations.alert_creation.general.schema.alert import CreateAlertResponse
from app.integrations.alert_creation.general.services.alert import create_alert
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)

general_alerts_router = APIRouter()


async def is_rule_id_valid(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession,
) -> bool:
    """
    Checks if the given rule ID is valid for the specified customer.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the rule ID and customer information.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the rule ID is valid for the customer, False otherwise.
    """
    logger.info(
        f"Checking if rule_id: {create_alert_request.rule_id} is valid for customer: {create_alert_request.agent_labels_customer}",
    )

    result = await session.execute(
        select(AlertCreationSettings).where(
            AlertCreationSettings.customer_code == create_alert_request.agent_labels_customer,
        ),
    )
    settings = result.scalars().first()

    if settings and str(create_alert_request.rule_id) in (settings.excluded_wazuh_rules or "").split(","):
        return False

    return True


async def is_customer_code_valid(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession,
) -> bool:
    """
    Checks if the customer code provided in the create_alert_request is valid.

    Args:
        create_alert_request (CreateAlertRequest): The request object containing the alert creation details.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the customer code is valid, False otherwise.
    """
    logger.info(
        f"Checking if customer_code: {create_alert_request.agent_labels_customer} is valid.",
    )

    result = await session.execute(
        select(AlertCreationSettings).where(
            AlertCreationSettings.customer_code == create_alert_request.agent_labels_customer,
        ),
    )
    settings = result.scalars().first()

    if settings:
        return True

    return False


@general_alerts_router.post(
    "",
    response_model=CreateAlertResponse,
    description="Create a general alert in IRIS.",
)
async def create_general_alert(
    create_alert_request: CreateAlertRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Create a general alert in IRIS. This route is to be used with Praeco.

    Args:
        create_alert_request (CreateAlertRequest): The request payload for creating the alert.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the customer code or rule ID is invalid.

    Returns:
        CreateAlertResponse: The response containing the created alert.
    """
    logger.info(f"create_alert_request: {create_alert_request.dict()}")

    if await is_customer_code_valid(create_alert_request, session) is False:
        logger.info(
            f"Invalid customer_code: {create_alert_request.agent_labels_customer}",
        )
        raise HTTPException(status_code=200, detail="Invalid customer_code.")

    if await is_rule_id_valid(create_alert_request, session) is False:
        logger.info(f"Invalid rule_id: {create_alert_request.rule_id}")
        raise HTTPException(status_code=200, detail="Invalid rule_id.")

    logger.info(f"Rule id is valid: {create_alert_request.rule_id}")
    return await create_alert(create_alert_request, session=session)
